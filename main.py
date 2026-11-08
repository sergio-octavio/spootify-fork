from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

# Permite `python main.py` sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from spootify.artwork import save_album_cover
from spootify.downloader import download_track
from spootify.parser import build_track_index, serialize_index
from spootify.state_manager import StateManager
from spootify.youtube import download_track_youtube


logger = logging.getLogger("spootify")

DEFAULT_ZOTIFY_BIN = Path(__file__).parent / ".venv" / "bin" / "zotify"


# --- subcomando: build-index -------------------------------------------------

def cmd_build_index(args: argparse.Namespace) -> int:
    index, stats = build_track_index(args.csv_dir)
    if not args.dry_run:
        serialize_index(index, args.output)
    _print_index_summary(stats, index, args.output, args.dry_run)
    return 0


def _print_index_summary(stats, index, output_path, dry_run) -> None:
    print("=" * 50)
    print("Resumen de parseo")
    print("=" * 50)
    print(f"Playlists leídas:       {stats.playlists_read}")
    print(f"Playlists saltadas:     {stats.playlists_skipped}")
    print(f"Filas CSV totales:      {stats.csv_rows_total}")
    print(f"Tracks únicos:          {stats.unique_tracks}")
    print(f"Duplicados colapsados:  {stats.duplicates_collapsed}")
    print(f"Tracks locales saltados:{stats.local_skipped}")
    print(f"Filas sin URI saltadas: {stats.empty_uri_skipped}")
    print(f"URIs no válidas saltadas: {stats.invalid_uri_skipped}")
    print("-" * 50)
    if dry_run:
        print("(dry-run) no se ha escrito el índice")
    else:
        print(f"Índice escrito en: {output_path}")


# --- subcomando: download ----------------------------------------------------

def _load_index(path: Path) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Ejecuta antes: python main.py --build-index"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_download(args: argparse.Namespace) -> int:
    index = _load_index(args.index)
    all_uris = list(index.keys())

    state = StateManager(state_dir=args.state_dir)
    state.load()

    if args.retry_failed:
        pending = [uri for uri in all_uris if uri in state.failed and uri not in state.downloaded]
    else:
        pending = state.get_pending(
            all_uris,
            retry_attempts=args.retry_attempts,
            # Lo que Spotify marca como "unavailable" suele estar en YouTube.
            include_unavailable=args.include_unavailable or args.source == "youtube",
        )

    if args.limit:
        pending = pending[: args.limit]

    total_in_lib = len(all_uris)
    already_ok = len(state.downloaded)
    logger.info(
        "Biblioteca: %d tracks · ya descargados: %d · pendientes a intentar ahora: %d",
        total_in_lib,
        already_ok,
        len(pending),
    )

    if not pending:
        logger.info("Nada que descargar.")
        return 0

    zotify_bin = Path(args.zotify_bin)
    if args.source == "zotify" and not zotify_bin.exists():
        logger.error("No se encontró el binario de Zotify en %s", zotify_bin)
        return 2
    logger.info("Fuente de descarga: %s", args.source)

    # Flush del estado si el usuario corta.
    def _flush(signum, frame):
        logger.warning("Señal %s recibida — guardando estado y saliendo", signum)
        state.save()
        sys.exit(130)

    signal.signal(signal.SIGINT, _flush)
    signal.signal(signal.SIGTERM, _flush)

    ok = fail = unavailable = 0
    started = time.monotonic()
    try:
        for i, uri in enumerate(pending, 1):
            info = index[uri]
            label = f"{', '.join(info.get('artists', [])) or '?'} — {info.get('name', '?')}"
            logger.info("[%d/%d] %s  (%s)", i, len(pending), label, uri)

            if args.source == "youtube":
                result = download_track_youtube(
                    uri=uri,
                    info=info,
                    library_root=args.library,
                    audio_format=args.yt_format,
                    timeout_seconds=args.track_timeout,
                )
            else:
                result = download_track(
                    uri=uri,
                    zotify_bin=zotify_bin,
                    library_root=args.library,
                    audio_format=args.audio_format,
                    download_quality=args.download_quality,
                    timeout_seconds=args.track_timeout,
                )

            if result.success:
                state.mark_success(
                    uri,
                    path=result.path or "",
                    bitrate_kbps=result.bitrate_kbps or (
                        _quality_to_kbps(args.download_quality) if args.source == "zotify" else None
                    ),
                    size_bytes=result.size_bytes,
                    source="zotify",
                    codec=Path(result.path).suffix.lower().lstrip(".") if result.path else args.audio_format,
                )
                ok += 1
                logger.info(
                    "  ✓ %s (%.1fs, %s)",
                    Path(result.path).name if result.path else "?",
                    result.elapsed_seconds,
                    _human_bytes(result.size_bytes),
                )
                if result.path and not args.no_cover and args.source == "zotify":
                    try:
                        cover = save_album_cover(Path(result.path))
                        if cover is not None:
                            logger.debug("  ↳ cover: %s", cover)
                    except Exception as exc:
                        logger.warning("  ↳ no pude extraer cover: %s", exc)
            else:
                state.mark_failure(uri, result.reason, classification=result.classification)
                if result.classification == "unavailable":
                    unavailable += 1
                    logger.warning("  ✗ unavailable — %s", result.reason)
                else:
                    fail += 1
                    logger.warning("  ✗ [%s] %s", result.classification, result.reason)
                if args.verbose:
                    if result.stdout_tail:
                        logger.debug("    stdout: %s", result.stdout_tail)
                    if result.stderr_tail:
                        logger.debug("    stderr: %s", result.stderr_tail)

            # Guardado periódico + barra de progreso.
            if i % args.save_every == 0:
                state.save()
                elapsed = time.monotonic() - started
                rate = i / elapsed if elapsed > 0 else 0  # tracks/s
                remaining = len(pending) - i
                eta = remaining / rate if rate > 0 else 0
                logger.info(
                    "  %s · OK:%d FAIL:%d UNAV:%d · %.1f/min · ETA %s",
                    _progress_bar(i, len(pending)),
                    ok, fail, unavailable,
                    rate * 60,
                    _fmt_eta(eta),
                )

            if args.pause_between and i < len(pending):
                time.sleep(args.pause_between)
    finally:
        state.save()

    elapsed = time.monotonic() - started
    print("-" * 50)
    print(f"OK: {ok} · fallidos: {fail} · unavailable: {unavailable}")
    print(f"Tiempo total: {elapsed/60:.1f} min")
    return 0


def _quality_to_kbps(q: str) -> int | None:
    return {"normal": 96, "high": 160, "very_high": 320}.get(q)


def _human_bytes(n: int | None) -> str:
    if n is None:
        return "?"
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_eta(seconds: float) -> str:
    if seconds <= 0 or seconds != seconds:  # NaN-safe
        return "?"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h:
        return f"{h}h {m}m"
    s = int(seconds % 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _progress_bar(done: int, total: int, width: int = 24) -> str:
    frac = (done / total) if total else 0
    filled = int(frac * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {done}/{total} ({frac*100:.1f}%)"


# --- subcomando: import-local ----------------------------------------------

def cmd_import_local(args: argparse.Namespace) -> int:
    from spootify.local_import import import_local_library

    index = _load_index(args.index)
    state = StateManager(state_dir=args.state_dir)
    state.load()

    report = import_local_library(
        source_dir=args.import_local,
        index=index,
        state=state,
        library_root=args.library,
        mode=args.import_mode,
        upgrade=not args.no_upgrade,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        state.save()

    print("=" * 50)
    print("Importación local" + (" (dry-run, no se ha copiado nada)" if args.dry_run else ""))
    print("=" * 50)
    print(f"Importadas:                 {len(report.imported)}")
    print(f"  de ellas, mejoran calidad:{len(report.upgraded)}")
    print(f"Ya estaban (igual o mejor): {len(report.skipped_existing)}")
    print(f"Sin coincidencia en índice: {len(report.unmatched)}")
    print(f"Ilegibles:                  {len(report.unreadable)}")
    if report.unmatched:
        print("-" * 50)
        print("Sin coincidencia (revisa sus tags de artista/título o ISRC):")
        for p in report.unmatched[:30]:
            print(f"  · {p}")
        if len(report.unmatched) > 30:
            print(f"  … y {len(report.unmatched) - 30} más")
    return 0


# --- argparse ---------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Spootify — backup de biblioteca Spotify vía Exportify + Zotify.",
    )
    p.add_argument("--verbose", action="store_true", help="Logging DEBUG")

    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--build-index", action="store_true", help="Parsea CSVs y genera track_index.json")
    action.add_argument("--download", action="store_true", help="Descarga tracks pendientes del índice")
    action.add_argument("--retry-failed", action="store_true", help="Reintenta solo los tracks de failed.json")
    action.add_argument("--serve", action="store_true", help="Arranca el reproductor web local")
    action.add_argument("--progress", action="store_true", help="Muestra el progreso actual de la descarga")
    action.add_argument("--import-local", type=Path, metavar="DIR", help="Importa audio propio (FLAC, ALAC, WAV...) desde DIR")

    # progress
    p.add_argument("--watch", action="store_true", help="Con --progress: refresca en vivo (Ctrl+C para salir)")
    p.add_argument("--interval", type=float, default=1.0, help="Intervalo de refresco de --watch en segundos")

    # serve
    p.add_argument("--host", default="0.0.0.0", help="Host del servidor web (default: 0.0.0.0, accesible desde la LAN)")
    p.add_argument("--port", type=int, default=8000, help="Puerto del servidor web (default: 8000)")
    p.add_argument("--web-dir", type=Path, default=Path("web"))
    p.add_argument("--no-auth", action="store_true",
                   help="Desactiva el token de acceso (cualquiera en tu red podrá entrar)")
    p.add_argument("--reset-token", action="store_true",
                   help="Genera un token nuevo (los móviles emparejados tendrán que volver a emparejarse)")
    p.add_argument("--allow-host", action="append", default=[], metavar="NOMBRE",
                   help="Nombre de host extra permitido (además de IPs, localhost, *.local y *.ts.net)")

    # build-index
    p.add_argument("--csv-dir", type=Path, default=Path("playlists_csv"))
    p.add_argument("--output", type=Path, default=Path("state/track_index.json"), help="Ruta del índice generado por --build-index")
    p.add_argument("--dry-run", action="store_true", help="Con --build-index / --import-local: no escribe nada")

    # import-local
    p.add_argument("--import-mode", default="copy", choices=["copy", "move", "link"], help="Copiar, mover o hacer hardlink de los ficheros importados")
    p.add_argument("--no-upgrade", action="store_true", help="No sustituir canciones ya descargadas aunque la importada sea de más calidad")

    # download
    p.add_argument("--index", type=Path, default=Path("state/track_index.json"), help="Índice ya generado (input de --download)")
    p.add_argument("--state-dir", type=Path, default=Path("state"))
    p.add_argument("--library", type=Path, default=Path("downloads/raw"), help="Directorio raíz donde Zotify guarda los audios")
    p.add_argument("--zotify-bin", type=Path, default=DEFAULT_ZOTIFY_BIN)
    p.add_argument("--source", default="zotify", choices=["zotify", "youtube"],
                   help="De dónde descargar: zotify (Spotify Premium) o youtube (YouTube Music vía yt-dlp)")
    p.add_argument("--yt-format", default="best", choices=["best", "opus", "m4a", "mp3", "flac"],
                   help="Con --source youtube: 'best' guarda el audio original sin recomprimir (recomendado)")
    p.add_argument("--audio-format", default="mp3")
    p.add_argument("--download-quality", default="very_high", choices=["normal", "high", "very_high", "auto"])
    p.add_argument("--track-timeout", type=int, default=180, help="Timeout por track en segundos")
    p.add_argument("--retry-attempts", type=int, default=3, help="Intentos máximos por track retriable")
    p.add_argument("--pause-between", type=float, default=2.0, help="Pausa entre tracks (s)")
    p.add_argument("--save-every", type=int, default=5, help="Flushea estado cada N tracks")
    p.add_argument("--limit", type=int, default=0, help="Parar tras N tracks (0 = sin límite)")
    p.add_argument("--include-unavailable", action="store_true", help="Reintentar también los marcados 'unavailable'")
    p.add_argument("--no-cover", action="store_true", help="No extraer cover.jpg en la carpeta del álbum")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.build_index:
        return cmd_build_index(args)
    if args.download or args.retry_failed:
        return cmd_download(args)
    if args.serve:
        return cmd_serve(args)
    if args.progress:
        return cmd_progress(args)
    if args.import_local:
        return cmd_import_local(args)
    parser.error("Acción no soportada")
    return 1


def cmd_progress(args: argparse.Namespace) -> int:
    import subprocess

    def snapshot() -> dict:
        index_path = Path(args.index)
        total = len(
            json.loads(index_path.read_text(encoding="utf-8"))
            if index_path.exists() else {}
        )
        sm = StateManager(state_dir=args.state_dir)
        sm.load()
        unav = sum(1 for f in sm.failed.values() if f.classification == "unavailable")
        return {
            "total": total,
            "done": len(sm.downloaded),
            "retriable": len(sm.failed) - unav,
            "unav": unav,
            "bytes": sum((e.bytes or 0) for e in sm.downloaded.values()),
        }

    def is_download_running() -> str | None:
        try:
            r = subprocess.run(
                ["pgrep", "-af", "main.py --download"],
                capture_output=True, text=True, timeout=2,
            )
            lines = [l for l in r.stdout.splitlines() if "--progress" not in l]
            return lines[0].split()[0] if lines else None
        except Exception:
            return None

    def render(s: dict, instant_rate_per_min: float | None = None, pid: str | None = None) -> list[str]:
        pending = max(0, s["total"] - s["done"] - s["unav"])
        eta = (pending * 60 / instant_rate_per_min) if (instant_rate_per_min and instant_rate_per_min > 0) else 0
        lines = [
            _progress_bar(s["done"], s["total"], width=40),
            f"  Descargados: {s['done']:>5}/{s['total']}"
            f"   Pendientes: {pending:>5}   "
            f"Fallidos: {s['retriable']}+{s['unav']}u",
            f"  Tamaño: {_human_bytes(s['bytes']):>10}   "
            f"Ritmo: {instant_rate_per_min:>5.1f}/min" if instant_rate_per_min is not None else f"  Tamaño: {_human_bytes(s['bytes'])}",
            f"  ETA: {_fmt_eta(eta) if eta else '—'}",
            f"  Proceso: {('PID ' + pid) if pid else 'no activo'}",
        ]
        return lines

    if not args.watch:
        s = snapshot()
        pid = is_download_running()
        for line in render(s, pid=pid):
            print(line)
        return 0

    # --watch: refresco en vivo, tasa instantánea = delta entre ticks.
    import sys
    try:
        prev = snapshot()
        t_prev = time.monotonic()
        printed_lines = 0
        # hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        while True:
            cur = snapshot()
            t_cur = time.monotonic()
            dt = max(1e-6, t_cur - t_prev)
            rate = (cur["done"] - prev["done"]) / dt  # tracks/s
            # Solo actualiza rate base si hubo progreso; si no, arrastra el último
            if not hasattr(cmd_progress, "_ema") or rate > 0:
                ema = getattr(cmd_progress, "_ema", rate)
                ema = 0.3 * rate + 0.7 * ema if ema else rate
                cmd_progress._ema = ema  # type: ignore[attr-defined]
            rate_per_min = (cmd_progress._ema or 0) * 60  # type: ignore[attr-defined]
            pid = is_download_running()

            lines = render(cur, instant_rate_per_min=rate_per_min, pid=pid)
            # Move cursor up to overwrite previous block
            if printed_lines:
                sys.stdout.write(f"\033[{printed_lines}A")
            for ln in lines:
                sys.stdout.write("\033[2K" + ln + "\n")
            sys.stdout.flush()
            printed_lines = len(lines)

            prev, t_prev = cur, t_cur
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\n")  # show cursor + newline
        sys.stdout.flush()
    return 0


def _lan_ip() -> str | None:
    """IP de este ordenador en la red local (no envía tráfico: UDP sin datos)."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    from spootify.security import load_or_create_token
    from spootify.server import create_app

    project_root = Path(__file__).parent.resolve()
    token = None if args.no_auth else load_or_create_token(args.state_dir, reset=args.reset_token)
    app = create_app(
        project_root=project_root,
        downloads_root=args.library,
        web_dir=args.web_dir,
        token=token,
        extra_hosts=tuple(args.allow_host),
    )
    suffix = f"/?token={token}" if token else ""
    logger.info("Spootify web (en este ordenador): http://localhost:%d", args.port)
    lan_ip = _lan_ip()
    logger.info(
        "Desde tu móvil (o en la app Android), abre una vez: http://%s:%d%s",
        lan_ip or "<ip-de-este-ordenador>", args.port, suffix,
    )
    if token:
        logger.info("Con Tailscale: https://<tu-ordenador>.<tu-tailnet>.ts.net%s", suffix)
        logger.info("No compartas esa dirección: da acceso a tu música. Cambiar el token: ./run.sh serve --reset-token")
    else:
        logger.warning("--no-auth: cualquiera en tu red puede ver y descargar tu música.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
