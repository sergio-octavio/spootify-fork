"""Descarga de canciones desde YouTube Music con yt-dlp.

Alternativa a Zotify: no necesita cuenta Spotify Premium y encuentra canciones
que Spotify ha retirado de su catálogo. Para cada track del índice:

1. Busca en YouTube Music (pestaña "Canciones", que devuelve los audios
   oficiales "- Topic" con la carátula del álbum) y, si no hay suerte, en
   YouTube normal.
2. Elige el mejor candidato comparando duración y título con los metadatos
   de Spotify, y penaliza versiones en directo, covers, karaoke, etc.
3. Descarga la mejor pista de audio **sin recomprimir** (Opus o AAC tal cual
   los sirve YouTube), le pone los tags de Spotify y guarda `cover.jpg`.

La salida usa el mismo `DownloadResult` que el wrapper de Zotify, así que el
resto del pipeline (estado, reintentos, servidor web) no cambia.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from .artwork import album_dir_for
from .downloader import DownloadResult

logger = logging.getLogger(__name__)

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav", ".webm"}

# Palabras que indican que el vídeo NO es la grabación de estudio. Solo
# penalizan si no aparecen también en el título original de Spotify.
_BAD_WORDS = [
    "live", "en vivo", "en directo", "concert", "cover", "karaoke",
    "instrumental", "remix", "sped up", "slowed", "reverb", "8d",
    "nightcore", "acoustic", "acústico", "lyrics video", "letra", "tutorial",
    "reaction", "1 hour", "1 hora", "extended",
]

_RETRIABLE_RE = re.compile(
    r"timed? ?out|connection|temporarily|network|HTTP Error 5\d\d|HTTP Error 429|"
    r"rate.?limit|Sign in to confirm",
    re.IGNORECASE,
)
_UNAVAILABLE_RE = re.compile(
    r"Video unavailable|Private video|not available|copyright|removed|"
    r"blocked it in your country",
    re.IGNORECASE,
)


@dataclass
class Candidate:
    url: str
    title: str
    channel: str
    duration: float | None
    from_music: bool
    score: float = 0.0


# --- utilidades de texto ----------------------------------------------------

def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if len(t) > 1}


def _strip_feat(title: str) -> str:
    # "Song (feat. X)" / "Song - Remastered 2011" → "Song"
    title = re.sub(r"\s*[\(\[](feat|ft|with)\.?[^\)\]]*[\)\]]", "", title, flags=re.I)
    title = re.sub(r"\s+-\s+.*(remaster|version|edit|mix).*$", "", title, flags=re.I)
    return title.strip()


def safe_filename(text: str, max_len: int = 120) -> str:
    text = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", text or "").strip().strip(".")
    return (text or "Desconocido")[:max_len].rstrip()


def build_query(info: dict) -> str:
    artists = info.get("artists") or []
    main_artist = artists[0] if artists else ""
    title = _strip_feat(info.get("name", ""))
    return f"{main_artist} {title}".strip()


# --- scoring ----------------------------------------------------------------

def score_candidate(cand: Candidate, info: dict) -> float:
    """Puntúa un resultado de búsqueda. Más alto = mejor. <0 = descartable."""
    want_title = _strip_feat(info.get("name", ""))
    artists = info.get("artists") or []
    want_dur = (info.get("duration_ms") or 0) / 1000 or None

    title_tok = _tokens(want_title)
    cand_tok = _tokens(f"{cand.title} {cand.channel}")
    score = 0.0

    # Coincidencia del título.
    if title_tok:
        overlap = len(title_tok & cand_tok) / len(title_tok)
        score += 40 * overlap
        if overlap < 0.5:
            score -= 30

    # Coincidencia del artista principal (en título o canal).
    if artists:
        art_tok = _tokens(artists[0])
        if art_tok and art_tok <= cand_tok:
            score += 25
        elif art_tok & cand_tok:
            score += 10

    # Duración: el mejor indicador de que es la misma grabación.
    if want_dur and cand.duration:
        diff = abs(cand.duration - want_dur)
        if diff <= 3:
            score += 30
        elif diff <= 10:
            score += 15
        elif diff <= 30:
            score -= 5
        else:
            score -= 40

    # Versiones que no son la de estudio.
    original = _norm(info.get("name", ""))
    cand_norm = _norm(cand.title)
    for word in _BAD_WORDS:
        if f" {word} " in f" {cand_norm} " and f" {word} " not in f" {original} ":
            score -= 25

    # YouTube Music "Canciones" y canales "- Topic" son audio oficial.
    if cand.from_music:
        score += 15
    if cand.channel.endswith(" - Topic"):
        score += 10
    return score


def pick_best(candidates: list[Candidate], info: dict, min_score: float = 35.0) -> Candidate | None:
    for c in candidates:
        c.score = score_candidate(c, info)
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    if ranked and ranked[0].score >= min_score:
        return ranked[0]
    return None


# --- yt-dlp -----------------------------------------------------------------

def _import_ytdlp():
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "yt-dlp no está instalado. Ejecuta ./setup.sh o: pip install -U yt-dlp"
        ) from exc
    return yt_dlp


def _entries_to_candidates(entries, from_music: bool) -> list[Candidate]:
    out: list[Candidate] = []
    for e in entries or []:
        if not e:
            continue
        vid = e.get("id")
        url = e.get("url") or e.get("webpage_url")
        if vid and (not url or not url.startswith("http")):
            url = f"https://www.youtube.com/watch?v={vid}"
        if not url:
            continue
        out.append(
            Candidate(
                url=url,
                title=e.get("title") or "",
                channel=e.get("channel") or e.get("uploader") or "",
                duration=e.get("duration"),
                from_music=from_music,
            )
        )
    return out


def search_candidates(query: str, limit: int = 5) -> list[Candidate]:
    yt_dlp = _import_ytdlp()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "playlistend": limit,
    }
    candidates: list[Candidate] = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        music_url = (
            "https://music.youtube.com/search?q="
            + urllib.parse.quote(query)
            + "#songs"
        )
        try:
            res = ydl.extract_info(music_url, download=False)
            candidates += _entries_to_candidates((res or {}).get("entries"), from_music=True)
        except Exception as exc:
            logger.debug("Búsqueda YouTube Music falló (%s); sigo con YouTube", exc)
        try:
            res = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            candidates += _entries_to_candidates((res or {}).get("entries"), from_music=False)
        except Exception as exc:
            logger.debug("Búsqueda YouTube falló: %s", exc)
    # Dedup por URL conservando el primero (el de YouTube Music si aparece en ambos).
    seen: set[str] = set()
    unique = []
    for c in candidates:
        key = c.url.split("&")[0]
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _target_paths(info: dict, library_root: Path) -> tuple[Path, str]:
    artists = info.get("artists") or ["Desconocido"]
    artist_dir = safe_filename(artists[0])
    album_dir = safe_filename(info.get("album") or "Singles")
    stem = safe_filename(f"{', '.join(artists)} - {info.get('name', '')}")
    return library_root / artist_dir / album_dir, stem


def tag_file(path: Path, info: dict) -> None:
    """Escribe título/artista/álbum/fecha de Spotify en el fichero."""
    try:
        import mutagen
    except ImportError:  # pragma: no cover
        return
    try:
        audio = mutagen.File(path, easy=True)
    except Exception as exc:
        logger.debug("No pude abrir %s para taggear: %s", path, exc)
        return
    if audio is None:
        return
    if audio.tags is None:
        try:
            audio.add_tags()
        except Exception:
            return
    values = {
        "title": info.get("name") or "",
        "artist": ", ".join(info.get("artists") or []),
        "album": info.get("album") or "",
        "date": (info.get("album_release_date") or "")[:10],
    }
    for key, val in values.items():
        if not val:
            continue
        try:
            audio[key] = val
        except Exception:
            pass
    try:
        audio.save()
    except Exception as exc:
        logger.debug("No pude guardar tags en %s: %s", path, exc)


def download_track_youtube(
    uri: str,
    info: dict,
    library_root: Path,
    audio_format: str = "best",
    timeout_seconds: int = 300,
    search_limit: int = 5,
) -> DownloadResult:
    """Busca y descarga un track del índice desde YouTube.

    `audio_format`:
      - "best" (por defecto): guarda el audio original sin recomprimir
        (normalmente Opus ~160 kbps, o AAC 128-256 kbps). Máxima calidad.
      - "opus" / "m4a": fuerza ese contenedor (remux si ya es ese códec).
      - "mp3": recomprime a MP3 320. Solo si tu reproductor no soporta Opus;
        recomprimir siempre pierde algo de calidad.
    """
    started = time.monotonic()

    def fail(classification: str, reason: str) -> DownloadResult:
        return DownloadResult(
            uri=uri, success=False, path=None, classification=classification,
            reason=reason, stdout_tail="", stderr_tail="",
            elapsed_seconds=time.monotonic() - started,
        )

    query = build_query(info)
    if not query:
        return fail("unavailable", "track sin nombre en el índice")

    try:
        candidates = search_candidates(query, limit=search_limit)
    except RuntimeError as exc:
        return fail("unknown", str(exc))
    except Exception as exc:
        cls = "retriable" if _RETRIABLE_RE.search(str(exc)) else "unknown"
        return fail(cls, f"búsqueda: {exc}"[:200])

    best = pick_best(candidates, info)
    if best is None:
        return fail("unavailable", f"sin coincidencia fiable en YouTube para «{query}»")
    logger.debug("  ↳ elegido %s (%s · %s · score %.0f)", best.url, best.title, best.channel, best.score)

    out_dir, stem = _target_paths(info, library_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    yt_dlp = _import_ytdlp()
    postprocessors: list[dict] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": "0",  # solo aplica si hay que recomprimir
        },
    ]
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestaudio/best",
        "outtmpl": {"default": str(out_dir / f"{stem}.%(ext)s")},
        "writethumbnail": True,
        "postprocessors": postprocessors + [
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"},
        ],
        "socket_timeout": 30,
        "retries": 3,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(best.url, download=True)
    except Exception as exc:
        msg = str(exc)
        if _RETRIABLE_RE.search(msg):
            return fail("retriable", msg[:200])
        if _UNAVAILABLE_RE.search(msg):
            return fail("unavailable", msg[:200])
        return fail("unknown", msg[:200])

    if time.monotonic() - started > timeout_seconds:
        logger.warning("  ↳ la descarga tardó más de %ss", timeout_seconds)

    audio_files = sorted(
        (p for p in out_dir.glob(f"{glob_escape(stem)}.*") if p.suffix.lower() in AUDIO_EXTS),
        key=lambda p: p.stat().st_mtime,
    )
    if not audio_files:
        return fail("unknown", "yt-dlp terminó pero no encuentro el fichero de audio")
    final = audio_files[-1]

    tag_file(final, info)
    _store_cover(out_dir, stem)

    abr = (meta or {}).get("abr")
    return DownloadResult(
        uri=uri, success=True, path=str(final), classification="success",
        reason=f"ok ({best.url})", stdout_tail="", stderr_tail="",
        elapsed_seconds=time.monotonic() - started,
        size_bytes=final.stat().st_size,
        bitrate_kbps=int(abr) if abr else None,
    )


def glob_escape(text: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", text)


def _store_cover(out_dir: Path, stem: str) -> None:
    """Mueve la miniatura descargada a `cover.jpg` del álbum (si no existe ya)."""
    thumbs = [p for p in out_dir.glob(f"{glob_escape(stem)}.*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    if not thumbs:
        return
    album_dir = album_dir_for(out_dir / "x")
    has_cover = any((album_dir / f"cover{ext}").exists() for ext in (".jpg", ".jpeg", ".png"))
    try:
        if has_cover:
            for t in thumbs:
                t.unlink(missing_ok=True)
        else:
            dest = album_dir / f"cover{thumbs[0].suffix.lower()}"
            shutil.move(str(thumbs[0]), str(dest))
            for t in thumbs[1:]:
                t.unlink(missing_ok=True)
            _crop_square(dest)
    except OSError as exc:
        logger.debug("No pude guardar la carátula: %s", exc)


def _crop_square(path: Path) -> None:
    """Las miniaturas de YouTube son 16:9 con la carátula centrada: recorta
    el cuadrado central para que se vea como una portada de álbum."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return
    tmp = path.with_name(f".tmp-{path.name}")
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(path),
             "-vf", "crop='min(iw,ih)':'min(iw,ih)'", str(tmp)],
            capture_output=True, timeout=30,
        )
        if proc.returncode == 0 and tmp.exists():
            tmp.replace(path)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("No pude recortar %s: %s", path, exc)
    finally:
        tmp.unlink(missing_ok=True)
