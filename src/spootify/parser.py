from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .models import TrackInfo

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"Track URI", "Track Name", "Artist Name(s)", "Album Name"}


@dataclass
class ParseStats:
    playlists_read: int = 0
    playlists_skipped: int = 0
    csv_rows_total: int = 0
    unique_tracks: int = 0
    duplicates_collapsed: int = 0
    local_skipped: int = 0
    empty_uri_skipped: int = 0
    invalid_uri_skipped: int = 0


def _split_artists(raw: str) -> list[str]:
    if not raw:
        return []
    # Exportify separa artistas múltiples con ", ".
    return [a.strip() for a in raw.split(",") if a.strip()]


def _playlist_name_from_path(csv_path: Path) -> str:
    # TODO: si Exportify incrusta metadata de la playlist en el CSV, preferir eso.
    # Por ahora derivamos del nombre del fichero.
    return csv_path.stem


# URIs que aceptamos. Se pasan como argumento a Zotify, así que cualquier otra
# cosa (p. ej. un texto que empiece por "-" en un CSV manipulado) se descarta.
_VALID_URI_RE = re.compile(r"^spotify:(track|episode):[A-Za-z0-9]+$")


def _is_valid_uri(uri: str) -> bool:
    return bool(_VALID_URI_RE.match(uri))


def _is_local_uri(uri: str) -> bool:
    return uri.startswith("spotify:local:")


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _parse_int(value) -> int | None:
    try:
        n = int(float(_clean(value)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _read_csv_safely(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:  # pragma: no cover
        logger.warning("No se pudo leer %s: %s", path.name, exc)
        return None


def build_track_index(
    csv_dir: Path,
) -> tuple[dict[str, TrackInfo], ParseStats]:
    """Lee todos los *.csv de csv_dir y construye un índice unificado de tracks.

    - Deduplica por `Track URI`, acumulando la lista de playlists donde aparece.
    - Salta tracks locales (`spotify:local:...`) y filas sin URI.
    - Salta CSVs cuyo schema no incluya las columnas requeridas.
    """
    csv_dir = Path(csv_dir)
    if not csv_dir.is_dir():
        raise FileNotFoundError(f"csv_dir no existe o no es directorio: {csv_dir}")

    index: dict[str, TrackInfo] = {}
    stats = ParseStats()

    csv_paths = sorted(csv_dir.glob("*.csv"))
    if not csv_paths:
        logger.warning("No se encontraron CSVs en %s", csv_dir)
        return index, stats

    for csv_path in csv_paths:
        df = _read_csv_safely(csv_path)
        if df is None:
            stats.playlists_skipped += 1
            continue

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning(
                "Saltando %s: faltan columnas %s",
                csv_path.name,
                sorted(missing),
            )
            stats.playlists_skipped += 1
            continue

        playlist_name = _playlist_name_from_path(csv_path)
        stats.playlists_read += 1
        stats.csv_rows_total += len(df)

        for row in df.to_dict(orient="records"):
            uri = _clean(row.get("Track URI"))

            if not uri:
                stats.empty_uri_skipped += 1
                continue
            if _is_local_uri(uri):
                stats.local_skipped += 1
                continue
            if not _is_valid_uri(uri):
                stats.invalid_uri_skipped += 1
                logger.warning("%s: URI no válida, se ignora: %.60r", csv_path.name, uri)
                continue

            added_at = _clean(row.get("Added At"))
            existing = index.get(uri)

            if existing is None:
                release_date = (
                    _clean(row.get("Release Date"))
                    or _clean(row.get("Album Release Date"))
                )
                index[uri] = TrackInfo(
                    uri=uri,
                    name=_clean(row.get("Track Name")),
                    artists=_split_artists(_clean(row.get("Artist Name(s)"))),
                    album=_clean(row.get("Album Name")),
                    album_release_date=release_date,
                    isrc=_clean(row.get("ISRC")) or None,
                    duration_ms=_parse_int(row.get("Duration (ms)") or row.get("Track Duration (ms)")),
                    playlists=[playlist_name],
                    added_at={playlist_name: added_at} if added_at else {},
                )
            else:
                if playlist_name not in existing.playlists:
                    existing.playlists.append(playlist_name)
                if added_at:
                    existing.added_at.setdefault(playlist_name, added_at)
                stats.duplicates_collapsed += 1

    stats.unique_tracks = len(index)
    return index, stats


def serialize_index(
    index: dict[str, TrackInfo], output_path: Path
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {uri: track.to_dict() for uri, track in index.items()}
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
