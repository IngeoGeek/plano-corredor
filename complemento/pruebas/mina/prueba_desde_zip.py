"""Prueba del complemento desde el ZIP instalable, con QGIS real sin pantalla: instalación, ventana, modo mina con DXF y DWG."""
import os, sys, json, shutil, time, traceback
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
CARPETA = sys.argv[1]; DATOS = sys.argv[2]; SALIDA = sys.argv[3]
sys.path.insert(0, CARPETA)
from qgis.core import QgsApplication, QgsProject, QgsCoordinateReferenceSystem
app = QgsApplication([], False); app.initQgis()
from qgis.PyQt.QtWidgets import QMainWindow, QToolBar, QMessageBox
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapCanvas, QgsMessageBar
class IfaceFalso:
    def __init__(self): self.v = QMainWindow(); self.c = QgsMapCanvas(self.v); self.b = QgsMessageBar(); self.t = QToolBar()
    def mainWindow(self): return self.v
    def mapCanvas(self): return self.c
    def messageBar(self): return self.b
    def addToolBarIcon(self, a): self.t.addAction(a)
    def removeToolBarIcon(self, a): self.t.removeAction(a)
    def addPluginToMenu(self, m, a): pass
    def removePluginMenu(self, m, a): pass
for n in ('information', 'warning', 'critical'): setattr(QMessageBox, n, staticmethod(lambda *a, **k: QMessageBox.Ok))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
pasos = []; fallo = False
def paso(nombre, f):
    global fallo
    t = time.time()
    try: r = f(); pasos.append({'paso': nombre, 'ok': True, 's': round(time.time() - t, 2), 'detalle': r}); print('OK  ', nombre, r if r else '')
    except Exception as e: fallo = True; pasos.append({'paso': nombre, 'ok': False, 'error': repr(e)}); print('FALLA', nombre, repr(e)); traceback.print_exc()
import maqueta3dweb
iface = IfaceFalso(); P = maqueta3dweb.classFactory(iface)
paso('initGui', lambda: (P.initGui(), None)[1])
paso('abrir ventana', lambda: (P.abrir(), P.dlg.windowTitle())[1])
d = P.dlg
def tam():
    from qgis.PyQt.QtGui import QFont
    f = QFont(); f.setPointSize(9); d.setFont(f); d.r_mina.setChecked(True); s = d.minimumSizeHint(); return f'{s.width()} × {s.height()} px'
paso('tamaño mínimo de la ventana (9 pt)', tam)
QgsProject.instance().setCrs(QgsCoordinateReferenceSystem('EPSG:9377'))
def mina(plano, sub):
    d.r_mina.setChecked(True); d.f_cad.setFilePath(plano); d._leer_cad()
    assert d.datos_cad, 'no leyó el plano'
    tabla = d._tabla_mina(); usados = [t['nombre'] for t in tabla if t['usar']]
    assert 'CURVAS_NIVEL' not in usados and 'ROTULO' not in usados, 'usa capas que no son labores'
    d.c_colores.setCurrentIndex(1)
    col = {t['nombre']: t['color'] for t in d._tabla_mina()}
    assert col['NIVEL_1'] == '#f2c200' and col['INCLINADO_PPAL'] == '#8c8c8c', col
    d.c_colores.setCurrentIndex(0)
    d.w_crs.setCrs(QgsCoordinateReferenceSystem('EPSG:9377'))
    d.c_sup.setCurrentIndex(1); d.f_dem_m.setFilePath(os.path.join(DATOS, 'dem_sintetico.tif'))
    n = d.t_gas.rowCount(); assert n >= 5, f'{n} frentes'
    lect = {'FRENTE N2 NORTE': '1,2', 'FRENTE N2 SUR': '0,6', 'AVANCE INCLINADO': '0.9'}
    from qgis.PyQt.QtWidgets import QTableWidgetItem
    for r in range(n):
        v = lect.get(d.t_gas.item(r, 1).text())
        if v: d.t_gas.setItem(r, 5, QTableWidgetItem(v))
        if d.t_gas.item(r, 1).text() == 'AVANCE INCLINADO': d.t_gas.setItem(r, 7, QTableWidgetItem('0,25'))
    assert 'VENTIL' in d.c_retorno.currentText(), d.c_retorno.currentText()
    out = os.path.join(SALIDA, sub); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    d.f_salida.setFilePath(out); d.r_zip.setChecked(True); d.e_url.setText('https://ejemplo.org/mina/'); d.e_titulo.setText('Mina sintética de prueba')
    d.generar()
    for f in ('sitio/index.html', 'sitio/mina.glb', 'sitio/config.js', 'sitio/plano.jpg', 'sitio/sw.js', 'sitio.zip', 'plano_carta.pdf', 'QR.png'):
        assert os.path.exists(os.path.join(out, f)), f'falta {f}'
    t = open(os.path.join(out, 'sitio/config.js'), encoding='utf-8').read(); cfg = json.loads(t[t.index('=') + 1:].rstrip().rstrip(';'))
    res = cfg['mina']['metano']['resultados']
    assert len(res) == 3 and cfg['proyeccion'] and cfg['proyeccion']['x_0'] == 5000000, (len(res), cfg['proyeccion'])
    return f"{len(tabla)} capas, {n} frentes, {len(res)} con metano, salida por «{res[0]['salida']}», {os.path.getsize(os.path.join(out, 'sitio/mina.glb')) // 1024} KB de GLB"
paso('modo mina con DXF (ventana completa)', lambda: mina(os.path.join(DATOS, 'mina_sintetica.dxf'), 'dxf'))
os.environ['PATH'] = '/home/claude/ldwg/libredwg-0.13.3/programs:' + os.environ['PATH']
paso('modo mina con DWG (LibreDWG dwg2dxf)', lambda: mina(os.path.join(DATOS, 'mina_sintetica.dwg'), 'dwg'))
def gdal_cad():
    from maqueta3dweb.nucleo import cad
    D = cad.leer_gdal_cad(os.path.join(DATOS, 'mina_sintetica.dwg'))
    return f"GDAL CAD: {len(D['lineas'])} líneas, {len(D['textos'])} textos, {len(D['capas'])} capas"
paso('lectura de respaldo con el controlador CAD de GDAL (R2000)', gdal_cad)
def dwg_autocad():
    from maqueta3dweb.nucleo import cad
    out = []
    for n in ('example_2000.dwg', 'example_2007.dwg', 'example_2013.dwg', 'example_2018.dwg', 'sample_2018.dwg'):
        D = cad.leer('/home/claude/ldwg/libredwg-0.13.3/test/test-data/' + n, registro=lambda t: None)
        assert D['capas'], n
        out.append(f"{n}: {len(D['lineas'])} líneas, {len(D['capas'])} capas")
    return '; '.join(out)
paso('DWG hechos con AutoCAD (2000 a 2018) por la cadena DWG → DXF', dwg_autocad)
def otros_modos():
    d.r_gpkg.setChecked(True); assert d.pila.currentIndex() == 0
    d.r_foto.setChecked(True); assert d.pila.currentIndex() == 1
    d.r_mina.setChecked(True); assert d.pila.currentIndex() == 2
paso('cambio entre los tres tipos de insumo', otros_modos)
paso('unload', lambda: (P.unload(), None)[1])
json.dump(pasos, open(os.path.join(SALIDA, 'pasos.json'), 'w'), ensure_ascii=False, indent=1)
app.exitQgis(); sys.exit(1 if fallo else 0)
