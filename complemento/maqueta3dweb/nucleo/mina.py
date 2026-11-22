# -*- coding: utf-8 -*-
"""Maqueta 3D de una mina subterránea a partir del plano de labores (DWG/DXF).

Flujo: leer capas → asignar cotas → red de galerías (uniones, frentes, bocaminas) → tramos, distancias y cubierta →
modelo ilustrativo de metano → sólidos 3D por capa + superficie (DEM o fotogrametría) + límite del título → página,
plano 2D y plano carta con QR.

Escena de la página igual que el kit: glTF con x al este, y arriba, z al sur, origen en el centro de la extensión;
1 unidad = 1 m de la maqueta física a escala 1:esc. Las medidas de la página se pasan a metros reales con esc."""
import datetime, heapq, json, math, os, shutil
import numpy as np
from . import cad

BASE = 0.0005
G = 9.81
DRHO = 0.45   # (ρaire − ρmetano)/ρaire en el número de estratificación de Bakke y Leach
TIPOS_LABOR = ('nivel', 'inclinado', 'cruzada', 'tambor', 'sobreguia', 'patio', 'frente', 'abandonada', 'proyectada', 'otra')
KIT_MINA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'kit_mina')
KIT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'kit')

# Clases según el artículo 53 del Decreto 1886 de 2015 (Reglamento de Seguridad en las Labores Mineras Subterráneas)
UMBRALES = (0.5, 1.0, 1.5, 2.0)
CLASES_CH4 = [
    ('#2e9e44', 'Hasta 0,5 %'),
    ('#f2b705', 'Más de 0,5 %: en minas de categoría II o III ese aire de retorno ya no puede pasar a frentes de producción (art. 53, parágrafo 2)'),
    ('#ef6c00', 'Más de 1,0 %: supera el máximo para frentes de trabajo y retornos principales; se suspenden labores y se retira al personal (art. 53)'),
    ('#d32f2f', 'Más de 1,5 %: supera también el máximo para retornos de tajos y de frentes de preparación y desarrollo (art. 53)'),
    ('#7b1fa2', 'Más de 2,0 %: solo entra personal de salvamento con equipo de protección, para diluir el gas (art. 53, parágrafo 1)')]


def clase_ch4(c):
    return sum(1 for u in UMBRALES if c > u)


def _color_ch4(c):
    """Rampa continua verde → amarillo → naranja → rojo → violeta para los vértices del halo de gas."""
    pts = [(0.0, (46, 158, 68)), (0.5, (242, 183, 5)), (1.0, (239, 108, 0)), (1.5, (211, 47, 47)), (2.0, (123, 31, 162))]
    c = max(0.0, min(2.0, c))
    for (a, ca), (b, cb) in zip(pts[:-1], pts[1:]):
        if c <= b:
            t = (c - a) / (b - a); return tuple(int(ca[k] + (cb[k] - ca[k]) * t) for k in range(3))
    return pts[-1][1]


def _num(v, d=1):
    return f'{v:,.{d}f}'.replace(',', ' ').replace('.', ',')


# ---------------------------------------------------------------- 1. Análisis del plano
def analizar(ruta, registro=print):
    D = cad.leer(ruta, registro)
    tabla = []
    for nombre, info in sorted(D['capas'].items(), key=lambda kv: kv[0].lower()):
        tipo = cad.tipo_sugerido(nombre, info)
        an, al = cad.SECCION.get(tipo, (2.0, 1.8))
        usar = info['visible'] and tipo not in ('ignorar', 'otra')
        tabla.append({'nombre': nombre, 'lineas': info['lineas'], 'textos': info['textos'], 'puntos': info['puntos'],
                      'color': cad.rgb_hex(info['color']), 'tipo': tipo, 'visible': info['visible'], 'ancho': an, 'alto': al,
                      'cota': None, 'usar': usar})
    D['tabla'] = tabla
    zs = [p[2] for l in D['lineas'] for p in l['xyz']]
    D['es_3d'] = bool(zs) and (max(zs) - min(zs) > 0.5)
    D['ruta'] = ruta
    registro(f"Plano leído ({D['version']}, unidades: {D['unidades']}): {len(D['lineas'])} líneas, {len(D['textos'])} textos y "
             f"{len(D['capas'])} capas. " + ('Los ejes traen cota (plano 3D).' if D['es_3d'] else
                                             'Los ejes no traen cota: se toman de los textos de cota o de la cota fija de cada capa.'))
    if D['unidades'] in ('milímetros', 'centímetros', 'pulgadas'):
        registro(f"Aviso: el dibujo está en {D['unidades']}; la maqueta supone coordenadas en metros.")
    return D


def _densificar(P, paso):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.linalg.norm(b[:2] - a[:2]))
        if L < 1e-6 and abs(b[2] - a[2]) < 1e-6: continue
        n = max(1, int(math.ceil(max(L, abs(b[2] - a[2])) / paso)))
        for k in range(1, n + 1): out.append(a + (b - a) * (k / n))
    return np.array(out)


def _cadenamiento(P):
    return np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1])))])


def _cotas_de_textos(D, tabla):
    """Textos de cota del plano (de las capas marcadas como cota; si no hay, de todos los textos), sin valores atípicos."""
    capas_cota = {t['nombre'] for t in tabla if t['tipo'] == 'cota' and t.get('usar', True)}
    out = []
    for t in D['textos']:
        if capas_cota and t['capa'] not in capas_cota: continue
        v = cad.numero_cota(t['texto'])
        if v is not None: out.append((t['xyz'][0], t['xyz'][1], v))
    C = np.array(out) if out else np.zeros((0, 3))
    if len(C) >= 3:
        med = np.median(C[:, 2]); C = C[np.abs(C[:, 2] - med) <= 400]
    return C


def _proyectar(C, P):
    """Distancia de cada punto C (k×2) a la polilínea P y cadenamiento del punto más cercano."""
    A, B = P[:-1, :2], P[1:, :2]; AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    s0 = _cadenamiento(P)[:-1]; Ls = np.sqrt(L2)
    AP = C[:, None, :2] - A[None]; t = np.clip((AP * AB[None]).sum(2) / L2[None], 0, 1)
    Q = A[None] + AB[None] * t[..., None]; d = np.hypot(*(Q - C[:, None, :2]).transpose(2, 0, 1))
    j = d.argmin(1); k = np.arange(len(C))
    return d[k, j], s0[j] + t[k, j] * Ls[j]


def _asignar_cotas(lineas, C, radio, registro):
    """Ejes 2D: los textos de cota cercanos se proyectan sobre el eje y la cota se interpola a lo largo de él.
    Un eje sin textos cerca toma la cota de los ejes vecinos en sus extremos."""
    pendientes = []
    for l in [l for l in lineas if not l.get('con_cota')]:
        P = l['P']
        if l.get('cota_fija') is not None:
            P[:, 2] = float(l['cota_fija']); l['con_cota'] = True; continue
        if len(C):
            x0, y0 = P[:, :2].min(0) - radio; x1, y1 = P[:, :2].max(0) + radio
            cerca = C[(C[:, 0] >= x0) & (C[:, 0] <= x1) & (C[:, 1] >= y0) & (C[:, 1] <= y1)]
            if len(cerca) and len(P) >= 2:
                d, s = _proyectar(cerca, P); ok = d <= radio
                if ok.any():
                    orden = np.argsort(s[ok], kind='stable')
                    P[:, 2] = np.interp(_cadenamiento(P), s[ok][orden], cerca[ok, 2][orden]); l['con_cota'] = True; continue
        pendientes.append(l)
    for _ in range(3):   # se propaga de vecino en vecino
        ref = [l for l in lineas if l.get('con_cota')]
        if not ref or not pendientes: break
        V = np.concatenate([l['P'] for l in ref]); quedan = []
        for l in pendientes:
            zs = []
            for p in (l['P'][0], l['P'][-1]):
                d = np.hypot(V[:, 0] - p[0], V[:, 1] - p[1]); k = int(d.argmin())
                zs.append(V[k, 2] if d[k] <= 5 else None)
            s = _cadenamiento(l['P'])
            if zs[0] is not None and zs[1] is not None: l['P'][:, 2] = np.interp(s, [0, s[-1]], zs)
            elif zs[0] is not None or zs[1] is not None: l['P'][:, 2] = zs[0] if zs[0] is not None else zs[1]
            else: quedan.append(l); continue
            l['con_cota'] = True
        pendientes = quedan
    if pendientes:
        ref = [l for l in lineas if l.get('con_cota')]
        z = float(np.median(np.concatenate([l['P'][:, 2] for l in ref]))) if ref else 0.0
        for l in pendientes: l['P'][:, 2] = z; l['cota_supuesta'] = True
        registro(f'Aviso: {len(pendientes)} eje(s) quedaron sin cota conocida y se dibujan a la cota media ({_num(z)} m). '
                 'Revisa los textos de cota o pon una cota fija a su capa.')


def _cruces(lineas, tol_z=2.5):
    """Une los ejes que se cruzan en planta a la misma cota (p. ej. un nivel dibujado de lado a lado que atraviesa el
    inclinado): agrega el punto de cruce a los dos ejes. Si las cotas difieren más de tol_z, una labor pasa por encima de
    la otra y no se unen."""
    cajas = [np.r_[l['P'][:, :2].min(0), l['P'][:, :2].max(0)] for l in lineas]
    nuevos = [[] for _ in lineas]; n = 0
    for i in range(len(lineas)):
        for j in range(i + 1, len(lineas)):
            a, b = cajas[i], cajas[j]
            if a[0] > b[2] + 0.1 or b[0] > a[2] + 0.1 or a[1] > b[3] + 0.1 or b[1] > a[3] + 0.1: continue
            P, Q = lineas[i]['P'], lineas[j]['P']
            r, s_ = np.diff(P[:, :2], axis=0), np.diff(Q[:, :2], axis=0)
            qp = Q[None, :-1, :2] - P[:-1, None, :2]
            rxs = r[:, None, 0] * s_[None, :, 1] - r[:, None, 1] * s_[None, :, 0]
            with np.errstate(divide='ignore', invalid='ignore'):
                t = (qp[..., 0] * s_[None, :, 1] - qp[..., 1] * s_[None, :, 0]) / rxs
                u = (qp[..., 0] * r[:, None, 1] - qp[..., 1] * r[:, None, 0]) / rxs
            e = 1e-9
            ok = (np.abs(rxs) > 1e-9) & (t >= -e) & (t <= 1 + e) & (u >= -e) & (u <= 1 + e)
            for si, sj in zip(*np.nonzero(ok)):
                tt, uu = float(np.clip(t[si, sj], 0, 1)), float(np.clip(u[si, sj], 0, 1))
                pa = P[si] + (P[si + 1] - P[si]) * tt; pb = Q[sj] + (Q[sj + 1] - Q[sj]) * uu
                if abs(pa[2] - pb[2]) > tol_z: continue
                pm = (pa + pb) / 2; nuevos[i].append((si, tt, pm)); nuevos[j].append((sj, uu, pm)); n += 1
    for l, ins in zip(lineas, nuevos):
        if not ins: continue
        P = l['P'].copy(); extra = {}
        for k, t, pm in ins:
            if t < 1e-6: P[k] = pm
            elif t > 1 - 1e-6: P[k + 1] = pm
            else: extra.setdefault(k, []).append((t, pm))
        out = []
        for k in range(len(P)):
            out.append(P[k])
            for t, pm in sorted(extra.get(k, []), key=lambda x: x[0]): out.append(pm)
        l['P'] = np.array(out)
    return n


class Red:
    """Grafo de galerías: nodos (E, N, Z) y aristas con su longitud 3D y su capa. Une vértices cercanos y empalmes en T."""
    def __init__(self, lineas, tol=0.6, tol_t=1.6):
        from scipy.spatial import cKDTree
        nodos, tabla_h = [], {}

        def nodo(p):
            k = tuple(np.floor(p / tol).astype(int))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for j in tabla_h.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                            if np.linalg.norm(nodos[j] - p) <= tol: return j
            nodos.append(np.array(p, float)); tabla_h.setdefault(k, []).append(len(nodos) - 1); return len(nodos) - 1
        self.ady, self.capa_arista = {}, {}
        for l in lineas:
            ids = [nodo(p) for p in l['P']]; l['nodos'] = ids
            for a, b in zip(ids[:-1], ids[1:]):
                if a != b: self._arista(a, b, nodos, l['capa'])
        self.N = np.array(nodos)
        dueno = {}
        for li, l in enumerate(lineas):
            for n in l['nodos']: dueno.setdefault(n, set()).add(li)
        arbol = cKDTree(self.N)
        for li, l in enumerate(lineas):   # empalmes en T: el extremo suelto de un eje que toca el costado de otro
            for e in (l['nodos'][0], l['nodos'][-1]):
                if len(self.ady.get(e, ())) != 1: continue
                cand = [k for k in arbol.query_ball_point(self.N[e], tol_t)
                        if k != e and not dueno.get(k, set()) <= {li} and k not in self.ady.get(e, {})]
                if cand:
                    k = min(cand, key=lambda k: float(np.linalg.norm(self.N[k] - self.N[e])))
                    self._arista(e, k, self.N, l['capa'])

    def _arista(self, a, b, nodos, capa):
        L = float(np.linalg.norm(np.asarray(nodos[a]) - np.asarray(nodos[b])))
        self.ady.setdefault(a, {})[b] = L; self.ady.setdefault(b, {})[a] = L
        self.capa_arista[(min(a, b), max(a, b))] = capa

    def grado(self, n): return len(self.ady.get(n, ()))

    def capa(self, a, b): return self.capa_arista.get((min(a, b), max(a, b)))

    def dijkstra(self, fuentes, prohibidos=()):
        dist = {f: 0.0 for f in fuentes}; prev = {}; q = [(0.0, f) for f in fuentes]; heapq.heapify(q)
        while q:
            d, u = heapq.heappop(q)
            if d > dist.get(u, math.inf): continue
            for v, L in self.ady.get(u, {}).items():
                if v in prohibidos: continue
                nd = d + L
                if nd < dist.get(v, math.inf): dist[v] = nd; prev[v] = u; heapq.heappush(q, (nd, v))
        return dist, prev

    def camino(self, prev, destino):
        c = [destino]
        while c[-1] in prev: c.append(prev[c[-1]])
        return c


def tramos(red):
    """Tramos entre uniones, extremos o cambios de capa, con su longitud 3D."""
    clave = set()
    for n, vec in red.ady.items():
        if len(vec) != 2: clave.add(n); continue
        a, b = list(vec)
        if red.capa(n, a) != red.capa(n, b): clave.add(n)
    vistos, out = set(), []

    def recorrer(n0, v):
        cam, L, prev, cur = [n0, v], red.ady[n0][v], n0, v
        vistos.add((min(n0, v), max(n0, v)))
        while cur not in clave:
            nxt = next(x for x in red.ady[cur] if x != prev); e = (min(cur, nxt), max(cur, nxt))
            if e in vistos: break
            vistos.add(e); L += red.ady[cur][nxt]; cam.append(nxt); prev, cur = cur, nxt
        return {'nodos': cam, 'L': L, 'capa': red.capa(cam[0], cam[1])}
    for n0 in list(clave):
        for v in list(red.ady[n0]):
            if (min(n0, v), max(n0, v)) not in vistos: out.append(recorrer(n0, v))
    for n0 in list(red.ady):   # anillos sin uniones
        for v in list(red.ady[n0]):
            if (min(n0, v), max(n0, v)) not in vistos: clave.add(n0); out.append(recorrer(n0, v))
    return out


# ---------------------------------------------------------------- 2. Preparar la mina (cotas, red, frentes, bocaminas)
def preparar(D, tabla, op, registro=print):
    """tabla: filas de la tabla del complemento ('usar', 'tipo', 'color', 'ancho', 'alto', 'cota').
    op: {'eje': 'piso'|'centro'|'techo', 'radio_cota': 12}"""
    porcapa = {t['nombre']: t for t in tabla}
    lineas = []
    for l in D['lineas']:
        t = porcapa.get(l['capa'])
        if not t or not t.get('usar') or t['tipo'] not in TIPOS_LABOR: continue
        P = np.array(l['xyz'], float)
        if len(P) < 2: continue
        cf = t.get('cota')
        lineas.append({'capa': l['capa'], 'tipo': t['tipo'], 'color': t['color'], 'ancho': float(t['ancho']), 'alto': float(t['alto']),
                       'cota_fija': None if cf in (None, '') else float(cf), 'P': _densificar(P, 2.0),
                       'tiene_z': bool(np.ptp(P[:, 2]) > 0.05 or abs(P[0, 2]) > 0.5)})
    if not lineas: raise RuntimeError('No quedó ningún eje de labor: revisa en la tabla qué capas se usan y de qué tipo son.')
    for l in lineas: l['con_cota'] = l['cota_fija'] is None and l['tiene_z']
    sin_z = [l for l in lineas if not l['con_cota']]
    if sin_z:
        C = _cotas_de_textos(D, tabla)
        registro(f'Cotas: {len(lineas) - len(sin_z)} eje(s) con cota propia; para {len(sin_z)} se usan {len(C)} textos de cota y la cota fija por capa.')
        _asignar_cotas(lineas, C, float(op.get('radio_cota', 12)), registro)
    else:
        registro('Cotas: tomadas de los ejes 3D del plano.')
    activas = [l for l in lineas if l['tipo'] not in ('abandonada', 'proyectada')]
    nc = _cruces(activas)
    red = Red(activas); T = tramos(red)
    if nc: registro(f'Cruces en planta a la misma cota unidos: {nc}.')
    registro(f'Red de galerías: {len(red.N)} nodos, {len(T)} tramos entre uniones y extremos.')
    largo_extremo = {}
    for t in T:
        for n in (t['nodos'][0], t['nodos'][-1]):
            if red.grado(n) == 1: largo_extremo[n] = max(largo_extremo.get(n, 0.0), t['L'])

    # Bocaminas: bloques, puntos o líneas de la capa de bocaminas (o textos «BOCAMINA»); el nombre sale del texto más cercano
    tipo_de = lambda c: porcapa.get(c, {}).get('tipo')
    pos_b = [p['xyz'] for p in D['puntos'] if tipo_de(p['capa']) == 'bocamina'] + [l['xyz'][0] for l in D['lineas'] if tipo_de(l['capa']) == 'bocamina']
    textos_b = [(t['xyz'], t['texto'].strip()) for t in D['textos'] if 'BOCAMINA' in cad._sin_tildes(t['texto'])]
    if not pos_b: pos_b = [xyz for xyz, _ in textos_b]
    extremos = [n for n in red.ady if red.grado(n) == 1]
    boc = {}
    for xyz in pos_b:
        cand = extremos or list(red.ady)
        d = [math.hypot(red.N[n][0] - xyz[0], red.N[n][1] - xyz[1]) for n in cand]; k = int(np.argmin(d))
        if d[k] <= 25: boc.setdefault(cand[k], None)
    libres = list(textos_b)
    for nodo in boc:
        if libres:
            d = [math.hypot(red.N[nodo][0] - x[0], red.N[nodo][1] - x[1]) for x, _ in libres]; k = int(np.argmin(d))
            if d[k] <= 60: boc[nodo] = libres.pop(k)[1]
    for i, nodo in enumerate(boc):
        if not boc[nodo]: boc[nodo] = f'Bocamina {i + 1}'
    supuesta = False
    if not boc and extremos:
        k = max(extremos, key=lambda n: red.N[n][2]); boc[k] = 'Bocamina (supuesta: extremo más alto)'; supuesta = True
    # Frentes: extremos activos (no bocamina, ni labor abandonada o proyectada, ni muñones de menos de 3 m)
    tipo_capa = {l['capa']: l['tipo'] for l in lineas}
    textos_f = [(t['xyz'], t['texto'].strip()) for t in D['textos'] if any(k in cad._sin_tildes(t['texto']) for k in ('FRENTE', 'AVANCE'))]
    frentes = []
    for n in sorted(extremos, key=lambda n: (round(red.N[n][0], 1), round(red.N[n][1], 1))):
        tipo = tipo_capa.get(red.capa(n, next(iter(red.ady[n]))), '')
        if n in boc or tipo in ('abandonada', 'proyectada') or largo_extremo.get(n, 0) < 3: continue
        nombre = None
        if textos_f:
            d = [math.hypot(red.N[n][0] - x[0], red.N[n][1] - x[1]) for x, _ in textos_f]; k = int(np.argmin(d))
            if d[k] <= 15: nombre = textos_f[k][1]
        frentes.append({'nodo': n, 'id': f'F{len(frentes) + 1}', 'nombre': nombre or f'Frente {len(frentes) + 1}',
                        'E': float(red.N[n][0]), 'N': float(red.N[n][1]), 'Z': float(red.N[n][2]), 'tipo': tipo})
    bocaminas = [{'nodo': n, 'nombre': nom, 'E': float(red.N[n][0]), 'N': float(red.N[n][1]), 'Z': float(red.N[n][2])} for n, nom in boc.items()]
    registro(f'{len(bocaminas)} bocamina(s){" (supuesta)" if supuesta else ""} y {len(frentes)} frente(s) detectados.')
    limites = [np.array(l['xyz'], float) for l in D['lineas']
               if porcapa.get(l['capa'], {}).get('tipo') == 'limite' and porcapa[l['capa']].get('usar')]
    return {'lineas': lineas, 'red': red, 'tramos': T, 'bocaminas': bocaminas, 'frentes': frentes, 'limites': limites,
            'eje': op.get('eje', 'piso'), 'tipo_capa': tipo_capa}


# ---------------------------------------------------------------- 3. Modelo ilustrativo de metano
def modelo_metano(M, mediciones, op, registro=print):
    """Modelo didáctico, no predictivo, del metano medido en los frentes.

    - El metano medido en un frente viaja con el aire de retorno hasta la bocamina de salida. Sin caudales se supone, del
      lado de la seguridad, que no se diluye en el camino. Con el caudal del frente y el de retorno, después de la primera
      unión se mezcla: C = Σ(Ci·Qi)/Qretorno.
    - Contra la corriente, hacia las galerías vecinas de esa ruta, el metano retrocede por dispersión longitudinal:
      C(x) = C0·exp(−u·x/E), solución estacionaria de la ecuación de advección y dispersión en una dimensión. La fórmula
      de Taylor da E ≈ 2 m²/s en galerías rectas; en redes con curvas, uniones y fondos ciegos se han calibrado valores
      mucho mayores (Bahrami et al., 2019, Mining, Metallurgy & Exploration, 36, 513–521).
    - Estratificación (Bakke y Leach): L = u/(g·Δρ/ρ·q/W)^(1/3); con L menor que 2 se forman capas de metano en el techo
      y con L de 5 o más la capa queda controlada.
    - El metano es más liviano que el aire: en labores ciegas que suben se acumula en el techo y en el fondo del frente."""
    red = M['red']; Ed = float(op.get('E', 2.0)); u_def = float(op.get('u', 0.3)); Qret = op.get('Q_retorno') or None
    ret = op.get('retorno')
    if isinstance(ret, (tuple, list)) and M['bocaminas']:
        ret = min(M['bocaminas'], key=lambda b: math.hypot(b['E'] - ret[0], b['N'] - ret[1]))['nodo']
    elif isinstance(ret, str) and M['bocaminas']:
        ret = next((b['nodo'] for b in M['bocaminas'] if b['nombre'] == ret), M['bocaminas'][0]['nodo'])
    if ret is None and M['bocaminas']: ret = M['bocaminas'][0]['nodo']
    nombre_ret = next((b['nombre'] for b in M['bocaminas'] if b['nodo'] == ret), '')
    C, fuentes, rutas, resultados = {}, {}, set(), []
    dist_ret, prev_ret = red.dijkstra([ret]) if ret is not None else ({}, {})
    for f in M['frentes']:
        m = mediciones.get(f['id'])
        if not m or m.get('ch4') in (None, ''): continue
        c0 = float(m['ch4']); u_med = float(m['u']) if m.get('u') not in (None, '', 0) else None
        Qf = float(m['Q']) if m.get('Q') not in (None, '', 0) else None
        l = next((l for l in M['lineas'] if f['nodo'] in l.get('nodos', ())), None)
        ancho, alto = (l['ancho'], l['alto']) if l else (2.0, 1.8)
        if not Qf and u_med: Qf = u_med * ancho * alto
        ruta = red.camino(prev_ret, f['nodo']) if f['nodo'] in dist_ret else [f['nodo']]
        union = next((n for n in ruta[1:] if red.grado(n) >= 3), None)
        diluye, pasada = bool(Qf and Qret), False
        for n in ruta:
            if n == union: pasada = True
            if diluye and pasada: C[n] = C.get(n, 0.0) + c0 * Qf / float(Qret)
            else: C[n] = max(C.get(n, 0.0), c0)
            fuentes[n] = C[n]
        rutas.update(ruta)
        q = Qreq = L = None
        if Qf:
            q = c0 / 100.0 * Qf; Qreq = q / 0.01
            if q > 0: L = (u_med or Qf / (ancho * alto)) / (G * DRHO * q / ancho) ** (1 / 3)
        sube = None
        ref = union if union is not None else ret
        if ref is not None and ref in ruta:
            tramo = ruta[:ruta.index(ref) + 1]
            dz = red.N[f['nodo']][2] - red.N[ref][2]
            dh = sum(math.hypot(*(red.N[a][:2] - red.N[b][:2])) for a, b in zip(tramo[:-1], tramo[1:]))
            if dz > 1.0 and dh > 0 and math.degrees(math.atan2(dz, dh)) > 5: sube = round(math.degrees(math.atan2(dz, dh)), 1)
        resultados.append({'id': f['id'], 'nombre': f['nombre'], 'ch4': c0, 'clase': clase_ch4(c0), 'fecha': m.get('fecha', '') or '',
                           'u': u_med, 'Q': round(Qf, 3) if Qf else None, 'q': round(q, 5) if q else None,
                           'Q_req': round(Qreq, 2) if Qreq else None, 'L': round(L, 1) if L else None, 'ascendente': sube,
                           'ruta_m': round(dist_ret.get(f['nodo'], 0.0), 1), 'salida': nombre_ret})
    # Retroceso por dispersión desde toda la ruta de retorno hacia las galerías vecinas (Dijkstra con varias fuentes)
    if fuentes and Ed > 0:
        k0 = {n: -(Ed / u_def) * math.log(max(c, 1e-6)) for n, c in fuentes.items()}
        kmax = -(Ed / u_def) * math.log(0.05)
        dist = dict(k0); q = [(k, n) for n, k in k0.items()]; heapq.heapify(q)
        while q:
            k, a = heapq.heappop(q)
            if k > dist.get(a, math.inf) or k > kmax: continue
            for b, Lab in red.ady.get(a, {}).items():
                if b in rutas: continue
                nk = k + Lab
                if nk < dist.get(b, math.inf): dist[b] = nk; heapq.heappush(q, (nk, b))
        for n, k in dist.items():
            if n not in rutas: C[n] = max(C.get(n, 0.0), math.exp(-u_def * k / Ed))
    registro(f'Metano: {len(resultados)} frente(s) con medición; salida del aire por «{nombre_ret}»; E = {_num(Ed)} m²/s y '
             f'u = {_num(u_def, 2)} m/s cuando no se midió la velocidad.')
    return C, resultados


# ---------------------------------------------------------------- 4. Superficie (DEM o fotogrametría)
def _warp(ruta, ext, ancho, alto, crs_wkt, bandas=None, remuestreo='bilinear'):
    from osgeo import gdal, osr
    src = gdal.Open(ruta) if isinstance(ruta, str) else ruta
    if src is None: raise RuntimeError(f'No se pudo abrir {ruta}')
    E0, E1, N0, N1 = ext
    op = dict(format='MEM', outputBounds=(E0, N0, E1, N1), width=ancho, height=alto, resampleAlg=remuestreo)
    sw = src.GetProjection()
    if crs_wkt and sw:
        a, b = osr.SpatialReference(), osr.SpatialReference(); a.ImportFromWkt(sw); b.ImportFromWkt(crs_wkt)
        if not a.IsSame(b): op['dstSRS'] = crs_wkt
    if bandas:
        src = gdal.Translate('', src, format='VRT', bandList=bandas)
    return gdal.Warp('', src, **op)


def superficie_dem(ruta_dem, ext, ruta_orto=None, celdas=260, crs_wkt=None, registro=print):
    """Malla regular del DEM en la extensión (E0, E1, N0, N1) + textura (ortofoto o relieve sombreado)."""
    from PIL import Image
    E0, E1, N0, N1 = ext
    paso = max(E1 - E0, N1 - N0) / celdas
    nx = max(2, int(round((E1 - E0) / paso))); ny = max(2, int(round((N1 - N0) / paso)))
    t = _warp(ruta_dem, ext, nx, ny, crs_wkt)
    b = t.GetRasterBand(1); Z = b.ReadAsArray().astype(float); nd = b.GetNoDataValue()
    if nd is not None: Z[Z == nd] = np.nan
    Z[(Z < -1000) | (Z > 9000)] = np.nan
    if np.isnan(Z).all(): raise RuntimeError('El DEM no tiene datos en la zona de la mina (¿está en el mismo sistema de coordenadas que el plano?).')
    if np.isnan(Z).any(): Z = _rellenar(Z)
    gx = E0 + (np.arange(nx) + 0.5) * (E1 - E0) / nx; gy = N1 - (np.arange(ny) + 0.5) * (N1 - N0) / ny
    EE, NN = np.meshgrid(gx, gy)
    V = np.column_stack([EE.ravel(), NN.ravel(), Z.ravel()])
    i = (np.arange(ny - 1)[:, None] * nx + np.arange(nx - 1)[None, :]).ravel()
    F = np.concatenate([np.stack([i, i + nx, i + 1], -1), np.stack([i + 1, i + nx, i + nx + 1], -1)])
    img = None
    if ruta_orto:
        try:
            w = 2048; h = max(2, int(w * (N1 - N0) / (E1 - E0)))
            o = _warp(ruta_orto, ext, w, h, crs_wkt, bandas=[1, 2, 3], remuestreo='average')
            img = Image.fromarray(np.dstack([o.GetRasterBand(k + 1).ReadAsArray() for k in range(3)]).astype(np.uint8))
        except Exception as e:
            registro(f'Aviso: no se pudo usar la ortofoto ({e}); se usa el relieve sombreado.')
    if img is None: img = _sombreado(Z, paso)
    registro(f'Superficie: DEM de {nx} × {ny} celdas de {_num(paso)} m.')
    return V, F, img, (E0, E1, N0, N1), (gx, gy, Z)


def _sombreado(Z, paso):
    """Relieve sombreado en tonos de terreno, para cuando no hay ortofoto."""
    from PIL import Image
    gy, gx = np.gradient(Z, paso)
    az, alt = math.radians(315), math.radians(45)
    pend = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
    hs = np.clip(np.sin(alt) * np.cos(pend) + np.cos(alt) * np.sin(pend) * np.cos(az - asp), 0, 1)
    t = (Z - Z.min()) / max(float(np.ptp(Z)), 1e-6)
    base = np.stack([118 + 60 * t, 146 + 40 * t, 96 + 38 * t], -1)
    rgb = np.clip(base * (0.55 + 0.6 * hs[..., None]), 0, 255).astype(np.uint8)
    return Image.fromarray(rgb).resize((Z.shape[1] * 4, Z.shape[0] * 4), Image.BICUBIC)


def superficie_fotogrametria(carpeta, ext, caras=200000, registro=print):
    """Malla del vuelo con dron (DJI Terra, Pix4D, WebODM…) recortada a la extensión de la mina, con su ortofoto."""
    from osgeo import gdal
    from PIL import Image
    from . import fotogrametria as FG
    A = FG.analizar(carpeta)
    if not A['objs']: raise RuntimeError('No hay malla OBJ en la carpeta del vuelo.')
    total = sum(FG._tam(o) for o in A['objs']); bloques, crudos = [], []
    for o in A['objs']:
        registro(f'Superficie: leyendo {os.path.basename(o)}…')
        V, F, tex = FG._leer_obj(o, con_textura=not A['orto'])
        if not A['orto']: crudos.append((V, F, tex))
        bloques.append(FG._simplificar(V, F, max(3000, caras * FG._tam(o) / total)))
    todo = np.concatenate([v for v, _ in bloques])
    if A['origen'] is not None: off = np.array(A['origen'])
    elif np.abs(todo[:, :2]).max() > 1e5: off = np.zeros(3)
    else: raise RuntimeError('La malla del vuelo no trae coordenadas reales (falta el origen del proyecto).')
    V = np.concatenate([v + off for v, _ in bloques]); k = 0; Fs = []
    for v, f in bloques: Fs.append(f + k); k += len(v)
    F = np.concatenate(Fs)
    E0, E1, N0, N1 = ext
    cen = V[F].mean(axis=1); sel = (cen[:, 0] >= E0) & (cen[:, 0] <= E1) & (cen[:, 1] >= N0) & (cen[:, 1] <= N1)
    if not sel.any(): raise RuntimeError('El vuelo no cubre la zona de la mina (revisa el sistema de coordenadas).')
    usados, inv = np.unique(F[sel], return_inverse=True); V = V[usados]; F = inv.reshape(-1, 3)
    if A['orto']: orto = gdal.Open(A['orto'])
    else: orto = FG._pseudo_orto([(v + off, f, t) for v, f, t in crudos], (E0, E1, N0, N1), max(0.05, (E1 - E0) / 4000), registro)
    w = 4096; h = max(2, int(w * (N1 - N0) / (E1 - E0)))
    o = gdal.Translate('', orto, format='MEM', bandList=[1, 2, 3], projWin=[E0, N1, E1, N0], width=w, height=h, resampleAlg='average')
    img = Image.fromarray(np.dstack([o.GetRasterBand(b + 1).ReadAsArray() for b in range(3)]).astype(np.uint8))
    res = max(0.5, (E1 - E0) / 400); nx = int(np.ceil((E1 - E0) / res)); ny = int(np.ceil((N1 - N0) / res))
    Gz = np.full((ny, nx), np.nan)
    ix = np.clip(((V[:, 0] - E0) / res).astype(int), 0, nx - 1); iy = np.clip(((N1 - V[:, 1]) / res).astype(int), 0, ny - 1)
    np.fmax.at(Gz, (iy, ix), V[:, 2])
    Gz = _rellenar(Gz)
    gx = E0 + (np.arange(nx) + 0.5) * res; gy = N1 - (np.arange(ny) + 0.5) * res
    return V, F, img, (E0, E1, N0, N1), (gx, gy, Gz)


def _rellenar(Gz):
    from scipy import ndimage
    m = np.isnan(Gz)
    if not m.any(): return Gz
    idx = ndimage.distance_transform_edt(m, return_distances=False, return_indices=True)
    return Gz[tuple(idx)]


def _z_superficie(rej, E, N):
    gx, gy, Z = rej
    j = np.clip(np.searchsorted(gx, np.asarray(E)), 0, len(gx) - 1)
    i = np.clip(np.searchsorted(-gy, -np.asarray(N)), 0, len(gy) - 1)
    return Z[i, j]


# ---------------------------------------------------------------- 5. Sólidos
def tubo(P, ancho, alto, eje='piso'):
    """Barre una sección rectangular a lo largo del eje P (n×3, coordenadas reales). Cada costado lleva sus propios
    vértices (aristas nítidas, sombreado suave a lo largo). Devuelve vértices, caras y el índice del anillo de cada vértice."""
    n = len(P)
    d = np.diff(P, axis=0); Ls = np.linalg.norm(d, axis=1); d = d / np.maximum(Ls[:, None], 1e-9)
    T = np.zeros_like(P); T[0] = d[0]; T[-1] = d[-1]
    if n > 2: T[1:-1] = d[:-1] + d[1:]
    T /= np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-9)
    lado = np.cross(T, np.array([0, 0, 1.0]))
    vertical = np.linalg.norm(lado, axis=1) < 0.15                    # tambores y chimeneas casi verticales
    lado[vertical] = np.cross(T[vertical], np.array([1.0, 0, 0]))
    lado /= np.maximum(np.linalg.norm(lado, axis=1)[:, None], 1e-9)
    sube = np.cross(lado, T); sube /= np.maximum(np.linalg.norm(sube, axis=1)[:, None], 1e-9)
    esc = np.ones(n)
    if n > 2:   # en los quiebres el ancho se corrige para que la sección no se adelgace
        cosang = np.clip((d[:-1] * d[1:]).sum(1), -1, 1); esc[1:-1] = 1 / np.maximum(np.sqrt((1 + cosang) / 2), 0.5)
    h0, h1 = {'piso': (0, alto), 'centro': (-alto / 2, alto / 2), 'techo': (-alto, 0)}[eje]
    w = (ancho / 2) * esc[:, None]
    K = np.stack([P - lado * w + sube * h0, P + lado * w + sube * h0, P + lado * w + sube * h1, P - lado * w + sube * h1], axis=1)
    Vs, Fs, Rs, off = [], [], [], 0
    i = np.arange(n - 1)
    for s in range(4):
        V = np.stack([K[:, s], K[:, (s + 1) % 4]], axis=1).reshape(-1, 3)
        Fs.append(np.concatenate([np.stack([2 * i, 2 * i + 1, 2 * i + 3], -1), np.stack([2 * i, 2 * i + 3, 2 * i + 2], -1)]) + off)
        Vs.append(V); Rs.append(np.repeat(np.arange(n), 2)); off += 2 * n
    for k in (0, n - 1):
        Vs.append(K[k]); Fs.append(np.array([[0, 1, 2], [0, 2, 3]]) + off); Rs.append(np.full(4, k)); off += 4
    return np.concatenate(Vs), np.concatenate(Fs), np.concatenate(Rs)


def _caja_vertical(p, z0, z1, r=0.3):
    x, y = p[0], p[1]
    V = np.array([[x - r, y - r, z0], [x + r, y - r, z0], [x + r, y + r, z0], [x - r, y + r, z0],
                  [x - r, y - r, z1], [x + r, y - r, z1], [x + r, y + r, z1], [x - r, y + r, z1]])
    F = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7], [4, 5, 6], [4, 6, 7], [0, 2, 1], [0, 3, 2]])
    return V, F


def _cortina(L, zbot, ztop_fn, ext, paso=4.0):
    """Cortina vertical del límite del título entre zbot y la superficie (o el techo de la maqueta), dentro de la extensión."""
    E0, E1, N0, N1 = ext
    P = _densificar(np.column_stack([L[:, :2], np.zeros(len(L))]), paso)
    dentro = (P[:, 0] >= E0) & (P[:, 0] <= E1) & (P[:, 1] >= N0) & (P[:, 1] <= N1)
    Vs, Fs, off = [], [], 0
    k = 0
    while k < len(P):
        if not dentro[k]: k += 1; continue
        j = k
        while j + 1 < len(P) and dentro[j + 1]: j += 1
        if j > k:
            Q = P[k:j + 1]; zt = ztop_fn(Q[:, 0], Q[:, 1])
            V = np.concatenate([np.column_stack([Q[:, :2], np.full(len(Q), zbot)]), np.column_stack([Q[:, :2], zt])])
            m = len(Q); i = np.arange(m - 1)
            Fs.append(np.concatenate([np.stack([i, i + 1, m + i + 1], -1), np.stack([i, m + i + 1, m + i], -1)]) + off)
            Vs.append(V); off += len(V)
        k = j + 1
    if not Vs: return None, None
    return np.concatenate(Vs), np.concatenate(Fs)


# ---------------------------------------------------------------- 6. Proceso completo
def procesar(par, progreso=print):
    """par: plano (ruta DWG/DXF), datos (opcional, de analizar), tabla, eje, crs_wkt, crs_nombre, proyeccion,
    superficie: None | {'dem', 'orto'} | {'carpeta'}, frentes_cfg: [{E, N, nombre, mostrar, ch4, fecha, u, Q}],
    mediciones: {F1: {...}} (opcional), metano: {'E', 'u', 'retorno', 'Q_retorno'}, salida, titulo, subtitulo, elaboro,
    pie, logo, color, funciones, url, plano_carta (bool), escala (opcional)"""
    import trimesh
    from PIL import Image
    from . import malla, sitio
    ruta = par.get('plano') or par.get('dxf')
    D = par.get('datos') or analizar(ruta, progreso)
    tabla = par.get('tabla') or D['tabla']
    M = preparar(D, tabla, {'eje': par.get('eje', 'piso'), 'radio_cota': par.get('radio_cota', 12)}, progreso)
    red = M['red']
    # Nombres, frentes que no se muestran y mediciones de metano desde la tabla del complemento
    mediciones = dict(par.get('mediciones') or {}); ocultos = set()
    for r in par.get('frentes_cfg') or []:
        if not M['frentes']: break
        f = min(M['frentes'], key=lambda f: math.hypot(f['E'] - r['E'], f['N'] - r['N']))
        if math.hypot(f['E'] - r['E'], f['N'] - r['N']) > 20: continue
        if r.get('nombre'): f['nombre'] = str(r['nombre']).strip()
        if r.get('mostrar') is False: ocultos.add(f['id']); continue
        if r.get('ch4') not in (None, ''): mediciones[f['id']] = r
    M['frentes'] = [f for f in M['frentes'] if f['id'] not in ocultos]
    S = par['salida']; web = os.path.join(S, 'sitio'); os.makedirs(S, exist_ok=True)
    copiar_kit_mina(web)

    # Extensión: labores + margen
    todos = np.concatenate([l['P'] for l in M['lineas']])
    margen = max(25.0, 0.12 * max(np.ptp(todos[:, 0]), np.ptp(todos[:, 1])))
    E0, E1 = todos[:, 0].min() - margen, todos[:, 0].max() + margen
    N0, N1 = todos[:, 1].min() - margen, todos[:, 1].max() + margen
    ext = (E0, E1, N0, N1)
    sup = rej = None; sp = par.get('superficie') or {}
    try:
        if sp.get('dem'): sup = superficie_dem(sp['dem'], ext, sp.get('orto'), crs_wkt=par.get('crs_wkt'), registro=progreso)
        elif sp.get('carpeta'): sup = superficie_fotogrametria(sp['carpeta'], ext, registro=progreso)
    except Exception as e:
        progreso(f'Aviso: no se pudo armar la superficie ({e}); la maqueta sigue sin ella.'); sup = None
    if sup: rej = sup[4]
    zmin = float(min(todos[:, 2].min() - 8, sup[0][:, 2].min() if sup else math.inf))
    zmax = float(max(todos[:, 2].max() + 6, sup[0][:, 2].max() if sup else -math.inf))
    lado = max(E1 - E0, N1 - N0)
    esc = float(par.get('escala') or next((e for e in (200, 250, 500, 750, 1000, 1500, 2000, 2500, 5000, 10000) if lado / e <= 0.95), 20000))
    Ec, Nc = (E0 + E1) / 2, (N0 + N1) / 2

    def a_escena(V):
        V = np.asarray(V, float)
        return np.column_stack([(V[:, 0] - Ec) / esc, (V[:, 2] - zmin) / esc + BASE, -(V[:, 1] - Nc) / esc])

    def pos(p): return [round(float(v), 6) for v in a_escena([p])[0]]

    def material(nombre, hexcol, rug=0.85):
        col = cad.hex_rgb(hexcol)
        return trimesh.visual.material.PBRMaterial(name=nombre, baseColorFactor=[*(int(round(malla._lin(c) * 255)) for c in col), 255],
                                                   metallicFactor=0.0, roughnessFactor=rug, doubleSided=True)

    escena = trimesh.Scene(); capas_cfg = []
    porcapa = {}
    for l in M['lineas']: porcapa.setdefault(l['capa'], []).append(l)
    for k, (capa, ls) in enumerate(sorted(porcapa.items(), key=lambda kv: kv[0].lower())):
        Vs, Fs, off = [], [], 0
        for l in ls:
            V, F, _ = tubo(l['P'], l['ancho'], l['alto'], M['eje']); Vs.append(V); Fs.append(F + off); off += len(V)
        nombre_mat = f'L{k:02d}' + ('_p' if ls[0]['tipo'] == 'proyectada' else '')
        m = trimesh.Trimesh(a_escena(np.concatenate(Vs)), np.concatenate(Fs), process=False)
        m.visual = trimesh.visual.TextureVisuals(material=material(nombre_mat, ls[0]['color']))
        escena.add_geometry(m, geom_name=nombre_mat)
        largo = sum(float(np.linalg.norm(np.diff(l['P'], axis=0), axis=1).sum()) for l in ls)
        capas_cfg.append({'material': nombre_mat, 'capa': capa, 'tipo': ls[0]['tipo'], 'tipo_nombre': cad.NOMBRES.get(ls[0]['tipo'], ls[0]['tipo']),
                          'color': ls[0]['color'], 'longitud_m': round(largo, 1), 'ejes': len(ls)})
    extras = {}
    if sup:
        V, F, img, ext_s, _ = sup
        uv = np.column_stack([(V[:, 0] - ext_s[0]) / (ext_s[1] - ext_s[0]), (V[:, 1] - ext_s[2]) / (ext_s[3] - ext_s[2])])
        m = trimesh.Trimesh(a_escena(V), F, process=False)
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=malla._material('Superficie', img))
        escena.add_geometry(m, geom_name='Superficie'); extras['superficie'] = True
    # Distancias desde la bocamina y cubierta sobre cada frente (con su línea vertical)
    dist_b, _ = red.dijkstra([b['nodo'] for b in M['bocaminas']]) if M['bocaminas'] else ({}, {})
    alto_de = {l['capa']: l['alto'] for l in M['lineas']}
    Vc, Fc, offc = [], [], 0
    for f in M['frentes']:
        p = red.N[f['nodo']]; al = alto_de.get(red.capa(f['nodo'], next(iter(red.ady[f['nodo']]))), 1.8)
        techo = p[2] + {'piso': al, 'centro': al / 2, 'techo': 0}[M['eje']]
        f['dist_bocamina'] = round(dist_b[f['nodo']], 1) if f['nodo'] in dist_b else None
        f['cubierta'] = round(float(_z_superficie(rej, p[0], p[1]) - techo), 1) if rej else None
        f['dist_limite'] = round(_dist_a_limites(p, M['limites']), 1) if M['limites'] else None
        if f['cubierta'] and f['cubierta'] > 1:
            V, F = _caja_vertical(p, techo + 0.3, techo + f['cubierta'], r=max(0.12, esc / 5000)); Vc.append(V); Fc.append(F + offc); offc += len(V)
    if Vc:
        m = trimesh.Trimesh(a_escena(np.concatenate(Vc)), np.concatenate(Fc), process=False)
        m.visual = trimesh.visual.TextureVisuals(material=material('Cubierta', '#37474f', 0.6))
        escena.add_geometry(m, geom_name='Cubierta'); extras['cubierta'] = True
    # Límite del título como cortina vertical
    if M['limites']:
        Vl, Fl, offl = [], [], 0
        ztop = (lambda E, N: _z_superficie(rej, E, N) + 3) if rej else (lambda E, N: np.full(len(E), zmax))
        for L in M['limites']:
            V, F = _cortina(L, zmin + 2, ztop, ext)
            if V is not None: Vl.append(V); Fl.append(F + offl); offl += len(V)
        if Vl:
            m = trimesh.Trimesh(a_escena(np.concatenate(Vl)), np.concatenate(Fl), process=False)
            m.visual = trimesh.visual.TextureVisuals(material=material('Limite', '#c62828', 1.0))
            escena.add_geometry(m, geom_name='Limite'); extras['limite'] = True
    # Metano
    p_met = dict(par.get('metano') or {})
    C, res_ch4 = modelo_metano(M, mediciones, p_met, progreso) if mediciones else ({}, [])
    if C:
        Vs, Fs, Cs, off = [], [], [], 0
        for l in M['lineas']:
            if 'nodos' not in l: continue
            c = np.array([C.get(n, 0.0) for n in l['nodos']]); con = c >= 0.05
            if not con.any(): continue
            k = 0
            while k < len(c):   # tramos seguidos con gas, con un vértice más a cada lado para que el color se desvanezca
                if not con[k]: k += 1; continue
                j = k
                while j + 1 < len(c) and con[j + 1]: j += 1
                a, b = max(0, k - 1), min(len(c) - 1, j + 1)
                if b > a:
                    V, F, anillo = tubo(l['P'][a:b + 1], l['ancho'] * 1.35, l['alto'] * 1.3, M['eje'])
                    if M['eje'] == 'piso': V = V - np.array([0, 0, l['alto'] * 0.15])
                    Vs.append(V); Fs.append(F + off); Cs.append(np.array([_color_ch4(x) for x in c[a:b + 1]])[anillo]); off += len(V)
                k = j + 1
        if Vs:
            col = np.concatenate(Cs)
            m = trimesh.Trimesh(a_escena(np.concatenate(Vs)), np.concatenate(Fs), process=False)
            m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.column_stack([col, np.full(len(col), 255)]).astype(np.uint8))
            escena.add_geometry(m, geom_name='Gas'); extras['gas'] = True
    glb = _parchar_mina(escena.export(file_type='glb', include_normals=True))
    with open(os.path.join(web, 'mina.glb'), 'wb') as fo: fo.write(glb)
    progreso(f'Maqueta 3D: {len(glb) / 1e6:.1f} MB · escala 1:{_num(esc, 0)}')

    # Marcas: bocaminas, frentes, cubierta y longitud de los tramos
    marcas = []
    for b in M['bocaminas']:
        marcas.append({'tipo': 'bocamina', 'pos': pos(red.N[b['nodo']] + [0, 0, 3.0]), 'texto': b['nombre']})
    for f in M['frentes']:
        p = red.N[f['nodo']]; r = next((x for x in res_ch4 if x['id'] == f['id']), None)
        marcas.append({'tipo': 'frente', 'pos': pos(p + [0, 0, 3.0]), 'texto': f['nombre'] + (f" · {_num(r['ch4'], 2)} % CH₄" if r else ''),
                       'clase': r['clase'] if r else None, 'id': f['id']})
        if f.get('cubierta') and f['cubierta'] > 1:
            marcas.append({'tipo': 'cubierta', 'pos': pos(p + [0, 0, 2.0 + f['cubierta'] / 2]), 'texto': f"Cubierta ≈ {_num(f['cubierta'], 0)} m"})
    ejes = []
    for t in M['tramos']:
        P = red.N[t['nodos']]; L = t['L']
        tipo = M['tipo_capa'].get(t['capa'], 'otra')
        ejes.append({'capa': t['capa'], 'tipo': tipo, 'pts': np.round(P[::max(1, len(P) // max(2, int(L / 6)))].tolist() + [P[-1].tolist()], 1).tolist()})
        if L < 8: continue
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]); mid = np.array([np.interp(L / 2, s, P[:, k]) for k in range(3)])
        dz = P[-1, 2] - P[0, 2]; dh = float(np.hypot(*np.diff(P[:, :2], axis=0).T).sum())
        incl = math.degrees(math.atan2(abs(dz), dh)) if dh > 0 else 90.0
        marcas.append({'tipo': 'distancia', 'pos': pos(mid + [0, 0, alto_de.get(t['capa'], 1.8) + 1.2]),
                       'texto': f'{_num(L)} m' + (f' · {incl:.0f}°' if incl >= 3 else ''), 'capa': t['capa']})
    E_lab = a_escena(todos); lo, hi = E_lab.min(0), E_lab.max(0)
    camara = {'objetivo': [round(float(v), 6) for v in (lo + hi) / 2], 'radio': round(float(np.linalg.norm(hi - lo) / 2), 6)}
    # Plano 2D (vista en planta) y relieve para el GPS
    plano2d(M, ext, os.path.join(web, 'plano.jpg'), sup, res_ch4, C)
    if rej:
        gx, gy, Z = rej
        Image.fromarray(np.clip((Z - zmin) / max(zmax - zmin, 0.01) * 65535, 0, 65535).astype(np.uint16)).save(os.path.join(web, 'relieve.png'))
    else:
        Image.fromarray(np.full((8, 8), 65535, np.uint16)).save(os.path.join(web, 'relieve.png'))

    proy = par.get('proyeccion')
    if proy is not None and not isinstance(proy, dict): proy = sitio.proyeccion_tm(proy)
    aw, ah = (E1 - E0) / esc * 1000, (N1 - N0) / esc * 1000
    total_lab = sum(c['longitud_m'] for c in capas_cfg if c['tipo'] != 'proyectada')
    ficha = [['Escala de la maqueta', f'1:{_num(esc, 0)}'], ['Exageración vertical', 'ninguna (alturas reales)'],
             ['Labores dibujadas', f'{_num(total_lab, 0)} m de ejes'],
             ['Cotas', 'de los ejes 3D del plano' if D.get('es_3d') else 'de los textos de cota del plano'],
             ['Eje levantado en', {'piso': 'el piso de la labor', 'centro': 'el centro de la labor', 'techo': 'el techo de la labor'}[M['eje']]],
             ['Superficie', 'vuelo con dron' if sp.get('carpeta') and sup else ('modelo digital de elevación' if sup else 'sin superficie')],
             ['Plano fuente', os.path.basename(ruta or '')]]
    if par.get('crs_nombre'): ficha.append(['Sistema de coordenadas', par['crs_nombre']])
    logo = ''
    if par.get('logo') and os.path.exists(par['logo']):
        logo = 'logo' + os.path.splitext(par['logo'])[1].lower(); shutil.copy(par['logo'], os.path.join(web, logo))
    color = par.get('color') or (sitio.color_del_logo(par['logo']) if par.get('logo') else '#014f7d')
    fun = dict(par.get('funciones') or {})
    if not proy: fun['gps'] = False; fun['recorrido'] = False
    ahora = datetime.datetime.now()
    cfg = {'version': int(ahora.strftime('%Y%m%d%H%M')), 'titulo': par.get('titulo') or 'Mina subterránea', 'subtitulo': par.get('subtitulo', ''),
           'color': color, 'hoja': {'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3)},
           'marco': {'x_mm': 0, 'y_mm': 0, 'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3), 'E_min': E0, 'E_max': E1, 'N_min': N0, 'N_max': N1},
           'relieve': {'imagen': 'relieve.png', 'z_min': zmin, 'z_max': zmax, 'exageracion': 1},
           'proyeccion': proy, 'archivos': {'modelo': 'mina.glb', 'modelo_iphone': '', 'plano2d': 'plano.jpg', 'poster': ''},
           'ficha': ficha, 'elaboro': par.get('elaboro') or {'nombre': '', 'titulos': []}, 'pie': {'logo': logo, 'texto': par.get('pie', '')},
           'funciones': fun,
           'mina': {'escala': esc, 'eje': M['eje'], 'camara': camara, 'capas': capas_cfg, 'marcas': marcas, 'extras': extras, 'ejes': ejes,
                    'superficie': bool(sup),
                    'frentes': [{k: f.get(k) for k in ('id', 'nombre', 'E', 'N', 'Z', 'dist_bocamina', 'cubierta', 'dist_limite')} for f in M['frentes']],
                    'bocaminas': [{k: b[k] for k in ('nombre', 'E', 'N', 'Z')} for b in M['bocaminas']],
                    'metano': {'resultados': res_ch4,
                               'clases': [{'desde': ([0.0] + list(UMBRALES))[i], 'color': c, 'texto': t} for i, (c, t) in enumerate(CLASES_CH4)],
                               'parametros': {'E': float(p_met.get('E', 2.0)), 'u': float(p_met.get('u', 0.3))}},
                    'fecha': ahora.date().isoformat()}}
    sitio.escribir_config(web, cfg)
    if par.get('plano_carta', True):
        try:
            plano_carta(M, ext, sup, res_ch4, capas_cfg, cfg, os.path.join(S, 'plano_carta.pdf'), par.get('url'), C)
            progreso('Plano tamaño carta con QR: plano_carta.pdf')
        except Exception as e:
            progreso(f'Aviso: no se pudo hacer el plano carta ({e})')
    z = sitio.comprimir(web, os.path.join(S, 'sitio.zip'))
    progreso(f'Sitio listo: {web} · {os.path.getsize(z) / 1e6:.1f} MB en sitio.zip')
    if par.get('url'): sitio.qr(par['url'], os.path.join(S, 'QR.png'))
    return dict(sitio=web, zip=z, escala=esc, frentes=M['frentes'], bocaminas=M['bocaminas'], metano=res_ch4, capas=capas_cfg, cfg=cfg)


def _dist_a_limites(p, limites):
    mejor = math.inf
    for L in limites:
        if len(L) < 2: continue
        d, _ = _proyectar(np.array([p[:2]]), L)
        mejor = min(mejor, float(d[0]))
    return mejor


def _parchar_mina(datos):
    """Especular 0 y bordes CLAMP; superficie, límite y gas semitransparentes (alphaMode BLEND)."""
    import struct
    lj = struct.unpack_from('<I', datos, 12)[0]
    js = json.loads(datos[20:20 + lj]); resto = datos[20 + lj:]
    js['extensionsUsed'] = sorted(set(js.get('extensionsUsed', [])) | {'KHR_materials_specular'})
    mats = js.setdefault('materials', [])
    for m in mats:
        m.setdefault('extensions', {})['KHR_materials_specular'] = {'specularFactor': 0.0}
        alfa = {'Superficie': 0.3, 'Limite': 0.16}.get(m.get('name')) or (0.35 if m.get('name', '').endswith('_p') else None)
        if alfa:
            pbr = m.setdefault('pbrMetallicRoughness', {}); bc = pbr.get('baseColorFactor', [1, 1, 1, 1]); bc[3] = alfa
            pbr['baseColorFactor'] = bc; m['alphaMode'] = 'BLEND'; m['doubleSided'] = True
    for s in js.get('samplers', []): s.update(wrapS=33071, wrapT=33071)
    for me in js.get('meshes', []):
        if me.get('name', '').startswith('Gas'):
            mats.append({'name': 'Gas', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 0.55], 'metallicFactor': 0, 'roughnessFactor': 1},
                         'alphaMode': 'BLEND', 'doubleSided': True, 'extensions': {'KHR_materials_specular': {'specularFactor': 0.0}}})
            for p in me['primitives']: p['material'] = len(mats) - 1
    nj = json.dumps(js, separators=(',', ':')).encode(); nj += b' ' * ((4 - len(nj) % 4) % 4)
    cuerpo = struct.pack('<II', len(nj), 0x4E4F534A) + nj + resto
    return struct.pack('<4sII', b'glTF', 2, 12 + len(cuerpo)) + cuerpo


def copiar_kit_mina(destino):
    """Kit de la página de mina: index.html, sw.js y manifest propios + las librerías del kit general."""
    if os.path.exists(destino): shutil.rmtree(destino)
    shutil.copytree(KIT_MINA, destino)
    shutil.copytree(os.path.join(KIT, 'lib'), os.path.join(destino, 'lib'))
    for n in ('icono-192.png', 'icono-512.png'):
        if os.path.exists(os.path.join(KIT, n)): shutil.copy(os.path.join(KIT, n), os.path.join(destino, n))
    open(os.path.join(destino, '.nojekyll'), 'w').close()


# ---------------------------------------------------------------- 7. Plano en planta (2D) y plano carta con QR
def _dibujar_planta(ax, M, ext, sup, res_ch4, etiquetas=True, grosor=2.2, escala_texto=1.0, C=None, longitudes=False):
    from matplotlib.collections import LineCollection
    E0, E1, N0, N1 = ext
    if sup: ax.imshow(np.asarray(sup[2]), extent=[sup[3][0], sup[3][1], sup[3][2], sup[3][3]], alpha=0.55, zorder=0)
    for L in M['limites']:
        ax.plot(L[:, 0], L[:, 1], color='#c62828', lw=1.3 * escala_texto, ls=(0, (6, 3)), zorder=1)
    if C:   # posible recorrido del metano, debajo de las labores
        segs, cols = [], []
        for l in M['lineas']:
            if 'nodos' not in l: continue
            c = np.array([C.get(n, 0.0) for n in l['nodos']])
            for k in range(len(c) - 1):
                cm = max(c[k], c[k + 1])
                if cm >= 0.05: segs.append(l['P'][k:k + 2, :2]); cols.append([v / 255 for v in _color_ch4(cm)] + [0.55])
        if segs: ax.add_collection(LineCollection(segs, colors=cols, linewidths=grosor * 3.4, capstyle='round', zorder=1.5))
    for l in sorted(M['lineas'], key=lambda l: l['P'][:, 2].mean()):
        estilo = '--' if l['tipo'] == 'proyectada' else '-'
        ax.plot(l['P'][:, 0], l['P'][:, 1], estilo, color='#1c252b', lw=grosor + 1.6, solid_capstyle='round', zorder=2)
        ax.plot(l['P'][:, 0], l['P'][:, 1], estilo, color=l['color'], lw=grosor, solid_capstyle='round', zorder=3)
    caja = dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.85)
    if longitudes:
        red = M['red']
        for t in M['tramos']:
            if t['L'] < 15: continue
            P = red.N[t['nodos']]; s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
            k = int(np.searchsorted(s_, t['L'] / 2)); k = min(max(k, 1), len(P) - 1)
            a, b = P[k - 1], P[k]; ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if ang > 90: ang -= 180
            if ang < -90: ang += 180
            m = np.array([np.interp(t['L'] / 2, s_, P[:, j]) for j in range(2)])
            ax.text(m[0], m[1], f"{_num(t['L'], 0)} m", fontsize=6.5 * escala_texto, rotation=ang, rotation_mode='anchor', ha='center', va='bottom',
                    color='#1c252b', zorder=4, bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.75))
    for b in M['bocaminas']:
        ax.plot(b['E'], b['N'], marker='s', ms=9 * escala_texto, mfc='#014f7d', mec='white', zorder=5)
        if etiquetas: ax.annotate(b['nombre'], (b['E'], b['N']), xytext=(7, 7), textcoords='offset points', fontsize=8 * escala_texto,
                                  weight='bold', color='#014f7d', zorder=6, bbox=caja)
    for f in M['frentes']:
        r = next((x for x in res_ch4 if x['id'] == f['id']), None)
        ax.plot(f['E'], f['N'], marker='o', ms=8 * escala_texto, mfc=CLASES_CH4[r['clase']][0] if r else '#5d4037', mec='white', zorder=5)
        if etiquetas:
            t = f['nombre'] + (f"\n{_num(r['ch4'], 2)} % CH₄" if r else '')
            der = f['E'] > E0 + 0.72 * (E1 - E0)
            ax.annotate(t, (f['E'], f['N']), xytext=(-6 if der else 6, -12), textcoords='offset points', ha='right' if der else 'left',
                        fontsize=7.5 * escala_texto, zorder=6, bbox=caja)
    ax.set_xlim(E0, E1); ax.set_ylim(N0, N1); ax.set_aspect('equal')


def _norte_y_escala(ax, ext):
    import matplotlib.patches as mp
    E0, E1, N0, N1 = ext
    ancho, alto = E1 - E0, N1 - N0
    largo = [v for v in (5, 10, 20, 25, 50, 100, 200, 250, 500, 1000) if v <= ancho * 0.25][-1]
    x0, y0 = E0 + ancho * 0.04, N0 + alto * 0.05
    ax.add_patch(mp.Rectangle((x0 - ancho * 0.012, y0 - alto * 0.025), largo + ancho * 0.03, alto * 0.075, fc='white', ec='none', alpha=0.88, zorder=7))
    ax.plot([x0, x0 + largo / 2], [y0, y0], color='#1c252b', lw=5, solid_capstyle='butt', zorder=8)
    ax.plot([x0 + largo / 2, x0 + largo], [y0, y0], color='white', lw=5, solid_capstyle='butt', zorder=8)
    ax.plot([x0, x0 + largo], [y0, y0], color='#1c252b', lw=0.8, zorder=9)
    ax.text(x0, y0 + alto * 0.014, '0', fontsize=7, ha='center', zorder=9)
    ax.text(x0 + largo, y0 + alto * 0.014, f'{largo} m', fontsize=7, ha='center', zorder=9)
    xn, yn, h = E1 - ancho * 0.06, N1 - alto * 0.13, alto * 0.07
    ax.annotate('', xy=(xn, yn + h), xytext=(xn, yn), arrowprops=dict(arrowstyle='-|>', lw=2, color='#1c252b'), zorder=9)
    ax.text(xn, yn + h * 1.15, 'N', ha='center', va='bottom', fontsize=11, weight='bold', zorder=9)


def plano2d(M, ext, ruta, sup, res_ch4, C=None):
    """Planta para la vista 2D de la página (el norte y la escala gráfica los pone la página): legible al abrir, sin acercar."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    E0, E1, N0, N1 = ext
    k = 10.0 / max(E1 - E0, N1 - N0); w, h = (E1 - E0) * k, (N1 - N0) * k
    fig = plt.figure(figsize=(w, h), dpi=300); ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
    _dibujar_planta(ax, M, ext, sup, res_ch4, grosor=2.6, escala_texto=1.35, C=C, longitudes=True)
    png = ruta[:-4] + '_tmp.png'
    fig.savefig(png, dpi=300, facecolor='white'); plt.close(fig)
    Image.open(png).convert('RGB').save(ruta, quality=88); os.remove(png)


def plano_carta(M, ext, sup, res_ch4, capas_cfg, cfg, ruta, url=None, C=None):
    """Plano carta horizontal para llevar a la visita: planta, convenciones, metano medido, rótulo y QR."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mp
    from matplotlib.backends.backend_pdf import PdfPages
    fig = plt.figure(figsize=(11, 8.5))
    E0, E1, N0, N1 = ext
    r = (N1 - N0) / (E1 - E0) * (11 / 8.5); W = 0.66
    if r * W > 0.9: W = 0.9 / r
    ax = fig.add_axes([0.03, 0.05 + (0.9 - W * r) / 2, W, W * r]); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_color('#1c252b')
    _dibujar_planta(ax, M, ext, sup, res_ch4, grosor=1.8, escala_texto=0.9, C=C)
    _norte_y_escala(ax, ext)
    x = min(0.72, max(0.5, 0.03 + W + 0.035)); azul = cfg.get('color', '#014f7d')
    ancho_txt = int((0.985 - x - 0.04) * 11 * 72 / (7 * 0.52))   # caracteres que caben a 7 pt
    corta = lambda t: t if len(t) <= ancho_txt else t[:ancho_txt - 1] + '…'
    fig.text(x, 0.945, cfg['titulo'], fontsize=13, weight='bold', va='top', wrap=True)
    if cfg.get('subtitulo'): fig.text(x, 0.905, cfg['subtitulo'], fontsize=8.5, va='top', color='#444', wrap=True)
    y = 0.85; fig.text(x, y, 'Convenciones', fontsize=9.5, weight='bold', color=azul); y -= 0.03
    for c in capas_cfg[:14]:
        fig.add_artist(mp.Rectangle((x, y - 0.006), 0.03, 0.012, transform=fig.transFigure, fc=c['color'], ec='#222', lw=0.5))
        fig.text(x + 0.038, y, corta(f"{c['capa']} ({c['tipo_nombre'].lower()}, {_num(c['longitud_m'], 0)} m)"), fontsize=7, va='center'); y -= 0.024
    if M['limites']:
        fig.add_artist(matplotlib.lines.Line2D([x, x + 0.03], [y, y], transform=fig.transFigure, color='#c62828', lw=1.3, ls=(0, (6, 3))))
        fig.text(x + 0.038, y, 'Límite del título', fontsize=7, va='center'); y -= 0.024
    if res_ch4:
        y -= 0.01; fig.text(x, y, 'Metano medido en los frentes (% CH₄)', fontsize=9.5, weight='bold', color=azul); y -= 0.028
        for rr in res_ch4[:9]:
            fig.add_artist(mp.Circle((x + 0.006, y), 0.006, transform=fig.transFigure, fc=CLASES_CH4[rr['clase']][0], ec='white'))
            fig.text(x + 0.02, y, f"{rr['nombre']}: {_num(rr['ch4'], 2)} %" + (f"  ({rr['fecha']})" if rr.get('fecha') else ''), fontsize=7, va='center'); y -= 0.022
        fig.text(x, y - 0.004, 'Máximo en frentes de trabajo y retornos principales: 1,0 %\n(Decreto 1886 de 2015, art. 53).', fontsize=6.3, color='#7a1f1f', va='top')
    if url:
        import qrcode
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=10, border=2); q.add_data(url); q.make(fit=True)
        axq = fig.add_axes([x, 0.12, 0.13, 0.13 * 11 / 8.5]); axq.imshow(q.make_image(fill_color='black', back_color='white').convert('RGB')); axq.axis('off')
        fig.text(x + 0.14, 0.185, 'Escanee para ver\nla mina en 3D', fontsize=8, va='center')
    pie = (cfg.get('pie') or {}).get('texto', ''); elab = (cfg.get('elaboro') or {}).get('nombre', '')
    fig.text(x, 0.085, pie + (f' · Elaboró: {elab}' if elab else ''), fontsize=7, color='#444')
    fig.text(x, 0.065, f"Fecha: {cfg['mina']['fecha']} · Escala gráfica", fontsize=6.5, color='#444')
    fig.text(x, 0.045, 'Esquema para socializar: no reemplaza el plano oficial de labores.', fontsize=6.5, color='#7a1f1f')
    with PdfPages(ruta) as pdf: pdf.savefig(fig)
    fig.savefig(ruta[:-4] + '.png', dpi=150); plt.close(fig)
