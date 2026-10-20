// Versión 3 (GPS de campo sin internet y recorrido): guarda el visor en el celular. Usa la red cuando hay conexión (siempre la versión más reciente)
// y la copia guardada cuando no la hay.
const CACHE = 'plano-corredor-v3-2';
const MARCA = 'marca-guardado-completo';
const BASE = ['./', 'index.html', 'ver.html', '../lib/model-viewer.min.js', 'lib/openseadragon.min.js', 'lib/gps-campo.js',
  'plano_relieve.glb', 'poster_relieve.jpg', 'alturas.json', 'plano2d/plano.dzi', 'logo_invercoal.png', 'etiquetas.json', 'manifest.webmanifest', 'icono-192.png', 'icono-512.png'];
const MOTOR = ['../lib/three/three.min.js', '../lib/three/GLTFLoader.js', '../lib/8thwall/xr.js', '../lib/8thwall/xr-slam.js',
  '../lib/8thwall/resources/media-worker.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASE)).then(() => self.skipWaiting()));
});

// Al actualizar la página no se pierde lo ya guardado: las teselas del plano 2D, el motor de RA y la marca
// de «guardado completo» pasan de la copia anterior a la nueva; el resto se descarta.
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const nueva = await caches.open(CACHE);
    for (const k of await caches.keys()) {
      if (!k.startsWith('plano-corredor-v3') || k === CACHE) continue;
      const vieja = await caches.open(k);
      for (const req of await vieja.keys()) {
        const u = req.url;
        if (u.includes('/plano2d/plano_files/') || u.includes('/lib/') || u.endsWith(MARCA)) {
          if (!(await nueva.match(req))) await nueva.put(req, await vieja.match(req));
        }
      }
      await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

async function guardarTodo(){
  const c = await caches.open(CACHE);
  await c.addAll(BASE.concat(MOTOR));
  const teselas = await (await fetch('lista_plano2d.json')).json();
  for (let i = 0; i < teselas.length; i += 60) await c.addAll(teselas.slice(i, i + 60));
  await c.put(MARCA, new Response(new Date().toISOString()));
}
self.addEventListener('message', (e) => {
  if (e.data !== 'guardarTodo') return;
  e.waitUntil(guardarTodo().then(() => e.source.postMessage('guardado')).catch(() => e.source.postMessage('error')));
});

// Primero la red (siempre lo más reciente); si no hay conexión, la copia guardada. Si hay copia y la red tarda
// más de 4 s (señal débil en campo), se usa la copia y la red la actualiza por detrás para la próxima vez.
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin || req.headers.has('range')) return;
  e.respondWith((async () => {
    const red = fetch(req).then((res) => {
      if (res.ok && res.type === 'basic') { const copia = res.clone(); caches.open(CACHE).then((c) => c.put(req, copia)); }
      return res;
    });
    const hit = await caches.match(req, {ignoreSearch: true});
    if (!hit) return red.catch(() => Response.error());
    e.waitUntil(red.catch(() => null));
    return Promise.race([red, new Promise((ok) => setTimeout(() => ok(hit), 4000))]).catch(() => hit);
  })());
});
