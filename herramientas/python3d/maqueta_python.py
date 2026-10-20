"""Maqueta 3D del plano en relieve SIN Blender: numpy + pyfqmr (simplificación) + trimesh (GLB).
Reemplaza maqueta_blender.py + chinchetas_blender.py con el mismo resultado: relieve en 4 mosaicos de textura,
paredes del bloque, hoja con canto, rótulo en alta, chinchetas con letreros y alturas.json para el GPS.

Uso: python3 maqueta_python.py W SALIDA [--esc 65000] [--ve 2.5] [--zmin 100] [--caras 340000] [--sin-chinchetas]
W contiene (igual que para Blender): layout.json, dem30.json, dem30f.npy, tex2/mapa_00..11.jpg, tex2/pared.png,
tex2/hoja.jpg, tex2/rotulo_0.jpg, tex2/rotulo_1.jpg y, para chinchetas, etiquetas.json + atlas.json + tex2/etiquetas_atlas.png.
Escena en metros del objeto físico: x este, y norte, z arriba (como Blender); al exportar pasa a glTF (x, z, −y)."""
import sys, json, os, struct, argparse, io
import numpy as np, trimesh, pyfqmr
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('W'); ap.add_argument('OUT')
ap.add_argument('--esc', type=float, default=65000.0); ap.add_argument('--ve', type=float, default=2.5)
ap.add_argument('--zmin', type=float, default=100.0); ap.add_argument('--zocalo', type=float, default=0.004)
ap.add_argument('--caras', type=int, default=340000); ap.add_argument('--sin-chinchetas', action='store_true')
A = ap.parse_args(); W, OUT = A.W, A.OUT; os.makedirs(OUT, exist_ok=True)
ESC, VE, ZMIN, ZOCALO = A.esc, A.ve, A.zmin, A.zocalo

lay = json.load(open(f'{W}/layout.json')); meta = json.load(open(f'{W}/dem30.json'))
MX, MY, MW, MH = lay['map']; RX, RY, RW, RH = lay['rot']; PW, PH = lay['page']
E0, E1, N0, N1, res = meta['E0'], meta['E1'], meta['N0'], meta['N1'], meta['res']
def px(xmm): return (xmm - PW / 2) / 1000.0
def py(ymm): return (PH / 2 - ymm) / 1000.0
x0, x1, ytop, ybot = px(MX), px(MX + MW), py(MY), py(MY + MH)
xm, ym = (x0 + x1) / 2, (ytop + ybot) / 2

def material(nombre, imagen=None, color=(240, 238, 232, 255), rug=1.0):
    img = None
    if not imagen:   # glTF guarda el color base en espacio lineal: convertir desde sRGB
        lin = lambda c: ((c / 255) / 12.92 if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4)
        color = tuple(int(round(lin(c) * 255)) for c in color[:3]) + (255,)
    if imagen:
        im = Image.open(imagen)
        if im.mode in ('RGBA', 'LA', 'P') and imagen.lower().endswith('.png'): img = im      # con transparencia: PNG
        else:                                                                                # resto: JPEG dentro del GLB
            b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=88); b.seek(0); img = Image.open(b)
    return trimesh.visual.material.PBRMaterial(name=nombre, baseColorTexture=img, baseColorFactor=None if img else color,
                                               metallicFactor=0.0, roughnessFactor=rug, doubleSided=False)
def a_gltf(v):   # (x, y norte, z arriba) -> glTF (x, y arriba, z sur)
    v = np.asarray(v, float); return np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])
PIEZAS = []      # (nombre, vértices escena, caras, uv o None, material, suave)
def pieza(nombre, V, F, uv, mat, suave=True): PIEZAS.append((nombre, np.asarray(V, float), np.asarray(F, np.int64), uv, mat, suave))

# ---------- 1. Rejilla del relieve ----------
Z = np.load(f'{W}/dem30f.npy').astype(np.float64); ny, nx = Z.shape
E = E0 + np.arange(nx) * res; E[-1] = E1
N = N1 - np.arange(ny) * res; N[-1] = N0
Xs = x0 + (E - E0) / ESC; Ys = ytop - (N1 - N) / ESC
ZZ = ZOCALO + (Z - ZMIN) * VE / ESC
# columna y fila de corte de los mosaicos, movidas exactamente a la mitad del mapa (desplazamiento < media celda)
ic = int(np.argmin(np.abs(Xs - xm))); jr = int(np.argmin(np.abs(Ys - ym)))
def interp_col(c, x):   # altura en x exacto entre columnas c-1/c/c+1
    k = c - 1 if Xs[c] > x else c; t = (x - Xs[k]) / (Xs[k + 1] - Xs[k]); return ZZ[:, k] * (1 - t) + ZZ[:, k + 1] * t
ZZ[:, ic] = interp_col(ic, xm); Xs = Xs.copy(); Xs[ic] = xm
k = jr - 1 if Ys[jr] < ym else jr; t = (ym - Ys[k]) / (Ys[k + 1] - Ys[k]); ZZ[jr, :] = ZZ[k, :] * (1 - t) + ZZ[k + 1, :] * t; Ys = Ys.copy(); Ys[jr] = ym

tw, th = (x1 - x0) / 2, (ytop - ybot) / 2
tot_tri = 2 * (nx - 1) * (ny - 1); caras_rel = 0
for j, (r0, r1) in enumerate(((0, jr), (jr, ny - 1))):          # j=0 arriba (norte)
    for i, (c0, c1) in enumerate(((0, ic), (ic, nx - 1))):      # i=0 izquierda (oeste)
        xs, ys = Xs[c0:c1 + 1], Ys[r0:r1 + 1]; zz = ZZ[r0:r1 + 1, c0:c1 + 1]
        XX, YY = np.meshgrid(xs, ys); V = np.column_stack([XX.ravel(), YY.ravel(), zz.ravel()])
        h, w = zz.shape; idx = np.arange(h * w).reshape(h, w)
        a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
        F = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
        meta_obj = int(A.caras * len(F) / tot_tri)
        s = pyfqmr.Simplify(); s.setMesh(V, F)
        s.simplify_mesh(target_count=meta_obj, aggressiveness=7, preserve_border=True, verbose=False)
        V2, F2, _ = s.getMesh()
        tx0 = x0 + i * tw; ty0 = ytop - (j + 1) * th
        uv = np.column_stack([np.clip((V2[:, 0] - tx0) / tw, 0, 1), np.clip((V2[:, 1] - ty0) / th, 0, 1)])
        pieza(f'Relieve_{j}{i}', V2, F2, uv, material(f'Mapa_{j}{i}', f'{W}/tex2/mapa_{j}{i}.jpg'))
        caras_rel += len(F2)
print('caras del relieve:', caras_rel)

# ---------- 2. Paredes del bloque (borde de la rejilla completa hasta z = 0) ----------
borde = ([(0, c) for c in range(nx)] + [(r, nx - 1) for r in range(1, ny)] +
         [(ny - 1, c) for c in range(nx - 2, -1, -1)] + [(r, 0) for r in range(ny - 2, 0, -1)])
P = np.array([(Xs[c], Ys[r], ZZ[r, c]) for r, c in borde]); n = len(P)
arriba = P; abajo = P.copy(); abajo[:, 2] = 0.0
Vw = np.concatenate([arriba, abajo]); Fw = []
for q in range(n):
    a_, b_ = q, (q + 1) % n
    Fw += [(a_, n + b_, n + a_), (a_, b_, n + b_)]     # el borde se recorre en sentido horario: así las normales miran hacia afuera
zt = ZZ.max(); uvw = np.column_stack([np.full(2 * n, 0.5), np.concatenate([P[:, 2] / zt, np.zeros(n)])])
pieza('Paredes', Vw, Fw, uvw, material('Paredes', f'{W}/tex2/pared.png', rug=0.95), suave=False)

# ---------- 3. Hoja, canto y rótulo ----------
def rect(nombre, xa, xb, ya, yb, z, mat):
    pieza(nombre, [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], [(0, 1, 2), (0, 2, 3)], np.array([(0, 0), (1, 0), (1, 1), (0, 1)], float), mat, False)
rect('Hoja', -PW / 2000, PW / 2000, -PH / 2000, PH / 2000, 0.0, material('Hoja', f'{W}/tex2/hoja.jpg'))
caja = trimesh.creation.box(extents=(PW / 1000, PH / 1000, 0.0039)); caja.apply_translation((0, 0, -0.00205))
pieza('Canto', caja.vertices, caja.faces, None, material('Canto', color=(238, 235, 228, 255)), False)
half = RH / 2
rect('Rotulo_superior', px(RX), px(RX + RW), py(RY + half), py(RY), 0.0004, material('Rotulo_0', f'{W}/tex2/rotulo_0.jpg'))
rect('Rotulo_inferior', px(RX), px(RX + RW), py(RY + RH), py(RY + half), 0.0004, material('Rotulo_1', f'{W}/tex2/rotulo_1.jpg'))

# ---------- 4. Chinchetas (alfiler, cabeza y letrero de doble cara) ----------
if not A.sin_chinchetas and os.path.exists(f'{W}/etiquetas.json'):
    et = json.load(open(f'{W}/etiquetas.json')); at = json.load(open(f'{W}/atlas.json'))
    ALTO = 0.013; grupos = {'metal': [], 'azul': [], 'negro': []}; LV, LF, LU = [], [], []
    def cil(x, y, z0, z1, r):
        m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=12); m.apply_translation((x, y, (z0 + z1) / 2)); return m
    for grupo, alto, col in (('titulos', 0.034, 'azul'), ('municipios', 0.026, 'negro')):
        for it in et[grupo]:
            gx, gy, gz = it['pos']; x, y, zb = gx, -gz, gy; top = zb + alto
            grupos['metal'] += [cil(x, y, zb - 0.001, top, 0.0007), cil(x, y, top, top + 0.004, 0.0006)]
            s = trimesh.creation.icosphere(subdivisions=2, radius=0.0032); s.apply_translation((x, y, top)); grupos[col].append(s)
            f = next(q for q in at['items'] if q['nombre'] == it['nombre'] and q['grupo'] == grupo)
            H, nf = at['H'], at['n']; w = ALTO * f['ancho_px'] / H; v0, v1 = 1 - (f['fila'] + 1) / nf, 1 - f['fila'] / nf; u1 = f['ancho_px'] / at['W']
            z = top + 0.004
            for dy, orden in ((-0.0004, ((x - w / 2), (x + w / 2))), (0.0004, ((x + w / 2), (x - w / 2)))):
                xa, xb = orden; base = len(LV)
                LV += [(xa, y + dy, z), (xb, y + dy, z), (xb, y + dy, z + ALTO), (xa, y + dy, z + ALTO)]
                LU += [(0, v0), (u1, v0), (u1, v1), (0, v1)]; LF += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
    for nombre, col in (('metal', (191, 191, 191, 255)), ('azul', (1, 79, 125, 255)), ('negro', (17, 21, 24, 255))):
        if grupos[nombre]:
            mm = trimesh.util.concatenate(grupos[nombre]); pieza(f'Chincheta_{nombre}', mm.vertices, mm.faces, None, material(f'Chincheta_{nombre}', color=col, rug=0.6))
    pieza('Chincheta_letreros', LV, LF, np.array(LU, float), material('Chincheta_letreros', f'{W}/tex2/etiquetas_atlas.png'), False)
    print('chinchetas:', sum(len(et[g]) for g in ('titulos', 'municipios')))

# ---------- 5. Alturas para el GPS (igual que la versión de Blender) ----------
gx, gy = 160, 140
ii = np.linspace(0, nx - 1, gx).round().astype(int); jj = np.linspace(0, ny - 1, gy).round().astype(int)
ZG = ZOCALO + (Z - ZMIN) * VE / ESC
json.dump({'ESC': ESC, 'VE': VE, 'E0': E0, 'E1': E1, 'N0': N0, 'N1': N1, 'x0': x0, 'x1': x1, 'ytop': ytop, 'ybot': ybot,
           'gx': gx, 'gy': gy, 'alt_01mm': (ZG[np.ix_(jj, ii)] * 1e4).round().astype(int).tolist()},
          open(f'{OUT}/alturas.json', 'w'), separators=(',', ':'))

# ---------- 6. Exportar GLB ----------
escena = trimesh.Scene()
for nombre, V, F, uv, mat, suave in PIEZAS:
    vis = trimesh.visual.TextureVisuals(uv=uv, material=mat) if uv is not None else trimesh.visual.TextureVisuals(material=mat)
    m = trimesh.Trimesh(vertices=a_gltf(V), faces=F, visual=vis, process=False)
    if not suave:   # caras planas: duplicar vértices por cara para que las normales no se promedien
        m.unmerge_vertices()
    escena.add_geometry(m, geom_name=nombre, node_name=nombre)
glb = escena.export(file_type='glb', include_normals=True)

def parchar_glb(datos):
    """Especular 0 (KHR_materials_specular) y texturas con bordes CLAMP, como deja Blender."""
    lj = struct.unpack_from('<I', datos, 12)[0]; js = json.loads(datos[20:20 + lj]); resto = datos[20 + lj:]
    js.setdefault('extensionsUsed', []); js['extensionsUsed'] = sorted(set(js['extensionsUsed']) | {'KHR_materials_specular'})
    for m in js.get('materials', []): m.setdefault('extensions', {})['KHR_materials_specular'] = {'specularFactor': 0.0}
    for s in js.get('samplers', []): s.update(wrapS=33071, wrapT=33071)
    nj = json.dumps(js, separators=(',', ':')).encode(); nj += b' ' * ((4 - len(nj) % 4) % 4)
    cuerpo = struct.pack('<II', len(nj), 0x4E4F534A) + nj + resto
    return struct.pack('<4sII', b'glTF', 2, 12 + len(cuerpo)) + cuerpo
open(f'{OUT}/plano_relieve.glb', 'wb').write(parchar_glb(glb))
print('GLB', round(os.path.getsize(f'{OUT}/plano_relieve.glb') / 1e6, 1), 'MB', '·', sum(len(p[2]) for p in PIEZAS), 'caras')
