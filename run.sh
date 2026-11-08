#!/usr/bin/env bash
# Spootify — wrapper de uso diario.
# Uso: ./run.sh <comando>

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "No existe .venv/. Lanza primero: ./setup.sh" >&2
  exit 1
fi

PY=.venv/bin/python

cmd=${1:-help}
shift || true

case "$cmd" in
  index|build-index)
    $PY main.py --build-index "$@"
    ;;
  download)
    mkdir -p logs
    nohup $PY main.py --download > logs/bulk-download.log 2>&1 &
    PID=$!
    disown
    echo "Descarga lanzada en background (PID $PID)."
    echo "Ver progreso:  ./run.sh progress"
    echo "Ver log:       tail -f logs/bulk-download.log"
    echo "Parar:         ./run.sh stop"
    ;;
  download-test)
    # Descarga las 3 primeras canciones pendientes — útil para probar Zotify y la auth.
    $PY main.py --download --limit 3
    ;;
  retry)
    $PY main.py --retry-failed "$@"
    ;;
  stop)
    PIDS=$(pgrep -f "main.py --download" || true)
    if [ -z "$PIDS" ]; then echo "No hay descarga corriendo."; exit 0; fi
    echo "Parando PIDs: $PIDS"
    kill $PIDS
    ;;
  progress)
    $PY main.py --progress "$@"
    ;;
  watch)
    $PY main.py --progress --watch "$@"
    ;;
  serve)
    $PY main.py --serve "$@"
    ;;
  import)
    if [ $# -lt 1 ]; then echo "Uso: ./run.sh import <carpeta> [--dry-run] [--import-mode move|link]" >&2; exit 1; fi
    DIR=$1; shift
    $PY main.py --import-local "$DIR" "$@"
    ;;
  test)
    $PY -m pytest tests/ -v
    ;;
  help|--help|-h|"")
    cat <<EOF
Spootify — wrapper de comandos.

Uso: ./run.sh <comando>

  index             Construye el índice a partir de los CSVs en playlists_csv/
  download-test     Descarga 3 canciones (prueba inicial / auth)
  download          Descarga toda la biblioteca en background
  progress          Muestra progreso una vez
  watch             Muestra progreso en vivo (Ctrl+C para salir)
  stop              Para la descarga en background
  retry             Reintenta canciones que fallaron
  import <carpeta>  Importa tus FLAC/ALAC/WAV (Bandcamp, Qobuz, CDs...)
  serve             Arranca el reproductor web (http://localhost:8000)
  test              Ejecuta los tests

Lee el README para los pasos completos.
EOF
    ;;
  *)
    echo "Comando desconocido: $cmd" >&2
    echo "Usa: ./run.sh help" >&2
    exit 1
    ;;
esac
