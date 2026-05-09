from __future__ import annotations

from pathlib import Path

from spootify.state_manager import StateManager


def test_mark_success_and_persist(tmp_path: Path) -> None:
    sm = StateManager(state_dir=tmp_path)
    sm.load()
    sm.mark_success("spotify:track:aaa", path="/out/a.mp3", bitrate_kbps=320, size_bytes=1234)
    sm.save()

    sm2 = StateManager(state_dir=tmp_path)
    sm2.load()
    assert "spotify:track:aaa" in sm2.downloaded
    assert sm2.downloaded["spotify:track:aaa"].path == "/out/a.mp3"
    assert sm2.downloaded["spotify:track:aaa"].bitrate_kbps == 320


def test_mark_failure_increments_attempts(tmp_path: Path) -> None:
    sm = StateManager(state_dir=tmp_path)
    sm.load()
    sm.mark_failure("spotify:track:bbb", "net timeout", classification="retriable")
    sm.mark_failure("spotify:track:bbb", "net timeout", classification="retriable")
    assert sm.failed["spotify:track:bbb"].attempts == 2


def test_success_clears_previous_failure(tmp_path: Path) -> None:
    sm = StateManager(state_dir=tmp_path)
    sm.load()
    sm.mark_failure("spotify:track:ccc", "net", classification="retriable")
    sm.mark_success("spotify:track:ccc", "/out/c.mp3")
    assert "spotify:track:ccc" not in sm.failed


def test_get_pending_respects_state(tmp_path: Path) -> None:
    sm = StateManager(state_dir=tmp_path)
    sm.load()
    sm.mark_success("spotify:track:done", "/x/done.mp3")
    sm.mark_failure("spotify:track:unav", "Track is not available", classification="unavailable")
    sm.mark_failure("spotify:track:retry", "Connection reset", classification="retriable")
    sm.mark_failure("spotify:track:retry", "Connection reset", classification="retriable")
    sm.mark_failure("spotify:track:retry", "Connection reset", classification="retriable")

    all_uris = [
        "spotify:track:done",
        "spotify:track:unav",
        "spotify:track:retry",
        "spotify:track:new",
    ]

    # retry=3 → 'retry' tiene attempts==3 → excluido; 'done' ya ok → excluido; 'unav' no retriable.
    pending = sm.get_pending(all_uris, retry_attempts=3)
    assert pending == ["spotify:track:new"]

    # Con retry=5, 'retry' vuelve a estar disponible.
    pending = sm.get_pending(all_uris, retry_attempts=5)
    assert "spotify:track:retry" in pending
    assert "spotify:track:new" in pending
    assert "spotify:track:done" not in pending

    # include_unavailable=True añade 'unav'.
    pending = sm.get_pending(all_uris, retry_attempts=3, include_unavailable=True)
    assert "spotify:track:unav" in pending


def test_empty_load_creates_state_dir(tmp_path: Path) -> None:
    target = tmp_path / "state"
    sm = StateManager(state_dir=target)
    sm.load()
    assert target.exists()
    assert sm.downloaded == {}
    assert sm.failed == {}
