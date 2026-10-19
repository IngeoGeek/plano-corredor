# Acciones de pantalla del capítulo 1 (se ejecuta dentro de QGIS con --code)
import sys, os, json
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap1'
sys.path.insert(0, V + '/rec')
from motor import Motor
from qgis.utils import iface
from qgis.core import QgsProject, QgsLayoutItemMap
from qgis.PyQt.QtCore import QTimer, Qt, QPoint, QPointF, QRect
from qgis.PyQt.QtGui import QTextCursor, QContextMenuEvent, QKeySequence
from qgis.PyQt.QtWidgets import (QApplication, QWidget, QFileDialog, QLineEdit, QListView, QTreeView, QTextEdit, QDialogButtonBox,
                                 QPushButton, QTabBar, QScrollArea, QGroupBox, QDockWidget, QMenu, QToolButton, QAbstractButton)
m = Motor(C + '/eventos.jsonl', C + '/duraciones.json')
PROY = '/home/osney/Plano3D/Corredor_Carbonifero_Santander.qgz'

def por_nombre(w, n, tipo=QWidget): return [x for x in w.findChildren(tipo) if x.objectName() == n]
def accion_menu(menu, texto, exacto=False):
    for a in menu.actions():
        t = a.text().replace('&', '').strip().lower()
        if (t == texto.lower()) if exacto else (texto.lower() in t): return a
    raise Exception('sin acción ' + texto + ': ' + str([a.text() for a in menu.actions()]))
def esperar_que(cond, maxs=10):
    import time; t = time.time()
    while time.time() - t < maxs:
        r = cond()
        if r: return r
        yield 0.1
    raise Exception('tiempo agotado esperando')

def guion():
    mw = iface.mainWindow(); mw.showMaximized(); yield 2.5
    iface.messageBar().clearWidgets(); yield 0.5
    yield from m.destello()
    mb = mw.menuBar(); mproy = [a for a in mb.actions() if a.menu() and a.menu().objectName() == 'mProjectMenu'][0]
    # s01: pantalla de inicio
    yield from m.seg('s01')
    yield from m.mover(960, 600, 1.2)
    # s02: Proyecto → Abrir
    yield from m.seg('s02')
    yield 0.6
    yield from m.clic(mb, mb.actionGeometry(mproy).center())
    yield 0.6
    menu = mproy.menu(); ab = [a for a in menu.actions() if a.objectName() == 'mActionOpenProject'][0]
    yield from m.clic(menu, menu.actionGeometry(ab).center())
    dlg = yield from esperar_que(lambda: QApplication.activeModalWidget() if isinstance(QApplication.activeModalWidget(), QFileDialog) else None)
    yield 0.6
    # s03: ir a la carpeta
    yield from m.seg('s03')
    fn = por_nombre(dlg, 'fileNameEdit', QLineEdit)[0]
    yield from m.clic(fn)
    yield from m.escribir(fn, '/home/osney/Plano3D/')
    yield from m.tecla(fn, Qt.Key_Return, txt='Enter')
    yield 1.2
    # s04: elegir el .qgz y Abrir
    yield from m.seg('s04')
    lv = [v for v in dlg.findChildren(QListView) if v.isVisible() and v.objectName() == 'listView'] or [v for v in dlg.findChildren(QTreeView) if v.isVisible()]
    lv = lv[0]; mod = lv.model(); raiz = lv.rootIndex(); idx = None
    for r in range(mod.rowCount(raiz)):
        i = mod.index(r, 0, raiz)
        if str(i.data()).endswith('.qgz'): idx = i
    rc = lv.visualRect(idx)
    yield from m.clic(lv.viewport(), rc.center())
    yield 0.8
    bb = dlg.findChildren(QDialogButtonBox)[0]
    bt = [b for b in bb.buttons() if bb.buttonRole(b) == QDialogButtonBox.AcceptRole][0]
    yield from m.clic(bt)
    yield from esperar_que(lambda: QgsProject.instance().fileName() != '', 20)
    yield 2.5
    iface.messageBar().clearWidgets()
    # s05: la esquina con el SRC
    yield from m.seg('s05')
    sb = mw.statusBar(); crs = por_nombre(sb, 'mOntheFlyProjectionStatusButton')[0]
    yield 1.5
    yield from m.zoom([1340, 960, 580, 120])
    yield from m.ir(crs)
    yield 0.4
    yield from m.resaltar(m.rect_global(crs), 7, '1')
    # s06: si está en grados…
    yield from m.seg('s06')
    yield from m.mover(crs.mapToGlobal(crs.rect().center()).x() - 40, crs.mapToGlobal(crs.rect().center()).y() - 6, 1.0)
    yield 2.0
    yield from m.ir(crs)
    # s07: clic en el botón
    yield from m.seg('s07')
    yield 4.5
    yield from m.clic(crs, mover=False)
    yield from m.alejar()
    dprop = yield from esperar_que(lambda: QApplication.activeModalWidget(), 10)
    yield 0.8
    # s08: propiedades del proyecto → SRC
    yield from m.seg('s08')
    te = por_nombre(dprop, 'teProjection', QTextEdit)[0]
    yield 2.5
    yield from m.ir(te.viewport())
    yield from m.resaltar(m.rect_global(te), 4)
    # s09: bajar hasta Proj4
    yield from m.seg('s09')
    yield from m.zoom(m.rect_global(te), None)
    doc = te.document(); bloque = None
    for i in range(doc.blockCount()):
        b = doc.findBlockByNumber(i)
        if '+proj=' in b.text(): bloque = b
    sbv = te.verticalScrollBar()
    for _ in range(25):
        c = QTextCursor(bloque); r = te.cursorRect(c)
        if r.bottom() < te.viewport().height() - 20 or sbv.value() >= sbv.maximum(): break
        yield from m.rueda(te, te.viewport().rect().center(), 1)
    yield 0.6
    # s10: seleccionar y copiar
    yield from m.seg('s10')
    c0 = QTextCursor(bloque); c1 = QTextCursor(bloque); c1.movePosition(QTextCursor.EndOfBlock)
    p0 = te.cursorRect(c0).center(); p1 = te.cursorRect(c1).center()
    if p1.x() > te.viewport().width() - 5: p1.setX(te.viewport().width() - 10)
    yield from m.ir(te.viewport(), p0, 0.6)
    yield 0.3
    sel = QTextCursor(bloque); n = len(bloque.text())
    pasos = 24
    g0 = te.viewport().mapToGlobal(p0); g1 = te.viewport().mapToGlobal(QPoint(p1.x(), p1.y() + (te.cursorRect(c1).center().y() - p0.y())))
    for k in range(1, pasos + 1):
        s = k / pasos
        from qgis.PyQt.QtGui import QCursor
        QCursor.setPos(int(g0.x() + (g1.x() - g0.x()) * s), int(g0.y() + (g1.y() - g0.y()) * s))
        sel.setPosition(bloque.position()); sel.setPosition(bloque.position() + int(n * s), QTextCursor.KeepAnchor); te.setTextCursor(sel)
        yield 0.05
    yield 0.4
    yield from m.tecla(te, Qt.Key_C, Qt.ControlModifier, txt='Ctrl + C')
    yield from m.resaltar(m.rect_global(te.viewport(), QRect(0, te.cursorRect(c0).top() - 3, te.viewport().width(), te.cursorRect(c1).bottom() - te.cursorRect(c0).top() + 6)), 6, '1')
    m.ev('portapapeles', txt=QApplication.clipboard().text())
    # s11: cerrar con Cancelar
    yield from m.seg('s11')
    yield from m.alejar()
    yield 4.0
    bb = [b for b in dprop.findChildren(QDialogButtonBox) if b.isVisible()][0]
    cancel = [b for b in bb.buttons() if bb.buttonRole(b) == QDialogButtonBox.RejectRole][0]
    yield from m.clic(cancel)
    yield 1.0
    # s12: Proyecto → Composiciones → diseño
    yield from m.seg('s12')
    yield 0.5
    yield from m.clic(mb, mb.actionGeometry(mproy).center())
    yield 0.6
    comp = accion_menu(menu, 'Composiciones', True)
    yield from m.ir(menu, menu.actionGeometry(comp).center())
    yield 0.4
    menu.setActiveAction(comp); yield 0.8
    sub = comp.menu(); dis = accion_menu(sub, 'Plano_90x60')
    if not sub.isVisible(): sub.popup(menu.mapToGlobal(menu.actionGeometry(comp).topRight())); yield 0.5
    yield from m.mover(sub.mapToGlobal(sub.actionGeometry(dis).topLeft()).x() + 20, sub.mapToGlobal(sub.actionGeometry(dis).center()).y(), 0.5)
    yield from m.clic(sub, sub.actionGeometry(dis).center())
    dz = yield from esperar_que(lambda: iface.openLayoutDesigners(), 15)
    d = dz[0]; w = d.window(); w.showMaximized(); yield 1.5
    lay = d.layout(); view = d.view(); view.zoomFull(); yield 1.5
    # s13: panel Elementos → Mapa principal
    yield from m.seg('s13')
    idock = por_nombre(w, 'ItemsDock', QDockWidget)[0]; tv = [t for t in idock.findChildren(QTreeView) if t.isVisible()][0]
    mod = tv.model(); idx = None
    for r in range(mod.rowCount()):
        for col in range(mod.columnCount()):
            i = mod.index(r, col)
            if str(i.data()) == 'Mapa principal': idx = i
    yield 1.5
    yield from m.zoom(m.rect_global(idock), None)
    yield from m.ir(tv.viewport())
    for _ in range(30):
        r = tv.visualRect(idx)
        if 20 < r.center().y() < tv.viewport().height() - 20: break
        yield from m.rueda(tv, tv.viewport().rect().center(), 1)
    yield 0.4
    yield from m.clic(tv.viewport(), tv.visualRect(idx).center())
    yield 0.6
    yield from m.alejar()
    # s14: pestaña Propiedades del elemento, escala
    yield from m.seg('s14')
    tab = None
    for tb in w.findChildren(QTabBar):
        for i in range(tb.count()):
            if 'Propiedades del elemento' in tb.tabText(i) and tb.isVisible(): tab = (tb, i)
    if tab:
        yield from m.clic(tab[0], tab[0].tabRect(tab[1]).center())
        if tab[0].currentIndex() != tab[1]: tab[0].setCurrentIndex(tab[1])
    else:
        idk = por_nombre(w, 'ItemDock', QDockWidget)[0]; idk.raise_()
    yield 1.0
    dock = por_nombre(w, 'ItemDock', QDockWidget)[0]
    esc = [x for x in dock.findChildren(QLineEdit) if x.objectName() == 'mScaleLineEdit' and x.isVisible()][0]
    yield from m.zoom(m.rect_global(dock), None)
    yield from m.ir(esc)
    yield from m.resaltar(m.rect_global(esc), 4.5, '1')
    # s15: extensión
    yield from m.seg('s15')
    sa = esc.parentWidget()
    while sa is not None and not isinstance(sa, QScrollArea): sa = sa.parentWidget()
    ext = [g for g in dock.findChildren(QGroupBox) if g.objectName() == 'mExtentsCheckBox' and g.isVisible()][0]
    yield from m.bajar_hasta(sa, ext, 60)
    yield from m.ir(ext)
    yield from m.resaltar(m.rect_global(ext), 6, '2')
    # s16: Posición y tamaño
    yield from m.seg('s16')
    pos = [g for g in dock.findChildren(QGroupBox) if g.objectName() == 'mGeneralOptionsGroupBox' and g.isVisible()][0]
    yield from m.bajar_hasta(sa, pos, 60)
    btn = [b for b in pos.findChildren(QToolButton) if b.objectName() == 'collapseButton' and b.isVisible()]
    xs = [x for x in pos.findChildren(QWidget) if x.objectName() == 'mXPosSpin'][0]
    if not xs.isVisible():
        yield from m.clic(btn[0])
        yield 0.5
        if not xs.isVisible():
            from qgis.gui import QgsCollapsibleGroupBoxBasic
            import sip; sip.cast(pos, QgsCollapsibleGroupBoxBasic).setCollapsed(False)
    yield 0.6
    yield from m.bajar_hasta(sa, pos, 40)
    # s17: punto de referencia y medidas
    yield from m.seg('s17')
    yield from m.resaltar(m.rect_global(pos), 9, '1')
    ref = [b for b in pos.findChildren(QAbstractButton) if b.objectName() in ('mUpperLeftCheckBox', 'mUpperLeftRadioButton') and b.isVisible()]
    if ref: yield from m.ir(ref[0])
    yield 4.0
    for nm in ('mXPosSpin', 'mYPosSpin', 'mWidthSpin', 'mHeightSpin'):
        x = [s for s in pos.findChildren(QWidget) if s.objectName() == nm and s.isVisible()]
        if x: yield from m.ir(x[0], dur=0.5); yield 0.5
    yield from m.alejar()
    # s18: clic derecho en la hoja → Propiedades de página
    yield from m.seg('s18')
    pt = view.mapFromScene(QPointF(9, 300)); vp = view.viewport()
    yield 2.0
    yield from m.ir(vp, pt)
    yield 0.4
    gx, gy = m.centro(vp, pt); m.ev('clic', x=gx, y=gy, der=True)
    from qgis.PyQt.QtTest import QTest
    QTimer.singleShot(0, lambda: QTest.mousePress(vp, Qt.RightButton, Qt.NoModifier, pt))
    yield 0.8
    if not QApplication.activePopupWidget():
        QTest.mouseRelease(vp, Qt.RightButton, Qt.NoModifier, pt)
        QTimer.singleShot(0, lambda: QApplication.sendEvent(view, QContextMenuEvent(QContextMenuEvent.Mouse, view.mapFromGlobal(vp.mapToGlobal(pt)), vp.mapToGlobal(pt))))
    pm = yield from esperar_que(lambda: QApplication.activePopupWidget(), 5)
    yield 0.6
    ap = accion_menu(pm, 'Propiedades de la página')
    yield from m.clic(pm, pm.actionGeometry(ap).center())
    yield 1.0
    # s19: anchura y altura
    yield from m.seg('s19')
    ws = [x for x in dock.findChildren(QWidget) if x.objectName() == 'mWidthSpin' and x.isVisible()]
    hs = [x for x in dock.findChildren(QWidget) if x.objectName() == 'mHeightSpin' and x.isVisible()]
    yield from m.zoom(m.rect_global(dock), None)
    if ws: yield from m.ir(ws[0]); yield from m.resaltar(m.rect_global(ws[0]), 5, '1'); yield 0.8
    if hs: yield from m.ir(hs[0]); yield from m.resaltar(m.rect_global(hs[0]), 4.2, '2')
    yield from m.hasta(m.fin)
    yield from m.alejar()
    yield 1.5

def salir():
    os._exit(0)
QTimer.singleShot(3500, lambda: m.correr(guion(), salir))
