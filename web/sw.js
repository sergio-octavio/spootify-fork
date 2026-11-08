// Service worker de Spootify.
// - Hace la app instalable en Android ("Instalar app" en Chrome).
// - Cachea la interfaz (HTML, JSX, librerías) para que arranque al instante y
//   siga abriéndose aunque el servidor tarde en responder.
// - NO toca /media (audio con peticiones Range) ni /api salvo library.json,
//   que se sirve de la red y cae a la última copia si no hay conexión.
const CACHE = 'spootify-shell-v1';
const SHELL = [
  '/', '/index.html', '/components.jsx', '/screens.jsx', '/player.jsx',
  '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Audio y carátulas: directo a la red (el <audio> necesita Range requests).
  if (url.origin === location.origin && url.pathname.startsWith('/media/')) return;
  if (url.origin === location.origin && url.pathname.startsWith('/api/')
      && url.pathname !== '/api/library.json') return;

  const sameOrigin = url.origin === location.origin;
  const cdn = /(^|\.)unpkg\.com$|fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!sameOrigin && !cdn) return;

  // Network-first: siempre la versión nueva si el servidor responde.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok || res.type === 'opaque') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true }).then((hit) => hit || Response.error()))
  );
});
