from __future__ import annotations

import logging
import re
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError

logger = logging.getLogger(__name__)

# Zotify crea subcarpetas "Disc 1", "Disc 2"... solo en álbumes multi-disco
# (o siempre, dependiendo del template). Si el parent del mp3 es "Disc N",
# la carpeta del álbum es el abuelo.
_DISC_DIR_RE = re.compile(r"^Disc \d+$", re.IGNORECASE)

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}


def album_dir_for(track_path: Path) -> Path:
    parent = track_path.parent
    if _DISC_DIR_RE.match(parent.name):
        return parent.parent
    return parent


def save_album_cover(
    track_path: Path, filename_stem: str = "cover", overwrite: bool = False
) -> Path | None:
    """Extrae la carátula embebida del MP3 y la guarda como `cover.ext` en la
    carpeta del álbum. Devuelve el path escrito o None si no hizo falta / no se pudo.
    """
    album_dir = album_dir_for(track_path)

    # Si ya hay una cover, no la tocamos (salvo overwrite).
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = album_dir / f"{filename_stem}{ext}"
        if candidate.exists() and not overwrite:
            return None

    try:
        tags = ID3(track_path)
    except ID3NoHeaderError:
        logger.debug("%s sin tags ID3, no hay carátula que extraer", track_path)
        return None

    apics = tags.getall("APIC")
    if not apics:
        logger.debug("%s no tiene APIC embebido", track_path)
        return None

    # Nos quedamos con la imagen más grande si hay varias (normalmente "Cover (front)").
    apic = max(apics, key=lambda a: len(a.data))
    ext = MIME_TO_EXT.get(apic.mime.lower(), ".jpg")
    out_path = album_dir / f"{filename_stem}{ext}"
    out_path.write_bytes(apic.data)
    logger.debug("Carátula escrita: %s (%d bytes)", out_path, len(apic.data))
    return out_path
