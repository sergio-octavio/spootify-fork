"""Control de acceso del servidor web.

El servidor escucha en la red local para que el móvil pueda reproducir la
música, así que sin protección cualquiera en la misma WiFi podría ver la
biblioteca y descargar los audios. Este módulo añade tres defensas:

1. **Token de acceso.** Se genera una vez y se guarda en `state/server_token`.
   El móvil lo recibe abriendo la URL de emparejamiento que muestra
   `./run.sh serve` (`http://<ip>:8000/?token=...`): el servidor lo guarda en
   una cookie y a partir de ahí no hace falta volver a ponerlo. Las peticiones
   desde el propio ordenador (`http://localhost:8000`) no lo necesitan.
2. **Cabecera Host.** Solo se aceptan IPs, `localhost`, `*.local` y
   `*.ts.net` (Tailscale). Esto bloquea los ataques de *DNS rebinding*, en los
   que una web maliciosa hace que tu navegador hable con tu servidor bajo un
   dominio del atacante.
3. **Cabecera Origin.** Las peticiones que modifican algo (POST...) tienen que
   venir de la propia app, no de otra web (CSRF).
"""
from __future__ import annotations

import hmac
import html
import ipaddress
import json
import os
import secrets
import urllib.parse
from pathlib import Path
from typing import Iterable

COOKIE_NAME = "spootify_token"
COOKIE_MAX_AGE = 400 * 24 * 3600  # máximo que permiten los navegadores
TOKEN_FILE = "server_token"

# Ficheros sin datos personales que el navegador pide sin cookies (el
# manifest de la PWA se descarga con credentials: "omit").
PUBLIC_PATHS = {"/manifest.webmanifest", "/favicon.ico"}
PUBLIC_PREFIXES = ("/icons/",)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1"}


def load_or_create_token(state_dir: Path, reset: bool = False) -> str:
    """Lee el token de `state/server_token` o crea uno nuevo (permisos 600)."""
    state_dir = Path(state_dir)
    path = state_dir / TOKEN_FILE
    if not reset and path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) >= 16:
            return token
    state_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(token + "\n")
    os.chmod(path, 0o600)
    return token


def split_host(host_header: str) -> str:
    """'192.168.1.5:8000' → '192.168.1.5'; '[::1]:8000' → '::1'."""
    h = (host_header or "").strip().lower()
    if h.startswith("["):
        return h[1:].split("]", 1)[0]
    if h.count(":") == 1:
        return h.split(":", 1)[0]
    return h


def host_allowed(host: str, extra_hosts: Iterable[str] = ()) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True  # una IP literal no se puede usar para DNS rebinding
    except ValueError:
        pass
    if host == "localhost" or host.endswith(".localhost"):
        return True
    if host.endswith(".ts.net") or host.endswith(".local"):
        return True
    return host in {h.lower() for h in extra_hosts}


def _is_loopback(ip: str | None) -> bool:
    try:
        return ipaddress.ip_address(ip or "").is_loopback
    except ValueError:
        return False


class AccessGuard:
    """Middleware ASGI con las tres comprobaciones del docstring del módulo."""

    def __init__(self, app, token: str | None, extra_hosts: Iterable[str] = ()):
        self.app = app
        self.token = token
        self.extra_hosts = tuple(extra_hosts)

    def _token_ok(self, candidate: str | None) -> bool:
        if not candidate or not self.token:
            return False
        return hmac.compare_digest(candidate.encode(), self.token.encode())

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        raw_host = headers.get("host", "")
        host = split_host(raw_host)

        if not host_allowed(host, self.extra_hosts):
            return await _respond(send, 400, "Host no permitido.", scope)

        method = scope.get("method", "GET").upper()
        if method not in SAFE_METHODS:
            origin = headers.get("origin")
            if origin is not None:
                origin_host = urllib.parse.urlsplit(origin).netloc.lower()
                if origin_host != raw_host.strip().lower():
                    return await _respond(send, 403, "Origen no permitido.", scope)

        if self.token is None:
            return await self.app(scope, receive, send)

        path = scope.get("path", "/")
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await self.app(scope, receive, send)

        client = scope.get("client") or (None, None)
        if _is_loopback(client[0]) and host in LOOPBACK_NAMES:
            return await self.app(scope, receive, send)

        # 1) ?token=... en la URL: emparejamiento. Guarda la cookie y redirige
        #    a la misma URL sin el token (para que no quede en el historial).
        query = urllib.parse.parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
        q_token = next((v for k, v in query if k == "token"), None)
        if q_token is not None and method in {"GET", "HEAD"}:
            if not self._token_ok(q_token):
                return await _respond(send, 401, "Token incorrecto.", scope)
            rest = urllib.parse.urlencode([(k, v) for k, v in query if k != "token"])
            location = urllib.parse.quote(path) + ("?" + rest if rest else "")
            cookie = (
                f"{COOKIE_NAME}={self.token}; Path=/; Max-Age={COOKIE_MAX_AGE}; "
                "HttpOnly; SameSite=Lax"
            )
            if headers.get("x-forwarded-proto") == "https" or scope.get("scheme") == "https":
                cookie += "; Secure"
            await send({
                "type": "http.response.start",
                "status": 303,
                "headers": [
                    (b"location", location.encode("latin-1")),
                    (b"set-cookie", cookie.encode("latin-1")),
                    (b"cache-control", b"no-store"),
                    (b"content-length", b"0"),
                ],
            })
            return await send({"type": "http.response.body", "body": b""})

        # 2) Cookie de una visita anterior.
        cookies = _parse_cookies(headers.get("cookie", ""))
        if self._token_ok(cookies.get(COOKIE_NAME)):
            return await self.app(scope, receive, send)

        # 3) Cabecera Authorization: Bearer <token> (scripts, curl...).
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer ") and self._token_ok(auth[7:].strip()):
            return await self.app(scope, receive, send)

        return await _respond(send, 401, None, scope)


def _parse_cookies(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


_LOCKED_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spootify</title>
<style>
 body{{margin:0;background:#0a0a0a;color:#fff;font-family:system-ui,sans-serif;
 display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}}
 main{{max-width:440px;line-height:1.5}} code{{background:#1c1c1c;padding:2px 6px;border-radius:6px}}
 h1{{margin-top:0}} p{{color:rgba(255,255,255,.7)}}
</style></head><body><main>
<h1>Spootify está protegido</h1>
<p>{msg}</p>
<p>En el ordenador ejecuta <code>./run.sh serve</code>: muestra una dirección
que termina en <code>?token=…</code>. Ábrela una vez en este dispositivo
(o pégala en la app Android) y ya no te lo volverá a pedir.</p>
</main></body></html>"""


async def _respond(send, status: int, msg: str | None, scope) -> None:
    path = scope.get("path", "/")
    text = msg or "Necesitas el token de acceso."
    if path.startswith(("/api/", "/media/")):
        body = json.dumps({"detail": text}, ensure_ascii=False).encode()
        ctype = b"application/json"
    else:
        body = _LOCKED_PAGE.format(msg=html.escape(text)).encode()
        ctype = b"text/html; charset=utf-8"
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", ctype),
            (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({"type": "http.response.body", "body": body})
