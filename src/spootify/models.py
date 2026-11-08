from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TrackInfo:
    uri: str
    name: str
    artists: list[str]
    album: str
    album_release_date: str
    isrc: str | None
    duration_ms: int | None = None
    playlists: list[str] = field(default_factory=list)
    added_at: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
