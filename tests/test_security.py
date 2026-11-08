from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spootify.security import COOKIE_NAME, host_allowed, load_or_create_token, split_host
from spootify.server import create_app

TOKEN = "t" * 32
LAN = "192.168.1.20:8000"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "credentials.json").write_text("secreto")
    media = tmp_path / "downloads" / "raw" / "Artista"
    media.mkdir(parents=True)
    (media / "song.mp3").write_bytes(b"audio")
    web = tmp_path / "web"
    (web / "icons").mkdir(parents=True)
    (web / "index.html").write_text("<html>app</html>")
    (web / "manifest.webmanifest").write_text("{}")
    (web / "icons" / "icon-192.png").write_bytes(b"png")
    return tmp_path


def _client(project: Path, token: str | None = TOKEN, client=("192.168.1.50", 5000)) -> TestClient:
    app = create_app(project, web_dir=project / "web", token=token)
    return TestClient(app, base_url=f"http://{LAN}", client=client, follow_redirects=False)


def test_lan_without_token_is_rejected(project):
    c = _client(project)
    assert c.get("/").status_code == 401
    assert c.get("/api/library.json").status_code == 401
    assert c.get("/media/Artista/song.mp3").status_code == 401
    assert c.post("/api/refresh").status_code == 401


def test_pairing_sets_cookie_and_strips_token(project):
    c = _client(project)
    r = c.get(f"/?token={TOKEN}")
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    cookie = r.headers["set-cookie"]
    assert f"{COOKIE_NAME}={TOKEN}" in cookie
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    # Con la cookie ya entra en todo.
    assert c.get("/").status_code == 200
    assert c.get("/api/library.json").status_code == 200
    assert c.get("/media/Artista/song.mp3").content == b"audio"


def test_wrong_token_is_rejected(project):
    c = _client(project)
    assert c.get("/?token=nope").status_code == 401
    assert c.get("/", cookies={COOKIE_NAME: "nope"}).status_code == 401


def test_bearer_header(project):
    c = _client(project)
    r = c.get("/api/library.json", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200


def test_public_pwa_files_need_no_token(project):
    c = _client(project)
    assert c.get("/manifest.webmanifest").status_code == 200
    assert c.get("/icons/icon-192.png").status_code == 200


def test_localhost_needs_no_token(project):
    app = create_app(project, web_dir=project / "web", token=TOKEN)
    c = TestClient(app, base_url="http://localhost:8000", client=("127.0.0.1", 5000))
    assert c.get("/api/library.json").status_code == 200


def test_tailscale_proxy_from_loopback_still_needs_token(project):
    # `tailscale serve` llega desde 127.0.0.1 pero con Host *.ts.net.
    app = create_app(project, web_dir=project / "web", token=TOKEN)
    c = TestClient(app, base_url="https://pc.tail1234.ts.net", client=("127.0.0.1", 5000))
    assert c.get("/api/library.json").status_code == 401


def test_dns_rebinding_host_is_rejected(project):
    # Ni con token ni desde localhost: el Host de un dominio ajeno se rechaza.
    c = _client(project, token=None, client=("127.0.0.1", 5000))
    r = c.get("/api/library.json", headers={"Host": "evil.example.com:8000"})
    assert r.status_code == 400


def test_cross_origin_post_is_rejected(project):
    c = _client(project, token=None)
    r = c.post("/api/refresh", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 403
    r = c.post("/api/refresh", headers={"Origin": f"http://{LAN}"})
    assert r.status_code == 200


def test_no_path_traversal(project):
    c = _client(project)
    c.get(f"/?token={TOKEN}")
    for path in ("/media/../../state/credentials.json", "/media/..%2f..%2fstate%2fcredentials.json"):
        r = c.get(path)
        assert r.status_code == 404
        assert "secreto" not in r.text


def test_api_docs_disabled(project):
    c = _client(project, token=None)
    assert c.get("/openapi.json").status_code == 404
    assert c.get("/docs").status_code == 404


@pytest.mark.parametrize(
    "host,ok",
    [
        ("192.168.1.20", True), ("::1", True), ("localhost", True), ("pc.local", True),
        ("pc.tail1234.ts.net", True), ("evil.example.com", False), ("", False),
    ],
)
def test_host_allowed(host, ok):
    assert host_allowed(host) is ok


def test_split_host():
    assert split_host("192.168.1.5:8000") == "192.168.1.5"
    assert split_host("[::1]:8000") == "::1"
    assert split_host("PC.local") == "pc.local"


def test_token_file_is_private_and_stable(tmp_path):
    t1 = load_or_create_token(tmp_path)
    assert len(t1) >= 16
    assert load_or_create_token(tmp_path) == t1
    mode = stat.S_IMODE(os.stat(tmp_path / "server_token").st_mode)
    assert mode == 0o600
    assert load_or_create_token(tmp_path, reset=True) != t1
