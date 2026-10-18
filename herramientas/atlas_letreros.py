"""Dibuja los letreros de las chinchetas 3D (títulos en azul, municipios en negro) en una sola imagen.
Uso: python3 atlas_letreros.py <carpeta_trabajo>   (requiere etiquetas.json) → tex2/etiquetas_atlas.png + atlas.json"""
import json, sys
from PIL import Image, ImageDraw, ImageFont
M = sys.argv[1]; e = json.load(open(f'{M}/etiquetas.json'))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 84)
colores = {'titulos': (1, 79, 125), 'municipios': (17, 21, 24)}; filas = [(g, it['nombre']) for g in ('titulos', 'municipios') for it in e[g]]
H, W = 128, 1024; atlas = Image.new('RGB', (W, H*len(filas)), (255, 255, 255)); d = ImageDraw.Draw(atlas); info = []
for k, (g, n) in enumerate(filas):
    w = int(d.textlength(n, font=F) + 70); y = k*H
    d.rectangle((0, y, w, y+H-1), fill=colores[g]); d.rectangle((0, y+H-12, w, y+H-1), fill=(146, 146, 146) if g == 'titulos' else (1, 79, 125))
    d.text((35, y+H/2-5), n, font=F, fill=(255, 255, 255), anchor='lm'); info.append({'grupo': g, 'nombre': n, 'fila': k, 'ancho_px': w})
atlas.save(f'{M}/tex2/etiquetas_atlas.png'); json.dump({'H': H, 'W': W, 'n': len(filas), 'items': info}, open(f'{M}/atlas.json', 'w'), ensure_ascii=False)
