// Guarda la página en el celular para usarla sin internet. No hace falta editarlo: lee config.js.
importScripts('config.js');
const C = self.PLANO, CACHE = `plano-v${C.version}`, MARCA = `marca-guardado-v${C.version}`;
const A = C.archivos;
const BASE = ['./', 'index.html', 'config.js', 'manifest.webmanifest', 'icono-192.png', 'icono-512.png',
  'lib/model-viewer.min.js', 'lib/openseadragon.min.js', 'lib/gps-campo.js', A.modelo, C.relieve.imagen, A.plano2d]
  .concat([A.modelo_iphone, A.poster, C.pie && C.pie.logo].filter(Boolean))
  .concat((C.etiquetas || []).map((e) => e.archivo));
const MOTOR = ['lib/three/three.min.js', 'lib/three/GLTFLoader.js', 'lib/8thwall/xr.js', 'lib/8thwall/xr-slam.js', 'lib/8thwall/resources/media-worker.js'];

self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.add('./').catch(() => {})).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('plano-v') && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

// Lista de teselas a partir del archivo .dzi (ancho, alto, tamaño de tesela)
async function teselas(){
  if (!/\.dzi$/i.test(A.plano2d)) return [];
  const xml = await (await fetch(A.plano2d)).text(), n = (k) => +(xml.match(new RegExp(k + '="(\\d+)"')) || [])[1];
  const W = n('Width'), H = n('Height'), T = n('TileSize'), fmt = (xml.match(/Format="(\w+)"/) || [])[1] || 'jpg';
  const base = A.plano2d.replace(/\.dzi$/i, '_files/'), max = Math.ceil(Math.log2(Math.max(W, H))), lista = [];
  for (let L = 0; L <= max; L++){
    const s = Math.pow(2, L - max), w = Math.ceil(W * s), h = Math.ceil(H * s);
    for (let c = 0; c < Math.ceil(w / T); c++) for (let r = 0; r < Math.ceil(h / T); r++) lista.push(`${base}${L}/${c}_${r}.${fmt}`);
  }
  return lista;
}
async function guardarTodo(){
  const c = await caches.open(CACHE);
  const faltan = [];
  for (const u of BASE.concat(MOTOR)) { try { await c.add(u); } catch (e) { faltan.push(u); } }
  if (faltan.length) throw new Error(faltan.join(', '));
  const t = await teselas();
  for (let i = 0; i < t.length; i += 60) await c.addAll(t.slice(i, i + 60));
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
