# -*- coding: utf-8 -*-
"""Arma la página (kit con config.js), el plano 2D en teselas, el .zip y los QR."""
import os, json, math, shutil, zipfile

KIT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'kit')


def dzi(imagen, carpeta, T=254, O=1):
    """Teselas Deep Zoom del plano 2D (lo que lee OpenSeadragon en la página)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = imagen.convert('RGB'); W, H = im.size; maxL = math.ceil(math.log2(max(W, H))); lvl = im; n = 0
    for L in range(maxL, -1, -1):
        w, h = lvl.size; d = os.path.join(carpeta, 'plano_files', str(L)); os.makedirs(d, exist_ok=True)
        for c in range(math.ceil(w / T)):
            for r in range(math.ceil(h / T)):
                lvl.crop((max(c * T - O, 0), max(r * T - O, 0), min((c + 1) * T + O, w), min((r + 1) * T + O, h))).save(os.path.join(d, f'{c}_{r}.jpg'), quality=82); n += 1
        lvl = lvl.resize((max(1, math.ceil(w / 2)), max(1, math.ceil(h / 2))), Image.LANCZOS)
    with open(os.path.join(carpeta, 'plano.dzi'), 'w') as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{T}" Overlap="{O}" Format="jpg"><Size Width="{W}" Height="{H}"/></Image>')
    return n


def copiar_kit(destino):
    if os.path.exists(destino): shutil.rmtree(destino)
    shutil.copytree(KIT, destino)
    for basura in ('config.js', 'LEEME.txt'):
        p = os.path.join(destino, basura)
        if os.path.exists(p): os.remove(p)
    open(os.path.join(destino, '.nojekyll'), 'w').close()


def color_del_logo(ruta, por_defecto='#014f7d'):
    """Color principal: el tono más saturado y frecuente del logo (ignora blancos, negros y grises)."""
    try:
        from PIL import Image
        import colorsys
        im = Image.open(ruta).convert('RGBA').resize((120, 120))
        cuenta = {}
        for r, g, b, a in im.getdata():
            if a < 128: continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s < 0.35 or v < 0.2 or v > 0.97: continue
            k = (r // 16, g // 16, b // 16); cuenta[k] = cuenta.get(k, 0) + 1
        if not cuenta: return por_defecto
        r, g, b = max(cuenta, key=cuenta.get)
        return '#%02x%02x%02x' % (r * 16 + 8, g * 16 + 8, b * 16 + 8)
    except Exception:
        return por_defecto


def escribir_config(destino, cfg):
    with open(os.path.join(destino, 'config.js'), 'w', encoding='utf-8') as f:
        f.write('/* Generado por el complemento Maqueta 3D Web de QGIS. Se puede editar a mano. */\n')
        f.write('self.PLANO = ' + json.dumps(cfg, ensure_ascii=False, indent=1) + ';\n')


def comprimir(carpeta, zip_ruta):
    with zipfile.ZipFile(zip_ruta, 'w', zipfile.ZIP_DEFLATED) as z:
        for raiz, _, archivos in os.walk(carpeta):
            for a in archivos:
                p = os.path.join(raiz, a); z.write(p, os.path.relpath(p, carpeta))
    return zip_ruta


def qr(url, ruta_png):
    import qrcode
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=16, border=4)
    q.add_data(url); q.make(fit=True); q.make_image(fill_color='black', back_color='white').save(ruta_png)
    return ruta_png


def proyeccion_tm(crs):
    """Parámetros de Transversa de Mercator para el GPS de la página, desde un QgsCoordinateReferenceSystem."""
    import re
    p4 = crs.toProj()
    par = dict(re.findall(r'\+(\w+)=([^\s]+)', p4))
    ellps = par.get('ellps', 'GRS80')
    if par.get('proj') == 'utm':
        z = int(par['zone'])
        return dict(lat_0=0, lon_0=6 * z - 183, k=0.9996, x_0=500000, y_0=10000000 if '+south' in p4 else 0, elipsoide='WGS84' if ellps == 'WGS84' else 'GRS80')
    if par.get('proj') != 'tmerc':
        return None
    return dict(lat_0=float(par.get('lat_0', 0)), lon_0=float(par.get('lon_0', 0)), k=float(par.get('k', par.get('k_0', 1))),
                x_0=float(par.get('x_0', 0)), y_0=float(par.get('y_0', 0)), elipsoide={'WGS84': 'WGS84', 'intl': 'INTERNACIONAL'}.get(ellps, 'GRS80'))
