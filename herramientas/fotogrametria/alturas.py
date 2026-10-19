"""Mapa de alturas relieve.png (16 bits) desde los vértices reales de la malla. Uso: python3 alturas.py W"""
# Mapa de alturas (relieve.png 16 bits) desde los vértices reales de la malla, sobre la extensión de la ortofoto
import numpy as np, json, sys
from PIL import Image
from scipy.interpolate import griddata
W = sys.argv[1]; I = json.load(open(W + '/info.json'))
V = np.load(W + '/vert_real.npy'); E, N, Z = V.T
res = 0.5; nx = int(round((I['E1'] - I['E0']) / res)); ny = int(round((I['N1'] - I['N0']) / res))
ix = np.clip(((E - I['E0']) / res).astype(int), 0, nx - 1); iy = np.clip(((I['N1'] - N) / res).astype(int), 0, ny - 1)
G = np.full((ny, nx), np.nan); np.fmax.at(G, (iy, ix), Z)
yy, xx = np.nonzero(~np.isnan(G)); gy, gx = np.mgrid[0:ny, 0:nx]
F = griddata((yy, xx), G[yy, xx], (gy, gx), method='linear')
M = np.isnan(F); F[M] = griddata((yy, xx), G[yy, xx], (gy[M], gx[M]), method='nearest')
z0, z1 = I['zmin'], I['zmax']
Image.fromarray(np.clip((F - z0) / (z1 - z0) * 65535, 0, 65535).astype(np.uint16)).save(W + '/sitio/relieve.png')
print('relieve', nx, ny, round(z0, 2), round(z1, 2))
