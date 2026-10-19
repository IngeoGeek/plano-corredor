"""Reduce las texturas del OBJ (por defecto a 1/8) rellenando el fondo negro del atlas, para que no salgan
triángulos oscuros en los bordes de cada isla. Uso: python3 texturas.py CARPETA_ORIGEN CARPETA_DESTINO [factor]"""
import sys, glob, os, numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
src, dst = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(src + '/**/*.jpg', recursive=True)):
    im = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32); h, w = im.shape[:2]
    kk = k if min(h, w) // k >= 128 else max(1, min(h, w) // 128)
    H, Wd = h // kk, w // kk; im = im[:H * kk, :Wd * kk]
    m = (im.max(axis=2) > 4).astype(np.float32)
    s = (im * m[..., None]).reshape(H, kk, Wd, kk, 3).sum(axis=(1, 3)); c = m.reshape(H, kk, Wd, kk).sum(axis=(1, 3))
    out = np.where(c[..., None] > 0, s / np.maximum(c, 1)[..., None], 0); vac = c == 0
    if vac.any() and (~vac).any():
        idx = ndimage.distance_transform_edt(vac, return_distances=False, return_indices=True); out = out[idx[0], idx[1]]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst + '/' + os.path.basename(f), quality=90)
print('texturas', len(glob.glob(dst + '/*.jpg')))
