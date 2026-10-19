# Acciones de pantalla del capítulo 4 (relieve.png con Traducir)
import sys, os, glob, time
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap4'
sys.path.insert(0, V + '/rec')
from motor import Motor
from util import *
from qgis.utils import iface
from qgis.core import QgsProject, QgsRasterLayer
from qgis.PyQt.QtCore import QTimer, Qt, QPoint
from qgis.PyQt.QtWidgets import QApplication, QWidget, QComboBox, QLineEdit, QGroupBox, QToolButton, QScrollArea, QPlainTextEdit, QDialog
T = '/home/osney/Plano3D/trabajo/'
for f in glob.glob(T + 'relieve*'): os.remove(f)
m = Motor(C + '/eventos.jsonl', C + '/duraciones.json')
def ww(dlg, nombre):
    w = dlg.mainWidget().wrappers[nombre]
    return w.wrappedWidget() if hasattr(w, 'wrappedWidget') else w.widget
def guion():
    mw = iface.mainWindow(); mw.showMaximized(); yield 2.5
    iface.messageBar().clearWidgets()
    for d in mw.findChildren(QWidget):
        if d.objectName() == 'ProcessingToolbox': d.hide()
    # dem_suave visible en el mapa, como al final del capítulo 2
    iface.addRasterLayer(T + 'dem_suave.tif', 'dem_suave'); yield 2.0
    iface.messageBar().clearWidgets()
    yield from m.destello()
    yield from m.seg('s01')
    yield from m.mover(900, 560, 1.2)
    yield from m.seg('s02')
    yield 0.6
    antes = visibles()
    yield from abrir_menu(m, mw.menuBar(), ['Ráster', 'Conversión', 'Traducir'])
    dlg = yield from esperar_que(dialogo_nuevo(antes), 10); yield 0.8
    yield from m.seg('s03')
    yield from m.zoom(m.rect_global(dlg))
    inp = [c for c in ww(dlg, 'INPUT').findChildren(QComboBox) if c.isVisible()][0]
    yield from m.elegir_combo(inp, 'dem_suave')
    yield from m.resaltar(m.rect_global(inp), 2.5, '1')
    yield from m.seg('s04')
    adv = [g for g in hijos(dlg, QGroupBox) if g.objectName() == 'grpAdvanced'][0]
    sa = adv.parentWidget()
    while sa is not None and not isinstance(sa, QScrollArea): sa = sa.parentWidget()
    ex = ww(dlg, 'EXTRA'); exl = ex if isinstance(ex, QLineEdit) else hijos(ex, QLineEdit, vis=False)[0]
    if not exl.isVisible():
        yield from m.bajar_hasta(sa, adv, 30)
        cb = [b for b in adv.findChildren(QToolButton) if b.objectName() == 'collapseButton'][0]
        yield from m.clic(cb); yield 0.6
        if not exl.isVisible():
            from qgis.gui import QgsCollapsibleGroupBoxBasic
            import sip; sip.cast(adv, QgsCollapsibleGroupBoxBasic).setCollapsed(False); yield 0.4
    yield from m.bajar_hasta(sa, exl, 160)
    yield from m.clic(exl); yield from m.escribir(exl, '-scale 100 2000 0 65535', cps=12)
    yield from m.resaltar(m.rect_global(exl), 5, '2')
    yield from m.seg('s05')
    dt = ww(dlg, 'DATA_TYPE'); dtc = dt if isinstance(dt, QComboBox) else hijos(dt, QComboBox)[0]
    yield from m.bajar_hasta(sa, dtc, 200)
    yield from m.elegir_combo(dtc, 'UInt16')
    yield from m.resaltar(m.rect_global(dtc), 2.5, '3')
    yield from m.seg('s06')
    out = hijos(ww(dlg, 'OUTPUT'), QLineEdit, 'leText')[0]
    yield from m.bajar_hasta(sa, out, 200)
    yield from m.clic(out); yield from m.escribir(out, T + 'relieve.png', cps=20)
    QTimer.singleShot(0, lambda: __import__('qgis.PyQt.QtTest', fromlist=['QTest']).QTest.keyClick(out, Qt.Key_Tab)); yield 0.6
    yield from m.seg('s07')
    con = [p for p in dlg.findChildren(QPlainTextEdit) if p.isVisible()]
    if con:
        yield from m.bajar_hasta(sa, con[0], 300)
        yield from m.ir(con[0]); yield from m.resaltar(m.rect_global(con[0]), 6, '4'); m.ev('info', consola=con[0].toPlainText())
    yield 6.0
    n0 = len(QgsProject.instance().mapLayers())
    yield from m.alejar()
    yield from m.clic(boton(dlg, 'Ejecutar')); yield 1.0
    yield from m.corte_ini()
    yield from esperar_que(lambda: len(QgsProject.instance().mapLayers()) > n0 and os.path.exists(T + 'relieve.png'), 300)
    yield 0.8
    yield from m.corte_fin()
    yield from m.seg('s08')
    yield from m.clic(boton(dlg, 'Cerrar')); yield 1.5
    yield from m.mover(700, 560, 1.0)
    yield from m.hasta(m.fin)
    yield 1.0
    from PIL import Image
    im = Image.open(T + 'relieve.png'); m.ev('info', relieve=[im.size, im.mode])
QTimer.singleShot(3500, lambda: m.correr(guion(), lambda: os._exit(0)))
