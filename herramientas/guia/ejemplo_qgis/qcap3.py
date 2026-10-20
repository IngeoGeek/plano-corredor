import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm')
from qcap_base import *
from qgis.core import QgsLayoutItemMap, QgsRectangle
from qgis.gui import QgsCollapsibleGroupBoxBasic
from qgis.PyQt.QtWidgets import QTextEdit, QDockWidget, QScrollArea, QGroupBox
G = {}
def por_nombre(w, n, tipo=QWidget): return [x for x in w.findChildren(tipo) if x.objectName() == n]
@paso(3000)
def p0():
    ventana(); iface.mapCanvas().setExtent(QgsRectangle(4885966.641, 2241436.912, 4928420.741, 2278431.036)); iface.mapCanvas().refresh()
@paso(1500)
def p1():
    iface.messageBar().clearWidgets(); sb = iface.mainWindow().statusBar()
    crs = por_nombre(sb, 'mOntheFlyProjectionStatusButton')[0]
    foto('q01_proyecto', None, [rect(crs) + ['1']]); volcar(iface.mainWindow().statusBar(), 'dump_status2.txt')
@paso(4000)
def p3():
    lay = QgsProject.instance().layoutManager().layoutByName('Plano_90x60_Corredor_Carbonifero')
    d = iface.openLayoutDesigner(lay); G['d'] = d; G['lay'] = lay
    w = d.window(); w.setGeometry(0, 0, 1600, 1000); w.show()
    mapa = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap) and i.displayName() == 'Mapa principal'][0]; G['mapa'] = mapa
    lay.setSelectedItem(mapa); d.showItemOptions(mapa, True)
    dock = por_nombre(w, 'ItemDock', QDockWidget)[0]; G['dock'] = dock
    w.resizeDocks([dock], [470], Qt.Horizontal)
@paso(2000)
def p4():
    dock = G['dock']
    for gb in dock.findChildren(QGroupBox):
        if gb.title() in ('Capas',) and hasattr(gb, 'setCollapsed'): gb.setCollapsed(True)
@paso(1500)
def p5():
    dock = G['dock']; sa = [s for s in dock.findChildren(QScrollArea) if s.isVisible()]
    esc = por_nombre(dock, 'mScaleLineEdit')[0]; ext = por_nombre(dock, 'mExtentsCheckBox', QGroupBox)[0]
    for s in sa:
        try: s.ensureWidgetVisible(ext, 0, 0)
        except Exception: pass
    QTimer.singleShot(600, lambda: foto('q03_extension', None, [rect(esc) + ['1'], rect(ext) + ['2']]))
@paso(2000)
def p6():
    dock = G['dock']
    for gb in dock.findChildren(QGroupBox):
        if gb.title() in ('Propiedades principales', 'Extensión') and hasattr(gb, 'setCollapsed'): gb.setCollapsed(True)
        if gb.objectName() == 'mGeneralOptionsGroupBox' and hasattr(gb, 'setCollapsed'): gb.setCollapsed(False)
@paso(1500)
def p7():
    dock = G['dock']; pos = por_nombre(dock, 'mGeneralOptionsGroupBox', QGroupBox)[0]
    for s in dock.findChildren(QScrollArea):
        try: s.ensureWidgetVisible(pos, 0, 0)
        except Exception: pass
    QTimer.singleShot(600, lambda: (volcar(dock, 'dump_pos.txt'), foto('q04_posicion', None, [rect(pos) + ['1']])))
@paso(2500)
def p8():
    G['d'].showItemOptions(G['lay'].pageCollection().page(0), True)
@paso(1500)
def p9():
    volcar(G['dock'], 'dump_page.txt'); foto('q05_pagina_raw')
arrancar()
