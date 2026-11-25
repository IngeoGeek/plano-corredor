// Vidal RB: guarda la página para usarla sin internet. Lee config.js; no hace falta editarlo.
// Prefijo de caché propio: otras maquetas del mismo dominio (ingeogeek.github.io) no se borran entre sí.
importScripts('config.js');
const C = self.PLANO, PREFIJO = 'vidalrb2-v', CACHE = `${PREFIJO}${C.version}`, MARCA = `vidalrb2-marca-v${C.version}`;
const A = C.archivos;
const BASE = ['./', 'index.html', 'config.js', 'manifest.webmanifest', 'icono-192.png', 'icono-512.png',
  'lib/model-viewer.min.js', 'lib/openseadragon.min.js', A.modelo, C.relieve.imagen, A.plano2d]
  .concat([A.modelo_iphone, A.poster, C.pie && C.pie.logo].filter(Boolean))
  .concat((C.etiquetas || []).map((e) => e.archivo));
const MOTOR = ['lib/three/three.min.js', 'lib/three/GLTFLoader.js', 'lib/8thwall/xr.js', 'lib/8thwall/xr-slam.js', 'lib/8thwall/resources/media-worker.js'];

self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.add('./').catch(() => {})).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if ((k.startsWith(PREFIJO) && k !== CACHE) || k.startsWith('vidalrb-v')) await caches.delete(k);  // 'vidalrb-v' = versión anterior del visor
    await self.clients.claim();
  })());
});
async function guardarTodo(){
  const c = await caches.open(CACHE), faltan = [];
  for (const u of BASE.concat(MOTOR)) { try { await c.add(u); } catch (e) { faltan.push(u); } }
  if (faltan.length) throw new Error(faltan.join(', '));
  await c.put(MARCA, new Response(new Date().toISOString()));
}
self.addEventListener('message', (e) => {
  if (e.data !== 'guardarTodo') return;
  e.waitUntil(guardarTodo().then(() => e.source.postMessage('guardado')).catch((err) => e.source.postMessage('error:' + err.message)));
});
// Primero la red (siempre lo más nuevo); sin conexión, la copia guardada
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin || req.headers.has('range')) return;
  e.respondWith(fetch(req).then((res) => {
    if (res.ok && res.type === 'basic') { const copia = res.clone(); caches.open(CACHE).then((c) => c.put(req, copia)); }
    return res;
  }).catch(() => caches.match(req, {ignoreSearch: true}).then((hit) => hit || Response.error())));
});
