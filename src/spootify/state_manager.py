from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DownloadedEntry:
    uri: str
    path: str
    timestamp: str
    bitrate_kbps: int | None = None
    bytes: int | None = None


@dataclass
class FailureEntry:
    uri: str
    reason: str
    classification: str  # "unavailable" | "retriable" | "unknown"
    attempts: int = 0
    last_try: str = ""


@dataclass
class StateManager:
    state_dir: Path
    downloaded: dict[str, DownloadedEntry] = field(default_factory=dict)
    failed: dict[str, FailureEntry] = field(default_factory=dict)

    @property
    def downloaded_path(self) -> Path:
        return self.state_dir / "downloaded.json"

    @property
    def failed_path(self) -> Path:
        return self.state_dir / "failed.json"

    def load(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.downloaded_path.exists():
            raw = json.loads(self.downloaded_path.read_text(encoding="utf-8"))
            self.downloaded = {
                uri: DownloadedEntry(**data) for uri, data in raw.items()
            }
        if self.failed_path.exists():
            raw = json.loads(self.failed_path.read_text(encoding="utf-8"))
            self.failed = {uri: FailureEntry(**data) for uri, data in raw.items()}
        logger.info(
            "Estado cargado: %d descargados, %d fallidos",
            len(self.downloaded),
            len(self.failed),
        )

    def save(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_path.write_text(
            json.dumps(
                {uri: asdict(e) for uri, e in self.downloaded.items()},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        self.failed_path.write_text(
            json.dumps(
                {uri: asdict(e) for uri, e in self.failed.items()},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def mark_success(
        self,
        uri: str,
        path: str,
        bitrate_kbps: int | None = None,
        size_bytes: int | None = None,
    ) -> None:
        self.downloaded[uri] = DownloadedEntry(
            uri=uri,
            path=path,
            timestamp=_now_iso(),
            bitrate_kbps=bitrate_kbps,
            bytes=size_bytes,
        )
        # Un éxito limpia cualquier registro previo de fallo.
        self.failed.pop(uri, None)

    def mark_failure(
        self, uri: str, reason: str, classification: str = "unknown"
    ) -> None:
        existing = self.failed.get(uri)
        attempts = (existing.attempts + 1) if existing else 1
        self.failed[uri] = FailureEntry(
            uri=uri,
            reason=reason,
            classification=classification,
            attempts=attempts,
            last_try=_now_iso(),
        )

    def get_pending(
        self,
        all_uris: list[str],
        retry_attempts: int,
        include_unavailable: bool = False,
    ) -> list[str]:
        """Devuelve URIs por intentar: no descargadas y sin haber agotado reintentos.

        - Saltamos URIs ya descargadas.
        - Saltamos URIs clasificadas como 'unavailable' salvo si include_unavailable=True.
        - Saltamos URIs 'retriable' o 'unknown' con attempts >= retry_attempts.
        """
        pending: list[str] = []
        for uri in all_uris:
            if uri in self.downloaded:
                continue
            fail = self.failed.get(uri)
            if fail is not None:
                if fail.classification == "unavailable" and not include_unavailable:
                    continue
                if fail.attempts >= retry_attempts:
                    continue
            pending.append(uri)
        return pending


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
