import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm')
from qcap_base import *
from qgis.core import QgsLayoutItemMap, QgsRectangle, QgsRasterLayer, QgsCoordinateReferenceSystem
from qgis.gui import QgsCollapsibleGroupBoxBasic
from qgis.PyQt.QtWidgets import QTextEdit, QDockWidget, QScrollArea, QGroupBox, QComboBox, QFileDialog
import processing
T = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/trabajo/'
G = {}
def por_nombre(w, n, tipo=QWidget): return [x for x in w.findChildren(tipo) if x.objectName() == n]
EXT = '4885966.641,4928420.741,2241436.912,2278431.036 [EPSG:9377]'
def dialogo(alg, params, nombre, w=980, h=760):
    d = processing.createAlgorithmDialog(alg, params); G[nombre] = d
    d.setGeometry(310, 120, w, h); d.show()
    for gb in d.findChildren(QgsCollapsibleGroupBoxBasic): gb.setCollapsed(False)
    QTimer.singleShot(1500, lambda: (volcar(d, f'dump_{nombre}.txt'), foto(nombre + '_raw'), d.close()))
@paso(3000)
def p0():
    ventana(); iface.mapCanvas().setExtent(QgsRectangle(4885966.641, 2241436.912, 4928420.741, 2278431.036))
    cl = QgsProject.instance().mapLayersByName('Curvas de nivel')[0]; G['curvas'] = cl
@paso(3500)
def p1():
    cl = G['curvas']
    data = f'{cl.source()}::~::0::~::{cl.fields().indexOf("elev")}::~::1'
    dialogo('qgis:tininterpolation', {'INTERPOLATION_DATA': data, 'METHOD': 0, 'EXTENT': EXT, 'PIXEL_SIZE': 30, 'OUTPUT': T + 'dem_tin.tif'}, 'q06_tin')
@paso(3500)
def p2():
    r = iface.addRasterLayer(T + 'dem_tin_struct.tif', 'dem_tin'); G['tin'] = r
    dialogo('gdal:warpreproject', {'INPUT': r, 'RESAMPLING': 5, 'TARGET_RESOLUTION': 90, 'OUTPUT': T + 'dem90.tif'}, 'q07_combar90')
@paso(3500)
def p3():
    r = iface.addRasterLayer(T + 'dem90.tif', 'dem90')
    dialogo('gdal:warpreproject', {'INPUT': r, 'RESAMPLING': 3, 'TARGET_RESOLUTION': 30, 'TARGET_EXTENT': EXT, 'OUTPUT': T + 'dem_suave.tif'}, 'q08_combar30')
@paso(3500)
def p4():
    r = iface.addRasterLayer(T + 'dem_suave.tif', 'dem_suave'); G['suave'] = r
    dialogo('gdal:translate', {'INPUT': r, 'DATA_TYPE': 3, 'EXTRA': '-scale 100 2000 0 65535', 'OUTPUT': T + 'relieve.png'}, 'q10_traducir')
@paso(4000)
def p5():
    QTimer.singleShot(2500, lambda: (volcar(modal(), 'dump_q09.txt'), foto('q09_minmax_raw'), cerrar_modales()))
    iface.showLayerProperties(G['suave'], 'mOptsPage_Symbology')
@paso(4000)
def p6():
    def f():
        m = modal(); volcar(m, 'dump_q11.txt')
        foto('q11_mapa_imagen_raw'); cerrar_modales()
    QTimer.singleShot(2500, f)
    [a for a in iface.mainWindow().findChildren(QAction) if a.objectName() == 'mActionSaveMapAsImage'][0].trigger()
@paso(3500)
def p7():
    l = QgsProject.instance().mapLayersByName('Fallas')[0]
    dialogo('native:pointonsurface', {'INPUT': l, 'ALL_PARTS': False}, 'q13_punto_superficie', 900, 600)
@paso(4000)
def p8():
    from qgis.gui import QgsVectorLayerSaveAsDialog
    l = QgsProject.instance().mapLayersByName('Proyectos piloto')[0]
    d = QgsVectorLayerSaveAsDialog(l, QgsVectorLayerSaveAsDialog.AllOptions, iface.mainWindow()); G['sv'] = d
    d.setGeometry(310, 40, 760, 940); d.show()
    QTimer.singleShot(1500, lambda: (volcar(d, 'dump_q14.txt'), foto('q14_csv_raw')))
arrancar()
