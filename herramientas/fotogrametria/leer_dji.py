"""Lee un proyecto de DJI Terra y deja proyecto.json con lo que necesitan los demás pasos.
Uso: python3 leer_dji.py CARPETA_PROYECTO_DJI W [escala]   (sin escala: la mayor que deje la maqueta en <= 0,95 m de lado)
Necesita: models/pc/0/terra_obj/metadata.xml y map/report/map_report.json (vienen con el proyecto)."""
import sys, json, re, subprocess, glob, os
P, W = sys.argv[1], sys.argv[2]
os.makedirs(W, exist_ok=True)
meta = open(glob.glob(P + '/models/pc/*/terra_obj/metadata.xml')[0]).read()
epsg = re.search(r'<SRS>(EPSG:\d+)</SRS>', meta).group(1)
oE, oN, oZ = map(float, re.search(r'<SRSOrigin>([^<]+)</SRSOrigin>', meta).group(1).split(','))
rep = json.load(open(P + '/map/report/map_report.json'))
rgb = [d['tfw'] for d in rep['datasets_tfw'] if d['type'] == 'RGB'][0]
E0 = oE + rgb['corner_tl_x']; N1 = oN + rgb['corner_tl_y']
E1 = E0 + rgb['width'] * rgb['scale_x']; N0 = N1 + rgb['height'] * rgb['scale_y']
proj = subprocess.run(['gdalsrsinfo', '-o', 'proj4', epsg], capture_output=True, text=True).stdout
par = dict(re.findall(r'\+(\w+)=([^\s]+)', proj))
if par.get('proj') == 'utm':
    z = int(par['zone']); par = dict(lat_0=0, lon_0=6 * z - 183, k=0.9996, x_0=500000, y_0=10000000 if '+south' in proj else 0, ellps=par.get('ellps', 'WGS84'))
elif par.get('proj') != 'tmerc':
    sys.exit(f'{epsg} no es Transversa de Mercator ({par.get("proj")}): reproyectar el modelo a UTM antes de seguir')
rp = glob.glob(P + '/AT/report/report.md') + glob.glob(P + '/map/report/report.md') + glob.glob(P + '/models/pc/*/report/report.md')
at = open(rp[0]).read() if rp else ''
lado = max(E1 - E0, N1 - N0)
esc = float(sys.argv[3]) if len(sys.argv) > 3 else next(s for s in (100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000) if lado / s <= 0.95)
fotos = re.search(r'# Input Images\s*\|\s*(\d+)', at); fix = re.search(r'\|\s*FIX\s*\|\s*(\d+)', at)
out = dict(epsg=epsg, escala=esc, ancho_mm=round((E1 - E0) / esc * 1000, 1), alto_mm=round((N1 - N0) / esc * 1000, 1), oE=oE, oN=oN, oZ=oZ, E0=E0, E1=E1, N0=N0, N1=N1, gsd=rep.get('TDOM GSD'),
           area_ha=round(rep.get('covered area', 0) * 100, 1), fotos=int(fotos.group(1)) if fotos else None, fix=int(fix.group(1)) if fix else None,
           proyeccion=dict(lat_0=float(par.get('lat_0', 0)), lon_0=float(par['lon_0']), k=float(par.get('k', par.get('k_0', 1))),
                           x_0=float(par.get('x_0', 0)), y_0=float(par.get('y_0', 0)), elipsoide={'GRS80': 'GRS80', 'WGS84': 'WGS84', 'intl': 'INTERNACIONAL'}.get(par.get('ellps', 'GRS80'), 'GRS80')),
           obj=sorted(glob.glob(P + '/models/pc/*/terra_obj/*/*.obj')), vista_previa=P + '/map/report/dom_screennail.png')
json.dump(out, open(W + '/proyecto.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != 'obj'}, indent=1, ensure_ascii=False), '\nbloques:', len(out['obj']))
