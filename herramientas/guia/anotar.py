import json, sys
from PIL import Image, ImageDraw, ImageFont
C = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/cap/'
F = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/fin/'
M = json.load(open(C + 'marcas.json'))
try: M.update(json.load(open(C + 'marcas_extra.json')))
except Exception: pass
fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
ROJO = (220, 38, 38)
def anotar(nombre, recorte=None, marcas=None, salida=None, escala=1.0, pad=50):
    im = Image.open(C + nombre + '.png').convert('RGB')
    ms = marcas if marcas is not None else M.get(nombre, [])
    ms = [[round(v * 1.0425) for v in m[:4]] + list(m[4:]) for m in ms]
    if recorte == 'todo': recorte = [0, 0, im.width, im.height]
    elif recorte is None:
        xs = [m[0] for m in ms] + [m[0] + m[2] for m in ms]; ys = [m[1] for m in ms] + [m[1] + m[3] for m in ms]
        recorte = [max(0, min(xs) - pad), max(0, min(ys) - pad), min(im.width, max(xs) + pad), min(im.height, max(ys) + pad)]
    else: recorte = [recorte[0], recorte[1], recorte[0] + recorte[2], recorte[1] + recorte[3]]
    d = ImageDraw.Draw(im)
    for m in ms:
        x, y, w, h = m[:4]; et = m[4] if len(m) > 4 else ''
        d.rounded_rectangle([x - 4, y - 4, x + w + 4, y + h + 4], radius=6, outline=ROJO, width=4)
        if et:
            cx, cy = x - 4, y - 4; r = 15
            cx = max(recorte[0] + r + 2, cx); cy = max(recorte[1] + r + 2, cy)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ROJO, outline='white', width=2)
            d.text((cx, cy), et, fill='white', font=fnt, anchor='mm')
    im = im.crop(recorte)
    if escala != 1.0: im = im.resize((int(im.width * escala), int(im.height * escala)), Image.LANCZOS)
    im.save(F + (salida or nombre) + '.png', optimize=True)
    return im.size
if __name__ == '__main__':
    exec(open(sys.argv[1]).read())
