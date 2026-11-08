from __future__ import annotations

import json
import logging
import mimetypes
import re
import unicodedata
import urllib.parse
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import mutagen

from .artwork import album_dir_for
from .security import AccessGuard

logger = logging.getLogger(__name__)

# Python no siempre conoce estos tipos; sin ellos el navegador recibe
# application/octet-stream y algunos (Chrome Android) no reproducen el audio.
for _ext, _mime in {
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".opus": "audio/ogg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
}.items():
    mimetypes.add_type(_mime, _ext)


def _slug(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return norm or "unknown"


def _to_epoch_ms(iso_str: str) -> int:
    if not iso_str:
        return 0
    try:
        # Acepta '2021-01-10T12:00:00Z' o similares.
        s = iso_str.replace("Z", "+00:00")
        return int(datetime.fromisoformat(s).timestamp() * 1000)
    except Exception:
        return 0


def _url_path(rel: Path) -> str:
    # Encode componentes individualmente para preservar separadores /.
    parts = [urllib.parse.quote(p, safe="") for p in rel.parts]
    return "/media/" + "/".join(parts)


def _classify_csvs(track_index: dict) -> dict[str, str]:
    """Clasifica cada CSV (playlist exportada) como 'album' o 'playlist'.

    Heurística: un CSV es un álbum si todas (o casi todas) sus canciones
    pertenecen al mismo (artista principal, álbum). Exportify exporta
    álbumes guardados en Spotify como si fueran playlists; este paso los
    detecta para no mezclarlos con las playlists del usuario.
    """
    from collections import defaultdict

    csv_tracks: dict[str, list[dict]] = defaultdict(list)
    for _, info in track_index.items():
        for pl_name in info.get("playlists", []):
            csv_tracks[pl_name].append(info)

    classification: dict[str, str] = {}
    for name, tracks in csv_tracks.items():
        if name.lower() in {"liked_songs", "liked songs"}:
            classification[name] = "playlist"
            continue
        if len(tracks) < 3:
            classification[name] = "playlist"
            continue
        albums = {(t.get("album") or "").strip() for t in tracks}
        albums.discard("")
        primary_artists = {
            ((t.get("artists") or [""])[0] or "").strip() for t in tracks
        }
        primary_artists.discard("")
        if len(albums) == 1 and len(primary_artists) == 1:
            classification[name] = "album"
        else:
            classification[name] = "playlist"
    return classification


def build_library(
    project_root: Path, downloads_root: Path | None = None
) -> dict:
    """Transforma state/track_index.json + state/downloaded.json al shape que
    espera el front-end React (data.jsx): ARTISTS, SONGS, PLAYLISTS, ALBUMS.

    - SONGS: todos los tracks descargados (1 entry por URI).
    - ARTISTS: artistas únicos de esos tracks.
    - PLAYLISTS: solo CSVs que son playlists reales del usuario (ver _classify_csvs).
    - ALBUMS: agrupación natural (artista+álbum) derivada de la metadata de los tracks.
    """
    state_dir = project_root / "state"
    downloads_root = downloads_root or (project_root / "downloads" / "raw")

    index_path = state_dir / "track_index.json"
    downloaded_path = state_dir / "downloaded.json"

    track_index = (
        json.loads(index_path.read_text(encoding="utf-8"))
        if index_path.exists()
        else {}
    )
    downloaded = (
        json.loads(downloaded_path.read_text(encoding="utf-8"))
        if downloaded_path.exists()
        else {}
    )

    csv_class = _classify_csvs(track_index)

    artists_by_name: dict[str, dict] = {}
    songs: list[dict] = []
    playlists_map: dict[str, list[dict]] = {}

    for uri, info in track_index.items():
        dl = downloaded.get(uri)
        if not dl:
            continue
        mp3_path = Path(dl["path"])
        if not mp3_path.is_absolute():
            mp3_path = project_root / mp3_path
        if not mp3_path.exists():
            continue

        primary_artist = (info.get("artists") or ["Desconocido"])[0] or "Desconocido"
        if primary_artist not in artists_by_name:
            artists_by_name[primary_artist] = {
                "id": f"artist:{_slug(primary_artist)}",
                "name": primary_artist,
                "genre": "",
                "monthly": 0,
            }
        artist_id = artists_by_name[primary_artist]["id"]

        # Duración desde el fichero (MP3, FLAC, M4A...).
        try:
            dur = int(mutagen.File(mp3_path).info.length)
        except Exception:
            dur = 0

        try:
            audio_rel = mp3_path.relative_to(downloads_root)
        except ValueError:
            audio_rel = Path(mp3_path.name)
        audio_url = _url_path(audio_rel)

        # Cover.jpg a nivel de álbum. Comprobar que existe; si no, no mandamos URL.
        album_dir = album_dir_for(mp3_path)
        cover_url = None
        for ext in (".jpg", ".jpeg", ".png"):
            cover_path = album_dir / f"cover{ext}"
            if cover_path.exists():
                try:
                    cover_rel = cover_path.relative_to(downloads_root)
                except ValueError:
                    cover_rel = Path(cover_path.name)
                cover_url = _url_path(cover_rel)
                break

        songs.append(
            {
                "id": uri,
                "title": info.get("name", ""),
                "artistId": artist_id,
                "album": info.get("album", ""),
                "dur": dur,
                "audioUrl": audio_url,
                "coverUrl": cover_url,
                "quality": dl.get("quality") or (
                    f"MP3 {dl['bitrate_kbps']} kbps" if dl.get("bitrate_kbps") else None
                ),
                "source": dl.get("source") or "zotify",
            }
        )

        for pl_name in info.get("playlists", []):
            if csv_class.get(pl_name) == "album":
                # Los álbumes no deben aparecer como playlists del usuario.
                # Sus tracks ya están en SONGS y son navegables vía ALBUMS.
                continue
            added_at = info.get("added_at", {}).get(pl_name, "")
            playlists_map.setdefault(pl_name, []).append(
                {"id": uri, "addedAt": _to_epoch_ms(added_at)}
            )

    # Las playlists NO usan cover de álbum: pueden contener tracks de múltiples
    # álbumes, así que pintamos el gradiente generativo del prototipo (lo gestiona
    # el cliente a partir de `coverSeed`). Solo los tracks y álbumes tienen cover real.
    pl_list: list[dict] = []
    for name, items in playlists_map.items():
        is_liked = name.lower() in {"liked_songs", "liked songs"}
        items_sorted = sorted(items, key=lambda x: x["addedAt"] or 0, reverse=True)
        pl_list.append(
            {
                "id": "saved" if is_liked else f"pl:{_slug(name)}",
                "title": "Canciones guardadas" if is_liked else name.replace("_", " "),
                "subtitle": "Tu biblioteca" if is_liked else "Desde Spotify",
                "pinned": is_liked,
                "items": items_sorted,
            }
        )
    pl_list.sort(key=lambda p: (not p.get("pinned"), p["title"].lower()))

    # ALBUMS: agrupación natural a partir de los SONGS.
    from collections import defaultdict

    album_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for s in songs:
        key = (s["artistId"], s["album"] or "")
        album_groups[key].append(s)

    albums_list: list[dict] = []
    for (artist_id, album_name), items in album_groups.items():
        if not album_name:
            continue
        cover = next((s["coverUrl"] for s in items if s.get("coverUrl")), None)
        artist_name = next(
            (a["name"] for a in artists_by_name.values() if a["id"] == artist_id),
            "",
        )
        albums_list.append(
            {
                "id": f"album:{_slug(artist_name)}:{_slug(album_name)}",
                "title": album_name,
                "artistId": artist_id,
                "artistName": artist_name,
                "coverUrl": cover,
                "items": [
                    {"id": s["id"], "addedAt": 0} for s in items
                ],
            }
        )
    albums_list.sort(key=lambda a: (a["artistName"].lower(), a["title"].lower()))

    detected_albums = [n for n, c in csv_class.items() if c == "album"]
    if detected_albums:
        logger.info(
            "CSVs clasificados como \u00e1lbumes (excluidos de playlists): %s",
            ", ".join(sorted(detected_albums)),
        )

    return {
        "ARTISTS": list(artists_by_name.values()),
        "SONGS": songs,
        "PLAYLISTS": pl_list,
        "ALBUMS": albums_list,
    }


def create_app(
    project_root: Path,
    downloads_root: Path | None = None,
    web_dir: Path | None = None,
    token: str | None = None,
    extra_hosts: tuple[str, ...] = (),
) -> FastAPI:
    """Crea la app. Con `token`, todo (salvo localhost) exige el token de acceso;
    la comprobación de Host/Origin se aplica siempre (ver security.py)."""
    project_root = Path(project_root).resolve()
    downloads_root = Path(downloads_root or project_root / "downloads" / "raw").resolve()
    web_dir = Path(web_dir or project_root / "web").resolve()

    # Sin /docs ni /openapi.json: no hacen falta y describen la API a cualquiera.
    app = FastAPI(title="Spootify", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(AccessGuard, token=token, extra_hosts=extra_hosts)

    # Cache en memoria invalidado por mtime de state/downloaded.json. Así,
    # mientras corre la descarga en background, la UI ve nuevos tracks al recargar.
    _cache: dict = {"library": None, "mtime": 0.0}
    downloaded_path = project_root / "state" / "downloaded.json"

    def refresh_library() -> dict:
        lib = build_library(project_root, downloads_root)
        _cache["library"] = lib
        try:
            _cache["mtime"] = downloaded_path.stat().st_mtime
        except FileNotFoundError:
            _cache["mtime"] = 0.0
        logger.info(
            "Library (re)build: %d songs, %d artists, %d playlists, %d albums",
            len(lib["SONGS"]),
            len(lib["ARTISTS"]),
            len(lib["PLAYLISTS"]),
            len(lib.get("ALBUMS", [])),
        )
        return lib

    def get_library() -> dict:
        try:
            cur = downloaded_path.stat().st_mtime
        except FileNotFoundError:
            cur = 0.0
        if _cache["library"] is None or cur > _cache["mtime"]:
            return refresh_library()
        return _cache["library"]

    @app.on_event("startup")
    def _warmup() -> None:
        refresh_library()

    @app.get("/api/library.json")
    def api_library():
        return JSONResponse(get_library())

    @app.post("/api/refresh")
    def api_refresh():
        return JSONResponse(
            {"ok": True, "counts": {k: len(v) for k, v in refresh_library().items()}}
        )

    @app.get("/api/progress")
    def api_progress():
        index_path = project_root / "state" / "track_index.json"
        downloaded_path = project_root / "state" / "downloaded.json"
        failed_path = project_root / "state" / "failed.json"
        total = len(
            json.loads(index_path.read_text(encoding="utf-8"))
            if index_path.exists() else {}
        )
        downloaded = (
            json.loads(downloaded_path.read_text(encoding="utf-8"))
            if downloaded_path.exists() else {}
        )
        failed = (
            json.loads(failed_path.read_text(encoding="utf-8"))
            if failed_path.exists() else {}
        )
        unav = sum(1 for f in failed.values() if f.get("classification") == "unavailable")
        return JSONResponse({
            "total": total,
            "downloaded": len(downloaded),
            "failed_retriable": len(failed) - unav,
            "unavailable": unav,
            "pending": max(0, total - len(downloaded) - unav),
        })

    # Static: los MP3s + covers se sirven bajo /media. StaticFiles soporta
    # byte-range requests automáticamente, lo que permite seek en el <audio>.
    if downloads_root.exists():
        app.mount(
            "/media",
            StaticFiles(directory=str(downloads_root)),
            name="media",
        )
    else:
        logger.warning("downloads_root no existe: %s", downloads_root)

    # Static: front-end. Montado el último con html=True para servir index.html.
    if web_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(web_dir), html=True),
            name="web",
        )
    else:
        logger.warning("web_dir no existe: %s", web_dir)

    return app
