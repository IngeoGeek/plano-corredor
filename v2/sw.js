// Versión 2: guarda el visor en el celular. Usa la red cuando hay conexión (siempre la versión más reciente)
// y la copia guardada cuando no la hay.
const CACHE = 'plano-corredor-v2-2';
const BASE = ['./', 'index.html', 'ver.html', '../lib/model-viewer.min.js', 'lib/openseadragon.min.js',
  'plano_relieve.glb', 'poster_relieve.jpg', 'alturas.json', 'plano2d/plano.dzi', 'logo_invercoal.png'];
const MOTOR = ['../lib/three/three.min.js', '../lib/three/GLTFLoader.js', '../lib/8thwall/xr.js', '../lib/8thwall/xr-slam.js',
  '../lib/8thwall/resources/media-worker.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k.startsWith('plano-corredor-v2') && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function guardarTodo(){
  const c = await caches.open(CACHE);
  await c.addAll(BASE.concat(MOTOR));
  const teselas = await (await fetch('lista_plano2d.json')).json();
  for (let i = 0; i < teselas.length; i += 60) await c.addAll(teselas.slice(i, i + 60));
}
self.addEventListener('message', (e) => {
  if (e.data !== 'guardarTodo') return;
  e.waitUntil(guardarTodo().then(() => e.source.postMessage('guardado')).catch(() => e.source.postMessage('error')));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin || req.headers.has('range')) return;
  e.respondWith(fetch(req).then((res) => {
    if (res.ok && res.type === 'basic') { const copia = res.clone(); caches.open(CACHE).then((c) => c.put(req, copia)); }
    return res;
  }).catch(() => caches.match(req, {ignoreSearch: true}).then((hit) => hit || Response.error())));
});
