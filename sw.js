// Guarda el visor en el celular para que abra sin internet.
const CACHE = 'plano-corredor-v2';
const BASE = ['./', 'index.html', 'ver.html', 'lib/model-viewer.min.js', 'plano_relieve.glb', 'poster_relieve.jpg', 'alturas.json'];
const TODO = BASE.concat([
  'ra.html', 'plano_relieve.usdz', 'marcador.patt', 'marcador_10cm_carta.pdf',
  'lib/three/three.min.js', 'lib/three/GLTFLoader.js',
  'lib/8thwall/xr.js', 'lib/8thwall/xr-slam.js', 'lib/8thwall/resources/media-worker.js',
  'lib/aframe-v1.3.0.min.js', 'lib/aframe-ar.js', 'lib/camera_para.dat',
]);

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('message', (e) => {
  if (e.data !== 'guardarTodo') return;
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(TODO))
    .then(() => e.source.postMessage('guardado'))
    .catch(() => e.source.postMessage('error')));
});

// Primero la copia guardada; si no existe, la red, y se guarda para la próxima vez.
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin || req.headers.has('range')) return;
  e.respondWith(caches.match(req, {ignoreSearch: true}).then((hit) => hit || fetch(req).then((res) => {
    if (res.ok && res.type === 'basic') { const copia = res.clone(); caches.open(CACHE).then((c) => c.put(req, copia)); }
    return res;
  })));
});
