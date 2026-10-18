"""Corta la imagen del plano en teselas Deep Zoom (DZI) para el visor 2D (OpenSeadragon).
Uso: python3 dzi.py <imagen.png> <carpeta_salida>   → plano.dzi + plano_files/ + lista_plano2d.json"""
import sys, os, math, json
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
src, out = sys.argv[1], sys.argv[2]; T, O = 254, 1
im = Image.open(src).convert('RGB'); W, H = im.size; maxL = math.ceil(math.log2(max(W, H))); lista = []
lvl = im
for L in range(maxL, -1, -1):
    w, h = lvl.size; d = f'{out}/plano_files/{L}'; os.makedirs(d, exist_ok=True)
    for c in range(math.ceil(w/T)):
        for r in range(math.ceil(h/T)):
            lvl.crop((max(c*T-O, 0), max(r*T-O, 0), min((c+1)*T+O, w), min((r+1)*T+O, h))).save(f'{d}/{c}_{r}.jpg', quality=82)
            lista.append(f'plano2d/plano_files/{L}/{c}_{r}.jpg')
    lvl = lvl.resize((max(1, math.ceil(w/2)), max(1, math.ceil(h/2))), Image.LANCZOS)
open(f'{out}/plano.dzi', 'w').write(f'<?xml version="1.0" encoding="UTF-8"?><Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{T}" Overlap="{O}" Format="jpg"><Size Width="{W}" Height="{H}"/></Image>')
json.dump(lista + ['plano2d/plano.dzi'], open(f'{os.path.dirname(out.rstrip("/")) or "."}/lista_plano2d.json', 'w'))
print('teselas', len(lista), 'tamaño', W, H)
