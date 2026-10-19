"""Plano 2D desde la vista previa de la ortofoto de DJI Terra (map/report/dom_screennail.png), recortada al área con datos.
Uso: python plano2d.py CARPETA_PROYECTO W   → W/sitio/plano.jpg. Si hay una ortofoto liviana (5–10 cm), úsala en su lugar."""
import sys
from PIL import Image
P, W = sys.argv[1], sys.argv[2]
im = Image.open(P + '/map/report/dom_screennail.png').convert('RGBA'); im = im.crop(im.getchannel('A').getbbox())
bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel('A')); bg.save(W + '/sitio/plano.jpg', quality=88)
print('plano', bg.size)
