/* GPS de campo: funciona sin internet (solo satélites), no se rinde y guarda el recorrido en el celular.
   - Muestra de inmediato la última posición que el celular ya conoce, mientras llegan los satélites.
   - Vigila sin límite de tiempo; si el GPS se cae, vuelve a pedirlo solo.
   - Mantiene la pantalla encendida mientras la ubicación está activa (si la pantalla se apaga, el navegador deja de leer el GPS).
   - Guarda el recorrido (puntos con precisión de 30 m o mejor) aunque se cierre la página, y lo exporta en GPX.
   Uso: GPSCampo.iniciar({posicion(p, info), esperando(seg), perdida(seg), error(e), recorrido(puntos)}) · GPSCampo.detener() */
(function () {
  const CLAVE = 'recorrido:' + location.pathname.replace(/index\.html$/, '');
  const PREC_MAX = 30, PASO_MIN = 3;            // metros
  let vigia = null, reloj = null, t0 = 0, ultima = 0, cb = null, bloqueo = null, activo = false;

  function leer() { try { return JSON.parse(localStorage.getItem(CLAVE) || '[]'); } catch (e) { return []; } }
  let puntos = leer();
  function guardar() { try { localStorage.setItem(CLAVE, JSON.stringify(puntos)); } catch (e) { /* sin espacio: se queda en memoria */ } }

  function distancia(a, b) {   // metros, fórmula del haversine
    const r = Math.PI / 180, dlat = (b[0] - a[0]) * r, dlon = (b[1] - a[1]) * r;
    const h = Math.sin(dlat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dlon / 2) ** 2;
    return 12742000 * Math.asin(Math.sqrt(h));
  }
  function longitud() { let s = 0; for (let i = 1; i < puntos.length; i++) if (!puntos[i][4]) s += distancia(puntos[i - 1], puntos[i]); return s; }

  function anotar(p) {
    const c = p.coords; if (!(c.accuracy <= PREC_MAX)) return;
    const q = [+c.latitude.toFixed(7), +c.longitude.toFixed(7), Date.now(), Math.round(c.accuracy), 0,
               c.altitude == null ? null : Math.round(c.altitude * 10) / 10];
    const u = puntos[puntos.length - 1];
    if (u && distancia(u, q) < Math.max(PASO_MIN, c.accuracy / 3)) return;
    if (u && Date.now() - u[2] > 10 * 60000) q[4] = 1;   // pausa larga: arranca un tramo nuevo
    puntos.push(q); guardar(); if (cb && cb.recorrido) cb.recorrido(puntos);
  }

  async function despierto(on) {
    try {
      if (on && 'wakeLock' in navigator && document.visibilityState === 'visible') { bloqueo = await navigator.wakeLock.request('screen'); }
      else if (!on && bloqueo) { await bloqueo.release(); bloqueo = null; }
    } catch (e) { bloqueo = null; }
  }
  document.addEventListener('visibilitychange', () => {
    if (!activo) return;
    if (document.visibilityState === 'visible') { despierto(true); vigilar(); }   // al volver a la página, se retoma
  });

  function vigilar() {
    if (vigia !== null) navigator.geolocation.clearWatch(vigia);
    vigia = navigator.geolocation.watchPosition((p) => {
      ultima = Date.now(); if (cb.guardar !== false) anotar(p); cb.posicion(p, {vieja: false});
    }, (e) => {
      if (e.code === 1) { cb.error(e); detener(); return; }
      setTimeout(() => { if (activo) vigilar(); }, 3000);     // sin señal: se vuelve a pedir, nunca se rinde
    }, {enableHighAccuracy: true, maximumAge: 0});
  }

  function iniciar(o) {
    cb = o; activo = true; t0 = Date.now(); ultima = 0;
    if (!('geolocation' in navigator)) { cb.error({code: 0}); return; }
    // Lo último que el celular ya sabe (sirve sin internet): aparece al instante mientras llegan los satélites
    navigator.geolocation.getCurrentPosition((p) => { if (!ultima && activo) cb.posicion(p, {vieja: true}); },
      () => {}, {enableHighAccuracy: false, maximumAge: Infinity, timeout: 5000});
    vigilar(); despierto(true);
    clearInterval(reloj);
    reloj = setInterval(() => {
      if (!ultima) cb.esperando((Date.now() - t0) / 1000);
      else if (Date.now() - ultima > 25000 && cb.perdida) cb.perdida((Date.now() - ultima) / 1000);
    }, 1000);
    if (cb.recorrido && cb.guardar !== false) cb.recorrido(puntos);
  }
  function detener() {
    activo = false; clearInterval(reloj); reloj = null;
    if (vigia !== null) navigator.geolocation.clearWatch(vigia); vigia = null; despierto(false);
  }

  function gpx(nombre) {
    const t = (ms) => new Date(ms).toISOString();
    let s = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="GPS de campo" xmlns="http://www.topografix.com/GPX/1/1">\n'
          + `<trk><name>${(nombre || 'Recorrido').replace(/[<&>]/g, '')}</name><trkseg>\n`;
    puntos.forEach((p, i) => {
      if (i && p[4]) s += '</trkseg><trkseg>\n';
      s += `<trkpt lat="${p[0]}" lon="${p[1]}">${p[5] == null ? '' : `<ele>${p[5]}</ele>`}<time>${t(p[2])}</time><desc>±${p[3]} m</desc></trkpt>\n`;
    });
    return s + '</trkseg></trk>\n</gpx>\n';
  }
  function descargar(nombre) {
    const b = new Blob([gpx(nombre)], {type: 'application/gpx+xml'}), a = document.createElement('a');
    const d = new Date(), f = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    a.href = URL.createObjectURL(b); a.download = `recorrido_${f}.gpx`; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function borrar() { puntos = []; guardar(); if (cb && cb.recorrido) cb.recorrido(puntos); }

  /* Dibuja el recorrido sobre el plano 2D (OpenSeadragon). aPx(lat, lon) → {x, y} en píxeles de la imagen, o null. */
  let capa = null;
  function dibujar2d(visor, aPx, ancho, alto) {
    if (!visor || !visor.world.getItemAt(0)) return;
    if (!capa) {
      capa = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      capa.setAttribute('viewBox', `0 0 ${ancho} ${alto}`); capa.setAttribute('preserveAspectRatio', 'none');
      capa.style.pointerEvents = 'none'; capa.innerHTML = '<g fill="none" stroke-linejoin="round" stroke-linecap="round"></g>';
      visor.addOverlay({element: capa, location: new OpenSeadragon.Rect(0, 0, 1, alto / ancho)});
    }
    const g = capa.firstChild; let d = '';
    puntos.forEach((p, i) => { const q = aPx(p[0], p[1]); if (!q) return; d += `${i && !p[4] && d ? 'L' : 'M'}${q.x.toFixed(1)} ${q.y.toFixed(1)}`; });
    // línea discreta: azul oscuro semitransparente con un borde blanco fino, para que no tape el plano
    g.innerHTML = d ? `<path d="${d}" stroke="#fff" stroke-opacity=".7" stroke-width="4" vector-effect="non-scaling-stroke"/>`
                    + `<path d="${d}" stroke="#1f4e8c" stroke-opacity=".85" stroke-width="2" vector-effect="non-scaling-stroke"/>` : '';
  }

  window.GPSCampo = {iniciar, detener, descargar, borrar, dibujar2d, longitud, puntos: () => puntos, activo: () => activo};
})();
