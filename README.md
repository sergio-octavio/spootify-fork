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
2. Descarga todas las canciones con sus covers (carátulas) y metadatos, desde
   Spotify (Zotify, necesita Premium) **o desde YouTube Music** (yt-dlp, sin
   cuenta). Ver [Descargar desde YouTube Music](#descargar-desde-youtube-music).
3. Te ofrece un reproductor web tipo Spotify para escucharlos desde el móvil
   o el navegador, con tus playlists, álbumes y artistas. En **Android** se
   instala como app, ver [Usar Spootify en Android](#usar-spootify-en-android).

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

### Paso 6 (opcional) — Importar tu música en alta calidad (FLAC, ALAC…)

Spotify da como máximo MP3 a 320 kbps (con pérdida). Si tienes la música en
mejor calidad, Spootify puede usarla en lugar del MP3:

- **Compras sin DRM** en [Bandcamp](https://bandcamp.com) (FLAC, ALAC, WAV),
  [Qobuz](https://www.qobuz.com/shop) (hasta 24-bit/192 kHz),
  [7digital](https://www.7digital.com) o [HDtracks](https://www.hdtracks.com).
- **CDs propios** ripeados a FLAC (por ejemplo con
  [Exact Audio Copy](https://www.exactaudiocopy.de/) o
  [fre:ac](https://www.freac.org/)).
- Música con licencia libre de [Jamendo](https://www.jamendo.com),
  [Free Music Archive](https://freemusicarchive.org) o
  [Internet Archive](https://archive.org/details/audio) (mucha en FLAC).

Pon los ficheros en cualquier carpeta (con sus subcarpetas) y ejecuta:

```
./run.sh import ~/Music/Bandcamp --dry-run   # primero, para ver qué encaja
./run.sh import ~/Music/Bandcamp             # copia a downloads/raw/
```

Cada fichero se empareja con una canción de tus playlists por **ISRC** o, si
no lo tiene, por **artista + título** (ignorando acentos, "feat." y
"Remastered"). Si la canción ya estaba descargada en MP3, la versión
lossless la **sustituye** en el reproductor (el MP3 antiguo no se borra).
Al final te lista los ficheros que no ha sabido emparejar.

Opciones: `--import-mode move` (mover en vez de copiar), `--import-mode link`
(hardlink, no ocupa espacio extra) y `--no-upgrade` (no sustituir lo que ya
tienes). En el reproductor verás una etiqueta tipo `FLAC 24-bit/96 kHz`.

> [!NOTE]
> FLAC se reproduce en Chrome/Firefox (Android, PC) y Safari (iPhone, Mac).
> ALAC (`.m4a` de Apple) solo en Safari: para Android, mejor FLAC.

> [!NOTE]
> No hay importador desde YouTube a propósito: descargar de YouTube va contra
> sus Términos de Servicio, y además su audio es AAC/Opus a ~128-160 kbps,
> **peor** que el MP3 320 de Spotify. No ganarías calidad.

---

## Descargar desde YouTube Music

Alternativa a Zotify que no necesita Spotify Premium ni iniciar sesión. Usa
[yt-dlp](https://github.com/yt-dlp/yt-dlp) para buscar cada canción de tus
CSVs en YouTube Music y descargar el audio.

> [!IMPORTANT]
> Igual que con Zotify, descargar de YouTube va contra sus Términos de Servicio.
> Es **uso personal**: no distribuyas lo que descargues.

```
./run.sh index              # si no lo has hecho ya
./run.sh download-yt-test   # prueba con 3 canciones
./run.sh download-yt        # toda la biblioteca en background
./run.sh retry-yt           # reintenta en YouTube lo que falló con Zotify
```

Cómo elige la canción: busca primero en la pestaña *Canciones* de YouTube
Music (los audios oficiales de los canales "- Topic", con la carátula del
álbum) y luego en YouTube. Puntúa cada resultado por título, artista y
**duración** (si tu CSV de Exportify trae la columna *Duration (ms)*, que es lo
normal) y descarta directos, covers, karaoke, remixes, *sped up*… salvo que la
canción original de Spotify también lo sea. Si no encuentra nada fiable, la
marca como `unavailable` en vez de bajar algo que no es.

Puedes mezclar fuentes: las canciones ya descargadas con Zotify no se tocan,
y las que Spotify marcó como "no disponibles" se intentan en YouTube.

### ¿Y la calidad?

Siendo sinceros: **YouTube no suena mejor que Spotify Premium**. Lo que ofrece:

| Fuente | Formato | Calidad aproximada |
| --- | --- | --- |
| Spotify Premium (Zotify) | Ogg Vorbis 320 kbps → convertido a MP3 | Muy alta |
| YouTube Music (yt-dlp) | Opus ~130-160 kbps, original | Alta; Opus a ese bitrate suena casi igual que MP3 320 |
| Bandcamp / Qobuz / 7digital (comprando) | FLAC sin pérdida | Máxima |

Por eso, por defecto Spootify guarda el audio de YouTube **tal cual, sin
recomprimir** (`--yt-format best`, ficheros `.opus` o `.m4a`): cada conversión
pierde algo. Opciones:

```
./run.sh download-yt --yt-format m4a   # AAC; mejor para iPhone/Safari
./run.sh download-yt --yt-format mp3   # recomprime a MP3 (pierde calidad)
```

Si quieres de verdad **más** calidad que Spotify, la vía es comprar en FLAC
(Bandcamp, Qobuz…). El reproductor ya lee FLAC, Opus, M4A y MP3.

> [!TIP]
> YouTube cambia a menudo y yt-dlp se actualiza para seguirle el ritmo. Si las
> descargas empiezan a fallar, vuelve a lanzar `./setup.sh` (actualiza yt-dlp).

---

## Usar Spootify en Android

El ordenador sigue siendo el que guarda la música y ejecuta `./run.sh serve`;
el móvil la reproduce por la red. Hay dos formas, elige una:

### Opción A — Instalar como app desde Chrome (recomendada)

Es lo más sencillo y lo que mejor funciona en segundo plano: controles en la
pantalla de bloqueo y en la notificación, botones de auriculares Bluetooth y
Android Auto.

1. En el móvil abre Chrome en `http://<ip-del-ordenador>:8000`.
2. Menú ⋮ → **Añadir a pantalla de inicio** / **Instalar app**.

Chrome solo instala la app "de verdad" (pantalla completa, icono propio,
arranque instantáneo) si la web va por **HTTPS**. La forma más fácil de
tenerlo, y de escuchar tu música también **fuera de casa**, es
[Tailscale](https://tailscale.com) (gratis para uso personal):

```
# En el ordenador, con Tailscale instalado y la sesión iniciada:
tailscale serve --bg 8000
```

Instala Tailscale también en el móvil con la misma cuenta, y abre en Chrome
la dirección `https://<nombre-del-ordenador>.<tu-tailnet>.ts.net` que te
muestra el comando. Desde ahí, **Instalar app**.

### Opción B — APK de Android

En `android-app/` hay una app Android (Capacitor) que abre el reproductor de
tu ordenador. La primera vez te pide la dirección (`192.168.1.20:8000`, o la
de Tailscale) y la recuerda. El botón "atrás" la manda a segundo plano sin
cortar la música, y mantiene una notificación para que Android no la cierre
con la pantalla apagada.

**Descargar el APK ya compilado:** en GitHub → pestaña **Actions** → workflow
**Android APK** → la ejecución más reciente → *Artifacts* → `spootify-apk`.
Descomprime el zip, pasa `app-debug.apk` al móvil y ábrelo (Android te pedirá
permitir "instalar apps de origen desconocido").

**Compilarlo tú** (necesitas Node 20+ y Android Studio / JDK 21):

```
cd android-app
npm install
npm run build:debug   # → android/app/build/outputs/apk/debug/app-debug.apk
```

> [!NOTE]
> Con el APK la pantalla de bloqueo no muestra carátula ni botones de
> siguiente/anterior (el WebView de Android no los expone). Si los quieres,
> usa la opción A.

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
./run.sh download        # Descarga toda la biblioteca en background (Spotify)
./run.sh download-yt-test # Descarga 3 canciones desde YouTube Music (prueba)
./run.sh download-yt     # Descarga toda la biblioteca desde YouTube Music
./run.sh retry-yt        # Reintenta en YouTube las que fallaron
./run.sh progress        # Snapshot del progreso
./run.sh watch           # Progreso en vivo
./run.sh stop            # Para la descarga
./run.sh retry           # Reintenta fallos
./run.sh import <dir>    # Importa tus FLAC/ALAC/WAV
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
│   ├── youtube.py          # Descargas desde YouTube Music (yt-dlp)
│   ├── artwork.py          # Extracción de carátulas
│   ├── local_import.py     # Importador de audio propio (FLAC, ALAC...)
│   └── server.py           # Reproductor web (FastAPI)
├── web/                    # Front-end React (Babel in-browser), PWA instalable
│   ├── index.html
│   ├── manifest.webmanifest
│   ├── sw.js
│   ├── components.jsx
│   ├── screens.jsx
│   └── player.jsx
├── android-app/            # App Android (Capacitor) → APK
├── playlists_csv/          # ⬅ Tú pones aquí los CSVs de Exportify
├── downloads/raw/          # MP3s descargados
└── state/                  # Estado interno (índice, descargados, fallos)
```

---

## Licencia

MIT (uso personal). No te hago responsable a ti ni a mí del uso indebido.
