from __future__ import annotations

import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from spootify import youtube
from spootify.youtube import Candidate, build_query, pick_best, safe_filename, score_candidate

INFO = {
    "name": "Bohemian Rhapsody - Remastered 2011",
    "artists": ["Queen"],
    "album": "A Night At The Opera",
    "album_release_date": "1975-11-21",
    "duration_ms": 354_000,
}


def _c(title, channel="", duration=354, music=False):
    return Candidate(url=f"https://www.youtube.com/watch?v={abs(hash(title))}", title=title,
                     channel=channel, duration=duration, from_music=music)


def test_build_query_strips_remaster_and_feat():
    assert build_query(INFO) == "Queen Bohemian Rhapsody"
    assert build_query({"name": "Song (feat. X)", "artists": ["A", "X"]}) == "A Song"


def test_official_audio_beats_live_and_cover():
    official = _c("Bohemian Rhapsody", "Queen - Topic", 355, music=True)
    live = _c("Queen - Bohemian Rhapsody (Live Aid 1985)", "Queen Official", 360)
    cover = _c("Bohemian Rhapsody cover", "Random Guy", 352)
    best = pick_best([live, cover, official], INFO)
    assert best is official
    assert score_candidate(live, INFO) < score_candidate(official, INFO)


def test_wrong_duration_is_penalised():
    right = _c("Queen - Bohemian Rhapsody", "Queen", 354)
    wrong = _c("Queen - Bohemian Rhapsody", "Queen", 3600)
    assert score_candidate(right, INFO) > score_candidate(wrong, INFO) + 50


def test_no_reliable_match_returns_none():
    unrelated = _c("Never Gonna Give You Up", "Rick Astley", 213)
    assert pick_best([unrelated], INFO) is None


def test_live_allowed_if_original_is_live():
    info = {**INFO, "name": "Bohemian Rhapsody - Live", "duration_ms": 360_000}
    live = _c("Queen - Bohemian Rhapsody (Live)", "Queen", 360)
    assert pick_best([live], info) is live


def test_safe_filename():
    assert safe_filename('AC/DC: "Back" in Black?') == "AC_DC_ _Back_ in Black_"
    assert safe_filename("") == "Desconocido"


# --- flujo de descarga con yt-dlp simulado ----------------------------------

@pytest.fixture
def fake_ytdlp(monkeypatch, tmp_path):
    """Sustituye yt_dlp por un doble que 'descarga' un fichero de audio real."""
    ffmpeg = shutil.which("ffmpeg")
    calls = {"downloads": []}

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            if not download:
                if "music.youtube.com" in url:
                    return {"entries": [{"id": "good", "title": "Bohemian Rhapsody",
                                         "channel": "Queen - Topic", "duration": 355}]}
                return {"entries": [{"id": "live", "title": "Bohemian Rhapsody (Live)",
                                     "channel": "Queen", "duration": 400}]}
            calls["downloads"].append(url)
            tmpl = self.opts["outtmpl"]["default"]
            audio = Path(tmpl.replace("%(ext)s", "opus"))
            if ffmpeg:
                subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                "sine=frequency=440:duration=2", "-c:a", "libopus", str(audio)],
                               check=True)
            else:
                audio.write_bytes(b"\0" * 100)
            Path(tmpl.replace("%(ext)s", "jpg")).write_bytes(b"\xff\xd8fakejpg")
            return {"abr": 160.3}

    mod = types.SimpleNamespace(YoutubeDL=FakeYDL)
    monkeypatch.setitem(sys.modules, "yt_dlp", mod)
    return calls


def test_download_track_youtube_end_to_end(fake_ytdlp, tmp_path):
    lib = tmp_path / "raw"
    res = youtube.download_track_youtube("spotify:track:x", INFO, lib)

    assert res.success, res.reason
    assert fake_ytdlp["downloads"] == ["https://www.youtube.com/watch?v=good"]
    path = Path(res.path)
    assert path.parent == lib / "Queen" / "A Night At The Opera"
    assert path.suffix == ".opus"
    assert res.bitrate_kbps == 160
    # La miniatura pasa a ser la carátula del álbum.
    assert (path.parent / "cover.jpg").exists()
    assert not list(path.parent.glob("Queen - *.jpg"))

    if shutil.which("ffmpeg"):
        import mutagen
        tags = mutagen.File(path, easy=True)
        assert tags["title"] == [INFO["name"]]
        assert tags["album"] == [INFO["album"]]


def test_download_unavailable_when_no_match(monkeypatch, tmp_path):
    monkeypatch.setattr(youtube, "search_candidates", lambda q, limit=5: [])
    res = youtube.download_track_youtube("spotify:track:x", INFO, tmp_path)
    assert not res.success
    assert res.classification == "unavailable"
