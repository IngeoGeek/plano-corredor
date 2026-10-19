"""Lee la georreferencia de DJI Terra y escribe params.json.
Uso: python parametros.py CARPETA_PROYECTO W [escala]   (escala por defecto: la que deja la maqueta en ~0,9 m de lado)
Toma el origen y el EPSG de models/pc/0/terra_obj/metadata.xml y la extensión de la ortofoto de map/report/map_report.json."""
import json, re, sys, math
P, W = sys.argv[1], sys.argv[2]
x = open(P + '/models/pc/0/terra_obj/metadata.xml', encoding='utf-8').read()
epsg = re.search(r'<SRS>(.*?)</SRS>', x).group(1)
oE, oN, oZ = map(float, re.search(r'<SRSOrigin>(.*?)</SRSOrigin>', x).group(1).split(','))
r = json.load(open(P + '/map/report/map_report.json', encoding='utf-8'))
t = [d['tfw'] for d in r['datasets_tfw'] if d['type'] == 'RGB'][0]
E0 = oE + t['corner_tl_x']; N1 = oN + t['corner_tl_y']; E1 = E0 + t['width'] * t['scale_x']; N0 = N1 + t['height'] * t['scale_y']
lado = max(E1 - E0, N1 - N0)
esc = float(sys.argv[3]) if len(sys.argv) > 3 else [s for s in (100, 200, 250, 500, 1000, 2000, 2500, 5000) if lado / s <= 0.95][0]
p = dict(epsg=epsg, oE=oE, oN=oN, oZ=oZ, E0=E0, E1=E1, N0=N0, N1=N1, ESC=esc, gsd=r.get('TDOM GSD'),
         area_ha=round(r.get('covered area', 0) * 100, 1), ancho_mm=(E1 - E0) / esc * 1000, alto_mm=(N1 - N0) / esc * 1000)
json.dump(p, open(W + '/params.json', 'w'), indent=1); print(json.dumps(p, indent=1))
