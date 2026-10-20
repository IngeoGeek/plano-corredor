# Utilidades para capturar QGIS bajo Xvfb: pasos encadenados, captura de pantalla completa y rectángulos a resaltar
import json, os, sys
from qgis.PyQt.QtCore import QTimer, QRect, QPoint, Qt
from qgis.PyQt.QtWidgets import QApplication, QWidget, QAction, QMenu, QDialog, QAbstractButton, QLabel, QGroupBox
from qgis.PyQt.QtGui import QGuiApplication
from qgis.utils import iface
from qgis.core import QgsProject
OUT = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/cap/'
MARCAS = {}
PASOS = []
def paso(ms=1500):
    def deco(f): PASOS.append((f, ms)); return f
    return deco
def correr(i=0):
    if i >= len(PASOS):
        try: viejo = json.load(open(OUT + 'marcas.json'))
        except Exception: viejo = {}
        viejo.update(MARCAS); json.dump(viejo, open(OUT + 'marcas.json', 'w'), ensure_ascii=False, indent=1); os._exit(0)
    f, ms = PASOS[i]
    try: f()
    except Exception as e:
        import traceback; open(OUT + 'errores.txt', 'a').write(f'{f.__name__}: {traceback.format_exc()}\n')
    QTimer.singleShot(ms, lambda: correr(i + 1))
def rect(w):
    p = w.mapToGlobal(QPoint(0, 0)); return [p.x(), p.y(), w.width(), w.height()]
def foto(nombre, recorte=None, marcas=(), base=None):
    if base is not None:
        img = base.grab(); g = base.mapToGlobal(QPoint(0, 0)); off = [g.x(), g.y()]
    else:
        img = QGuiApplication.primaryScreen().grabWindow(0); off = [0, 0]
    if recorte: img = img.copy(QRect(*recorte)); off = [off[0] + recorte[0], off[1] + recorte[1]]
    img.save(OUT + nombre + '.png')
    MARCAS[nombre] = [[m[0] - off[0], m[1] - off[1], m[2], m[3]] + list(m[4:]) for m in marcas]
def hijos(w, tipo=QWidget):
    return w.findChildren(tipo)
def volcar(w, archivo):
    with open(OUT + archivo, 'w') as f:
        for c in w.findChildren(QWidget):
            if not c.isVisible(): continue
            t = ''
            for a in ('text', 'title', 'currentText'):
                if hasattr(c, a):
                    try: t = getattr(c, a)(); break
                    except Exception: pass
            f.write(f'{type(c).__name__}\t{c.objectName()}\t{str(t)[:50]!r}\t{rect(c)}\n')
def ventana():
    mw = iface.mainWindow(); mw.setGeometry(0, 0, 1600, 1000); mw.showNormal(); mw.setGeometry(0, 0, 1600, 1000)
    iface.messageBar().clearWidgets()
def modal(): return QApplication.activeModalWidget()
def cerrar_modales():
    for _ in range(4):
        m = QApplication.activeModalWidget()
        if m: m.reject()
def arrancar(): QTimer.singleShot(7000, correr)
def seguro(fn):
    def w(*a):
        try: return fn(*a)
        except Exception:
            import traceback; open(OUT + 'errores.txt', 'a').write(f'{getattr(fn, "__name__", "?")}: {traceback.format_exc()}\n')
    return w
