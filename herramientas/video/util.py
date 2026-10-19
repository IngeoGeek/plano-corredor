# Ayudas comunes para los guiones de grabación en QGIS
import time, os
from qgis.PyQt.QtCore import QTimer, Qt, QPoint
from qgis.PyQt.QtWidgets import QApplication, QWidget, QPushButton, QDialog, QFileDialog, QLineEdit, QComboBox, QDialogButtonBox, QListView, QTreeView
from qgis.PyQt.QtTest import QTest

def hijos(w, tipo=QWidget, nombre=None, vis=True):
    return [x for x in w.findChildren(tipo) if (nombre is None or x.objectName() == nombre) and (x.isVisible() or not vis)]
def boton(w, texto):
    return [b for b in hijos(w, QPushButton) if b.text().replace('&', '') == texto][0]
def accion(menu, texto, exacto=False):
    for a in menu.actions():
        t = a.text().replace('&', '').strip().lower()
        if (t == texto.lower()) if exacto else (texto.lower() in t): return a
    raise Exception(f'sin {texto}: {[a.text() for a in menu.actions()]}')
def esperar_que(cond, maxs=15):
    t = time.time()
    while time.time() - t < maxs:
        r = cond()
        if r: return r
        yield 0.1
    raise Exception('tiempo agotado esperando')
def visibles(): return [w for w in QApplication.topLevelWidgets() if w.isVisible()]
def dialogo_nuevo(antes, tipo=QDialog):
    def f():
        for w in QApplication.topLevelWidgets():
            if isinstance(w, tipo) and w.isVisible() and w not in antes: return w
    return f
def abrir_menu(m, barra, ruta):
    """Clic en el menú de la barra y recorrido real por los submenús hasta la última opción."""
    a = [x for x in barra.actions() if ruta[0].lower() in x.text().replace('&', '').lower()][0]
    yield from m.clic(barra, barra.actionGeometry(a).center()); yield 0.5
    menu = a.menu()
    for i, t in enumerate(ruta[1:]):
        if i < len(ruta) - 2:
            act = [x for x in menu.actions() if x.menu() and t.lower() in x.text().replace('&', '').lower()][0]
        else:
            act = accion(menu, t)
        r = menu.actionGeometry(act)
        if i == len(ruta) - 2:
            yield from m.clic(menu, r.center()); yield 0.3
            yield from m.cerrar_popups(barra); return
        yield from m.ir(menu, r.center()); menu.setActiveAction(act); yield 0.7
        sub = act.menu()
        if not sub.isVisible(): sub.popup(menu.mapToGlobal(r.topRight())); yield 0.4
        yield from m.mover(sub.mapToGlobal(QPoint(20, 0)).x(), menu.mapToGlobal(r.center()).y(), 0.4)
        menu = sub
def guardar_como(m, dlg, carpeta, nombre, filtro=None):
    """En un QFileDialog: va a la carpeta, elige el tipo, escribe el nombre y pulsa Guardar."""
    fn = hijos(dlg, QLineEdit, 'fileNameEdit')[0]
    yield from m.clic(fn); QTest.keyClick(fn, Qt.Key_A, Qt.ControlModifier)
    yield from m.escribir(fn, carpeta); yield from m.tecla(fn, Qt.Key_Return, txt='Enter'); yield 1.0
    if filtro:
        cb = hijos(dlg, QComboBox, 'fileTypeCombo')
        if cb: yield from m.elegir_combo(cb[0], filtro)
    yield from m.clic(fn); QTest.keyClick(fn, Qt.Key_A, Qt.ControlModifier)
    yield from m.escribir(fn, nombre); yield 0.4
    bb = dlg.findChildren(QDialogButtonBox)[0]
    ok = [b for b in bb.buttons() if bb.buttonRole(b) == QDialogButtonBox.AcceptRole][0]
    yield from m.clic(ok)
def espera_archivo(ruta, maxs=600):
    """Espera a que el archivo exista y deje de crecer."""
    t = time.time(); prev = -1
    while time.time() - t < maxs:
        if os.path.exists(ruta):
            s = os.path.getsize(ruta)
            if s > 0 and s == prev: return True
            prev = s
        yield 0.5
    raise Exception('no apareció ' + ruta)
