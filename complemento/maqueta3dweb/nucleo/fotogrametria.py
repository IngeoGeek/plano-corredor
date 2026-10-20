# -*- coding: utf-8 -*-
"""Modo fotogrametría: se elige la carpeta del vuelo procesado y el complemento encuentra todo.
Reconoce DJI Terra (probado con Carboland), WebODM/ODM, Pix4D y, de forma genérica, cualquier carpeta con un OBJ
(Metashape u otros). La malla se simplifica por bloques (bordes fijos, sin grietas) y se viste con la ortofoto
vista desde arriba; si la carpeta no trae ortofoto, se arma una con las texturas de la propia malla."""
import os, re, glob, json, math
import numpy as np

BASE = 0.0005


def _mayor(patrones, raiz):
    c = [f for p in patrones for f in glob.glob(os.path.join(raiz, p), recursive=True)]
    return max(c, key=os.path.getsize) if c else None


def _epsg_utm(texto):
    m = re.search(r'UTM\s*(?:zone\s*)?(\d{1,2})\s*([NS])', texto, re.I)
    if not m: return None
    return f'EPSG:{(32600 if m.group(2).upper() == "N" else 32700) + int(m.group(1))}'


def _objs_y_zips(raiz):
    """OBJ de cada bloque; si un bloque viene comprimido (.zip con el .obj adentro) también cuenta."""
    import zipfile
    out = sorted(glob.glob(os.path.join(raiz, '*', '*.obj')))
    hechos = {os.path.dirname(o) for o in out}
    for z in sorted(glob.glob(os.path.join(raiz, '*', '*.zip'))):
        if os.path.dirname(z) in hechos: continue
        try:
            if any(n.lower().endswith('.obj') for n in zipfile.ZipFile(z).namelist()): out.append(z)
        except Exception: pass
    return out


def analizar(carpeta):
    A = dict(carpeta=carpeta, programa='Genérico', objs=[], epsg=None, origen=None, orto=None, vista_previa=None, fotos=None, fix=None, gsd=None, area_ha=None, avisos=[])
    meta = glob.glob(os.path.join(carpeta, '**', 'terra_obj', 'metadata.xml'), recursive=True)
    if meta:
        A['programa'] = 'DJI Terra'; x = open(meta[0], encoding='utf-8', errors='ignore').read()
        A['epsg'] = re.search(r'<SRS>([^<]+)</SRS>', x).group(1)
        A['origen'] = tuple(map(float, re.search(r'<SRSOrigin>([^<]+)</SRSOrigin>', x).group(1).split(',')))
        A['objs'] = _objs_y_zips(os.path.dirname(meta[0]))
        A['orto'] = _mayor(['map/result.tif', 'map/*.tif'], carpeta)
        vp = os.path.join(carpeta, 'map', 'report', 'dom_screennail.png'); A['vista_previa'] = vp if os.path.exists(vp) else None
        rep = os.path.join(carpeta, 'map', 'report', 'map_report.json')
        if os.path.exists(rep):
            r = json.load(open(rep, encoding='utf-8')); A['gsd'] = r.get('TDOM GSD'); A['area_ha'] = round(r.get('covered area', 0) * 100, 1)
            t = [d['tfw'] for d in r.get('datasets_tfw', []) if d.get('type') == 'RGB']
            if t:
                t = t[0]; E0 = A['origen'][0] + t['corner_tl_x']; N1 = A['origen'][1] + t['corner_tl_y']
                A['ext_orto'] = (E0, E0 + t['width'] * t['scale_x'], N1 + t['height'] * t['scale_y'], N1)
        for rp in glob.glob(os.path.join(carpeta, '**', 'report', 'report.md'), recursive=True):
            md = open(rp, encoding='utf-8', errors='ignore').read()
            f = re.search(r'# Input Images\s*\|\s*(\d+)', md); x2 = re.search(r'\|\s*FIX\s*\|\s*(\d+)', md)
            if f: A['fotos'] = int(f.group(1))
            if x2: A['fix'] = int(x2.group(1))
            if f: break
    elif glob.glob(os.path.join(carpeta, '**', 'odm_textured_model_geo.obj'), recursive=True):
        A['programa'] = 'WebODM / ODM'
        A['objs'] = glob.glob(os.path.join(carpeta, '**', 'odm_textured_model_geo.obj'), recursive=True)[:1]
        co = glob.glob(os.path.join(carpeta, '**', 'odm_georeferencing', 'coords.txt'), recursive=True)
        if co:
            l = open(co[0]).read().splitlines(); A['epsg'] = _epsg_utm(l[0]) if l else None
            if len(l) > 1: e, n = map(float, l[1].split()[:2]); A['origen'] = (e, n, 0.0)
        A['orto'] = _mayor(['**/odm_orthophoto.tif'], carpeta)
    elif glob.glob(os.path.join(carpeta, '**', '2_densification', '3d_mesh', '*.obj'), recursive=True):
        A['programa'] = 'Pix4D'
        A['objs'] = [max(glob.glob(os.path.join(carpeta, '**', '2_densification', '3d_mesh', '*.obj'), recursive=True), key=os.path.getsize)]
        off = glob.glob(os.path.join(carpeta, '**', '1_initial', 'params', '*offset.xyz'), recursive=True)
        if off: A['origen'] = tuple(map(float, open(off[0]).read().split()[:3]))
        A['orto'] = _mayor(['**/3_dsm_ortho/2_mosaic/*.tif'], carpeta)
    else:
        o = _mayor(['**/*.obj'], carpeta); A['objs'] = [o] if o else []
        A['orto'] = None
        for t in sorted(glob.glob(os.path.join(carpeta, '**', '*.tif'), recursive=True), key=os.path.getsize, reverse=True):
            try:
                from osgeo import gdal
                ds = gdal.Open(t)
                if ds and ds.RasterCount >= 3: A['orto'] = t; break
            except Exception: pass
        if A['objs']:
            prj = glob.glob(os.path.splitext(A['objs'][0])[0] + '*.prj')
            if prj:
                from qgis.core import QgsCoordinateReferenceSystem
                c = QgsCoordinateReferenceSystem.fromWkt(open(prj[0]).read()); A['epsg'] = c.authid() or None
    if A['orto'] and (not A['epsg'] or 'ext_orto' not in A):
        try:
            from osgeo import gdal, osr
            ds = gdal.Open(A['orto']); gt = ds.GetGeoTransform()
            A['ext_orto'] = A.get('ext_orto') or (gt[0], gt[0] + gt[1] * ds.RasterXSize, gt[3] + gt[5] * ds.RasterYSize, gt[3])
            if not A['epsg']:
                s = osr.SpatialReference(wkt=ds.GetProjection()); s.AutoIdentifyEPSG()
                if s.GetAuthorityCode(None): A['epsg'] = f'EPSG:{s.GetAuthorityCode(None)}'
            if A['gsd'] is None: A['gsd'] = abs(gt[1])
        except Exception as e: A['avisos'].append(f'No se pudo leer la ortofoto ({e})')
    if not A['objs']: A['avisos'].append('No se encontró ninguna malla .obj en la carpeta.')
    if not A['epsg']: A['avisos'].append('No se encontró el sistema de coordenadas: hace falta indicarlo.')
    if A['origen'] is None and A['objs']: A['avisos'].append('Sin desplazamiento de origen en los metadatos: la malla se ubicará con la ortofoto.')
    return A


def resumen(A):
    t = [f'<b>Programa:</b> {A["programa"]}',
         f'<b>Malla:</b> {len(A["objs"])} archivo(s) OBJ' + (f' ({sum(os.path.getsize(o) for o in A["objs"]) / 1e6:.0f} MB)' if A['objs'] else ''),
         f'<b>Sistema:</b> {A["epsg"] or "—"}', f'<b>Ortofoto:</b> {"sí" if A["orto"] else "no está en la carpeta (se arma desde la malla)"}' + (f' · GSD {A["gsd"] * 100:.2f} cm' if A.get('gsd') else '')]
    if A.get('fotos'): t.append(f'<b>Fotos:</b> {A["fotos"]}' + (f' · RTK FIX en {A["fix"]}' if A.get('fix') else ''))
    if A.get('area_ha'): t.append(f'<b>Área:</b> {A["area_ha"]} ha')
    return '<br>'.join(t + [f'<span style="color:#b26a00">⚠ {a}</span>' for a in A['avisos']])




# ---------------------------------------------------------------- lectura de mallas
def _leer_obj(ruta, con_textura=False, tmp=None):
    """Posiciones y caras de un OBJ (rápido, con numpy). Con con_textura también devuelve, por cara,
    el centro en coordenadas de textura y la imagen de su material (para hacer una ortofoto si no hay)."""
    if ruta.lower().endswith('.zip'):
        import zipfile
        zf = zipfile.ZipFile(ruta); n = next(x for x in zf.namelist() if x.lower().endswith('.obj'))
        d = zf.read(n); base = os.path.dirname(ruta)
    else:
        d = open(ruta, 'rb').read(); base = os.path.dirname(ruta)
    L = d.split(b'\n'); del d
    V = np.array(b' '.join(l[2:] for l in L if l.startswith(b'v ')).split(), dtype=np.float64).reshape(-1, 3)
    if not con_textura:
        tok = b' '.join(l[2:] for l in L if l.startswith(b'f ')).split()
        F = np.array([t.split(b'/', 1)[0] for t in tok] if b'/' in tok[0] else tok, dtype=np.int64).reshape(-1, 3) - 1
        return V, F, None
    VT = np.array(b' '.join(l[3:] for l in L if l.startswith(b'vt ')).split(), dtype=np.float64).reshape(-1, 2)
    Fs, Ts, Ms, nombres, mat = [], [], [], [], -1; tramo = []

    def cerrar():
        if not tramo: return
        tok = np.array(b' '.join(tramo).replace(b'/', b' ').split(), dtype=np.int64)
        k = len(tok) // (len(tramo) * 3); tok = tok.reshape(len(tramo), 3, k) - 1
        Fs.append(tok[:, :, 0]); Ts.append(tok[:, :, 1] if k > 1 else np.zeros((len(tramo), 3), np.int64)); Ms.append(np.full(len(tramo), mat))
        tramo.clear()
    for l in L:
        if l.startswith(b'f '): tramo.append(l[2:].replace(b'//', b'/0/'))
        elif l.startswith(b'usemtl '):
            cerrar(); nombres.append(l[7:].strip().decode('utf-8', 'ignore')); mat = len(nombres) - 1
    cerrar()
    F = np.concatenate(Fs); T = np.concatenate(Ts); fm = np.concatenate(Ms)
    UVc = VT[T].mean(axis=1) if len(VT) else np.zeros((len(F), 2))
    imgs = {}
    mtl = re.search(rb'mtllib\s+(\S[^\r\n]*)', b'\n'.join(L[:50]))
    if mtl:
        rm = os.path.join(base, mtl.group(1).decode().strip()); actual = None
        if os.path.exists(rm):
            for l in open(rm, encoding='utf-8', errors='ignore'):
                if l.startswith('newmtl'): actual = l.split(None, 1)[1].strip()
                elif l.strip().startswith('map_Kd') and actual is not None: imgs[actual] = os.path.join(base, l.split(None, 1)[1].strip())
    return V, F, (UVc, fm, [imgs.get(n) for n in nombres])


def _tam(o):
    """Tamaño real del OBJ (descomprimido si viene en .zip): reparte las caras de forma justa entre bloques."""
    if o.lower().endswith('.zip'):
        import zipfile
        return sum(i.file_size for i in zipfile.ZipFile(o).infolist() if i.filename.lower().endswith('.obj'))
    return os.path.getsize(o)


def _simplificar(V, F, caras):
    import pyfqmr
    if len(F) <= caras: return V, F
    s = pyfqmr.Simplify(); s.setMesh(V, F)
    s.simplify_mesh(target_count=int(caras), aggressiveness=7, preserve_border=True, verbose=False)
    v, f, _ = s.getMesh(); return v, f


def _pseudo_orto(bloques, ext, res, progreso):
    """Sin ortofoto: color de cada cara (en su textura) proyectado desde arriba, la cara más alta gana."""
    from PIL import Image
    from osgeo import gdal
    E0, E1, N0, N1 = ext; nx = int(np.ceil((E1 - E0) / res)); ny = int(np.ceil((N1 - N0) / res))
    Z = np.full(ny * nx, -1e18); C = np.full((ny * nx, 3), 255, np.uint8)   # fuera del vuelo: blanco
    for (V, F, tex) in bloques:
        if tex is None: continue
        UVc, fm, imgs = tex; cen = V[F].mean(axis=1); col = np.full((len(F), 3), 128, np.uint8)
        for k, ruta in enumerate(imgs):
            sel = fm == k
            if not sel.any() or not ruta or not os.path.exists(ruta): continue
            im = Image.open(ruta).convert('RGB'); w, h = im.size; a = np.asarray(im)
            u = np.clip((UVc[sel, 0] % 1.0) * (w - 1), 0, w - 1).astype(int); v = np.clip((1 - UVc[sel, 1] % 1.0) * (h - 1), 0, h - 1).astype(int)
            col[sel] = a[v, u]
        ix = np.clip(((cen[:, 0] - E0) / res).astype(int), 0, nx - 1); iy = np.clip(((N1 - cen[:, 1]) / res).astype(int), 0, ny - 1)
        idx = iy * nx + ix; orden = np.argsort(cen[:, 2])            # la última escritura (la más alta) gana
        idx, zz, cc = idx[orden], cen[orden, 2], col[orden]; mejor = zz > Z[idx]
        Z[idx[mejor]] = zz[mejor]; C[idx[mejor]] = cc[mejor]
    vacio = (Z < -1e17).reshape(ny, nx); C = C.reshape(ny, nx, 3)
    ds = gdal.GetDriverByName('MEM').Create('', nx, ny, 3, gdal.GDT_Byte); ds.SetGeoTransform((E0, res, 0, N1, 0, -res))
    for b in range(3):
        ds.GetRasterBand(b + 1).WriteArray(C[..., b])
    if vacio.any():
        m = gdal.GetDriverByName('MEM').Create('', nx, ny, 1, gdal.GDT_Byte); m.GetRasterBand(1).WriteArray((~vacio).astype(np.uint8))
        for b in range(3): gdal.FillNodata(ds.GetRasterBand(b + 1), m.GetRasterBand(1), 20, 0)
    progreso(f'Ortofoto armada desde la malla ({nx} × {ny} px a {res * 100:.0f} cm)')
    return ds


# ---------------------------------------------------------------- proceso completo
def procesar(par, progreso=print):
    import trimesh
    from PIL import Image
    from osgeo import gdal
    from . import malla, sitio
    from qgis.core import QgsCoordinateReferenceSystem
    A = analizar(par['carpeta']); progreso(re.sub(r'<[^>]+>', '', resumen(A).replace('<br>', ' · ')))
    if not A['objs']: raise RuntimeError('No hay malla OBJ en la carpeta.')
    S = par['salida']; web = os.path.join(S, 'sitio'); os.makedirs(S, exist_ok=True); sitio.copiar_kit(web)
    sin_orto = not A['orto']
    total = sum(_tam(o) for o in A['objs']); objetivo = int(par.get('caras', 300000))

    # 1. Leer y simplificar cada bloque por separado (bordes fijos: no se abren grietas entre bloques)
    bloques = []
    for o in A['objs']:
        progreso(f'Leyendo {os.path.basename(o)} ({_tam(o) / 1e6:.0f} MB)…')
        V, F, tex = _leer_obj(o, con_textura=sin_orto)
        if sin_orto: bloques.append((V, F, tex))
        v, f = _simplificar(V, F, max(3000, objetivo * _tam(o) / total))
        progreso(f'  {len(F):,} → {len(f):,} caras'.replace(',', ' ')); bloques.append((v, f, 'simple'))
    crudos = [(V, F, t) for V, F, t in bloques if t != 'simple']; simples = [(V, F) for V, F, t in bloques if t == 'simple']

    # 2. Georreferenciar
    todo = np.concatenate([v for v, _ in simples])
    if A['origen'] is not None: oE, oN, oZ = A['origen']
    elif np.abs(todo[:, :2]).max() > 1e5: oE = oN = oZ = 0.0                    # la malla ya viene en coordenadas reales
    elif A.get('ext_orto'):
        e = A['ext_orto']; oE = (e[0] + e[1]) / 2 - (todo[:, 0].min() + todo[:, 0].max()) / 2; oN = (e[2] + e[3]) / 2 - (todo[:, 1].min() + todo[:, 1].max()) / 2; oZ = 0.0
    else: raise RuntimeError('No hay cómo ubicar la malla: no tiene coordenadas reales ni ortofoto.')
    if not A['epsg']: raise RuntimeError('No se encontró el sistema de coordenadas del vuelo (exporta la ortofoto con su sistema o un .prj junto al OBJ).')
    off = np.array([oE, oN, oZ]); simples = [(v + off, f) for v, f in simples]; crudos = [(v + off, f, t) for v, f, t in crudos]
    todo = todo + off
    E0, N0, z0 = todo.min(axis=0); E1, N1, z1 = todo.max(axis=0)
    lado = max(E1 - E0, N1 - N0)
    esc = float(par.get('escala') or next((s for s in (100, 200, 250, 500, 750, 1000, 1500, 2000, 2500, 5000, 10000, 25000) if lado / s <= 0.95), 50000))
    Ec, Nc = (E0 + E1) / 2, (N0 + N1) / 2
    progreso(f'Escala 1:{esc:,.0f} · {E1 - E0:.0f} × {N1 - N0:.0f} m · cotas {z0:.1f} a {z1:.1f} m'.replace(',', ' '))

    # 3. Ortofoto (la del programa o una armada desde las texturas de la malla)
    if A['orto']: orto = gdal.Open(A['orto'])
    else: orto = _pseudo_orto(crudos, (E0, E1, N0, N1), max(0.05, lado / 6000), progreso)
    del crudos
    gsd = abs(orto.GetGeoTransform()[1])

    # 4. Maqueta: malla en 4 cuadrantes, cada uno con su parte de la ortofoto (máx. 4096 px, lo que aguantan los celulares)
    V = np.concatenate([v for v, _ in simples]); k = 0; Fs = []
    for v, f in simples: Fs.append(f + k); k += len(v)
    F = np.concatenate(Fs); cen = V[F].mean(axis=1)
    escena = trimesh.Scene()
    for qi, (cx, cy) in enumerate(((0, 1), (1, 1), (0, 0), (1, 0))):
        sel = ((cen[:, 0] >= Ec) == bool(cx)) & ((cen[:, 1] >= Nc) == bool(cy))
        if not sel.any(): continue
        usados, inv = np.unique(F[sel], return_inverse=True); vq = V[usados]; fq = inv.reshape(-1, 3)
        e0, n0 = vq[:, 0].min(), vq[:, 1].min(); e1, n1 = vq[:, 0].max(), vq[:, 1].max()
        px = int(min(4096, max(256, (e1 - e0) / gsd))); py = int(min(4096, max(256, (n1 - n0) / gsd)))
        t = gdal.Translate('', orto, format='MEM', bandList=[1, 2, 3], projWin=[e0, n1, e1, n0], width=px, height=py, resampleAlg='average')
        img = Image.fromarray(np.dstack([t.GetRasterBand(b + 1).ReadAsArray() for b in range(3)]).astype(np.uint8))
        uv = np.column_stack([(vq[:, 0] - e0) / (e1 - e0), (vq[:, 1] - n0) / (n1 - n0)])
        x = (vq[:, 0] - Ec) / esc; y = (vq[:, 1] - Nc) / esc; z = (vq[:, 2] - z0) / esc + BASE
        m = trimesh.Trimesh(np.column_stack([x, z, -y]), fq, process=False)
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=malla._material(f'Malla_{qi}', img))
        escena.add_geometry(m, geom_name=f'Malla_{qi}')
    glb = malla._parchar_glb(escena.export(file_type='glb', include_normals=True)); open(os.path.join(web, 'plano_relieve.glb'), 'wb').write(glb)
    progreso(f'Maqueta: {len(glb) / 1e6:.1f} MB · {len(F):,} caras'.replace(',', ' '))

    # 5. Alturas reales para el GPS (máximo por celda, huecos rellenos)
    res = max(0.25, lado / 2000); nx = int(np.ceil((E1 - E0) / res)); ny = int(np.ceil((N1 - N0) / res))
    ix = np.clip(((V[:, 0] - E0) / res).astype(int), 0, nx - 1); iy = np.clip(((N1 - V[:, 1]) / res).astype(int), 0, ny - 1)
    G = np.full((ny, nx), -1e9, np.float32); np.maximum.at(G, (iy, ix), V[:, 2].astype(np.float32))
    ds = gdal.GetDriverByName('MEM').Create('', nx, ny, 1, gdal.GDT_Float32); b = ds.GetRasterBand(1); b.SetNoDataValue(-1e9); b.WriteArray(G)
    gdal.FillNodata(b, None, 100, 0); G = b.ReadAsArray(); G[G < -1e8] = z0
    Image.fromarray(np.clip((G - z0) / max(z1 - z0, 0.01) * 65535, 0, 65535).astype(np.uint16)).save(os.path.join(web, 'relieve.png'))

    # 6. Plano 2D
    ancho = int(min(6000, (E1 - E0) / gsd))
    t = gdal.Translate('', orto, format='MEM', bandList=[1, 2, 3], projWin=[E0, N1, E1, N0], width=ancho, height=0, resampleAlg='average')
    Image.fromarray(np.dstack([t.GetRasterBand(b + 1).ReadAsArray() for b in range(3)]).astype(np.uint8)).save(os.path.join(web, 'plano.jpg'), quality=88)
    progreso('Plano 2D listo')

    # 7. iPhone, configuración, zip y QR
    usdz = ''
    try:
        from . import usdz as U
        U.glb_a_usdz(os.path.join(web, 'plano_relieve.glb'), os.path.join(web, 'plano_relieve.usdz')); usdz = 'plano_relieve.usdz'
    except Exception as e:
        progreso(f'Sin .usdz para iPhone ({e.__class__.__name__}: {e})')
    crs = QgsCoordinateReferenceSystem(A['epsg']); proy = sitio.proyeccion_tm(crs)
    if not proy: progreso('Aviso: el sistema no es Transverso de Mercator; el GPS de la página puede no ubicarse bien.')
    aw, ah = (E1 - E0) / esc * 1000, (N1 - N0) / esc * 1000
    ficha = [['Escala de la maqueta', f'1:{esc:,.0f}'.replace(',', ' ')], ['Exageración vertical', '1 × (alturas reales)']]
    if A.get('fotos'): ficha.append(['Fotografías', f'{A["fotos"]}' + (f' · RTK FIX en {A["fix"]}' if A.get('fix') else '')])
    ficha.append(['Ortofoto', (f'GSD {(A.get("gsd") or gsd) * 100:.2f} cm' if A['orto'] else 'armada desde la malla').replace('.', ',')])
    if A.get('area_ha'): ficha.append(['Área levantada', f'{A["area_ha"]} ha'.replace('.', ',')])
    ficha += [['Sistema', A['epsg']], ['Procesado con', A['programa']]]
    logo = ''
    if par.get('logo') and os.path.exists(par['logo']):
        import shutil; logo = 'logo' + os.path.splitext(par['logo'])[1].lower(); shutil.copy(par['logo'], os.path.join(web, logo))
    color = par.get('color') or (sitio.color_del_logo(par['logo']) if par.get('logo') else '#014f7d')
    cfg = {'version': 1, 'titulo': par.get('titulo') or os.path.basename(par['carpeta'].rstrip('/\\')), 'subtitulo': par.get('subtitulo', ''), 'color': color,
           'hoja': {'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3)},
           'marco': {'x_mm': 0, 'y_mm': 0, 'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3), 'E_min': E0, 'E_max': E1, 'N_min': N0, 'N_max': N1},
           'relieve': {'imagen': 'relieve.png', 'z_min': float(z0), 'z_max': float(z1), 'exageracion': 1},
           'proyeccion': proy or {'lat_0': 0, 'lon_0': 0, 'k': 1, 'x_0': 0, 'y_0': 0, 'elipsoide': 'GRS80'},
           'archivos': {'modelo': 'plano_relieve.glb', 'modelo_iphone': usdz, 'plano2d': 'plano.jpg', 'poster': ''},
           'etiquetas': [], 'ficha': ficha, 'elaboro': par.get('elaboro') or {'nombre': '', 'titulos': []}, 'pie': {'logo': logo, 'texto': par.get('pie', '')}}
    sitio.escribir_config(web, cfg)
    z = sitio.comprimir(web, os.path.join(S, 'sitio.zip')); progreso(f'Sitio listo: {web} · {os.path.getsize(z) / 1e6:.1f} MB en sitio.zip')
    if par.get('url'): sitio.qr(par['url'], os.path.join(S, 'QR.png'))
    return dict(sitio=web, zip=z, escala=esc)
