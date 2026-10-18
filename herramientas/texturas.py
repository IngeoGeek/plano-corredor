"""Recorta el PDF rasterizado en mosaicos para la maqueta y genera la imagen de la hoja.
Uso: python3 texturas.py <carpeta_trabajo>   (requiere tex/page255.png y layout.json)"""
import sys, json, numpy as np
from PIL import Image, ImageEnhance
Image.MAX_IMAGE_PIXELS = None
W = sys.argv[1]; lay = json.load(open(f'{W}/layout.json'))
im = Image.open(f'{W}/tex/page255.png').convert('RGB'); k = im.size[0] / lay['page'][0]   # px por mm
def crop(x, y, w, h): return im.crop((round(x*k), round(y*k), round((x+w)*k), round((y+h)*k)))
def ajustar(t, c, b, s): return ImageEnhance.Color(ImageEnhance.Brightness(ImageEnhance.Contrast(t).enhance(c)).enhance(b)).enhance(s)
import os; os.makedirs(f'{W}/tex2', exist_ok=True)
MX, MY, MW, MH = lay['map']; mapa = crop(MX, MY, MW, MH).resize((6144, round(6144*MH/MW)), Image.LANCZOS); w, h = mapa.size
for i in range(2):
    for j in range(2):
        ajustar(mapa.crop((i*w//2, j*h//2, (i+1)*w//2, (j+1)*h//2)), 1.15, 0.90, 1.12).save(f'{W}/tex2/mapa_{j}{i}.jpg', quality=86)
RX, RY, RW, RH = lay['rot']; rot = crop(RX, RY, RW, RH); rw, rh = rot.size
for j in range(2): ajustar(rot.crop((0, j*rh//2, rw, (j+1)*rh//2)), 1.08, 0.94, 1.05).save(f'{W}/tex2/rotulo_{j}.jpg', quality=88)
ajustar(im.resize((3072, round(3072*im.size[1]/im.size[0])), Image.LANCZOS), 1.08, 0.93, 1.05).save(f'{W}/tex2/hoja.jpg', quality=85)
g = np.linspace(0, 1, 256)[:, None]; col = (np.array([92, 66, 44])*g + np.array([176, 140, 96])*(1-g)).astype('uint8')
Image.fromarray(np.repeat(col[:, None, :], 8, 1)).save(f'{W}/tex2/pared.png'); print('texturas listas')
