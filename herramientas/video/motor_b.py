# Motor de grabación para Blender: cursor, clics y teclas reales con xdotool (eventos X verdaderos),
# búsqueda de botones por OCR (tesseract) y registro de eventos para la edición (mismo formato que QGIS).
import bpy, json, os, time, math, subprocess, csv, io

class MotorB:
    def __init__(self, log, duraciones, hueco=0.7):
        self.log = open(log, 'w'); self.dur = json.load(open(duraciones)); self.hueco = hueco; self.fin = 0
        self.tmp = os.path.dirname(log) + '/ocr.png'

    # ---------- registro y planificador ----------
    def ev(self, tipo, **k):
        k.update(t=time.time(), tipo=tipo); self.log.write(json.dumps(k, ensure_ascii=False) + '\n'); self.log.flush()
    def correr(self, gen, al_final):
        self.gen = gen; self.al_final = al_final; bpy.app.timers.register(self._paso, first_interval=0.1, persistent=True)
    def _paso(self):
        try:
            w = next(self.gen)
        except StopIteration:
            self.ev('fin'); self.log.close(); self.al_final(); return None
        except Exception:
            import traceback; self.ev('error', txt=traceback.format_exc()); self.log.close(); self.al_final(); return None
        return max(0.01, w or 0.01)
    def hasta(self, t):
        while time.time() < t: yield min(0.05, t - time.time())
    def seg(self, sid):
        if self.fin: yield from self.hasta(self.fin)
        self.ev('seg', id=sid); self.fin = time.time() + self.dur[sid] + self.hueco; yield 0.05
    def destello(self):
        p = subprocess.Popen(['bash', os.path.dirname(__file__) + '/rojo.sh']); yield 0.5
        self.ev('destello'); yield 1.0

    # ---------- entrada real (X11) ----------
    def xdo(self, *a): subprocess.run(['xdotool', *map(str, a)])
    def pos(self):
        o = subprocess.run(['xdotool', 'getmouselocation', '--shell'], capture_output=True, text=True).stdout
        d = dict(l.split('=') for l in o.split() if '=' in l); return int(d['X']), int(d['Y'])
    def mover(self, x, y, dur=0.7):
        x0, y0 = self.pos(); dist = math.hypot(x - x0, y - y0)
        if dist < 3: return
        dur = min(dur, 0.25 + dist / 1400); n = max(2, int(dur * 40))
        for i in range(1, n + 1):
            s = i / n; e = s * s * (3 - 2 * s)
            self.xdo('mousemove', int(x0 + (x - x0) * e), int(y0 + (y - y0) * e)); yield dur / n
    def clic(self, x, y, boton=1, doble=False, pausa=0.2, mover=True):
        if mover: yield from self.mover(x, y)
        yield pausa
        self.ev('clic', x=x, y=y, der=(boton == 3))
        self.xdo('click', '--repeat', 2 if doble else 1, '--delay', 80, boton); yield 0.35
    def tecla(self, combo, txt=None):
        self.ev('tecla', txt=txt or combo.replace('+', ' + ').title()); self.xdo('key', '--delay', 60, combo); yield 0.35
    def escribir(self, texto, cps=12):
        for ch in texto:
            self.xdo('type', '--delay', 0, ch); yield 1 / cps
        yield 0.2
    def editar_campo(self, x, y, valor):
        """Doble clic en un campo numérico o de texto de Blender, borra, escribe y Enter (todo real)."""
        yield from self.clic(x, y, doble=True); yield 0.3
        self.xdo('key', 'ctrl+a'); yield 0.15
        self.xdo('key', 'BackSpace'); yield 0.15
        yield from self.escribir(valor)
        self.xdo('key', 'Return'); yield 0.4

    # ---------- OCR ----------
    def captura(self, region=None):
        args = ['import', '-silent', '-window', 'root']
        if region: x, y, w, h = region; args += ['-crop', f'{w}x{h}+{x}+{y}']
        subprocess.run(args + [self.tmp])
        return region[:2] if region else (0, 0)
    def buscar(self, texto, region=None, todos=False):
        """Busca una o varias palabras en pantalla. Devuelve (x, y, w, h) en coordenadas de pantalla o None."""
        ox, oy = self.captura(region); esc = 3
        pre = self.tmp.replace('.png', '_p.png')
        subprocess.run(['convert', self.tmp, '-resize', f'{esc * 100}%', '-colorspace', 'Gray', '-negate', '-threshold', '55%', pre])
        out = subprocess.run(['tesseract', pre, '-', '--psm', '11', 'tsv'], capture_output=True, text=True).stdout
        filas = [r for r in csv.DictReader(io.StringIO(out), delimiter='\t') if r.get('text', '').strip()]
        pal = texto.lower().split(); res = []
        for i in range(len(filas) - len(pal) + 1):
            grupo = filas[i:i + len(pal)]
            if all(((g['text'].lower().strip(':.,') == p) if len(p) <= 2 else (p in g['text'].lower())) for p, g in zip(pal, grupo)) and len({g['block_num'] + g['par_num'] + g['line_num'] for g in grupo}) == 1:
                x0 = min(int(g['left']) for g in grupo); y0 = min(int(g['top']) for g in grupo)
                x1 = max(int(g['left']) + int(g['width']) for g in grupo); y1 = max(int(g['top']) + int(g['height']) for g in grupo)
                res.append((ox + x0 // esc, oy + y0 // esc, (x1 - x0) // esc, (y1 - y0) // esc))
        if todos: return res
        return res[0] if res else None
    def esperar_texto(self, texto, region=None, maxs=8):
        t = time.time()
        while time.time() - t < maxs:
            r = self.buscar(texto, region)
            if r: return r
            yield 0.3
        raise Exception('no aparece en pantalla: ' + texto)
    def centro(self, r): return r[0] + r[2] // 2, r[1] + r[3] // 2

    # ---------- marcas para la edición ----------
    def resaltar(self, rect, dur=3.0, n=None): self.ev('resaltar', r=list(map(int, rect)), dur=dur, n=n); yield 0.05
    def zoom(self, rect, escala=None, dur=0.8): self.ev('zoom', r=list(map(int, rect)), escala=escala, dur=dur); yield 0.05
    def alejar(self, dur=0.8): self.ev('alejar', dur=dur); yield 0.05
    def corte_ini(self): self.ev('corte_ini'); yield 0.05
    def corte_fin(self): self.ev('corte_fin'); yield 0.05

# ---------- utilidades de Blender ----------
def ventana(): return bpy.context.window_manager.windows[0]
def area(tipo): return [a for a in ventana().screen.areas if a.type == tipo][0]
def region(a, tipo='WINDOW'): return [r for r in a.regions if r.type == tipo][0]
def rect_pantalla(r):
    """Rectángulo de una región de Blender en coordenadas de pantalla (Blender cuenta Y desde abajo)."""
    w = ventana(); H = w.height
    return [r.x, H - (r.y + r.height) + OFFSET_Y, r.width, r.height]
OFFSET_Y = 0
def ov(tipo='VIEW_3D'):
    a = area(tipo); return bpy.context.temp_override(window=ventana(), area=a, region=region(a))
def punto_3d(co):
    """Posición en pantalla de un punto 3D de la escena (para hacer clic sobre un objeto)."""
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    a = area('VIEW_3D'); r = region(a); p = location_3d_to_region_2d(r, a.spaces[0].region_3d, co)
    w = ventana(); return int(r.x + p.x), int(w.height - (r.y + p.y) + OFFSET_Y)
