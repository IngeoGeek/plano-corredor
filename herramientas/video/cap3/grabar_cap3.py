# Acciones de pantalla del capítulo 3 (exportar imágenes del plano)
import sys, os, glob, time
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap3'
sys.path.insert(0, V + '/rec')
from motor import Motor
from util import *
from qgis.utils import iface
from qgis.core import QgsProject, QgsLayoutItemMap, QgsLayoutItem, QgsLayoutItemPage
from qgis.PyQt.QtCore import QTimer, Qt, QPoint, QRect
from qgis.PyQt.QtWidgets import (QApplication, QWidget, QToolButton, QToolBar, QFileDialog, QDialog, QDockWidget, QTreeView, QTabBar,
                                 QGroupBox, QListWidget, QAbstractSpinBox, QDialogButtonBox, QScrollArea, QInputDialog, QLineEdit, QPushButton, QAbstractButton)
from qgis.PyQt.QtTest import QTest
T = '/home/osney/Plano3D/trabajo/'
for f in glob.glob(T + 'plano_*'): os.remove(f)
m = Motor(C + '/eventos.jsonl', C + '/duraciones.json')

def boton_accion(w, nombre):
    for tb in w.findChildren(QToolBar):
        for b in tb.findChildren(QToolButton):
            if b.defaultAction() and b.defaultAction().objectName() == nombre and b.isVisible(): return b
def exportar(w, nombre, ppp, seg_opciones=None, narrar_ancho=False):
    b = boton_accion(w, 'mActionExportAsImage'); antes = visibles()
    yield from m.clic(b)
    fd = yield from esperar_que(dialogo_nuevo(antes, QFileDialog), 10); yield 0.6
    yield from guardar_como(m, fd, T, nombre, 'jpg')
    ex = yield from esperar_que(lambda: (lambda d: d if d and not isinstance(d, QFileDialog) else None)(QApplication.activeModalWidget()), 15)
    yield 0.8
    if seg_opciones: yield from m.seg(seg_opciones)
    yield from m.zoom(m.rect_global(ex))
    rs = hijos(ex, QAbstractSpinBox, 'mResolutionSpinBox')[0]
    yield from m.reemplazar(rs, str(ppp))
    yield from m.resaltar(m.rect_global(rs), 3, '1')
    ws = hijos(ex, QAbstractSpinBox, 'mWidthSpinBox')
    if ws: yield from m.ir(ws[0]); yield from m.resaltar(m.rect_global(ws[0]), 3, '2'); m.ev('info', ancho=ws[0].text()); yield 1.2
    cl = [g for g in ex.findChildren(QGroupBox) if g.objectName() == 'mClipToContentGroupBox']
    if cl: yield from m.ir(cl[0], QPoint(60, 10)); cl[0].setChecked(False); yield 0.8
    oks = [x for bb in ex.findChildren(QDialogButtonBox) for x in bb.buttons() if bb.buttonRole(x) in (QDialogButtonBox.AcceptRole, QDialogButtonBox.YesRole, QDialogButtonBox.ApplyRole) and x.isVisible()]
    m.ev('info', botones_export=[(x.text(), int(bb.buttonRole(x))) for bb in ex.findChildren(QDialogButtonBox) for x in bb.buttons()])
    ok = oks[0] if oks else [x for x in hijos(ex, QPushButton) if x.text().replace('&', '') in ('Guardar', 'Save', 'Aceptar')][0]
    yield from m.alejar()
    yield from m.clic(ok); yield 1.0
    yield from m.corte_ini()
    yield from espera_archivo(T + nombre)
    yield from esperar_que(lambda: not QApplication.activeModalWidget(), 120)
    yield 0.5
    yield from m.corte_fin()
    for msg in [x for x in w.findChildren(QWidget) if type(x).__name__ == 'QgsMessageBar']: msg.clearWidgets()

def guion():
    mw = iface.mainWindow(); mw.showMaximized(); yield 2.5
    iface.messageBar().clearWidgets()
    for d in mw.findChildren(QWidget):
        if d.objectName() == 'ProcessingToolbox': d.hide()
    yield 1.0
    yield from m.destello()
    yield from m.seg('s01')
    yield from m.mover(900, 560, 1.2)
    yield from m.seg('s02')
    yield from m.mover(1000, 600, 1.0)
    # s03 abrir diseño → exportar como imagen
    yield from m.seg('s03')
    antes = visibles()
    yield from abrir_menu(m, mw.menuBar(), ['Proyecto', 'Composiciones', 'Plano_90x60'])
    dz = yield from esperar_que(lambda: iface.openLayoutDesigners(), 15)
    d = dz[0]; w = d.window(); w.showMaximized(); yield 1.2
    d.view().zoomFull(); yield 1.0
    b = boton_accion(w, 'mActionExportAsImage')
    yield from m.zoom([0, 0, 900, 140]); yield from m.ir(b); yield from m.resaltar(m.rect_global(b), 2.5, '1'); yield 1.5
    yield from m.alejar()
    # s04 + s05 hoja a 116 ppp
    yield from m.seg('s04')
    yield from exportar(w, 'plano_hoja.jpg', 116, 's05')
    # s06 hoja HD a 254 ppp
    yield from m.seg('s06')
    yield from exportar(w, 'plano_hoja_hd.jpg', 254)
    # s07 Diseño → Duplicar composición
    yield from m.seg('s07')
    yield 5.5
    antes = visibles()
    yield from abrir_menu(m, w.menuBar(), ['Diseño', 'Duplicar composición'])
    dlg = yield from esperar_que(lambda: (lambda x: x if isinstance(x, QDialog) else None)(QApplication.activeModalWidget()), 10)
    yield 0.6
    # s08 nombre Textura
    yield from m.seg('s08')
    le = hijos(dlg, QLineEdit)[0]
    yield from m.clic(le); QTest.keyClick(le, Qt.Key_A, Qt.ControlModifier); yield from m.escribir(le, 'Textura')
    bb = dlg.findChildren(QDialogButtonBox)[0]; ok = [x for x in bb.buttons() if bb.buttonRole(x) == QDialogButtonBox.AcceptRole][0]
    n0 = len(iface.openLayoutDesigners())
    yield from m.clic(ok)
    yield from esperar_que(lambda: len([x for x in iface.openLayoutDesigners() if x.masterLayout().name() == 'Textura']) > 0, 20)
    d2 = [x for x in iface.openLayoutDesigners() if x.masterLayout().name() == 'Textura'][0]; w2 = d2.window(); w2.showMaximized(); w2.raise_(); w2.activateWindow(); yield 1.5
    d2.view().zoomFull(); yield 1.0
    lay = d2.layout()
    # s09 seleccionar todo menos el mapa
    yield from m.seg('s09')
    idock = [x for x in w2.findChildren(QDockWidget) if x.objectName() == 'ItemsDock'][0]; tv = [t for t in idock.findChildren(QTreeView) if t.isVisible()][0]
    mod = tv.model(); col = 2 if mod.columnCount() > 2 else mod.columnCount() - 1
    filas = mod.rowCount()
    yield from m.zoom(m.rect_global(idock))
    tv.scrollToTop(); yield 0.3
    yield from m.clic(tv.viewport(), tv.visualRect(mod.index(0, col)).center())
    yield 0.4
    yield from m.ir(tv.viewport())
    for _ in range(30):
        if tv.visualRect(mod.index(filas - 1, col)).bottom() < tv.viewport().height(): break
        yield from m.rueda(tv, tv.viewport().rect().center(), 1)
    yield 0.3
    yield from m.clic(tv.viewport(), tv.visualRect(mod.index(filas - 1, col)).center(), mod=Qt.ShiftModifier)
    m.ev('tecla', txt='Mayús + clic'); yield 0.6
    idx = [mod.index(r, col) for r in range(filas) if str(mod.index(r, col).data()) == 'Mapa principal'][0]
    tv.scrollTo(idx); yield 0.4
    yield from m.clic(tv.viewport(), tv.visualRect(idx).center(), mod=Qt.ControlModifier)
    m.ev('tecla', txt='Ctrl + clic'); yield 0.6
    # s10 Suprimir
    yield from m.seg('s10')
    yield 0.6
    yield from m.tecla(tv, Qt.Key_Delete, txt='Supr')
    yield 1.0
    resto = lambda: [i for i in lay.items() if isinstance(i, QgsLayoutItem) and not isinstance(i, (QgsLayoutItemMap, QgsLayoutItemPage))]
    m.ev('info', quedan=len(resto()))
    if len(resto()) > 0:
        [a for a in w2.findChildren(__import__('qgis.PyQt.QtWidgets', fromlist=['QAction']).QAction) if a.objectName() == 'mActionDeleteSelection'][0].trigger()
    yield 1.0
    yield from m.alejar()
    # s11 mapa → cuadrículas → quitar
    yield from m.seg('s11')
    mapa = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)][0]
    idx = [mod.index(r, col) for r in range(mod.rowCount()) if str(mod.index(r, col).data()) == 'Mapa principal'][0]
    yield from m.clic(tv.viewport(), tv.visualRect(idx).center()); yield 0.6
    for tb in w2.findChildren(QTabBar):
        for i in range(tb.count()):
            if 'Propiedades del elemento' in tb.tabText(i) and tb.isVisible():
                yield from m.clic(tb, tb.tabRect(i).center())
                if tb.currentIndex() != i: tb.setCurrentIndex(i)
    yield 0.8
    dock = [x for x in w2.findChildren(QDockWidget) if x.objectName() == 'ItemDock'][0]
    gg = [g for g in dock.findChildren(QGroupBox) if g.objectName() == 'mGridGroupBox' and g.isVisible()][0]
    sa = gg.parentWidget()
    while sa is not None and not isinstance(sa, QScrollArea): sa = sa.parentWidget()
    yield from m.zoom(m.rect_global(dock))
    yield from m.bajar_hasta(sa, gg, 40)
    gl = [x for x in gg.findChildren(QListWidget) if x.objectName() == 'mGridListWidget'][0]
    if not gl.isVisible():
        cb = [b for b in gg.findChildren(QToolButton) if b.objectName() == 'collapseButton'][0]
        yield from m.clic(cb); yield 0.6
        if not gl.isVisible():
            from qgis.gui import QgsCollapsibleGroupBoxBasic
            import sip; sip.cast(gg, QgsCollapsibleGroupBoxBasic).setCollapsed(False); yield 0.4
    yield from m.bajar_hasta(sa, gg, 40)
    if gl.count():
        yield from m.clic(gl.viewport(), gl.visualItemRect(gl.item(0)).center()); yield 0.5
        yield from m.resaltar(m.rect_global(gl), 3, '1')
    rm = [b for b in gg.findChildren(QAbstractButton) if b.isVisible() and 'remove' in b.objectName().lower()]
    m.ev('info', botones=[b.objectName() for b in gg.findChildren(QAbstractButton) if b.isVisible()])
    if rm:
        yield from m.clic(rm[0]); yield from m.resaltar(m.rect_global(rm[0]), 2.5, '2')
    yield 0.6
    # s12 desmarcar Marco
    yield from m.seg('s12')
    fg = [g for g in dock.findChildren(QGroupBox) if g.objectName() == 'mFrameGroupBox' and g.isVisible()][0]
    yield from m.bajar_hasta(sa, fg, 120)
    chk = [b for b in fg.findChildren(QAbstractButton) if b.isVisible() and b.objectName() != 'collapseButton' and b.mapTo(fg, QPoint(0, 0)).y() < 20 and type(b).__name__ == 'QCheckBox']
    if chk: yield from m.clic(chk[0])
    else: yield from m.clic(fg, QPoint(30, 10))
    if fg.isChecked(): fg.setChecked(False)
    yield from m.resaltar(m.rect_global(fg, QRect(0, 0, fg.width(), 24)), 2.5, '3')
    yield 0.5
    # s13 pestaña Diseño → ajustar al contenido
    yield from m.seg('s13')
    for tb in w2.findChildren(QTabBar):
        for i in range(tb.count()):
            if tb.tabText(i) == 'Diseño' and tb.isVisible():
                yield from m.clic(tb, tb.tabRect(i).center())
                if tb.currentIndex() != i: tb.setCurrentIndex(i)
    yield 0.8
    ldock = [x for x in w2.findChildren(QDockWidget) if x.objectName() == 'LayoutDock'][0]
    rp = [b for b in ldock.findChildren(QPushButton) if b.objectName() == 'mResizePageButton'][0]
    sa2 = rp.parentWidget()
    while sa2 is not None and not isinstance(sa2, QScrollArea): sa2 = sa2.parentWidget()
    if not rp.isVisible():
        gbx = rp.parentWidget()
        while gbx is not None and not isinstance(gbx, QGroupBox): gbx = gbx.parentWidget()
        if gbx is not None:
            yield from m.bajar_hasta(sa2, gbx, 40)
            cb = [b for b in gbx.findChildren(QToolButton) if b.objectName() == 'collapseButton']
            if cb: yield from m.clic(cb[0]); yield 0.6
            if not rp.isVisible():
                from qgis.gui import QgsCollapsibleGroupBoxBasic
                import sip; sip.cast(gbx, QgsCollapsibleGroupBoxBasic).setCollapsed(False); yield 0.4
    yield from m.bajar_hasta(sa2, rp, 300)
    for nm in ('mTopMarginSpinBox', 'mRightMarginSpinBox', 'mBottomMarginSpinBox', 'mLeftMarginSpinBox'):
        x = [s for s in ldock.findChildren(QAbstractSpinBox) if s.objectName() == nm and s.isVisible()]
        if x: yield from m.ir(x[0], dur=0.4); yield 0.3
    yield from m.clic(rp); yield from m.resaltar(m.rect_global(rp), 3, '2')
    yield 1.0
    yield from m.alejar()
    d2.view().zoomFull(); yield 1.0
    # s14 exportar plano_mapa.jpg a 160 ppp
    yield from m.seg('s14')
    yield from exportar(w2, 'plano_mapa.jpg', 160)
    yield from m.hasta(m.fin)
    yield 1.0
    from PIL import Image
    for n in ('plano_hoja.jpg', 'plano_hoja_hd.jpg', 'plano_mapa.jpg'):
        try: m.ev('info', archivo=n, tam=list(Image.open(T + n).size))
        except Exception as e: m.ev('info', archivo=n, err=str(e))

QTimer.singleShot(3500, lambda: m.correr(guion(), lambda: os._exit(0)))
