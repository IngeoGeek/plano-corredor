import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm')
from qcap_base import *
_st = QTimer.singleShot
class _T:
    @staticmethod
    def singleShot(ms, fn): _st(ms, seguro(fn))

from qgis.core import QgsLayoutItemMap, QgsRectangle, QgsCoordinateReferenceSystem
from qgis.gui import QgsCollapsibleGroupBoxBasic, QgsMapLayerComboBox, QgsFieldComboBox, QgsExtentWidget, QgsExtentGroupBox, QgsScaleWidget
from qgis.PyQt.QtWidgets import QDockWidget, QScrollArea, QGroupBox, QComboBox, QFileDialog, QToolButton, QTreeWidget, QLineEdit, QSpinBox
import processing
T = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/trabajo/'
G = {}
RECT = QgsRectangle(4885966.641, 2241436.912, 4928420.741, 2278431.036); CRS = QgsCoordinateReferenceSystem('EPSG:9377')
def por_nombre(w, n, tipo=QWidget): return [x for x in w.findChildren(tipo) if x.objectName() == n]
EXT = '4885966.641,4928420.741,2241436.912,2278431.036 [EPSG:9377]'
def tops(): return [w for w in QApplication.topLevelWidgets() if w.isVisible() and isinstance(w, QDialog)]
@paso(3000)
def p0():
    ventana(); iface.mapCanvas().setExtent(RECT)
    G['curvas'] = QgsProject.instance().mapLayersByName('Curvas de nivel')[0]
    lay = QgsProject.instance().layoutManager().layoutByName('Plano_90x60_Corredor_Carbonifero'); G['lay'] = lay
    G['mapa'] = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap) and i.displayName() == 'Mapa principal'][0]
def p1():
    d = processing.createAlgorithmDialog('qgis:tininterpolation', {'METHOD': 0, 'EXTENT': EXT, 'PIXEL_SIZE': 30, 'OUTPUT': T + 'dem_tin.tif'})
    d.setGeometry(310, 110, 980, 760); d.show()
    d.findChildren(QgsMapLayerComboBox)[0].setLayer(G['curvas'])
    def b():
        d.findChildren(QgsFieldComboBox)[0].setField('elev'); por_nombre(d, 'btnAdd', QToolButton)[0].click()
        _T.singleShot(300, c)
    def c():
        for cb in d.findChildren(QComboBox):
            if cb.findText('Líneas de estructura') >= 0 and cb.isVisible(): cb.setCurrentIndex(cb.findText('Líneas de estructura'))
        for ew in d.findChildren(QgsExtentWidget): ew.setOutputExtentFromUser(RECT, CRS)
        _T.singleShot(800, tomar)
    def tomar():
        cmb = d.findChildren(QgsMapLayerComboBox)[0]; tree = por_nombre(d, 'layersTree', QTreeWidget)[0]
        ext = por_nombre(d, 'mCondensedLineEdit')[0]; px = por_nombre(d, 'mCellXSpinBox')[0]
        foto('q06_tin', None, [rect(cmb) + ['1'], rect(tree) + ['2'], rect(ext) + ['3'], rect(px) + ['4']]); volcar(d, 'dump_q06b.txt'); d.close()
    _T.singleShot(300, b)
def p3():
    r = iface.addRasterLayer(T + 'dem90.tif', 'dem90')
    d = processing.createAlgorithmDialog('gdal:warpreproject', {'INPUT': r, 'RESAMPLING': 3, 'TARGET_RESOLUTION': 30, 'TARGET_EXTENT': EXT, 'OUTPUT': T + 'dem_suave.tif'})
    d.setGeometry(310, 60, 980, 930); d.show()
    for bt in por_nombre(d, 'collapseButton', QToolButton): bt.click()
    def tomar():
        cs = [c for c in d.findChildren(QComboBox) if c.isVisible() and 'Spline' in c.currentText()]
        sp = [c for c in d.findChildren(QWidget) if type(c).__name__ == 'QgsDoubleSpinBox' and c.isVisible() and '30.0' in c.text()]
        ex = [c for c in d.findChildren(QgsExtentWidget) if c.isVisible()]
        volcar(d, 'dump_q08b.txt'); foto('q08_combar30', None, [rect(cs[0]) + ['1'], rect(sp[0]) + ['2']] + ([rect(ex[0]) + ['3']] if ex else [])); d.close()
    _T.singleShot(1800, tomar)
@paso(4500)
def p6():
    def f(n=0):
        ws = [x for x in QApplication.topLevelWidgets() if x.isVisible() and 'imagen' in x.windowTitle() and 'Guardar mapa' in x.windowTitle()]
        if not ws:
            if n < 10: _T.singleShot(700, lambda: f(n + 1))
            return
        w = ws[0]; w.move(330, 120)
        from qgis.PyQt import sip
        eg = por_nombre(w, 'mExtentGroupBox', QGroupBox)[0]
        sw = sip.cast(por_nombre(w, 'mScaleWidget')[0], QgsScaleWidget); G['sw'] = sw
        def g():
            from qgis.PyQt.QtTest import QTest
            from qgis.PyQt.QtCore import Qt as Q
            def tipear(wd, txt):
                wd.setFocus(); wd.selectAll(); QTest.keyClicks(wd, txt); QTest.keyClick(wd, Q.Key_Tab)
            sc = [x for x in w.findChildren(QLineEdit) if x.text().startswith('1:')][0]
            tipear(sc, '1:65000')
            rs = por_nombre(w, 'mResolutionSpinBox', QSpinBox)[0]; tipear(rs.lineEdit(), '160')
            for n, v in (('mXMinLineEdit', '4885966.641'), ('mXMaxLineEdit', '4928420.741'), ('mYMinLineEdit', '2241436.912'), ('mYMaxLineEdit', '2278431.036')):
                tipear(por_nombre(w, n, QLineEdit)[0], v)
            ow = por_nombre(w, 'mOutputWidthSpinBox', QSpinBox)[0]; tipear(ow.lineEdit(), '4114')
            _T.singleShot(800, h)
        def h():
            volcar(w, 'dump_q11b.txt')
            foto('q11_mapa_imagen', None, [rect(eg) + ['1'], rect(G['sw']) + ['2'], rect(por_nombre(w, 'mResolutionSpinBox', QSpinBox)[0]) + ['3'], rect(por_nombre(w, 'mOutputWidthSpinBox', QSpinBox)[0]) + ['4']])
            w.reject()
        _T.singleShot(600, g)
    _T.singleShot(2500, f)
    _T.singleShot(10, lambda: [a for a in iface.mainWindow().findChildren(QAction) if a.objectName() == 'mActionSaveMapAsImage'][0].trigger())
def p7():
    d = iface.openLayoutDesigner(G['lay']); G['d'] = d; w = d.window(); w.setGeometry(0, 0, 1600, 1000); w.show()
    acc = [a for a in w.findChildren(QAction) if a.objectName() == 'mActionExportAsImage'][0]; G['acc'] = acc
    btn = [b for b in w.findChildren(QToolButton) if b.defaultAction() is acc and b.isVisible()]
    G['btn'] = btn
    _T.singleShot(1500, lambda: foto('q12_exportar_boton', [0, 0, 1000, 160], [rect(btn[0]) + ['1']] if btn else []))
def p7b():
    p7()
def p8():
    def f():
        fd = [x for x in QApplication.topLevelWidgets() if isinstance(x, QFileDialog) and x.isVisible()]
        open(OUT + 'dump_tops2.txt', 'w').write(repr([type(x).__name__ + ':' + x.windowTitle() for x in tops()]))
        if fd:
            fd[0].selectFile(T + 'plano_hoja_hd.jpg')
            from qgis.PyQt.QtWidgets import QDialogButtonBox
            bb = fd[0].findChildren(QDialogButtonBox)[0]; bb.buttons()[0].click()
        _T.singleShot(2000, g)
    def g():
        ds = [x for x in tops()]
        open(OUT + 'dump_tops3.txt', 'w').write(repr([type(x).__name__ + ':' + x.windowTitle() for x in ds]))
        for x in ds:
            if 'opciones' in x.windowTitle().lower():
                x.move(500, 150); volcar(x, 'dump_q12.txt'); rs = por_nombre(x, 'mResolutionSpinBox', QSpinBox)[0]; rs.setValue(254); G['rs'] = (rs, por_nombre(x, 'mWidthSpinBox', QSpinBox)[0], por_nombre(x, 'mClipToContentGroupBox', QGroupBox)[0])
                _T.singleShot(600, lambda x=x: (foto('q12_opciones', None, [rect(G['rs'][0]) + ['1'], rect(G['rs'][1]) + ['2'], rect(G['rs'][2]) + ['3']]), x.reject()))
    _T.singleShot(2000, f)
    _T.singleShot(10, G['acc'].trigger)
def p9():
    from qgis.gui import QgsVectorLayerSaveAsDialog
    l = QgsProject.instance().mapLayersByName('Proyectos piloto')[0]
    d = QgsVectorLayerSaveAsDialog(l); d.setGeometry(310, 30, 760, 960); d.show()
    fm = por_nombre(d, 'mFormatComboBox', QComboBox)[0]; fm.setCurrentIndex(fm.findData('CSV'))
    def g():
        geo = por_nombre(d, 'GEOMETRY', QComboBox)[0]; geo.setCurrentIndex(geo.findText('AS_XY'))
        fn = [x for x in d.findChildren(QLineEdit) if x.isVisible()][0]
        try:
            from qgis.gui import QgsFileWidget
            fw = d.findChildren(QgsFileWidget)[0]; fw.setFilePath('C:/Plano3D/sitio/etiquetas/proyectos_piloto.csv')
        except Exception: pass
        _T.singleShot(700, lambda: (foto('q14_csv', None, [rect(fm) + ['1'], rect(d.findChildren(QgsFileWidget)[0]) + ['2'], rect(geo) + ['3']]), d.close()))
    _T.singleShot(800, g)
arrancar()
