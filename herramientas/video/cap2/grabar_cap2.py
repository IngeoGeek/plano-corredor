# Acciones de pantalla del capítulo 2 (DEM). Se ejecuta dentro de QGIS con --code y el proyecto abierto.
import sys, os, json, glob, time
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap2'
sys.path.insert(0, V + '/rec')
from motor import Motor
from qgis.utils import iface
from qgis.core import QgsProject, QgsRasterLayer
from qgis.PyQt.QtCore import QTimer, Qt, QPoint, QRect
from qgis.PyQt.QtWidgets import (QApplication, QWidget, QLineEdit, QTreeView, QTreeWidget, QComboBox, QPushButton, QToolButton, QGroupBox,
                                 QDoubleSpinBox, QListWidget, QRadioButton, QDialog, QScrollArea, QAbstractSpinBox)
T = '/home/osney/Plano3D/trabajo/'
for f in glob.glob(T + '*'): os.remove(f)
m = Motor(C + '/eventos.jsonl', C + '/duraciones.json')
EXT = '4885966.641,4928420.741,2241436.912,2278431.036 [EPSG:9377]'

def hijos(w, tipo=QWidget, nombre=None, vis=True):
    return [x for x in w.findChildren(tipo) if (nombre is None or x.objectName() == nombre) and (x.isVisible() or not vis)]
def boton(w, texto): return [b for b in hijos(w, QPushButton) if b.text().replace('&', '') == texto][0]
def accion(menu, texto):
    for a in menu.actions():
        if texto.lower() in a.text().replace('&', '').lower(): return a
    raise Exception(f'sin {texto}: {[a.text() for a in menu.actions()]}')
def esperar_que(cond, maxs=15):
    t = time.time()
    while time.time() - t < maxs:
        r = cond()
        if r: return r
        yield 0.1
    raise Exception('tiempo agotado esperando')
def dialogo_nuevo(antes):
    def f():
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible() and w not in antes: return w
    return f
def menu_principal(texto):
    mb = iface.mainWindow().menuBar()
    return mb, [a for a in mb.actions() if texto in a.text().replace('&', '')][0]
def abrir_menu(ruta):
    """ruta: ['Ráster', 'Proyecciones', 'Combar'] con clics y pasos reales por los submenús"""
    mb, a = menu_principal(ruta[0])
    yield from m.clic(mb, mb.actionGeometry(a).center()); yield 0.5
    menu = a.menu()
    for i, t in enumerate(ruta[1:]):
        act = accion(menu, t); r = menu.actionGeometry(act)
        if i == len(ruta) - 2:
            yield from m.clic(menu, r.center()); yield 0.3
            yield from m.cerrar_popups(mb); return
        yield from m.ir(menu, r.center()); menu.setActiveAction(act); yield 0.7
        sub = act.menu()
        if not sub.isVisible(): sub.popup(menu.mapToGlobal(r.topRight())); yield 0.4
        yield from m.mover(sub.mapToGlobal(QPoint(20, 0)).x(), menu.mapToGlobal(r.center()).y(), 0.4)
        menu = sub
def ejecutar_y_esperar(dlg, salida):
    n0 = len(QgsProject.instance().mapLayers())
    yield from m.clic(boton(dlg, 'Ejecutar'))
    yield 1.0
    yield from m.corte_ini()
    yield from esperar_que(lambda: len(QgsProject.instance().mapLayers()) > n0 and os.path.exists(salida), 600)
    yield 1.0
    yield from m.corte_fin()
    yield 0.8
def capa_combo(combo, nombre):
    for k in range(combo.count()):
        if nombre in combo.itemText(k): return combo.itemText(k)
    return combo.itemText(0)
def ww(dlg, nombre):
    w = dlg.mainWidget().wrappers[nombre]
    return w.wrappedWidget() if hasattr(w, 'wrappedWidget') else w.widget
def salida_de(dlg, nombre='OUTPUT'):
    return hijos(ww(dlg, nombre), QLineEdit, 'leText')[0]

def guion():
    mw = iface.mainWindow(); mw.showMaximized(); yield 2.5
    iface.messageBar().clearWidgets()
    for d in mw.findChildren(QWidget):
        if d.objectName() == 'ProcessingToolbox': d.hide()
    yield 1.0
    yield from m.destello()
    # s01 introducción
    yield from m.seg('s01')
    yield from m.mover(900, 560, 1.2)
    # s02 caja de herramientas
    yield from m.seg('s02')
    yield 1.5
    yield from abrir_menu(['Procesos', 'Caja de herramientas'])
    tb = yield from esperar_que(lambda: ([w for w in mw.findChildren(QWidget) if w.objectName() == 'ProcessingToolbox' and w.isVisible()] or [None])[0])
    yield 1.0
    # s03 buscar TIN y doble clic
    yield from m.seg('s03')
    sb = [x for x in tb.findChildren(QLineEdit) if x.isVisible()][0]
    yield from m.zoom(m.rect_global(tb))
    yield from m.clic(sb); yield from m.escribir(sb, 'TIN'); yield 1.2
    tree = [t for t in tb.findChildren(QTreeView) if t.isVisible()][0]; mod = tree.model()
    idx = mod.match(mod.index(0, 0), Qt.DisplayRole, 'Interpolación TIN', 1, Qt.MatchRecursive | Qt.MatchExactly)[0]
    tree.scrollTo(idx); yield 0.3
    antes = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
    yield from m.clic(tree.viewport(), tree.visualRect(idx).center(), doble=True)
    yield from m.alejar()
    yield 1.2
    if not dialogo_nuevo(antes)():
        QTimer.singleShot(0, lambda: tree.doubleClicked.emit(idx))
    dlg = yield from esperar_que(dialogo_nuevo(antes), 10)
    yield 1.0
    # s04 capa, campo y +
    yield from m.seg('s04')
    cl = hijos(dlg, QComboBox, 'cmbLayers')[0]; cf = hijos(dlg, QComboBox, 'cmbFields')[0]; add = hijos(dlg, QToolButton, 'btnAdd')[0]
    yield from m.zoom(m.rect_global(dlg))
    yield from m.elegir_combo(cl, 'Curvas de nivel')
    yield 0.4
    yield from m.elegir_combo(cf, 'elev', contiene=False)
    yield 0.4
    yield from m.clic(add)
    yield from m.resaltar(m.rect_global(add), 2.5, '1')
    # s05 tipo: líneas de estructura
    yield from m.seg('s05')
    lt = hijos(dlg, QTreeWidget, 'layersTree')[0]
    yield 1.5
    cb = [c for c in lt.findChildren(QComboBox) if c.isVisible()]
    if cb:
        yield from m.elegir_combo(cb[0], 'estructura')
        yield from m.resaltar(m.rect_global(cb[0]), 4, '2')
    # s06 método lineal y extensión
    yield from m.seg('s06')
    met = [c for c in hijos(dlg, QComboBox) if c.currentText() == 'Lineal']
    if met: yield from m.ir(met[0]); yield 1.0
    ext = hijos(dlg, QLineEdit, 'mCondensedLineEdit')[0]
    yield from m.clic(ext)
    yield from m.escribir(ext, EXT, cps=22)
    QTimer.singleShot(0, lambda: __import__('qgis.PyQt.QtTest', fromlist=['QTest']).QTest.keyClick(ext, Qt.Key_Tab)); yield 0.4
    yield from m.resaltar(m.rect_global(ext), 4, '3')
    # s07 tamaño de píxel
    yield from m.seg('s07')
    cx = hijos(dlg, QAbstractSpinBox, 'mCellXSpinBox')[0]; cy = hijos(dlg, QAbstractSpinBox, 'mCellYSpinBox')[0]
    yield from m.reemplazar(cx, '30')
    yield from m.reemplazar(cy, '30')
    yield from m.resaltar([*m.rect_global(cx)[:2], m.rect_global(cy)[0] + m.rect_global(cy)[2] - m.rect_global(cx)[0], m.rect_global(cy)[1] + m.rect_global(cy)[3] - m.rect_global(cx)[1]], 4, '4')
    # s08 salida y ejecutar
    yield from m.seg('s08')
    out = hijos(dlg, QLineEdit, 'leText')[0]
    yield from m.clic(out); yield from m.escribir(out, T + 'dem_tin.tif', cps=20)
    yield 0.5
    yield from m.alejar()
    yield from ejecutar_y_esperar(dlg, T + 'dem_tin.tif')
    # s09 cerrar
    yield from m.seg('s09')
    yield 1.0
    yield from m.clic(boton(dlg, 'Cerrar'))
    yield 1.5
    if tb.isVisible(): tb.hide()
    yield from m.mover(800, 560, 1.0)
    # s10 Ráster → Proyecciones → Combar
    yield from m.seg('s10')
    yield 6.5
    antes = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
    yield from abrir_menu(['Ráster', 'Proyecciones', 'Combar'])
    dlg = yield from esperar_que(dialogo_nuevo(antes), 10)
    yield 0.8
    # s11 entrada, media, 90
    yield from m.seg('s11')
    yield from m.zoom(m.rect_global(dlg))
    inp = [c for c in ww(dlg, 'INPUT').findChildren(QComboBox) if c.isVisible()][0]
    yield from m.elegir_combo(inp, capa_combo(inp, 'dem_tin'), contiene=False)
    rs = ww(dlg, 'RESAMPLING'); yield from m.elegir_combo(rs, 'Media')
    tr = ww(dlg, 'TARGET_RESOLUTION'); trs = tr if isinstance(tr, QAbstractSpinBox) else hijos(tr, QAbstractSpinBox)[0]
    yield from m.reemplazar(trs, '90')
    # s12 salida y ejecutar
    yield from m.seg('s12')
    out = salida_de(dlg)
    yield from m.clic(out); yield from m.escribir(out, T + 'dem90.tif', cps=20)
    yield from m.alejar()
    yield from ejecutar_y_esperar(dlg, T + 'dem90.tif')
    yield from m.clic(boton(dlg, 'Cerrar')); yield 1.0
    # s13 segundo Combar
    yield from m.seg('s13')
    antes = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
    yield from abrir_menu(['Ráster', 'Proyecciones', 'Combar'])
    dlg = yield from esperar_que(dialogo_nuevo(antes), 10)
    yield 0.6
    yield from m.zoom(m.rect_global(dlg))
    inp = [c for c in ww(dlg, 'INPUT').findChildren(QComboBox) if c.isVisible()][0]
    yield from m.elegir_combo(inp, capa_combo(inp, 'dem90'), contiene=False)
    rs = ww(dlg, 'RESAMPLING'); yield from m.elegir_combo(rs, 'B-Spline')
    tr = ww(dlg, 'TARGET_RESOLUTION'); trs = tr if isinstance(tr, QAbstractSpinBox) else hijos(tr, QAbstractSpinBox)[0]
    yield from m.reemplazar(trs, '30')
    # s14 avanzados → extensión
    yield from m.seg('s14')
    adv = [g for g in hijos(dlg, QGroupBox) if g.objectName() == 'grpAdvanced'][0]
    sa = adv.parentWidget()
    while sa is not None and not isinstance(sa, QScrollArea): sa = sa.parentWidget()
    te = ww(dlg, 'TARGET_EXTENT'); cle = hijos(te, QLineEdit, 'mCondensedLineEdit', vis=False)[0]
    if not cle.isVisible():
        yield from m.bajar_hasta(sa, adv, 30)
        cbtn = [b for b in adv.findChildren(QToolButton) if b.objectName() == 'collapseButton'][0]
        yield from m.clic(cbtn); yield 0.6
        if not cle.isVisible():
            from qgis.gui import QgsCollapsibleGroupBoxBasic
            import sip; sip.cast(adv, QgsCollapsibleGroupBoxBasic).setCollapsed(False); yield 0.4
    yield from m.bajar_hasta(sa, cle, 160)
    yield from m.clic(cle); yield from m.escribir(cle, EXT, cps=22)
    QTimer.singleShot(0, lambda: __import__('qgis.PyQt.QtTest', fromlist=['QTest']).QTest.keyClick(cle, Qt.Key_Tab)); yield 0.4
    yield from m.resaltar(m.rect_global(cle), 3.5, '4')
    # s15 salida y ejecutar
    yield from m.seg('s15')
    out = salida_de(dlg)
    yield from m.bajar_hasta(sa, out, 200)
    yield from m.clic(out); yield from m.escribir(out, T + 'dem_suave.tif', cps=20)
    yield from m.alejar()
    yield from ejecutar_y_esperar(dlg, T + 'dem_suave.tif')
    yield from m.clic(boton(dlg, 'Cerrar')); yield 1.0
    # s16 doble clic en la capa → Simbología
    yield from m.seg('s16')
    lyr = [l for l in QgsProject.instance().mapLayers().values() if isinstance(l, QgsRasterLayer) and 'suave' in l.source()][-1]
    view = iface.layerTreeView(); node = QgsProject.instance().layerTreeRoot().findLayer(lyr.id())
    idx = view.node2index(node) if hasattr(view, 'node2index') else view.layerTreeModel().node2index(node)
    view.scrollTo(idx); yield 0.3
    yield from m.zoom([0, 150, 700, 500])
    antes = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
    yield from m.clic(view.viewport(), view.visualRect(idx).center(), doble=True)
    yield from m.alejar()
    yield 1.2
    if not dialogo_nuevo(antes)():
        QTimer.singleShot(0, lambda: iface.showLayerProperties(lyr))
    dlg = yield from esperar_que(dialogo_nuevo(antes), 10)
    yield 1.0
    lw = hijos(dlg, QListWidget, 'mOptionsListWidget')[0]
    it = [lw.item(i) for i in range(lw.count()) if 'Simbolog' in lw.item(i).text()][0]
    yield from m.clic(lw.viewport(), lw.visualItemRect(it).center())
    yield 1.0
    # s17 mín/máx, precisión real
    yield from m.seg('s17')
    yield from m.zoom(m.rect_global(dlg))
    gb = [g for g in hijos(dlg, QGroupBox) if 'mín/máx' in g.title().lower() or 'min/max' in g.title().lower()]
    rb = [r for r in dlg.findChildren(QRadioButton) if r.objectName() == 'mMinMaxRadioButton']
    if gb and rb and not rb[0].isVisible():
        cbtn = [b for b in gb[0].findChildren(QToolButton) if b.objectName() == 'collapseButton']
        if cbtn: yield from m.clic(cbtn[0]); yield 0.6
        if not rb[0].isVisible():
            from qgis.gui import QgsCollapsibleGroupBoxBasic
            import sip; sip.cast(gb[0], QgsCollapsibleGroupBoxBasic).setCollapsed(False); yield 0.4
    if rb: yield from m.clic(rb[0], QPoint(8, rb[0].height() // 2))
    acc = [c for c in dlg.findChildren(QComboBox) if c.objectName() == 'cboAccuracy' and c.isVisible()]
    if acc: yield from m.elegir_combo(acc[0], 'Real')
    yield 0.6
    yield from m.clic(boton(dlg, 'Aplicar'))
    yield 1.5
    # s18 leer mín y máx, cancelar
    yield from m.seg('s18')
    mn = [x for x in dlg.findChildren(QLineEdit) if x.objectName() == 'mMinLineEdit' and x.isVisible()]
    mx = [x for x in dlg.findChildren(QLineEdit) if x.objectName() == 'mMaxLineEdit' and x.isVisible()]
    if mn: m.ev('info', minimo=mn[0].text(), maximo=mx[0].text()); yield from m.ir(mn[0]); yield from m.resaltar(m.rect_global(mn[0]), 6, '1'); yield 0.8
    if mx: yield from m.ir(mx[0]); yield from m.resaltar(m.rect_global(mx[0]), 5, '2')
    yield 5.5
    yield from m.alejar()
    yield from m.clic(boton(dlg, 'Cancelar'))
    yield from m.hasta(m.fin)
    yield 1.0

QTimer.singleShot(3500, lambda: m.correr(guion(), lambda: os._exit(0)))
