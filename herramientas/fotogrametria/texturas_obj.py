"""Reduce las texturas del OBJ a 1/k sin que el fondo negro del atlas manche los bordes (evita triángulos negros).
Uso: python texturas_obj.py CARPETA_terra_obj SALIDA [k=8]"""
import sys, glob, os, numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
src, dst = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(src + '/*/*.jpg')):
    im = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32); h, w = im.shape[:2]
    H, Wd = h // k, w // k; im = im[:H * k, :Wd * k]
    m = (im.max(axis=2) > 4).astype(np.float32)
    s = (im * m[..., None]).reshape(H, k, Wd, k, 3).sum(axis=(1, 3)); c = m.reshape(H, k, Wd, k).sum(axis=(1, 3))
    out = np.where(c[..., None] > 0, s / np.maximum(c, 1)[..., None], 0)
    vac = c == 0
    if vac.any() and (~vac).any():
        idx = ndimage.distance_transform_edt(vac, return_distances=False, return_indices=True); out = out[idx[0], idx[1]]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst + '/' + os.path.basename(f), quality=90)
print('texturas', len(os.listdir(dst)))
