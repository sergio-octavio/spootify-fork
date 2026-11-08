from __future__ import annotations

import struct
from pathlib import Path

from mutagen.flac import FLAC, Picture

from spootify.local_import import (
    AudioTags,
    TrackMatcher,
    import_local_library,
    normalize,
    read_audio_tags,
)
from spootify.state_manager import StateManager


def _make_flac(path: Path, *, sample_rate=96000, bits=24, cover: bytes | None = None, **tags) -> None:
    """FLAC mínimo válido (solo STREAMINFO, sin frames de audio) con tags Vorbis."""
    # STREAMINFO: min/max block, min/max frame, y 64 bits empaquetados con
    # sample_rate(20) | channels-1(3) | bits-1(5) | total_samples(36).
    packed = (sample_rate << 44) | (1 << 41) | ((bits - 1) << 36) | (sample_rate * 180)
    streaminfo = struct.pack(">HH", 4096, 4096) + b"\x00" * 6 + struct.pack(">Q", packed) + b"\x00" * 16
    header = bytes([0x80]) + len(streaminfo).to_bytes(3, "big")  # last-block=1, type=0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fLaC" + header + streaminfo)
    audio = FLAC(path)
    for key, value in tags.items():
        audio[key] = value
    if cover:
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.data = cover
        audio.add_picture(pic)
    audio.save()


INDEX = {
    "spotify:track:1": {
        "uri": "spotify:track:1",
        "name": "Bohemian Rhapsody - Remastered 2011",
        "artists": ["Queen"],
        "album": "A Night At The Opera",
        "isrc": "GBUM71029604",
        "playlists": ["Rock"],
    },
    "spotify:track:2": {
        "uri": "spotify:track:2",
        "name": "Despacito (feat. Daddy Yankee)",
        "artists": ["Luis Fonsi", "Daddy Yankee"],
        "album": "VIDA",
        "isrc": None,
        "playlists": ["Latino"],
    },
}


def _tags(**kw) -> AudioTags:
    base = dict(
        path=Path("x.flac"), title="", artists=[], album="", isrc=None,
        track_number=None, disc_number=None, codec="flac",
        bitrate_kbps=None, sample_rate=None, bits_per_sample=None,
    )
    base.update(kw)
    return AudioTags(**base)


def test_normalize_strips_versions_and_features() -> None:
    assert normalize("Bohemian Rhapsody - Remastered 2011") == "bohemian rhapsody"
    assert normalize("Despacito (feat. Daddy Yankee)") == "despacito"
    assert normalize("Canción Ñoña") == "cancion nona"


def test_match_by_isrc_wins_over_title() -> None:
    m = TrackMatcher.from_index(INDEX)
    assert m.match(_tags(title="Otra cosa", isrc="GB-UM7-10-29604")) == "spotify:track:1"


def test_match_by_artist_and_title() -> None:
    m = TrackMatcher.from_index(INDEX)
    assert m.match(_tags(title="Despacito", artists=["Daddy Yankee"])) == "spotify:track:2"
    assert m.match(_tags(title="Bohemian Rhapsody", artists=["Queen"])) == "spotify:track:1"
    assert m.match(_tags(title="Bohemian Rhapsody", artists=["Otro"])) is None


def test_read_flac_tags(tmp_path: Path) -> None:
    f = tmp_path / "a.flac"
    _make_flac(f, title="Despacito", artist="Luis Fonsi", tracknumber="3/10")
    t = read_audio_tags(f)
    assert t is not None
    assert t.codec == "flac" and t.lossless
    assert t.track_number == 3
    assert t.quality_label == "FLAC 24-bit/96 kHz"


def test_import_copies_marks_and_extracts_cover(tmp_path: Path) -> None:
    src = tmp_path / "compras"
    _make_flac(src / "01.flac", title="Bohemian Rhapsody", artist="Queen",
               tracknumber="11", cover=b"\xff\xd8fakejpeg")
    _make_flac(src / "02.flac", title="Desconocida", artist="Nadie")
    lib = tmp_path / "lib"
    state = StateManager(state_dir=tmp_path / "state")
    state.load()

    report = import_local_library(src, INDEX, state, lib)

    assert len(report.imported) == 1 and len(report.unmatched) == 1
    entry = state.downloaded["spotify:track:1"]
    dest = Path(entry.path)
    assert dest.exists() and dest.suffix == ".flac"
    assert dest.parent == lib / "Queen" / "A Night At The Opera"
    assert dest.name.startswith("11. Queen - ")
    assert (dest.parent / "cover.jpg").read_bytes() == b"\xff\xd8fakejpeg"
    assert entry.source == "local" and entry.codec == "flac"
    assert (src / "01.flac").exists()  # modo copy no toca el original


def test_import_upgrades_mp3_but_not_downgrades(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_flac(src / "d.flac", title="Despacito", artist="Luis Fonsi")
    state = StateManager(state_dir=tmp_path / "state")
    state.load()
    state.mark_success("spotify:track:2", path=str(tmp_path / "old.mp3"), bitrate_kbps=320, codec="mp3")

    report = import_local_library(src, INDEX, state, tmp_path / "lib")
    assert report.upgraded == ["spotify:track:2"]
    assert state.downloaded["spotify:track:2"].codec == "flac"

    # Segunda pasada: ya hay FLAC, no se reimporta.
    report2 = import_local_library(src, INDEX, state, tmp_path / "lib")
    assert report2.imported == [] and len(report2.skipped_existing) == 1


def test_no_upgrade_flag_keeps_existing(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_flac(src / "d.flac", title="Despacito", artist="Luis Fonsi")
    state = StateManager(state_dir=tmp_path / "state")
    state.load()
    state.mark_success("spotify:track:2", path="old.mp3", codec="mp3")
    report = import_local_library(src, INDEX, state, tmp_path / "lib", upgrade=False)
    assert report.imported == []
    assert state.downloaded["spotify:track:2"].path == "old.mp3"


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_flac(src / "d.flac", title="Despacito", artist="Luis Fonsi")
    state = StateManager(state_dir=tmp_path / "state")
    state.load()
    report = import_local_library(src, INDEX, state, tmp_path / "lib", dry_run=True)
    assert len(report.imported) == 1
    assert not (tmp_path / "lib").exists()
    assert state.downloaded == {}


def test_old_state_files_still_load(tmp_path: Path) -> None:
    (tmp_path / "downloaded.json").write_text(
        '{"u": {"uri": "u", "path": "a.mp3", "timestamp": "t", "bitrate_kbps": 320, "bytes": 1}}'
    )
    sm = StateManager(state_dir=tmp_path)
    sm.load()
    assert sm.downloaded["u"].codec is None


def test_import_uses_folder_cover_next_to_original(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_flac(src / "d.flac", title="Despacito", artist="Luis Fonsi")
    (src / "Folder.jpg").write_bytes(b"\xff\xd8folder")
    state = StateManager(state_dir=tmp_path / "state")
    state.load()
    import_local_library(src, INDEX, state, tmp_path / "lib", mode="move")
    dest = Path(state.downloaded["spotify:track:2"].path)
    assert not (src / "d.flac").exists()
    assert (dest.parent / "cover.jpg").read_bytes() == b"\xff\xd8folder"
