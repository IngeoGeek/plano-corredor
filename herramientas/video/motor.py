# Motor de grabación dentro de QGIS: mueve el cursor de verdad, hace clics y teclas reales sobre los widgets,
# y anota cada evento con su hora para la posproducción (resaltados, anillos de clic, zoom, audio).
import json, os, time, math
from qgis.PyQt.QtCore import QTimer, QPoint, QRect, Qt, QEvent, QPointF
from qgis.PyQt.QtGui import QCursor, QColor, QPalette, QMouseEvent, QWheelEvent
from qgis.PyQt.QtWidgets import QApplication, QWidget
from qgis.PyQt.QtTest import QTest

class Motor:
    def __init__(self, log, duraciones, hueco=0.7):
        self.log = open(log, 'w'); self.dur = json.load(open(duraciones)); self.hueco = hueco
        self.fin = 0; self.gen = None

    # ---------- registro ----------
    def ev(self, tipo, **k):
        k.update(t=time.time(), tipo=tipo); self.log.write(json.dumps(k, ensure_ascii=False) + '\n'); self.log.flush()

    # ---------- planificador de generadores ----------
    def correr(self, gen, al_final=None):
        self.gen = gen; self.al_final = al_final; QTimer.singleShot(0, self._paso)
    def _paso(self):
        try:
            w = next(self.gen)
        except StopIteration:
            self.ev('fin'); self.log.close()
            if self.al_final: self.al_final()
            return
        except Exception:
            import traceback; self.ev('error', txt=traceback.format_exc()); self.log.close()
            if self.al_final: self.al_final()
            return
        QTimer.singleShot(max(0, int((w or 0) * 1000)), self._paso)

    # ---------- utilidades de tiempo ----------
    def esperar(self, s):
        yield s
    def hasta(self, t):
        while time.time() < t:
            yield min(0.05, t - time.time())

    # ---------- segmentos de narración ----------
    def seg(self, sid):
        """Empieza un segmento: anota la hora; el audio sid.wav se pondrá aquí en la edición."""
        if self.fin: yield from self.hasta(self.fin)
        self.ev('seg', id=sid); self.fin = time.time() + self.dur[sid] + self.hueco
        yield 0.05

    # ---------- calibración (destello rojo para alinear video y registro) ----------
    def destello(self):
        w = QWidget(); w.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        w.setAutoFillBackground(True); p = w.palette(); p.setColor(QPalette.Window, QColor(255, 0, 0)); w.setPalette(p)
        w.setGeometry(0, 0, 1920, 1080); w.show(); w.raise_(); QApplication.processEvents()
        yield 0.25
        self.ev('destello'); yield 0.5
        w.close(); w.deleteLater(); yield 0.5

    # ---------- cursor ----------
    def mover(self, x, y, dur=0.75):
        p0 = QCursor.pos(); x0, y0 = p0.x(), p0.y(); n = max(2, int(dur * 60))
        dist = math.hypot(x - x0, y - y0)
        if dist < 3: return
        dur = min(dur, 0.25 + dist / 1400); n = max(2, int(dur * 60))
        for i in range(1, n + 1):
            s = i / n; e = s * s * (3 - 2 * s)
            QCursor.setPos(int(round(x0 + (x - x0) * e)), int(round(y0 + (y - y0) * e)))
            yield dur / n
    def centro(self, w, local=None):
        if local is None: local = w.rect().center()
        g = w.mapToGlobal(local); return g.x(), g.y()
    def ir(self, w, local=None, dur=0.75):
        x, y = self.centro(w, local); yield from self.mover(x, y, dur)

    # ---------- clics y teclas reales ----------
    def clic(self, w, local=None, boton=Qt.LeftButton, doble=False, mover=True, pausa=0.25):
        if local is None: local = w.rect().center()
        if mover: yield from self.ir(w, local)
        yield pausa
        x, y = self.centro(w, local); self.ev('clic', x=x, y=y, der=(boton == Qt.RightButton))
        if doble: QTimer.singleShot(0, lambda: QTest.mouseDClick(w, boton, Qt.NoModifier, local))
        else: QTimer.singleShot(0, lambda: QTest.mouseClick(w, boton, Qt.NoModifier, local))
        yield 0.35
    def tecla(self, w, key, mod=Qt.NoModifier, txt=''):
        self.ev('tecla', txt=txt); QTimer.singleShot(0, lambda: QTest.keyClick(w, key, mod)); yield 0.25
    def escribir(self, w, texto, cps=14):
        for ch in texto:
            QTest.keyClicks(w, ch); yield 1 / cps
        yield 0.2
    def rueda(self, w, local, pasos, dy=-120):
        x, y = self.centro(w, local)
        for _ in range(abs(pasos)):
            ev = QWheelEvent(QPointF(local), QPointF(x, y), QPoint(0, 0), QPoint(0, dy if pasos > 0 else -dy), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
            QApplication.sendEvent(w.viewport() if hasattr(w, 'viewport') else w, ev); yield 0.12

    def bajar_hasta(self, area, objetivo, margen=40, maxpasos=40):
        """Gira la rueda sobre un QScrollArea hasta que 'objetivo' quede visible arriba (con margen)."""
        vp = area.viewport(); local = vp.rect().center()
        yield from self.ir(vp, local)
        for _ in range(maxpasos):
            y = objetivo.mapTo(vp, QPoint(0, 0)).y()
            if margen - 10 <= y <= margen + 120 or (y > margen and area.verticalScrollBar().value() >= area.verticalScrollBar().maximum()): break
            sentido = 1 if y > margen else -1
            x, yy = self.centro(vp, local)
            ev = QWheelEvent(QPointF(local), QPointF(x, yy), QPoint(0, 0), QPoint(0, -120 * sentido), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
            QApplication.sendEvent(vp, ev); yield 0.11
        yield 0.3

    # ---------- marcas para la edición ----------
    def rect_global(self, w, r=None):
        r = r or w.rect(); g = w.mapToGlobal(r.topLeft()); return [g.x(), g.y(), r.width(), r.height()]
    def resaltar(self, rect, dur=3.0, n=None):
        self.ev('resaltar', r=list(rect), dur=dur, n=n); yield 0.05
    def zoom(self, rect, escala=None, dur=0.8):
        """Acerca la cámara virtual al rectángulo (global). escala None = encajar con margen."""
        self.ev('zoom', r=list(rect), escala=escala, dur=dur); yield 0.05
    def alejar(self, dur=0.8):
        self.ev('alejar', dur=dur); yield 0.05
    def nota(self, texto, dur=4.0):
        self.ev('nota', txt=texto, dur=dur); yield 0.05
