#!/usr/bin/env bash
# Spootify — bootstrap script.
# Crea el entorno virtual, instala dependencias y comprueba ffmpeg.
# Idempotente: puedes lanzarlo varias veces sin problema.

set -euo pipefail

cd "$(dirname "$0")"

GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
RESET=$'\033[0m'

step() { echo "${GREEN}==> $1${RESET}"; }
warn() { echo "${YELLOW}!! $1${RESET}"; }
fail() { echo "${RED}error: $1${RESET}" >&2; exit 1; }

# 1. Python 3.11+
step "Comprobando Python"
if ! command -v python3 >/dev/null 2>&1; then
  fail "Necesitas Python 3.11 o superior. Instálalo desde https://www.python.org/downloads/"
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYMAJ=$(echo "$PYV" | cut -d. -f1)
PYMIN=$(echo "$PYV" | cut -d. -f2)
if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 11 ]; }; then
  fail "Python $PYV detectado; necesitas 3.11 o superior."
fi
echo "Python $PYV OK"

# 2. ffmpeg (necesario para Zotify)
step "Comprobando ffmpeg"
if ! command -v ffmpeg >/dev/null 2>&1; then
  warn "ffmpeg no encontrado."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew >/dev/null 2>&1; then
      step "Instalando ffmpeg con Homebrew"
      brew install ffmpeg
    else
      fail "Instala Homebrew (https://brew.sh) y luego: brew install ffmpeg"
    fi
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    fail "Instala ffmpeg con: sudo apt install ffmpeg  (Debian/Ubuntu) o el equivalente en tu distro."
  else
    fail "Instala ffmpeg manualmente."
  fi
else
  echo "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}') OK"
fi

# 3. Virtual env
step "Creando entorno virtual (.venv)"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python3 -m pip install --upgrade pip --quiet

# 4. Dependencias
step "Instalando dependencias Python"
pip install -r requirements.txt --quiet

# 5. Zotify desde el fork de DraftKinner (soporte OAuth, indispensable para
#    cuentas creadas vía Facebook).
step "Instalando Zotify (fork DraftKinner con OAuth)"
pip install --quiet 'git+https://github.com/DraftKinner/zotify.git'

# 5b. yt-dlp (fuente alternativa: YouTube Music). Se actualiza a menudo porque
#     YouTube cambia; vuelve a lanzar ./setup.sh si las descargas empiezan a fallar.
step "Actualizando yt-dlp"
pip install --quiet --upgrade yt-dlp

# 6. Carpetas necesarias
mkdir -p playlists_csv state logs downloads/raw web

step "Listo ✅"
echo
echo "Siguientes pasos:"
echo "  1. Coloca tus CSVs de Exportify en  playlists_csv/  (ver README)"
echo "  2. Genera el índice:                  ./run.sh index"
echo "  3. Auténticate y prueba la descarga:  ./run.sh download-test"
echo "  4. Descarga toda la biblioteca:       ./run.sh download"
echo "  5. Lanza el reproductor web:          ./run.sh serve"
