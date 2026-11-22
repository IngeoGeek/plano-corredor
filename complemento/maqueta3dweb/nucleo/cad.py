# -*- coding: utf-8 -*-
"""Lectura de planos de labores en DWG o DXF.

Cada capa del plano es un tipo de labor (nivel, inclinado, cruzada, tambor…) y sus entidades son los ejes que levanta
el topógrafo. Se leen líneas, polilíneas 2D y 3D, arcos y splines (aplanados), textos (cotas y nombres), puntos y
bloques (bocaminas, frentes).

DXF: se lee directo con ezdxf.
DWG: se convierte primero a DXF con la herramienta que haya en el equipo, en este orden:
  1. ODA File Converter (gratuito de la Open Design Alliance; revisar sus condiciones de uso en la empresa),
  2. LibreDWG «dwg2dxf» (GPL-3, se puede descargar sola desde GitHub con permiso del usuario),
  3. el controlador CAD de GDAL que trae QGIS (solo DWG R2000).
Si nada funciona, se pide guardar el plano como DXF desde AutoCAD o Civil 3D (Guardar como → DXF 2018)."""
import glob, math, os, re, shutil, subprocess, tempfile, unicodedata, zipfile

LIBREDWG_URL = 'https://github.com/LibreDWG/libredwg/releases/download/0.13.3/libredwg-0.13.3-win64.zip'
LIBREDWG_SHA256 = 'b5133f8b6bd71b7e682a06ef5f99c93b40d628a791c30a31924a80d258c87173'
CARPETA_HERR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'herramientas')


class FaltaConversor(RuntimeError):
    """No hay cómo convertir el DWG: se puede ofrecer descargar LibreDWG o pedir el DXF."""


def _sin_tildes(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t or '') if unicodedata.category(c) != 'Mn').upper()


# ---------------------------------------------------------------- conversión DWG → DXF
def _oda():
    pats = [r'C:\Program Files\ODA\ODAFileConverter*\ODAFileConverter.exe', r'C:\Program Files (x86)\ODA\ODAFileConverter*\ODAFileConverter.exe',
            '/usr/bin/ODAFileConverter', '/opt/ODAFileConverter*/ODAFileConverter', '/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter']
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits: return hits[-1]
    return shutil.which('ODAFileConverter')


def _libredwg():
    exe = 'dwg2dxf.exe' if os.name == 'nt' else 'dwg2dxf'
    propio = os.path.join(CARPETA_HERR, 'libredwg', exe)
    return propio if os.path.exists(propio) else shutil.which('dwg2dxf')


def descargar_libredwg(registro=print):
    """Descarga LibreDWG 0.13.3 para Windows (≈13 MB, GPL-3) en la carpeta del complemento y verifica su huella SHA-256.
    Solo se llama con permiso del usuario."""
    import hashlib, urllib.request
    os.makedirs(os.path.join(CARPETA_HERR, 'libredwg'), exist_ok=True)
    zp = os.path.join(CARPETA_HERR, 'libredwg.zip')
    registro('Descargando LibreDWG (dwg2dxf) desde GitHub…')
    urllib.request.urlretrieve(LIBREDWG_URL, zp)
    if hashlib.sha256(open(zp, 'rb').read()).hexdigest() != LIBREDWG_SHA256:
        os.remove(zp); raise RuntimeError('El archivo descargado de LibreDWG no coincide con la versión esperada; no se usó.')
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            if '/' not in n and (n.lower() == 'dwg2dxf.exe' or n.lower().endswith('.dll')):
                with z.open(n) as src, open(os.path.join(CARPETA_HERR, 'libredwg', n), 'wb') as dst: shutil.copyfileobj(src, dst)
    os.remove(zp)
    registro('LibreDWG listo.')
    return _libredwg()


def conversores():
    """Qué hay disponible en este equipo para abrir DWG."""
    return {'oda': _oda(), 'libredwg': _libredwg()}


def dwg_a_dxf(ruta, registro=print):
    """Devuelve la ruta de un DXF equivalente (temporal) o None si hay que usar el controlador CAD de GDAL."""
    tmp = tempfile.mkdtemp(prefix='dwg2dxf_')
    flags = 0x08000000 if os.name == 'nt' else 0
    oda = _oda()
    if oda:
        registro('Convirtiendo el DWG con ODA File Converter…')
        dentro = os.path.join(tmp, 'in'); fuera = os.path.join(tmp, 'out'); os.makedirs(dentro); os.makedirs(fuera)
        shutil.copy(ruta, dentro)
        subprocess.run([oda, dentro, fuera, 'ACAD2018', 'DXF', '0', '1', '*.DWG'], capture_output=True, creationflags=flags, timeout=600)
        hechos = glob.glob(os.path.join(fuera, '*.dxf'))
        if hechos: return hechos[0]
        registro('ODA no produjo el DXF; se intenta con LibreDWG.')
    ld = _libredwg()
    if ld:
        registro('Convirtiendo el DWG con LibreDWG (dwg2dxf)…')
        out = os.path.join(tmp, os.path.splitext(os.path.basename(ruta))[0] + '.dxf')
        r = subprocess.run([ld, '-y', '-o', out, ruta], capture_output=True, text=True, creationflags=flags, timeout=600,
                           cwd=os.path.dirname(ld))
        if os.path.exists(out) and os.path.getsize(out) > 0: return out
        registro('LibreDWG no pudo convertir el archivo: ' + (r.stderr or '')[-300:])
    return None


# ---------------------------------------------------------------- lectura
def _rgb_aci(aci):
    from ezdxf import colors
    try: return colors.aci2rgb(int(aci))
    except Exception: return (128, 128, 128)


def _color_capa(doc, nombre):
    try:
        capa = doc.layers.get(nombre)
        if capa.dxf.hasattr('true_color'):
            from ezdxf import colors
            return colors.int2rgb(capa.dxf.true_color)
        aci = abs(capa.color)
        return (70, 70, 70) if aci == 7 else _rgb_aci(aci)      # el 7 es blanco o negro según el fondo: gris oscuro
    except Exception:
        return (128, 128, 128)


def _visible(doc, nombre):
    try:
        c = doc.layers.get(nombre); return c.is_on() and not c.is_frozen()
    except Exception:
        return True


def leer_dxf(ruta, registro=print):
    """Devuelve {'capas': {nombre: {'color', 'visible', 'lineas', 'textos', 'puntos'}}, 'lineas': [...], 'textos': [...], 'puntos': [...]}.
    Cada línea: {'capa', 'xyz': [[x, y, z], …], 'cerrada'}; cada texto: {'capa', 'texto', 'xyz'}; cada punto: {'capa', 'nombre', 'xyz'}."""
    import ezdxf
    from ezdxf import path as epath
    try:
        doc = ezdxf.readfile(ruta)
    except Exception:
        from ezdxf import recover
        doc, auditor = recover.readfile(ruta)
        registro(f'El DXF tenía errores; se recuperó ({len(auditor.errors)} corregidos).')
    msp = doc.modelspace()
    lineas, textos, puntos = [], [], []

    def entidad(e, capa_padre=None):
        t = e.dxftype(); capa = e.dxf.get('layer', '0')
        if capa == '0' and capa_padre: capa = capa_padre   # entidades de bloque en la capa 0 toman la capa del bloque
        if t in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'SPLINE', 'CIRCLE', 'ELLIPSE'):
            if t == 'POLYLINE' and (e.is_poly_face_mesh or e.is_polygon_mesh): return
            try:
                p = epath.make_path(e)
                pts = [(v.x, v.y, v.z) for v in p.flattening(distance=0.05, segments=8)]
            except Exception:
                return
            if len(pts) < 2: return
            lineas.append({'capa': capa, 'xyz': pts, 'cerrada': bool(getattr(e, 'closed', False) or getattr(e, 'is_closed', False))})
        elif t in ('TEXT', 'MTEXT', 'ATTRIB'):
            try:
                txt = e.plain_text() if t == 'MTEXT' else e.dxf.text
                ins = e.dxf.insert
                textos.append({'capa': capa, 'texto': (txt or '').strip(), 'xyz': (ins.x, ins.y, ins.z)})
            except Exception:
                pass
        elif t == 'POINT':
            l = e.dxf.location; puntos.append({'capa': capa, 'nombre': '', 'xyz': (l.x, l.y, l.z)})
        elif t == 'INSERT':
            ins = e.dxf.insert
            puntos.append({'capa': capa, 'nombre': e.dxf.name, 'xyz': (ins.x, ins.y, ins.z)})
            for a in getattr(e, 'attribs', []):
                try: textos.append({'capa': capa, 'texto': a.dxf.text.strip(), 'xyz': (a.dxf.insert.x, a.dxf.insert.y, a.dxf.insert.z)})
                except Exception: pass
            try:   # el contenido del bloque (p. ej. ejes dibujados dentro de un bloque)
                for v in e.virtual_entities():
                    if v.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'SPLINE'): entidad(v, capa)
            except Exception:
                pass

    for e in msp: entidad(e)
    capas = {}
    for col, lista in (('lineas', lineas), ('textos', textos), ('puntos', puntos)):
        for it in lista:
            c = capas.setdefault(it['capa'], {'color': _color_capa(doc, it['capa']), 'visible': _visible(doc, it['capa']),
                                              'lineas': 0, 'textos': 0, 'puntos': 0})
            c[col] += 1
    unidades = {0: 'sin unidad', 1: 'pulgadas', 2: 'pies', 4: 'milímetros', 5: 'centímetros', 6: 'metros'}.get(doc.header.get('$INSUNITS', 0), 'otra')
    return {'capas': capas, 'lineas': lineas, 'textos': textos, 'puntos': puntos, 'unidades': unidades, 'version': doc.dxfversion}


def leer_gdal_cad(ruta, registro=print):
    """Último recurso: controlador CAD de GDAL (solo DWG R2000). No trae colores de capa."""
    from osgeo import ogr
    ds = ogr.Open(ruta)
    if ds is None: raise RuntimeError('GDAL no pudo abrir el DWG (solo lee la versión R2000).')
    lineas, textos, puntos = [], [], []
    for i in range(ds.GetLayerCount()):
        L = ds.GetLayerByIndex(i); nombre = L.GetName()
        for f in L:
            g = f.GetGeometryRef()
            if g is None: continue
            gt = ogr.GT_Flatten(g.GetGeometryType())
            txt = None
            for campo in ('Text', 'text', 'TEXT'):
                try:
                    if f.GetFieldIndex(campo) >= 0: txt = f.GetField(campo); break
                except Exception: pass
            if gt == ogr.wkbLineString:
                pts = [g.GetPoint(k) for k in range(g.GetPointCount())]
                if len(pts) >= 2: lineas.append({'capa': nombre, 'xyz': pts, 'cerrada': False})
            elif gt == ogr.wkbMultiLineString:
                for j in range(g.GetGeometryCount()):
                    s = g.GetGeometryRef(j); pts = [s.GetPoint(k) for k in range(s.GetPointCount())]
                    if len(pts) >= 2: lineas.append({'capa': nombre, 'xyz': pts, 'cerrada': False})
            elif gt == ogr.wkbPoint:
                if txt: textos.append({'capa': nombre, 'texto': str(txt).strip(), 'xyz': g.GetPoint()})
                else: puntos.append({'capa': nombre, 'nombre': '', 'xyz': g.GetPoint()})
    capas = {}
    for col, lista in (('lineas', lineas), ('textos', textos), ('puntos', puntos)):
        for it in lista:
            c = capas.setdefault(it['capa'], {'color': (128, 128, 128), 'visible': True, 'lineas': 0, 'textos': 0, 'puntos': 0}); c[col] += 1
    return {'capas': capas, 'lineas': lineas, 'textos': textos, 'puntos': puntos, 'unidades': 'metros', 'version': 'DWG (GDAL CAD)'}


def leer(ruta, registro=print):
    """Lee un DWG o DXF. Lanza FaltaConversor si es DWG y no hay con qué abrirlo."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext == '.dxf':
        return leer_dxf(ruta, registro)
    if ext != '.dwg':
        raise RuntimeError('El plano debe ser .dwg o .dxf')
    dxf = dwg_a_dxf(ruta, registro)
    if dxf: return leer_dxf(dxf, registro)
    try:
        registro('Sin conversor: se intenta con el controlador CAD de GDAL (solo DWG R2000)…')
        return leer_gdal_cad(ruta, registro)
    except Exception as e:
        raise FaltaConversor(str(e))


# ---------------------------------------------------------------- tipos de labor por nombre de capa
TIPOS = ['nivel', 'inclinado', 'cruzada', 'tambor', 'sobreguia', 'patio', 'frente', 'abandonada', 'proyectada', 'bocamina',
         'limite', 'cota', 'otra', 'ignorar']
NOMBRES = {'nivel': 'Nivel o galería', 'inclinado': 'Inclinado', 'cruzada': 'Cruzada', 'tambor': 'Tambor o chimenea',
           'sobreguia': 'Sobreguía', 'patio': 'Patio', 'frente': 'Frente o avance', 'abandonada': 'Labor abandonada',
           'proyectada': 'Labor proyectada', 'bocamina': 'Bocamina', 'limite': 'Límite (título o área)', 'cota': 'Textos de cota',
           'otra': 'Otra labor', 'ignorar': 'No usar'}
# Sección típica (ancho × alto, m) para dibujar el sólido; se cambia en la tabla del complemento
SECCION = {'nivel': (2.2, 2.0), 'inclinado': (2.0, 1.8), 'cruzada': (2.0, 1.8), 'tambor': (1.5, 1.5), 'sobreguia': (1.8, 1.6),
           'patio': (3.0, 2.2), 'frente': (2.0, 1.8), 'abandonada': (2.0, 1.8), 'proyectada': (2.0, 1.8), 'otra': (2.0, 1.8)}
# Convención de colores de la empresa (editable). La Resolución 40600 de 2015 solo recomienda diferenciar con colores los niveles
# de explotación (numeral 2.6, literal m) y no fija un color por tipo de labor; por eso, por defecto se usan los colores del DWG.
CONVENCION = {'nivel': '#f2c200', 'patio': '#f2c200', 'inclinado': '#8c8c8c', 'cruzada': '#e8772e', 'tambor': '#c62828',
              'sobreguia': '#1e88e5', 'frente': '#8e24aa', 'abandonada': '#bdbdbd', 'proyectada': '#ffffff', 'otra': '#6d4c41'}
_CLAVES = [('sobreguia', ('SOBREGUIA', 'SOBRE GUIA', 'SOBRE-GUIA', 'SOBREG')),
           ('inclinado', ('INCLINAD', 'INCL', 'RAMPA', 'BAJADA', 'PLANO INCL', 'DESCENSO')),
           ('cruzada', ('CRUZADA', 'CRUCERO', 'TRAVIESA', 'TRANSVERSAL', 'XCUT', 'CROSSCUT')),
           ('tambor', ('TAMBOR', 'CHIMENEA', 'CLAVAD', 'POZO', 'APIQUE', 'CONTRAPOZO', 'COMUNICACION')),
           ('patio', ('PATIO',)),
           ('frente', ('FRENTE', 'AVANCE', 'TAJO')),
           ('abandonada', ('ABANDON', 'ANTIGU', 'DERRUMB', 'SELLAD', 'INACTIV', 'VIEJ')),
           ('proyectada', ('PROYECT', 'DISENO', 'PLANEAD', 'FUTUR')),
           ('bocamina', ('BOCAMINA', 'BOCA MINA', 'PORTAL', 'ENTRADA')),
           ('limite', ('LIMITE', 'TITULO', 'POLIGONO', 'AREA', 'LINDERO', 'CONCESION')),
           ('cota', ('COTA', 'ELEV', 'ALTURA', 'Z ')),
           ('nivel', ('NIVEL', 'NIV', 'GALERIA', 'GUIA', 'MANTO', 'TUNEL', 'SOCAVON', 'LABOR', 'EJE'))]


# Capas de dibujo que no son labores (topografía, rótulo, marco, cuadrícula…)
_NO_LABOR = ('CURVA', 'TOPOGRAF', 'VIA', 'CARRETERA', 'CAMINO', 'DRENAJE', 'QUEBRADA', 'RIO', 'CONSTRUC', 'VIVIENDA', 'EDIFIC',
             'CUADRICULA', 'GRILLA', 'GRID', 'MARCO', 'ROTULO', 'CAJETIN', 'MEMBRETE', 'DEFPOINTS', 'VIEWPORT', 'HATCH', 'ACHURA',
             'NORTE', 'ESCALA', 'LEYENDA', 'CONVENCION')


def tipo_sugerido(nombre_capa, info=None):
    n = _sin_tildes(nombre_capa)
    if 'CURVA' in n or (any(k in n for k in _NO_LABOR) and not any(k in n for k in ('INCLINAD', 'CRUZADA', 'TAMBOR', 'GALERIA'))):
        return 'cota' if info and info.get('lineas', 0) == 0 and info.get('textos', 0) > 0 and 'COTA' in n else 'ignorar'
    for tipo, claves in _CLAVES:
        if any(k in n for k in claves): return tipo
    if info and info.get('lineas', 0) == 0 and info.get('textos', 0) > 0: return 'cota'
    if info and info.get('lineas', 0) == 0: return 'ignorar'
    return 'otra'


def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return '#%02x%02x%02x' % tuple(int(v) for v in c[:3])


NUM = re.compile(r'(?<![\d.,])[-+]?\d{1,4}(?:[.,]\d{1,3})?(?![\d])')


def numero_cota(texto):
    """'Cota 1.234,5' / 'Z=1234.50' / '1234.5' → 1234.5 ; None si el texto no es una cota razonable."""
    t = texto.replace('\u00a0', ' ')
    t = re.sub(r'(\d)\.(\d{3})(?!\d)', r'\1\2', t) if re.search(r'\d\.\d{3}[.,]\d', t) else t
    m = NUM.findall(t)
    if not m: return None
    v = float(m[-1].replace(',', '.'))
    clave = re.search(r'COTA|ELEV|\bZ\s*[=:]|\bC\s*[=:]|MSNM', _sin_tildes(texto))
    if not clave and abs(v) < 100: return None          # «Nivel 2», «Frente 3», «25,3 m» no son cotas
    return v if -500 <= v <= 6000 else None
