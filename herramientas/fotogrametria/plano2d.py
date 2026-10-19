"""Plano 2D desde la vista previa de la ortofoto que deja DJI Terra (o desde una ortofoto reducida).
Uso: python3 plano2d.py W [ortofoto_reducida.tif]   → W/sitio/plano.jpg con la misma extensión que la maqueta"""
import sys, json, subprocess
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
W = sys.argv[1]; P = json.load(open(W + '/proyecto.json'))
if len(sys.argv) > 2:   # ortofoto propia: se recorta a la extensión exacta y se lleva a <= 16 Mpx
    subprocess.run(['gdal_translate', '-q', '-of', 'JPEG', '-co', 'QUALITY=88', '-b', '1', '-b', '2', '-b', '3', '-projwin', str(P['E0']), str(P['N1']), str(P['E1']), str(P['N0']),
                    '-outsize', '4000', '0', '-r', 'average', sys.argv[2], W + '/sitio/plano.jpg'], check=True)
else:
    im = Image.open(P['vista_previa']).convert('RGBA'); im = im.crop(im.getchannel('A').getbbox())
    bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel('A')); bg.save(W + '/sitio/plano.jpg', quality=88)
print(Image.open(W + '/sitio/plano.jpg').size)
