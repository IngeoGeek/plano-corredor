import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm')
from qcap_base import *
from qgis.core import QgsLayoutItemMap
G = {}
@paso(2500)
def p0():
    ventana(); iface.mapCanvas().zoomToFullExtent()
@paso(2500)
def p1():
    iface.messageBar().clearWidgets()
    sb = iface.mainWindow().statusBar(); volcar(iface.mainWindow().statusBar(), 'dump_status.txt')
    foto('q01_proyecto', [0, 0, 1600, 900])
@paso(3000)
def p2():
    QTimer.singleShot(2500, lambda: (volcar(modal(), 'dump_props.txt'), foto('q02_src_raw'), cerrar_modales()))
    iface.showProjectPropertiesDialog('mProjOptsCRS')
@paso(4000)
def p3():
    lay = QgsProject.instance().layoutManager().layoutByName('Plano_90x60_Corredor_Carbonifero')
    d = iface.openLayoutDesigner(lay); G['d'] = d
    w = d.window(); w.setGeometry(0, 0, 1600, 900); w.show()
    mapa = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap) and i.displayName() == 'Mapa principal'][0]
    lay.setSelectedItem(mapa); d.view().zoomFull() if hasattr(d.view(),'zoomFull') else None
@paso(3000)
def p4():
    volcar(G['d'].window(), 'dump_layout.txt'); foto('q03_diseno_raw')
arrancar()
