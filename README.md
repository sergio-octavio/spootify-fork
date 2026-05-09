# Spootify

Tu biblioteca de Spotify, descargada en local y con un reproductor web propio
que puedes usar desde tu iPhone, Android o cualquier ordenador en tu WiFi.

> [!IMPORTANT]
> Esta herramienta usa [Zotify](https://github.com/DraftKinner/zotify), que
> opera en una zona gris respecto a los Términos de Servicio de Spotify.
> Es **uso personal**: descarga tus playlists, no las distribuyas. Necesitas
> una cuenta **Spotify Premium** para descargar a 320 kbps.

---

## ¿Qué hace?

1. Lee los CSVs que exportas con [Exportify](https://exportify.net/) (lista de
   tus playlists con sus canciones).
2. Descarga todos los MP3s con sus covers (carátulas) y metadatos.
3. Te ofrece un reproductor web tipo Spotify para escucharlos desde el móvil
   o el navegador, con tus playlists, álbumes y artistas.

---

## Instalación (macOS)

### 1. Requisitos previos

- **macOS** (probado en Apple Silicon e Intel).
- **Python 3.11 o superior**. Comprueba con `python3 --version`.
  Si no lo tienes: descarga desde <https://www.python.org/downloads/>.
- **Homebrew** (lo necesitarás para `ffmpeg`). Instalación:
  ```
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- **Git**. Suele venir con macOS; si no: `xcode-select --install`.

### 2. Descargar Spootify

Abre la **Terminal** (Cmd+Espacio → escribe "Terminal" → Enter) y ejecuta:

```
cd ~
git clone https://github.com/eljommys/spootify.git
cd spootify
```

### 3. Ejecutar el setup

```
./setup.sh
```

Esto creará un entorno virtual, instalará las dependencias e instalará `ffmpeg`
si te falta. Tarda 2-3 minutos.

---

## Uso

### Paso 1 — Exportar tus playlists con Exportify

1. Abre <https://exportify.net> en el navegador donde tengas sesión iniciada
   en Spotify.
2. Botón **Log in with Spotify** y autoriza permisos de solo lectura.
3. Pulsa **Export All** arriba — descarga un ZIP con todos tus CSVs.
4. Descomprime el ZIP y mueve **todos los `.csv`** a la carpeta
   `playlists_csv/` dentro de la carpeta `spootify`.

> Tu lista "Canciones que te gustan" (corazón ❤️) aparece como **Liked Songs**
> en Exportify — exporta también ese CSV.

### Paso 2 — Construir el índice

```
./run.sh index
```

Lee tus CSVs, deduplica canciones que aparecen en varias playlists y crea un
índice unificado. Te dirá cuántas canciones únicas tienes.

### Paso 3 — Auth con Spotify (primera vez)

> [!NOTE]
> Si te creaste la cuenta de Spotify **con Facebook**, necesitas fijar una
> contraseña propia de Spotify primero, en
> <https://www.spotify.com/account/set-device-password/>. Sin ese paso Zotify
> no podrá iniciar sesión.

Lanza una descarga de prueba:

```
./run.sh download-test
```

La primera vez te abrirá una URL de Spotify en el navegador para autenticarte.
Inicia sesión y autoriza la app. Solo se hace una vez — la sesión queda
cacheada.

Si todo va bien, descargará 3 canciones y verás los MP3s en `downloads/raw/`.

### Paso 4 — Descargar toda la biblioteca

```
./run.sh download
```

Corre en segundo plano. Velocidad típica: ~2 canciones/min en modo seguro.
Para 3000 canciones cuenta unas 24 horas. Puedes parar y reanudar cuando
quieras — el estado se guarda cada 5 canciones.

**Ver progreso:**

```
./run.sh progress         # snapshot
./run.sh watch            # en vivo, refresco cada segundo
tail -f logs/bulk-download.log
```

**Parar:**

```
./run.sh stop
```

**Reintentar canciones fallidas:**

```
./run.sh retry
```

### Paso 5 — Lanzar el reproductor

```
./run.sh serve
```

Abre <http://localhost:8000> en cualquier navegador del Mac.

**Desde el móvil** (mismo WiFi):

1. Mira la IP de tu Mac: `ipconfig getifaddr en0` (o mira en Ajustes → Wi-Fi).
2. En el iPhone/Android abre el navegador y entra a `http://<ip-del-mac>:8000`.
3. Safari → Compartir → "Añadir a pantalla de inicio". Se comporta como app.

---

## Cómo funciona la organización en disco

```
downloads/raw/
└── <Artista>/
    └── <Álbum>/
        ├── cover.jpg              ← carátula extraída en alta resolución
        └── Disc 1/
            └── 01. Artist - Title.mp3
```

Una canción solo se guarda **una vez** aunque aparezca en varias playlists.
Las playlists se persisten en `state/track_index.json` con el orden y la
fecha en que añadiste cada canción.

---

## Comandos disponibles

```
./run.sh index           # Construye el índice desde los CSVs
./run.sh download-test   # Descarga 3 canciones (prueba)
./run.sh download        # Descarga toda la biblioteca en background
./run.sh progress        # Snapshot del progreso
./run.sh watch           # Progreso en vivo
./run.sh stop            # Para la descarga
./run.sh retry           # Reintenta fallos
./run.sh serve           # Arranca el reproductor web
./run.sh test            # Tests unitarios
./run.sh help            # Ayuda
```

---

## Problemas frecuentes

- **`BadCredentials` al autenticarse**: cuenta creada con Facebook sin
  contraseña Spotify propia. Fíjala en
  <https://www.spotify.com/account/set-device-password/>.
- **`zotify: command not found`**: el venv no está activo. Usa siempre
  `./run.sh <comando>` o activa el venv con `source .venv/bin/activate`.
- **El reproductor no muestra todos los tracks descargados**: el server
  detecta cambios en `state/downloaded.json` automáticamente; recarga la
  página y los nuevos tracks aparecen.
- **"Track not available"** en el log de descarga: la canción se retiró
  del catálogo de Spotify pero sigue en tu CSV. Aparece en `state/failed.json`
  con `unavailable`. No hay forma de descargarla con Zotify.

---

## Estructura del proyecto

```
spootify/
├── setup.sh                # Bootstrap (1ª vez)
├── run.sh                  # Wrapper de comandos
├── main.py                 # CLI principal
├── src/spootify/           # Código Python
│   ├── parser.py           # Parser de CSVs de Exportify
│   ├── state_manager.py    # Estado de descargas + resume
│   ├── downloader.py       # Wrapper de Zotify
│   ├── artwork.py          # Extracción de carátulas
│   └── server.py           # Reproductor web (FastAPI)
├── web/                    # Front-end React (Babel in-browser)
│   ├── index.html
│   ├── components.jsx
│   ├── screens.jsx
│   └── player.jsx
├── playlists_csv/          # ⬅ Tú pones aquí los CSVs de Exportify
├── downloads/raw/          # MP3s descargados
└── state/                  # Estado interno (índice, descargados, fallos)
```

---

## Licencia

MIT (uso personal). No te hago responsable a ti ni a mí del uso indebido.
