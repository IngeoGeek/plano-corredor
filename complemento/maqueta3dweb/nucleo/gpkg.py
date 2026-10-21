# -*- coding: utf-8 -*-
"""Modo GeoPackage: proyecto de QGIS guardado dentro del GeoPackage (diseño + DEM) → página web con maqueta 3D."""
import os, json, math
import numpy as np
from qgis.core import (QgsProject, QgsApplication, QgsLayoutItemMap, QgsLayoutExporter, QgsMapRendererCustomPainterJob,
                       QgsRasterLayer, QgsVectorLayer, QgsCoordinateTransform, QgsGeometry, QgsUnitTypes, QgsLayoutSize, QgsWkbTypes)
from qgis.PyQt.QtCore import QSize, QSizeF
from qgis.PyQt.QtGui import QImage, QPainter, QColor
from . import malla, sitio


def _usa_gpkg(proyecto, gpkg):
    """¿El archivo .qgz/.qgs carga capas de ese GeoPackage?"""
    import zipfile
    try:
        if proyecto.lower().endswith('.qgz'):
            with zipfile.ZipFile(proyecto) as z:
                texto = b''.join(z.read(n) for n in z.namelist() if n.lower().endswith('.qgs')).decode('utf-8', 'ignore')
        else:
            texto = open(proyecto, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False
    return os.path.basename(gpkg).lower() in texto.lower()


def proyectos_en(ruta):
    """Proyectos disponibles: los guardados dentro del GeoPackage y, además, los .qgz/.qgs de la misma carpeta
    que usan ese GeoPackage (por ejemplo, el editable que deja el complemento «Póster de relieve»).
    También se puede elegir directamente un .qgz o .qgs."""
    if ruta.lower().endswith(('.qgz', '.qgs')):
        return [os.path.basename(ruta)]
    st = QgsApplication.projectStorageRegistry().projectStorageFromType('geopackage')
    dentro = list(st.listProjects(ruta)) if st else []
    carpeta = os.path.dirname(ruta); base = os.path.splitext(os.path.basename(ruta))[0].lower()
    junto = [f for f in sorted(os.listdir(carpeta)) if f.lower().endswith(('.qgz', '.qgs'))]
    junto = sorted([f for f in junto if os.path.splitext(f)[0].lower() == base or _usa_gpkg(os.path.join(carpeta, f), ruta)],
                   key=lambda f: os.path.splitext(f)[0].lower() != base)
    return dentro + junto


def rasters_en_gpkg(ruta):
    """Rásteres de una banda guardados dentro del GeoPackage: [(nombre, uri GDAL, tipo de dato)]."""
    if not ruta.lower().endswith('.gpkg'): return []
    from osgeo import gdal
    out = []
    try:
        ds = gdal.Open(ruta)
        if ds is None: return []
        subs = ds.GetSubDatasets()
        cand = [(u, u.rsplit(':', 1)[-1]) for u, _ in subs] if subs else ([(ruta, os.path.splitext(os.path.basename(ruta))[0])] if ds.RasterCount else [])
        for uri, nombre in cand:
            r = ds if uri == ruta else gdal.Open(uri)
            if r is not None and r.RasterCount == 1:
                out.append((nombre, uri, gdal.GetDataTypeName(r.GetRasterBand(1).DataType)))
    except Exception:
        pass
    return out


def abrir(ruta, nombre):
    p = QgsProject()
    if nombre.lower().endswith(('.qgz', '.qgs')):
        archivo = ruta if ruta.lower().endswith(('.qgz', '.qgs')) else os.path.join(os.path.dirname(ruta), nombre)
        if not p.read(archivo):
            raise RuntimeError(f'No se pudo abrir el proyecto «{nombre}».')
        return p
    if not p.read(f'geopackage:{ruta}?projectName={nombre}'):
        raise RuntimeError(f'No se pudo abrir el proyecto «{nombre}» del GeoPackage.')
    return p


def disenos(p):
    return [l.name() for l in p.layoutManager().printLayouts()]


def mapas(p, diseno):
    lay = p.layoutManager().layoutByName(diseno)
    return [i.displayName() for i in lay.items() if isinstance(i, QgsLayoutItemMap)]


def capas(p, tipo):
    return [l for l in p.mapLayers().values() if (tipo == 'raster' and isinstance(l, QgsRasterLayer)) or (tipo == 'vector' and isinstance(l, QgsVectorLayer))]


def _qimage_pil(img):
    from PIL import Image
    img = img.convertToFormat(QImage.Format_RGBA8888)
    ptr = img.constBits(); ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)[:, :img.width()]
    return Image.fromarray(a.copy(), 'RGBA').convert('RGB')


def geometria_diseno(lay, mapa):
    pag = lay.pageCollection().page(0)
    ps = lay.convertToLayoutUnits(pag.pageSize())
    pos = mapa.pagePos(); tam = mapa.rect()
    return (ps.width(), ps.height()), (pos.x(), pos.y(), tam.width(), tam.height())


def _redondear_afuera(zmin, zmax):
    paso = 10 ** max(0, int(math.log10(max(1.0, zmax - zmin))) - 1)
    return math.floor(zmin / paso) * paso, math.ceil(zmax / paso) * paso


def dem_en_marco(capa_dem, ext, crs_mapa, max_celdas=1400):
    """Remuestrea el DEM a la extensión exacta del marco (fila 0 al norte). Devuelve (Z, resolución)."""
    from osgeo import gdal
    E0, E1, N0, N1 = ext
    fuente = capa_dem.source().split('|')[0]
    res = max((E1 - E0) / max_celdas, capa_dem.rasterUnitsPerPixelX() if capa_dem.crs() == crs_mapa else 0)
    nx = max(2, int(round((E1 - E0) / res)) + 1); ny = max(2, int(round((N1 - N0) / res)) + 1)
    ds = gdal.Warp('', fuente, format='MEM', dstSRS=crs_mapa.toWkt(), outputBounds=(E0, N0, E1, N1), width=nx, height=ny,
                   resampleAlg='bilinear', outputType=gdal.GDT_Float32, dstNodata=-99999)
    b = ds.GetRasterBand(1); gdal.FillNodata(b, None, 100, 0)
    Z = b.ReadAsArray().astype(np.float64); Z[Z <= -99998] = np.nan
    if np.isnan(Z).any(): Z = np.where(np.isnan(Z), np.nanmin(Z), Z)
    return Z, (E1 - E0) / (nx - 1)


def procesar(par, progreso=print):
    """par: gpkg, proyecto, diseno, mapa, dem (capa del proyecto o ruta), ve, etiquetas_pagina [(capa, campo, grupo, color)],
    chinchetas [(capa, campo, grupo_int)], titulo, subtitulo, ficha, elaboro, pie, logo, color, salida, url (opcional)"""
    p = abrir(par['gpkg'], par['proyecto']); lay = p.layoutManager().layoutByName(par['diseno'])
    mapa = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap) and i.displayName() == par['mapa']][0]
    hoja, marco = geometria_diseno(lay, mapa); ext_r = mapa.extent(); crs = mapa.crs()
    ext = (ext_r.xMinimum(), ext_r.xMaximum(), ext_r.yMinimum(), ext_r.yMaximum())
    esc = (ext[1] - ext[0]) / (marco[2] / 1000.0)
    progreso(f'Diseño «{par["diseno"]}»: hoja {hoja[0]:.0f} × {hoja[1]:.0f} mm · escala 1:{esc:,.0f}'.replace(',', ' '))
    S = par['salida']; web = os.path.join(S, 'sitio'); os.makedirs(S, exist_ok=True); sitio.copiar_kit(web)

    # --- DEM ---
    dem = par['dem'] if isinstance(par['dem'], QgsRasterLayer) else QgsRasterLayer(par['dem'], 'dem')
    Z, res = dem_en_marco(dem, ext, crs)
    zmin, zmax = _redondear_afuera(float(Z.min()), float(Z.max())); ve = float(par.get('ve', 2.5))
    progreso(f'DEM: {Z.shape[1]} × {Z.shape[0]} celdas de {res:.0f} m · cotas {Z.min():.1f} a {Z.max():.1f} m → {zmin:g} a {zmax:g}')
    from PIL import Image
    rel = np.clip((Z - zmin) / (zmax - zmin) * 65535, 0, 65535).astype(np.uint16)
    Image.fromarray(rel).save(os.path.join(web, 'relieve.png'))

    # --- Texturas: hoja completa y mapa sin cuadrícula ni marco (2 × 2 mosaicos) ---
    ex = QgsLayoutExporter(lay)
    def pagina(ancho):
        return _qimage_pil(ex.renderPageToImage(0, QSize(ancho, int(ancho * hoja[1] / hoja[0]))))
    tex_hoja = pagina(4096); progreso('Textura de la hoja lista')
    W = 6144; H = int(round(W * marco[3] / marco[2])); dpi = W / (marco[2] / 25.4)
    ms = mapa.mapSettings(ext_r, QSizeF(W, H), dpi, True); ms.setOutputSize(QSize(W, H)); ms.setOutputDpi(dpi)
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied); img.fill(QColor(255, 255, 255))
    pt = QPainter(img); job = QgsMapRendererCustomPainterJob(ms, pt); job.start(); job.waitForFinished(); pt.end()
    tm = _qimage_pil(img); w2, h2 = W // 2, H // 2
    tex_mapa = [[tm.crop((0, 0, w2, h2)), tm.crop((w2, 0, W, h2))], [tm.crop((0, h2, w2, H)), tm.crop((w2, h2, W, H))]]
    progreso('Textura del mapa lista (6144 px, sin cuadrícula ni marco)')

    # --- Etiquetas y chinchetas ---
    def puntos(capa, campo):
        tr = QgsCoordinateTransform(capa.crs(), crs, p)
        for f in capa.getFeatures():
            g = QgsGeometry(f.geometry())
            if g.isEmpty(): continue
            if g.type() == QgsWkbTypes.LineGeometry:
                partes = g.asGeometryCollection(); g = max(partes, key=lambda x: x.length()); g = g.interpolate(g.length() / 2)
            elif g.type() == QgsWkbTypes.PolygonGeometry:
                g = g.pointOnSurface()
            g.transform(tr); pt_ = g.asPoint()
            if ext[0] <= pt_.x() <= ext[1] and ext[2] <= pt_.y() <= ext[3]:
                yield str(f[campo]), pt_.x(), pt_.y()
    et_cfg = []; os.makedirs(os.path.join(web, 'etiquetas'), exist_ok=True)
    for capa, campo, grupo, color in par.get('etiquetas_pagina', []):
        nombre_csv = f'etiquetas/{len(et_cfg) + 1}.csv'
        with open(os.path.join(web, nombre_csv), 'w', encoding='utf-8') as f:
            f.write(f'X,Y,{campo}\n')
            for n, x, y in puntos(capa, campo): f.write(f'{x:.3f},{y:.3f},"{n.replace(chr(34), chr(39))}"\n')
        et_cfg.append({'archivo': nombre_csv, 'campo': campo, 'grupo': grupo, 'color': color})
    pines, nombres = [], []
    def escena_xy(E, N):
        x = (marco[0] + (E - ext[0]) / (ext[1] - ext[0]) * marco[2] - hoja[0] / 2) / 1000.0
        y = (hoja[1] / 2 - (marco[1] + (ext[3] - N) / (ext[3] - ext[2]) * marco[3])) / 1000.0
        i = min(Z.shape[1] - 1, max(0, int(round((E - ext[0]) / (ext[1] - ext[0]) * (Z.shape[1] - 1)))))
        j = min(Z.shape[0] - 1, max(0, int(round((ext[3] - N) / (ext[3] - ext[2]) * (Z.shape[0] - 1)))))
        return x, y, malla.BASE_REL + (Z[j, i] - zmin) * ve / esc
    for capa, campo, g in par.get('chinchetas', []):
        for n, E, N in puntos(capa, campo):
            x, y, z = escena_xy(E, N); pines.append(dict(nombre=n, grupo=g, x=x, y=y, z=z, fila=len(nombres))); nombres.append((g, n))
    atlas = malla.atlas_letreros(nombres) if pines else None

    # --- Maqueta ---
    malla.construir_plano(Z, ext, hoja, marco, esc, ve, zmin, tex_mapa, tex_hoja, os.path.join(web, 'plano_relieve.glb'),
                          caras=int(par.get('caras', 340000)), pines=pines, atlas=atlas, progreso=progreso)
    usdz = ''
    try:
        from . import usdz as U
        U.glb_a_usdz(os.path.join(web, 'plano_relieve.glb'), os.path.join(web, 'plano_relieve.usdz')); usdz = 'plano_relieve.usdz'
        progreso('Modelo para iPhone (.usdz) listo')
    except Exception as e:
        progreso(f'Sin .usdz para iPhone ({e.__class__.__name__}); la página funciona igual en Android y computador')

    # --- Plano 2D ---
    n = sitio.dzi(pagina(9000), os.path.join(web, 'plano2d')); progreso(f'Plano 2D: {n} teselas')

    # --- Página ---
    proy = sitio.proyeccion_tm(crs)
    if proy is None: progreso('Aviso: el sistema del mapa no es Transversa de Mercator; el GPS de la página no funcionará')
    logo = ''
    if par.get('logo'):
        import shutil; logo = 'logo' + os.path.splitext(par['logo'])[1].lower(); shutil.copy(par['logo'], os.path.join(web, logo))
    color = par.get('color') or (sitio.color_del_logo(par['logo']) if par.get('logo') else '#014f7d')
    ficha = par.get('ficha') or [['Escala horizontal', f'1:{esc:,.0f}'.replace(',', ' ')], ['Exageración vertical', f'{ve:g} ×'.replace('.', ',')],
                                 ['Sistema', crs.authid() + ' · ' + crs.description()], ['Plano', f'{hoja[0] / 10:g} × {hoja[1] / 10:g} cm'.replace('.', ',')]]
    cfg = {'version': 1, 'titulo': par.get('titulo') or par['diseno'], 'subtitulo': par.get('subtitulo', ''), 'color': color,
           'hoja': {'ancho_mm': round(hoja[0], 3), 'alto_mm': round(hoja[1], 3)},
           'marco': {'x_mm': round(marco[0], 3), 'y_mm': round(marco[1], 3), 'ancho_mm': round(marco[2], 3), 'alto_mm': round(marco[3], 3),
                     'E_min': ext[0], 'E_max': ext[1], 'N_min': ext[2], 'N_max': ext[3]},
           'relieve': {'imagen': 'relieve.png', 'z_min': zmin, 'z_max': zmax, 'exageracion': ve},
           'proyeccion': proy or {'lat_0': 0, 'lon_0': 0, 'k': 1, 'x_0': 0, 'y_0': 0, 'elipsoide': 'GRS80'},
           'archivos': {'modelo': 'plano_relieve.glb', 'modelo_iphone': usdz, 'plano2d': 'plano2d/plano.dzi', 'poster': ''},
           'etiquetas': et_cfg, 'ficha': ficha,
           'elaboro': par.get('elaboro') or {'nombre': '', 'titulos': []},
           'pie': {'logo': logo, 'texto': par.get('pie', '')}}
    sitio.escribir_config(web, cfg)
    z = sitio.comprimir(web, os.path.join(S, 'sitio.zip')); progreso(f'Sitio listo: {web}  ·  {os.path.getsize(z) / 1e6:.1f} MB en sitio.zip')
    if par.get('url'):
        sitio.qr(par['url'], os.path.join(S, 'QR.png')); progreso('QR generado')
    return dict(sitio=web, zip=z, escala=esc, zmin=zmin, zmax=zmax)
