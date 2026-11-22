# Mina sintética de prueba (EPSG:9377, cerca de Landázuri): inclinado y tambores en 3D, niveles en 2D con textos de cota.
import math, sys, numpy as np, ezdxf
from osgeo import gdal, osr
E0, N0 = 4910500.0, 2245600.0
def zs(E, N): return 820 + 0.35 * (E - E0) + 8 * math.sin((N - N0) / 60)   # ladera que sube al oriente
d = ezdxf.new(sys.argv[3] if len(sys.argv) > 3 else 'R2018', setup=True); d.header['$INSUNITS'] = 6
for nombre, color in (('INCLINADO_PPAL', 8), ('NIVEL_1', 2), ('NIVEL_2', 2), ('CRUZADA_MANTO2', 30), ('MANTO2_GUIA', 4),
                      ('TAMBORES', 1), ('CHIMENEA_VENTILACION', 6), ('LABORES_ABANDONADAS', 9), ('PROYECTADO', 7),
                      ('COTAS', 7), ('TEXTOS', 7), ('BOCAMINAS', 5), ('LIMITE_TITULO', 1), ('CURVAS_NIVEL', 94), ('ROTULO', 7)):
    d.layers.add(nombre, color=color)
msp = d.modelspace()
b = d.blocks.new('BOCAMINA'); b.add_circle((0, 0), 2); b.add_line((-2, 0), (2, 0)); b.add_line((0, -2), (0, 2))
inc, ca = math.radians(25), math.cos(math.radians(25))
def por_buzamiento(s): return (E0 + s * ca, N0, 820 - s * math.sin(inc))     # s: distancia inclinada desde la bocamina
# Inclinado principal 3D (bocamina → avance a 165 m)
msp.add_polyline3d([por_buzamiento(s) for s in range(0, 166, 5)], dxfattribs={'layer': 'INCLINADO_PPAL'})
def nivel(s, n_sur, n_norte, capa, pend=0.005):
    e, _, z = por_buzamiento(s)
    pts = [(e + 0.8 * math.sin(k / 25), N0 + k) for k in range(-n_sur, n_norte + 1, 10)]
    msp.add_lwpolyline(pts, dxfattribs={'layer': capa})
    for k in range(-n_sur, n_norte + 1, 20):    # estaciones del topógrafo con su cota
        msp.add_text(f'{z + pend * abs(k):.2f}'.replace('.', ','), height=1.2, dxfattribs={'layer': 'COTAS', 'insert': (e + 0.8 * math.sin(k / 25) + 1.5, N0 + k)})
    return e, z
e1, z1 = nivel(71, 90, 120, 'NIVEL_1')
e2, z2 = nivel(142, 110, 150, 'NIVEL_2')
# Cruzada al manto 2 desde el nivel 2 (N0+40) y guía en el manto 2
ec = e2 + 0.8 * math.sin(40 / 25)
msp.add_lwpolyline([(ec, N0 + 40), (ec + 42, N0 + 40)], dxfattribs={'layer': 'CRUZADA_MANTO2'})
msp.add_text(f'{z2 + 0.2:.2f}', height=1.2, dxfattribs={'layer': 'COTAS', 'insert': (ec + 20, N0 + 41.5)})
msp.add_text(f'{z2 + 0.3:.2f}', height=1.2, dxfattribs={'layer': 'COTAS', 'insert': (ec + 42, N0 + 41.5)})
msp.add_lwpolyline([(ec + 42, N0 + 5), (ec + 42, N0 + 40), (ec + 42, N0 + 78)], dxfattribs={'layer': 'MANTO2_GUIA'})
# Tambores 3D entre niveles (a N0+60 y N0−50) y chimenea de ventilación del nivel 1 a superficie (N0+100)
for k in (60, -50):
    a = (e2 + 0.8 * math.sin(k / 25), N0 + k, z2 + 0.005 * abs(k)); b_ = (e1 + 0.8 * math.sin(k / 25), N0 + k, z1 + 0.005 * abs(k))
    msp.add_polyline3d([tuple(np.add(a, np.subtract(b_, a) * t)) for t in np.linspace(0, 1, 8)], dxfattribs={'layer': 'TAMBORES'})
k = 100; a = (e1 + 0.8 * math.sin(k / 25), N0 + k, z1 + 0.005 * k); eb = E0 + 20; b_ = (eb, N0 + k, zs(eb, N0 + k))
msp.add_polyline3d([tuple(np.add(a, np.subtract(b_, a) * t)) for t in np.linspace(0, 1, 8)], dxfattribs={'layer': 'CHIMENEA_VENTILACION'})
# Labor antigua y extensión proyectada
ea, za = por_buzamiento(35)[0], por_buzamiento(35)[2]
msp.add_lwpolyline([(ea, N0 - 10), (ea, N0 - 80)], dxfattribs={'layer': 'LABORES_ABANDONADAS'})
msp.add_text(f'{za:.2f}', height=1.2, dxfattribs={'layer': 'COTAS', 'insert': (ea + 1.5, N0 - 40)})
msp.add_lwpolyline([(e2 + 0.8 * math.sin(150 / 25), N0 + 150), (e2 + 1, N0 + 200)], dxfattribs={'layer': 'PROYECTADO'})
# Bocaminas (bloques) y nombres de frentes
msp.add_blockref('BOCAMINA', (E0, N0, 820), dxfattribs={'layer': 'BOCAMINAS'})
msp.add_text('BOCAMINA PRINCIPAL', height=2, dxfattribs={'layer': 'BOCAMINAS', 'insert': (E0 - 30, N0 + 4)})
msp.add_blockref('BOCAMINA', b_, dxfattribs={'layer': 'BOCAMINAS'})
msp.add_text('BOCAMINA 2 VENTILACION', height=2, dxfattribs={'layer': 'BOCAMINAS', 'insert': (eb - 40, N0 + 104)})
for t, (x, y) in (('FRENTE N1 NORTE', (e1 + 3, N0 + 122)), ('FRENTE N1 SUR', (e1 + 3, N0 - 92)), ('FRENTE N2 NORTE', (e2 + 3, N0 + 152)),
                  ('FRENTE N2 SUR', (e2 + 3, N0 - 112)), ('AVANCE INCLINADO', (por_buzamiento(165)[0] + 3, N0 - 3)), ('FRENTE CRUZADA M2', (ec + 44, N0 + 80))):
    msp.add_text(t, height=1.5, dxfattribs={'layer': 'TEXTOS', 'insert': (x, y)})
# Límite del título (cerca de la cruzada) y curvas de nivel que el complemento debe ignorar
msp.add_lwpolyline([(E0 - 150, N0 - 250), (E0 + 205, N0 - 250), (E0 + 205, N0 + 300), (E0 - 150, N0 + 300)], close=True, dxfattribs={'layer': 'LIMITE_TITULO'})
for zc in range(800, 900, 10):
    pts = []
    for n in range(-260, 320, 10):
        f = lambda e: zs(e, N0 + n) - zc; a_, b2 = E0 - 200, E0 + 260
        if f(a_) * f(b2) > 0: continue
        for _ in range(40):
            m = (a_ + b2) / 2; a_, b2 = (m, b2) if f(a_) * f(m) > 0 else (a_, m)
        pts.append((a_, N0 + n))
    if len(pts) > 1: msp.add_lwpolyline(pts, dxfattribs={'layer': 'CURVAS_NIVEL', 'elevation': zc})
msp.add_text('PLANO DE LABORES MINA SINTETICA', height=4, dxfattribs={'layer': 'ROTULO', 'insert': (E0 - 140, N0 - 240)})
d.saveas(sys.argv[1])
# DEM de la ladera (2 m) en EPSG:9377
x0, y1, res = E0 - 200, N0 + 320, 2.0; nx, ny = 230, 300
Z = np.array([[zs(x0 + (i + .5) * res, y1 - (j + .5) * res) for i in range(nx)] for j in range(ny)], np.float32)
ds = gdal.GetDriverByName('GTiff').Create(sys.argv[2], nx, ny, 1, gdal.GDT_Float32); ds.SetGeoTransform((x0, res, 0, y1, 0, -res))
s = osr.SpatialReference(); s.ImportFromEPSG(9377); ds.SetProjection(s.ExportToWkt()); ds.GetRasterBand(1).WriteArray(Z); ds.GetRasterBand(1).SetNoDataValue(-9999); ds = None
print('ok', e1, z1, e2, z2)
