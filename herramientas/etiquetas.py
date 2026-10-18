import json, sys, numpy as np
from shapely.geometry import shape, box
from shapely.ops import linemerge, unary_union
M = sys.argv[1]
meta = json.load(open(f'{M}/dem30.json')); Z = np.load(f'{M}/dem30f.npy').astype(float)
E0, E1, N0, N1, res = meta['E0'], meta['E1'], meta['N0'], meta['N1'], meta['res']
ESC, VE, ZOC, ZMIN = 65000.0, 2.5, 0.004, 100.0
lay = json.load(open(f'{M}/layout.json')); MX, MY, MW, MH = lay['map']; PW, PH = lay['page']
x0 = (MX - PW/2)/1000; ytop = (PH/2 - MY)/1000
marco = box(E0, N0, E1, N1)
def altura(E, N):
    fi = (E - E0)/res; fj = (N1 - N)/res
    i0 = int(min(max(np.floor(fi), 0), Z.shape[1]-2)); j0 = int(min(max(np.floor(fj), 0), Z.shape[0]-2)); di, dj = fi-i0, fj-j0
    z = (Z[j0,i0]*(1-di)+Z[j0,i0+1]*di)*(1-dj) + (Z[j0+1,i0]*(1-di)+Z[j0+1,i0+1]*di)*dj
    return ZOC + (z - ZMIN)*VE/ESC
def modelo(E, N):   # coordenadas glTF (m): x este, y arriba, z sur
    X = x0 + (E - E0)/ESC; Yb = ytop - (N1 - N)/ESC
    return [round(X, 5), round(altura(E, N), 5), round(-Yb, 5)]
def gj(n): return json.load(open(f'{M}/lbl/{n}.geojson'))['features']
out = {'titulos': [], 'municipios': [], 'fallas': [], 'pliegues': [], 'operadores': [], 'bocaminas': []}
for f in gj('titulos'):
    g = shape(f['geometry']).intersection(marco)
    if g.is_empty: continue
    p = g.representative_point(); out['titulos'].append({'nombre': f['properties']['CODIGO_EXP'], 'E': p.x, 'N': p.y, 'pos': modelo(p.x, p.y)})
for f in gj('municipios'):
    E, N = f['properties']['rot_x'], f['properties']['rot_y']
    out['municipios'].append({'nombre': f['properties']['nombre_rotulo'], 'E': E, 'N': N, 'pos': modelo(E, N)})
for capa in ('fallas', 'pliegues'):
    grupos = {}
    for f in gj(capa):
        n = f['properties']['nombre']
        if n: grupos.setdefault(n, []).append(shape(f['geometry']))
    for n, gs in grupos.items():
        u = unary_union(gs)
        if u.geom_type == 'MultiLineString': u = linemerge(u)
        partes = list(u.geoms) if hasattr(u, 'geoms') else [u]
        l = max(partes, key=lambda g: g.length); p = l.interpolate(0.5, normalized=True)
        out[capa].append({'nombre': n, 'E': p.x, 'N': p.y, 'pos': modelo(p.x, p.y)})
for capa, campo in (('operadores', 'etiqueta'), ('bocaminas', 'etiqueta')):
    for f in gj(capa):
        n = f['properties'].get(campo)
        if not n: continue   # «Antonela 3» comparte rótulo con «Antonela 2 y 3», igual que en el plano
        c = f['geometry']['coordinates']; out[capa].append({'nombre': n, 'E': c[0], 'N': c[1], 'pos': modelo(c[0], c[1])})
json.dump(out, open(f'{M}/etiquetas.json', 'w'), ensure_ascii=False, indent=1)
for k, v in out.items(): print(k, len(v), [x['nombre'] for x in v])
