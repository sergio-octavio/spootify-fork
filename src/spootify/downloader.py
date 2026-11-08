from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Patrones que Zotify/librespot imprimen cuando algo falla.
# Los clasificamos para decidir si reintentar o descartar definitivamente.
UNAVAILABLE_PATTERNS = [
    re.compile(r"Track is not available", re.IGNORECASE),
    re.compile(r"not available in your country", re.IGNORECASE),
    re.compile(r"region[- ]locked", re.IGNORECASE),
    re.compile(r"ContentNotFound", re.IGNORECASE),
    re.compile(r"Unable to fetch media", re.IGNORECASE),
]

RETRIABLE_PATTERNS = [
    re.compile(r"ConnectionError", re.IGNORECASE),
    re.compile(r"timed? ?out", re.IGNORECASE),
    re.compile(r"TransportError", re.IGNORECASE),
    re.compile(r"Network is unreachable", re.IGNORECASE),
    re.compile(r"Rate[- ]?limit", re.IGNORECASE),
    re.compile(r"Session expired", re.IGNORECASE),
    re.compile(r"Authentication failed", re.IGNORECASE),
]


@dataclass
class DownloadResult:
    uri: str
    success: bool
    path: str | None
    classification: str  # "success" | "unavailable" | "retriable" | "unknown"
    reason: str
    stdout_tail: str
    stderr_tail: str
    elapsed_seconds: float
    size_bytes: int | None = None
    bitrate_kbps: int | None = None


def _classify_error(stdout: str, stderr: str) -> tuple[str, str]:
    combined = f"{stdout}\n{stderr}"
    for pat in UNAVAILABLE_PATTERNS:
        m = pat.search(combined)
        if m:
            return "unavailable", m.group(0)
    for pat in RETRIABLE_PATTERNS:
        m = pat.search(combined)
        if m:
            return "retriable", m.group(0)
    # Zotify suele poner un resumen en la última línea; cógelo como pista.
    tail = (stderr.strip().splitlines() or stdout.strip().splitlines() or ["(sin salida)"])[-1]
    return "unknown", tail[:200]


def _snapshot_files(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {p for p in root.rglob("*") if p.is_file()}


def download_track(
    uri: str,
    zotify_bin: Path,
    library_root: Path,
    audio_format: str = "mp3",
    download_quality: str = "very_high",
    artwork_size: str = "large",
    timeout_seconds: int = 180,
    extra_args: list[str] | None = None,
) -> DownloadResult:
    """Invoca Zotify para descargar una URI y clasifica el resultado.

    Detecta el fichero creado por diff antes/después en `library_root`,
    porque Zotify no imprime el path final de forma fiable.
    """
    if not uri.startswith("spotify:"):
        # Nunca pasar a Zotify algo que pueda interpretarse como una opción.
        return DownloadResult(
            uri=uri, success=False, path=None, classification="unavailable",
            reason="URI no válida", stdout_tail="", stderr_tail="", elapsed_seconds=0.0,
        )
    library_root.mkdir(parents=True, exist_ok=True)
    before = _snapshot_files(library_root)

    cmd = [
        str(zotify_bin),
        uri,
        "--library",
        str(library_root),
        "--audio-format",
        audio_format,
        "--download-quality",
        download_quality,
        "--artwork-size",
        artwork_size,
        "--save-metadata",
        "--skip-duplicates",
        "--skip-previous",
        "--print-downloads",
        "--print-warnings",
        "--print-errors",
    ]
    if extra_args:
        cmd.extend(extra_args)

    started = time.monotonic()
    logger.debug("$ %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout, stderr = proc.stdout, proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        elapsed = time.monotonic() - started
        return DownloadResult(
            uri=uri,
            success=False,
            path=None,
            classification="retriable",
            reason=f"timeout tras {timeout_seconds}s",
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr),
            elapsed_seconds=elapsed,
        )

    elapsed = time.monotonic() - started
    after = _snapshot_files(library_root)
    created = sorted(after - before, key=lambda p: p.stat().st_mtime)
    audio_exts = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}
    audio_files = [p for p in created if p.suffix.lower() in audio_exts]

    if returncode == 0 and audio_files:
        final = audio_files[-1]
        return DownloadResult(
            uri=uri,
            success=True,
            path=str(final),
            classification="success",
            reason="ok",
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr),
            elapsed_seconds=elapsed,
            size_bytes=final.stat().st_size,
        )

    classification, reason = _classify_error(stdout, stderr)
    if returncode != 0 and classification == "unknown":
        reason = f"exit={returncode}: {reason}"
    return DownloadResult(
        uri=uri,
        success=False,
        path=None,
        classification=classification,
        reason=reason,
        stdout_tail=_tail(stdout),
        stderr_tail=_tail(stderr),
        elapsed_seconds=elapsed,
    )


def _tail(text: str, n: int = 500) -> str:
    if not text:
        return ""
    return text[-n:]
