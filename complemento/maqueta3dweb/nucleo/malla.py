# -*- coding: utf-8 -*-
"""Construcción de la maqueta 3D (GLB) en Python puro: numpy + pyfqmr + trimesh. Sin Blender.

Escena en metros del objeto físico: x este, y norte, z arriba, origen en el centro de la hoja.
Al exportar pasa a glTF (x, y arriba, z sur), que es lo que espera la página del kit."""
import io, json, struct
import numpy as np

BASE_REL = 0.0005   # el relieve va 0,5 mm sobre la hoja (igual que la página del kit)


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _material(nombre, imagen=None, color=(240, 238, 232), rug=1.0):
    import trimesh
    from PIL import Image
    img = None
    if imagen is not None:
        im = imagen if isinstance(imagen, Image.Image) else Image.open(imagen)
        if im.mode in ('RGBA', 'LA') and 'A' in im.getbands() and min(im.getchannel('A').getextrema()) < 255:
            img = im                                   # con transparencia: PNG
        else:                                          # sin transparencia: JPEG dentro del GLB (mucho más liviano)
            b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=88); b.seek(0); img = Image.open(b)
    col = None if img is not None else tuple(int(round(_lin(c) * 255)) for c in color[:3]) + (255,)
    return trimesh.visual.material.PBRMaterial(name=nombre, baseColorTexture=img, baseColorFactor=col,
                                               metallicFactor=0.0, roughnessFactor=rug, doubleSided=False)


def _a_gltf(v):
    v = np.asarray(v, float)
    return np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])


def _parchar_glb(datos):
    """Especular 0 (KHR_materials_specular) y bordes de textura CLAMP."""
    lj = struct.unpack_from('<I', datos, 12)[0]
    js = json.loads(datos[20:20 + lj]); resto = datos[20 + lj:]
    js['extensionsUsed'] = sorted(set(js.get('extensionsUsed', [])) | {'KHR_materials_specular'})
    for m in js.get('materials', []):
        m.setdefault('extensions', {})['KHR_materials_specular'] = {'specularFactor': 0.0}
    for s in js.get('samplers', []):
        s.update(wrapS=33071, wrapT=33071)
    nj = json.dumps(js, separators=(',', ':')).encode(); nj += b' ' * ((4 - len(nj) % 4) % 4)
    cuerpo = struct.pack('<II', len(nj), 0x4E4F534A) + nj + resto
    return struct.pack('<4sII', b'glTF', 2, 12 + len(cuerpo)) + cuerpo


def pared_textura(alto=256):
    """Degradado café para las paredes del bloque (claro arriba, oscuro abajo)."""
    from PIL import Image
    a = np.linspace(0, 1, alto)[:, None]
    arriba, abajo = np.array([150, 112, 72]), np.array([86, 60, 36])
    col = (abajo * (1 - a) + arriba * a).astype(np.uint8)[::-1]
    return Image.fromarray(np.repeat(col[:, None, :], 8, axis=1).reshape(alto, 8, 3))


def construir_plano(Z, ext, hoja_mm, marco_mm, esc, ve, zmin, tex_mapa, tex_hoja, salida,
                    caras=340000, pines=None, atlas=None, progreso=print):
    """Z: rejilla de alturas (m) que cubre exactamente la extensión del marco, fila 0 al norte.
    ext = (E0, E1, N0, N1); hoja_mm = (ancho, alto); marco_mm = (x, y, ancho, alto) desde la esquina superior izquierda.
    tex_mapa: 2 × 2 imágenes [[NO, NE], [SO, SE]]; tex_hoja: imagen de la hoja completa.
    pines: lista de dict(nombre, grupo, x, y, z) en metros de escena; atlas: (imagen, info) de los letreros."""
    import trimesh, pyfqmr
    E0, E1, N0, N1 = ext; PW, PH = hoja_mm; MX, MY, MW, MH = marco_mm
    px = lambda xmm: (xmm - PW / 2) / 1000.0
    py = lambda ymm: (PH / 2 - ymm) / 1000.0
    x0, x1, ytop, ybot = px(MX), px(MX + MW), py(MY), py(MY + MH)
    xm, ym = (x0 + x1) / 2, (ytop + ybot) / 2
    piezas = []

    def pieza(nombre, V, F, uv, mat, suave=True):
        piezas.append((nombre, np.asarray(V, float), np.asarray(F, np.int64), uv, mat, suave))

    Z = np.asarray(Z, float); ny, nx = Z.shape
    Xs = np.linspace(x0, x1, nx); Ys = np.linspace(ytop, ybot, ny)
    ZZ = BASE_REL + (Z - zmin) * ve / esc
    ic = int(np.argmin(np.abs(Xs - xm))); jr = int(np.argmin(np.abs(Ys - ym)))
    k = ic - 1 if Xs[ic] > xm else ic; t = (xm - Xs[k]) / (Xs[k + 1] - Xs[k]); ZZ[:, ic] = ZZ[:, k] * (1 - t) + ZZ[:, k + 1] * t; Xs[ic] = xm
    k = jr - 1 if Ys[jr] < ym else jr; t = (ym - Ys[k]) / (Ys[k + 1] - Ys[k]); ZZ[jr, :] = ZZ[k, :] * (1 - t) + ZZ[k + 1, :] * t; Ys[jr] = ym

    tw, th = (x1 - x0) / 2, (ytop - ybot) / 2; tot = 2 * (nx - 1) * (ny - 1); n_rel = 0
    for j, (r0, r1) in enumerate(((0, jr), (jr, ny - 1))):
        for i, (c0, c1) in enumerate(((0, ic), (ic, nx - 1))):
            zz = ZZ[r0:r1 + 1, c0:c1 + 1]; XX, YY = np.meshgrid(Xs[c0:c1 + 1], Ys[r0:r1 + 1])
            V = np.column_stack([XX.ravel(), YY.ravel(), zz.ravel()]); h, w = zz.shape
            idx = np.arange(h * w).reshape(h, w); a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
            F = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
            s = pyfqmr.Simplify(); s.setMesh(V, F)
            s.simplify_mesh(target_count=max(1000, int(caras * len(F) / tot)), aggressiveness=7, preserve_border=True, verbose=False)
            V2, F2, _ = s.getMesh()
            tx0 = x0 + i * tw; ty0 = ytop - (j + 1) * th
            uv = np.column_stack([np.clip((V2[:, 0] - tx0) / tw, 0, 1), np.clip((V2[:, 1] - ty0) / th, 0, 1)])
            pieza(f'Relieve_{j}{i}', V2, F2, uv, _material(f'Mapa_{j}{i}', tex_mapa[j][i])); n_rel += len(F2)
    progreso(f'Relieve: {n_rel} caras')

    borde = ([(0, c) for c in range(nx)] + [(r, nx - 1) for r in range(1, ny)] +
             [(ny - 1, c) for c in range(nx - 2, -1, -1)] + [(r, 0) for r in range(ny - 2, 0, -1)])
    P = np.array([(Xs[c], Ys[r], ZZ[r, c]) for r, c in borde]); n = len(P)
    ab = P.copy(); ab[:, 2] = 0.0
    Fw = []
    for q in range(n):
        a_, b_ = q, (q + 1) % n
        Fw += [(a_, n + b_, n + a_), (a_, b_, n + b_)]
    zt = ZZ.max()
    uvw = np.column_stack([np.full(2 * n, 0.5), np.concatenate([P[:, 2] / zt, np.zeros(n)])])
    pieza('Paredes', np.concatenate([P, ab]), Fw, uvw, _material('Paredes', pared_textura(), rug=0.95), suave=False)

    def rect(nombre, xa, xb, ya, yb, z, mat):
        pieza(nombre, [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], [(0, 1, 2), (0, 2, 3)],
              np.array([(0, 0), (1, 0), (1, 1), (0, 1)], float), mat, False)
    rect('Hoja', -PW / 2000, PW / 2000, -PH / 2000, PH / 2000, 0.0, _material('Hoja', tex_hoja))
    caja = trimesh.creation.box(extents=(PW / 1000, PH / 1000, 0.0039)); caja.apply_translation((0, 0, -0.00205))
    pieza('Canto', caja.vertices, caja.faces, None, _material('Canto', color=(238, 235, 228)), False)

    if pines:
        img_atlas, info = atlas
        ALTO = 0.013; grupos = {'metal': [], 'azul': [], 'negro': []}; LV, LF, LU = [], [], []
        def cil(x, y, z0, z1, r):
            m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=12); m.apply_translation((x, y, (z0 + z1) / 2)); return m
        for p in pines:
            alto = 0.034 if p['grupo'] == 0 else 0.026; col = 'azul' if p['grupo'] == 0 else 'negro'
            x, y, zb = p['x'], p['y'], p['z']; top = zb + alto
            grupos['metal'] += [cil(x, y, zb - 0.001, top, 0.0007), cil(x, y, top, top + 0.004, 0.0006)]
            sph = trimesh.creation.icosphere(subdivisions=2, radius=0.0032); sph.apply_translation((x, y, top)); grupos[col].append(sph)
            f = info['items'][p['fila']]; H, nf = info['H'], info['n']
            w = ALTO * f['ancho_px'] / H; v0, v1 = 1 - (p['fila'] + 1) / nf, 1 - p['fila'] / nf; u1 = f['ancho_px'] / info['W']
            z = top + 0.004
            for dy, (xa, xb) in ((-0.0004, (x - w / 2, x + w / 2)), (0.0004, (x + w / 2, x - w / 2))):
                b0 = len(LV)
                LV += [(xa, y + dy, z), (xb, y + dy, z), (xb, y + dy, z + ALTO), (xa, y + dy, z + ALTO)]
                LU += [(0, v0), (u1, v0), (u1, v1), (0, v1)]; LF += [(b0, b0 + 1, b0 + 2), (b0, b0 + 2, b0 + 3)]
        for nombre, col in (('metal', (191, 191, 191)), ('azul', (1, 79, 125)), ('negro', (17, 21, 24))):
            if grupos[nombre]:
                mm = trimesh.util.concatenate(grupos[nombre]); pieza(f'Chincheta_{nombre}', mm.vertices, mm.faces, None, _material(f'Chincheta_{nombre}', color=col, rug=0.6))
        pieza('Chincheta_letreros', LV, LF, np.array(LU, float), _material('Chincheta_letreros', img_atlas), False)

    escena = trimesh.Scene()
    for nombre, V, F, uv, mat, suave in piezas:
        vis = trimesh.visual.TextureVisuals(uv=uv, material=mat) if uv is not None else trimesh.visual.TextureVisuals(material=mat)
        m = trimesh.Trimesh(vertices=_a_gltf(V), faces=F, visual=vis, process=False)
        if not suave: m.unmerge_vertices()
        escena.add_geometry(m, geom_name=nombre, node_name=nombre)
    datos = _parchar_glb(escena.export(file_type='glb', include_normals=True))
    open(salida, 'wb').write(datos)
    progreso(f'Maqueta: {len(datos) / 1e6:.1f} MB')
    return dict(x0=x0, x1=x1, ytop=ytop, ybot=ybot, caras=sum(len(p[2]) for p in piezas))


def atlas_letreros(nombres_por_grupo, fuente=None):
    """nombres_por_grupo: [(grupo, nombre)], grupo 0 = azul (títulos), 1 = negro (municipios). Devuelve (imagen, info)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        F = ImageFont.truetype(fuente or 'DejaVuSans-Bold.ttf', 84)
    except Exception:
        try: F = ImageFont.truetype('arialbd.ttf', 84)
        except Exception: F = ImageFont.load_default()
    colores = {0: (1, 79, 125), 1: (17, 21, 24)}; H, W = 128, 1024
    img = Image.new('RGB', (W, H * max(1, len(nombres_por_grupo))), (255, 255, 255)); d = ImageDraw.Draw(img); items = []
    for k, (g, n) in enumerate(nombres_por_grupo):
        w = min(W, int(d.textlength(n, font=F) + 70)); y = k * H
        d.rectangle((0, y, w, y + H - 1), fill=colores[g]); d.rectangle((0, y + H - 12, w, y + H - 1), fill=(146, 146, 146) if g == 0 else (1, 79, 125))
        d.text((35, y + H / 2 - 5), n, font=F, fill=(255, 255, 255), anchor='lm'); items.append({'grupo': g, 'nombre': n, 'ancho_px': w})
    return img, {'H': H, 'W': W, 'n': len(items), 'items': items}
