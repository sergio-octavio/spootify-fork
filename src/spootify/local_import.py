"""Importa audio local de alta calidad (FLAC, ALAC, WAV...) a la biblioteca.

Pensado para música que ya es tuya: CDs ripeados, compras en Bandcamp, Qobuz,
7digital, HDtracks, etc. Cada fichero se empareja con una canción del índice
(`state/track_index.json`) por ISRC o, si no hay ISRC, por artista + título.
Si encaja, se copia a `downloads/raw/<Artista>/<Álbum>/...` y se marca como
descargado, sustituyendo a la versión MP3 de Zotify cuando la importada es de
más calidad.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import mutagen

from .artwork import album_dir_for
from .state_manager import StateManager

logger = logging.getLogger(__name__)

AUDIO_EXTS = {".flac", ".m4a", ".alac", ".wav", ".aiff", ".aif", ".ogg", ".opus", ".mp3"}
LOSSLESS_CODECS = {"flac", "alac", "wav", "aiff"}
FOLDER_COVER_NAMES = ("cover", "folder", "front", "album")

# Orden de preferencia: mayor = mejor.
_QUALITY_RANK = {"flac": 3, "alac": 3, "wav": 3, "aiff": 3, "opus": 2, "aac": 1, "vorbis": 1, "mp3": 1}

_FEAT_RE = re.compile(r"\s*[\(\[]?\s*(feat\.?|ft\.?|featuring|con)\s+[^\)\]]*[\)\]]?", re.IGNORECASE)
_VERSION_RE = re.compile(
    r"\s*([\(\[][^\)\]]*(remaster|version|versión|edit|mono|stereo|live|en directo|deluxe)[^\)\]]*[\)\]]"
    r"|\s-\s.*(remaster|version|versión|edit|mono|stereo|live|en directo).*$)",
    re.IGNORECASE,
)
_UNSAFE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class AudioTags:
    path: Path
    title: str
    artists: list[str]
    album: str
    isrc: str | None
    track_number: int | None
    disc_number: int | None
    codec: str
    bitrate_kbps: int | None
    sample_rate: int | None
    bits_per_sample: int | None

    @property
    def lossless(self) -> bool:
        return self.codec in LOSSLESS_CODECS

    @property
    def quality_label(self) -> str:
        if self.lossless and self.bits_per_sample and self.sample_rate:
            return f"{self.codec.upper()} {self.bits_per_sample}-bit/{self.sample_rate / 1000:g} kHz"
        if self.bitrate_kbps:
            return f"{self.codec.upper()} {self.bitrate_kbps} kbps"
        return self.codec.upper()


@dataclass
class ImportReport:
    imported: list[tuple[str, Path]] = field(default_factory=list)  # (uri, destino)
    upgraded: list[str] = field(default_factory=list)
    skipped_existing: list[Path] = field(default_factory=list)
    unmatched: list[Path] = field(default_factory=list)
    unreadable: list[Path] = field(default_factory=list)


# --- normalización / matching -----------------------------------------------

def normalize(text: str) -> str:
    """Normaliza para comparar: sin acentos, sin 'feat.', sin '(Remastered)'..."""
    if not text:
        return ""
    t = _FEAT_RE.sub("", text)
    t = _VERSION_RE.sub("", t)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def _normalize_isrc(isrc: str | None) -> str | None:
    if not isrc:
        return None
    clean = re.sub(r"[^A-Za-z0-9]", "", isrc).upper()
    return clean or None


@dataclass
class TrackMatcher:
    by_isrc: dict[str, str]
    by_artist_title: dict[tuple[str, str], list[str]]
    by_title: dict[str, list[str]]
    index: dict[str, dict]

    @classmethod
    def from_index(cls, index: dict[str, dict]) -> "TrackMatcher":
        by_isrc: dict[str, str] = {}
        by_at: dict[tuple[str, str], list[str]] = {}
        by_title: dict[str, list[str]] = {}
        for uri, info in index.items():
            isrc = _normalize_isrc(info.get("isrc"))
            if isrc:
                by_isrc.setdefault(isrc, uri)
            title = normalize(info.get("name", ""))
            by_title.setdefault(title, []).append(uri)
            for artist in info.get("artists") or []:
                by_at.setdefault((normalize(artist), title), []).append(uri)
        return cls(by_isrc, by_at, by_title, index)

    def match(self, tags: AudioTags) -> str | None:
        isrc = _normalize_isrc(tags.isrc)
        if isrc and isrc in self.by_isrc:
            return self.by_isrc[isrc]

        title = normalize(tags.title)
        if not title:
            return None
        candidates: list[str] = []
        for artist in tags.artists:
            for uri in self.by_artist_title.get((normalize(artist), title), []):
                if uri not in candidates:
                    candidates.append(uri)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # Misma canción en varios álbumes (single + LP...): desempata por álbum.
        album = normalize(tags.album)
        for uri in candidates:
            if album and normalize(self.index[uri].get("album", "")) == album:
                return uri
        return candidates[0]


# --- lectura de tags --------------------------------------------------------

def _first(tags, *keys: str) -> str:
    if not tags:
        return ""
    for key in keys:
        try:
            val = tags.get(key)
        except (KeyError, ValueError):
            val = None
        if val:
            if isinstance(val, list):
                val = val[0]
            return str(val).strip()
    return ""


def _all(tags, key: str) -> list[str]:
    if not tags:
        return []
    try:
        val = tags.get(key) or []
    except (KeyError, ValueError):
        return []
    if not isinstance(val, list):
        val = [val]
    out: list[str] = []
    for v in val:
        # Algunos taggers meten "A; B" o "A, B" en un único campo.
        out.extend(p.strip() for p in re.split(r"\s*[;/]\s*|\s*,\s*", str(v)) if p.strip())
    return out


def _parse_num(raw: str) -> int | None:
    m = re.match(r"\s*(\d+)", raw or "")
    return int(m.group(1)) if m else None


def _codec_of(audio, path: Path) -> str:
    name = type(audio).__name__.lower()
    if "flac" in name:
        return "flac"
    if "mp4" in name or "easymp4" in name:
        codec = (getattr(audio.info, "codec", "") or "").lower()
        return "alac" if codec.startswith("alac") else "aac"
    if "wave" in name:
        return "wav"
    if "aiff" in name:
        return "aiff"
    if "opus" in name:
        return "opus"
    if "vorbis" in name or "ogg" in name:
        return "vorbis"
    if "mp3" in name:
        return "mp3"
    return path.suffix.lower().lstrip(".")


def read_audio_tags(path: Path) -> AudioTags | None:
    try:
        audio = mutagen.File(path, easy=True)
    except Exception as exc:
        logger.debug("mutagen no pudo leer %s: %s", path, exc)
        return None
    if audio is None:
        return None
    tags = audio.tags
    info = audio.info
    title = _first(tags, "title") or path.stem
    artists = _all(tags, "artist") or _all(tags, "albumartist")
    bitrate = getattr(info, "bitrate", None)
    return AudioTags(
        path=path,
        title=title,
        artists=artists,
        album=_first(tags, "album"),
        isrc=_first(tags, "isrc") or None,
        track_number=_parse_num(_first(tags, "tracknumber")),
        disc_number=_parse_num(_first(tags, "discnumber")),
        codec=_codec_of(audio, path),
        bitrate_kbps=int(bitrate / 1000) if bitrate else None,
        sample_rate=getattr(info, "sample_rate", None),
        bits_per_sample=getattr(info, "bits_per_sample", None),
    )


def quality_rank(codec: str | None) -> int:
    return _QUALITY_RANK.get((codec or "").lower(), 0)


# --- carátulas --------------------------------------------------------------

def extract_embedded_cover(path: Path) -> tuple[bytes, str] | None:
    """Devuelve (bytes, extensión) de la carátula embebida en FLAC/MP4/MP3/OGG."""
    try:
        audio = mutagen.File(path)
    except Exception:
        return None
    if audio is None:
        return None
    pictures = list(getattr(audio, "pictures", []) or [])  # FLAC
    if pictures:
        pic = max(pictures, key=lambda p: len(p.data))
        return pic.data, ".png" if "png" in (pic.mime or "") else ".jpg"
    tags = audio.tags
    if tags is None:
        return None
    covr = tags.get("covr") if hasattr(tags, "get") else None  # MP4
    if covr:
        data = bytes(covr[0])
        fmt = getattr(covr[0], "imageformat", None)
        return data, ".png" if fmt == 14 else ".jpg"
    if hasattr(tags, "getall"):  # ID3
        apics = tags.getall("APIC")
        if apics:
            apic = max(apics, key=lambda a: len(a.data))
            return apic.data, ".png" if "png" in apic.mime.lower() else ".jpg"
    return None


def _find_folder_cover(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.stem.lower() in FOLDER_COVER_NAMES and f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            return f
    return None


def ensure_album_cover(audio_path: Path, album_dir: Path, source_dir: Path | None = None) -> Path | None:
    """Guarda cover.jpg en la carpeta del álbum: primero busca cover/folder.jpg
    junto al fichero original y, si no hay, extrae la carátula embebida."""
    for ext in (".jpg", ".jpeg", ".png"):
        if (album_dir / f"cover{ext}").exists():
            return None
    folder_cover = _find_folder_cover(source_dir or audio_path.parent)
    if folder_cover is not None:
        dest = album_dir / f"cover{folder_cover.suffix.lower().replace('.jpeg', '.jpg')}"
        shutil.copy2(folder_cover, dest)
        return dest
    embedded = extract_embedded_cover(audio_path)
    if embedded is not None:
        data, ext = embedded
        dest = album_dir / f"cover{ext}"
        dest.write_bytes(data)
        return dest
    return None


# --- importación ------------------------------------------------------------

def _safe(name: str, fallback: str) -> str:
    clean = _UNSAFE_CHARS_RE.sub("_", name or "").strip().rstrip(".")
    return clean or fallback


def destination_for(info: dict, tags: AudioTags, library_root: Path) -> Path:
    """Misma estructura que Zotify: <Artista>/<Álbum>/[Disc N/]NN. Artista - Título.ext"""
    artists = info.get("artists") or tags.artists or ["Desconocido"]
    artist = _safe(artists[0], "Desconocido")
    album = _safe(info.get("album") or tags.album, "Desconocido")
    title = _safe(info.get("name") or tags.title, tags.path.stem)
    base = library_root / artist / album
    if tags.disc_number and tags.disc_number > 1:
        base = base / f"Disc {tags.disc_number}"
    prefix = f"{tags.track_number:02d}. " if tags.track_number else ""
    return base / f"{prefix}{', '.join(artists)} - {title}{tags.path.suffix.lower()}"


def _place(src: Path, dest: Path, mode: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "move":
        shutil.move(str(src), dest)
    elif mode == "link":
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)
    else:
        shutil.copy2(src, dest)


def scan_audio_files(source_dir: Path) -> list[Path]:
    return sorted(
        p for p in Path(source_dir).rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS and not p.name.startswith("._")
    )


def import_local_library(
    source_dir: Path,
    index: dict[str, dict],
    state: StateManager,
    library_root: Path,
    mode: str = "copy",
    upgrade: bool = True,
    dry_run: bool = False,
) -> ImportReport:
    """Empareja los audios de `source_dir` con el índice y los añade a la biblioteca.

    - `mode`: "copy" (por defecto), "move" o "link" (hardlink, no ocupa espacio extra).
    - `upgrade`: si la canción ya estaba descargada en peor calidad (p. ej. MP3 de
      Zotify), la sustituye por la importada. Nunca sustituye por algo peor.
    """
    if mode not in {"copy", "move", "link"}:
        raise ValueError(f"mode inválido: {mode}")
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"No existe la carpeta: {source_dir}")

    matcher = TrackMatcher.from_index(index)
    report = ImportReport()

    for path in scan_audio_files(source_dir):
        tags = read_audio_tags(path)
        if tags is None:
            report.unreadable.append(path)
            continue
        uri = matcher.match(tags)
        if uri is None:
            report.unmatched.append(path)
            continue

        existing = state.downloaded.get(uri)
        if existing is not None:
            existing_codec = existing.codec or Path(existing.path).suffix.lower().lstrip(".")
            if not upgrade or quality_rank(tags.codec) <= quality_rank(existing_codec):
                report.skipped_existing.append(path)
                continue

        dest = destination_for(index[uri], tags, library_root)
        logger.info("%s → %s [%s]", path.name, dest, tags.quality_label)
        if dry_run:
            report.imported.append((uri, dest))
            if existing is not None:
                report.upgraded.append(uri)
            continue

        if dest.resolve() != path.resolve():
            _place(path, dest, mode)
        try:
            ensure_album_cover(dest, album_dir_for(dest), source_dir=path.parent)
        except Exception as exc:  # una carátula rota no debe parar la importación
            logger.warning("No pude guardar la carátula de %s: %s", dest, exc)

        if existing is not None:
            report.upgraded.append(uri)
            old = Path(existing.path)
            if old.exists() and old.resolve() != dest.resolve():
                logger.info("  ↳ sustituye a %s (se conserva el fichero antiguo)", old.name)

        state.mark_success(
            uri,
            path=str(dest),
            bitrate_kbps=tags.bitrate_kbps,
            size_bytes=dest.stat().st_size,
            source="local",
            codec=tags.codec,
            quality=tags.quality_label,
        )
        report.imported.append((uri, dest))

    return report
