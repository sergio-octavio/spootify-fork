from __future__ import annotations

import json
from pathlib import Path

import pytest

from spootify.parser import build_track_index, serialize_index


EXPORTIFY_HEADER = (
    "Track URI,Track Name,Artist Name(s),Album Name,"
    "Album Release Date,ISRC,Added At\n"
)


def _write_csv(path: Path, rows: list[str]) -> None:
    path.write_text(EXPORTIFY_HEADER + "\n".join(rows) + "\n", encoding="utf-8")


@pytest.fixture
def csv_dir(tmp_path: Path) -> Path:
    d = tmp_path / "playlists_csv"
    d.mkdir()

    # Playlist A — contiene track1 y track2.
    _write_csv(
        d / "Favoritos.csv",
        [
            "spotify:track:aaa111,Song One,Artist A,Album X,2020-05-01,USAAA1234567,2021-01-10T12:00:00Z",
            "spotify:track:bbb222,Song Two,\"Artist B, Artist C\",Album Y,2019,USBBB7654321,2021-02-01T08:30:00Z",
        ],
    )

    # Playlist B — contiene track1 (duplicado) y un track local.
    _write_csv(
        d / "Road Trip.csv",
        [
            "spotify:track:aaa111,Song One,Artist A,Album X,2020-05-01,USAAA1234567,2022-06-15T09:00:00Z",
            "spotify:local::Local%20Artist:Local%20Album:Local%20Song:180,Local Song,Local Artist,Local Album,,,2022-07-01T10:00:00Z",
        ],
    )
    return d


@pytest.fixture
def csv_dir_with_broken(tmp_path: Path) -> Path:
    d = tmp_path / "playlists_csv"
    d.mkdir()
    _write_csv(
        d / "Good.csv",
        [
            "spotify:track:ccc333,Solo,Artist D,Album Z,2018,USCCC0000001,2020-01-01T00:00:00Z"
        ],
    )
    # CSV con columnas distintas — debe ser saltado con warning.
    (d / "Broken.csv").write_text(
        "Name,Author\nWhatever,Someone\n", encoding="utf-8"
    )
    return d


def test_dedup_merges_playlists(csv_dir: Path) -> None:
    index, stats = build_track_index(csv_dir)

    assert stats.playlists_read == 2
    assert stats.playlists_skipped == 0
    assert stats.unique_tracks == 2
    assert stats.duplicates_collapsed == 1
    assert stats.local_skipped == 1

    t1 = index["spotify:track:aaa111"]
    assert t1.name == "Song One"
    assert t1.artists == ["Artist A"]
    assert sorted(t1.playlists) == ["Favoritos", "Road Trip"]
    assert t1.added_at["Favoritos"] == "2021-01-10T12:00:00Z"
    assert t1.added_at["Road Trip"] == "2022-06-15T09:00:00Z"


def test_multi_artist_split(csv_dir: Path) -> None:
    index, _ = build_track_index(csv_dir)
    t2 = index["spotify:track:bbb222"]
    assert t2.artists == ["Artist B", "Artist C"]
    assert t2.album_release_date == "2019"
    assert t2.isrc == "USBBB7654321"


def test_local_tracks_are_skipped(csv_dir: Path) -> None:
    index, stats = build_track_index(csv_dir)
    assert stats.local_skipped == 1
    assert all(not uri.startswith("spotify:local:") for uri in index)


def test_broken_csv_is_skipped(csv_dir_with_broken: Path, caplog) -> None:
    with caplog.at_level("WARNING"):
        index, stats = build_track_index(csv_dir_with_broken)

    assert stats.playlists_read == 1
    assert stats.playlists_skipped == 1
    assert stats.unique_tracks == 1
    assert "spotify:track:ccc333" in index
    assert any("Broken.csv" in rec.getMessage() for rec in caplog.records)


def test_serialize_index_roundtrip(csv_dir: Path, tmp_path: Path) -> None:
    index, _ = build_track_index(csv_dir)
    out = tmp_path / "state" / "track_index.json"
    serialize_index(index, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(loaded.keys()) == set(index.keys())
    assert loaded["spotify:track:aaa111"]["name"] == "Song One"
    assert sorted(loaded["spotify:track:aaa111"]["playlists"]) == [
        "Favoritos",
        "Road Trip",
    ]


def test_empty_dir_returns_empty_index(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    index, stats = build_track_index(empty)
    assert index == {}
    assert stats.playlists_read == 0


def test_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_track_index(tmp_path / "nope")


def test_invalid_uris_are_skipped(tmp_path: Path) -> None:
    d = tmp_path / "csvs"
    d.mkdir()
    _write_csv(
        d / "Rara.csv",
        [
            "--help,Inyección,Artist A,Album X,2020,,",
            "spotify:track:ok123,Buena,Artist A,Album X,2020,,",
        ],
    )
    index, stats = build_track_index(d)
    assert list(index) == ["spotify:track:ok123"]
    assert stats.invalid_uri_skipped == 1
