"""Edita un capítulo: tarjetas, grabación con zoom/resaltados/clics, narración y subtítulos.
Uso: python3 editar.py CARPETA_CAPITULO [--rapido]"""
import sys, os, json, math, subprocess, importlib.util, re
import numpy as np, cv2, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/rec')
import sincro

C = sys.argv[1]; RAPIDO = '--rapido' in sys.argv
def cargar(n):
    s = importlib.util.spec_from_file_location(n, f'{C}/{n}.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
G = cargar('guion'); E = cargar('edicion')
W, H, FPS = 1920, 1080, 30
AZUL = (1, 79, 125); NARANJA = (242, 140, 0); AMARILLO = (255, 205, 0)
F = '/usr/share/fonts/opentype/inter/Inter-'
def fuente(peso, t): return ImageFont.truetype(F + peso + '.otf', t)
DUR = json.load(open(C + '/duraciones.json')); TXT = {s: (sub, voz) for s, sub, voz in G.SEG}

# ---------------- sincronía ----------------
d, td, EV = sincro.desfase(C + '/bruto.mp4', C + '/eventos.jsonl')
def vt(t): return t - td + d                          # hora del registro → segundo del video bruto
segs = [e for e in EV if e['tipo'] == 'seg']; fin = [e for e in EV if e['tipo'] == 'fin'][0]
A = vt(segs[0]['t']) - 0.6; B = vt(fin['t']) + 0.6
L0 = DUR['t0'] + 1.4                                  # tarjeta de título
O = L0                                                # inicio de la pantalla en el video final
def out(v): return O + (v - A)
T1 = O + (B - A); L1 = DUR['t1'] + 1.2; T2 = T1 + L1; L2 = DUR['t2'] + 2.2; TOTAL = T2 + L2

# ---------------- cámara virtual ----------------
def objetivo(r, esc=None):
    x, y, w, h = r
    s = esc or min(W / (w * 1.3), H / (h * 1.3), 2.0); s = max(1.0, s)
    cx, cy = x + w / 2, y + h / 2; cw, ch = W / s, H / s
    cx = min(max(cx, cw / 2), W - cw / 2); cy = min(max(cy, ch / 2), H - ch / 2)
    return (cx, cy, s)
TRANS = []; estado = (W / 2, H / 2, 1.0)
for e in EV:
    if e['tipo'] == 'zoom': TRANS.append((vt(e['t']), e.get('dur', 0.8), objetivo(e['r'], e.get('escala'))))
    if e['tipo'] == 'alejar': TRANS.append((vt(e['t']), e.get('dur', 0.8), (W / 2, H / 2, 1.0)))
def suave(p): p = min(max(p, 0), 1); return p * p * (3 - 2 * p)
def camara(v):
    st = (W / 2, H / 2, 1.0)
    for t0, du, tg in TRANS:
        if v < t0: break
        p = suave((v - t0) / du)
        # interpolar en escala logarítmica para que el zoom se sienta uniforme
        s = math.exp(math.log(st[2]) + (math.log(tg[2]) - math.log(st[2])) * p)
        st = (st[0] + (tg[0] - st[0]) * p, st[1] + (tg[1] - st[1]) * p, s)
    cx, cy, s = st; cw, ch = W / s, H / s
    cx = min(max(cx, cw / 2), W - cw / 2); cy = min(max(cy, ch / 2), H - ch / 2)
    return cx - cw / 2, cy - ch / 2, s

# ---------------- elementos gráficos ----------------
def rgba(img): return np.array(img.convert('RGBA'))[:, :, [2, 1, 0, 3]]
def pegar(fr, im, x, y, alfa=1.0):
    h, w = im.shape[:2]; x, y = int(x), int(y)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0: return
    a = im[y0 - y:y1 - y, x0 - x:x1 - x, 3:4].astype(np.float32) / 255 * alfa
    fr[y0:y1, x0:x1] = (fr[y0:y1, x0:x1] * (1 - a) + im[y0 - y:y1 - y, x0 - x:x1 - x, :3] * a).astype(np.uint8)
def etiqueta(texto, t=34, fondo=(20, 24, 30, 225), color=(255, 255, 255), peso='SemiBold', pad=(26, 14), radio=14, barra=None):
    f = fuente(peso, t); bb = f.getbbox(texto); w, h = bb[2] - bb[0] + pad[0] * 2 + (10 if barra else 0), t + pad[1] * 2
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([0, 0, w - 1, h - 1], radio, fill=fondo)
    if barra: dr.rounded_rectangle([0, 0, 9, h - 1], 4, fill=barra)
    dr.text((pad[0] + (10 if barra else 0) - bb[0], pad[1] - bb[1] + (t - (bb[3] - bb[1])) / 2), texto, font=f, fill=color)
    return rgba(im)
CACHE = {}
def num_badge(n):
    if n not in CACHE:
        im = Image.new('RGBA', (44, 44), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); dr.ellipse([0, 0, 43, 43], fill=NARANJA + (255,))
        f = fuente('Bold', 26); bb = f.getbbox(n); dr.text((22 - (bb[2] + bb[0]) / 2, 22 - (bb[3] + bb[1]) / 2), n, font=f, fill=(255, 255, 255)); CACHE[n] = rgba(im)
    return CACHE[n]
RES = [(vt(e['t']), e['dur'], e['r'], e.get('n')) for e in EV if e['tipo'] == 'resaltar']
CLICS = [(vt(e['t']), e['x'], e['y'], e.get('der')) for e in EV if e['tipo'] == 'clic']
TECLAS = [(vt(e['t']), etiqueta('Teclado:  ' + e['txt'], 38)) for e in EV if e['tipo'] == 'tecla']
SECC = [(vt(e['t']), etiqueta(E.SECCIONES[e['id']], 36, fondo=(255, 255, 255, 240), color=(20, 30, 40), barra=AZUL + (255,))) for e in segs if e['id'] in E.SECCIONES]
DER = etiqueta('clic derecho', 26, fondo=(242, 140, 0, 235))
def capa(fr, v):
    x0, y0, s = camara(v)
    def M(px, py): return (px - x0) * s, (py - y0) * s
    for t, du, r, n in RES:
        if t <= v <= t + du:
            a = min(1, (v - t) / 0.25, (t + du - v) / 0.35)
            ov = fr.copy(); (ax, ay), (bx, by) = M(r[0] - 4, r[1] - 4), M(r[0] + r[2] + 4, r[1] + r[3] + 4)
            p = lambda q: (int(round(q[0])), int(round(q[1])))
            rr = 10; c = NARANJA[::-1]
            for (u0, u1) in [((ax + rr, ay), (bx - rr, ay)), ((ax + rr, by), (bx - rr, by)), ((ax, ay + rr), (ax, by - rr)), ((bx, ay + rr), (bx, by - rr))]:
                cv2.line(ov, p(u0), p(u1), c, 5, cv2.LINE_AA)
            for cc, ang in [((ax + rr, ay + rr), 180), ((bx - rr, ay + rr), 270), ((bx - rr, by - rr), 0), ((ax + rr, by - rr), 90)]:
                cv2.ellipse(ov, p(cc), (rr, rr), ang, 0, 90, c, 5, cv2.LINE_AA)
            fr[:] = cv2.addWeighted(ov, a, fr, 1 - a, 0)
            if n: pegar(fr, num_badge(n), bx - 22, ay - 22, a)
    for t, x, y, der in CLICS:
        if t <= v <= t + 0.6:
            p = (v - t) / 0.6; (mx, my) = M(x, y); ov = fr.copy()
            cv2.circle(ov, (int(mx), int(my)), int(10 + 30 * p), AMARILLO[::-1], 4, cv2.LINE_AA)
            fr[:] = cv2.addWeighted(ov, 1 - p, fr, p, 0)
            if der: pegar(fr, DER, mx + 18, my + 14, 1 - p * 0.5)
    for t, im in TECLAS:
        if t <= v <= t + 1.6: pegar(fr, im, W / 2 - im.shape[1] / 2, H - 150, min(1, (v - t) / 0.15, (t + 1.6 - v) / 0.3))
    for t, im in SECC:
        if t <= v <= t + 4.5:
            a = min(1, (v - t) / 0.3, (t + 4.5 - v) / 0.4); dx = (1 - suave((v - t) / 0.4)) * -60
            pegar(fr, im, 40 + dx, 60, a)

# ---------------- tarjetas ----------------
def degradado():
    y = np.linspace(0, 1, H)[:, None, None]; c0 = np.array(AZUL, float); c1 = np.array((0, 34, 56), float)
    im = (c0 * (1 - y) + c1 * y) * np.ones((1, W, 1)); return Image.fromarray(im.astype(np.uint8))
def tarjeta_titulo():
    im = degradado(); dr = ImageDraw.Draw(im)
    dr.text((140, 250), E.SERIE.upper(), font=fuente('SemiBold', 34), fill=(160, 205, 230))
    dr.text((140, 320), f'Capítulo {E.NUM}', font=fuente('Bold', 120), fill=(255, 255, 255))
    y = 480
    for linea in envolver(E.TITULO, fuente('Medium', 60), 1500): dr.text((140, y), linea, font=fuente('Medium', 60), fill=(235, 242, 247)); y += 78
    dr.rectangle([140, 225, 260, 231], fill=NARANJA)
    dr.text((140, 940), E.AUTOR, font=fuente('Medium', 30), fill=(180, 210, 228))
    return np.array(im)[:, :, ::-1].copy()
def envolver(t, f, ancho):
    ls, cur = [], ''
    for p in t.split():
        if f.getlength((cur + ' ' + p).strip()) > ancho: ls.append(cur); cur = p
        else: cur = (cur + ' ' + p).strip()
    return ls + [cur]
def tarjeta_tabla():
    im = Image.new('RGB', (W, H), (243, 246, 249)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 150], fill=AZUL); dr.text((120, 45), E.TABLA_TITULO, font=fuente('Bold', 58), fill=(255, 255, 255))
    dr.text((W - 120 - fuente('Medium', 30).getlength(f'Capítulo {E.NUM}'), 62), f'Capítulo {E.NUM}', font=fuente('Medium', 30), fill=(180, 210, 228))
    x0, x1, x2, x3 = 120, 1010, 1130, W - 120; y = 200
    dr.text((x0, y), 'Dato', font=fuente('Bold', 30), fill=(90, 100, 110)); dr.text((x1, y), 'Paso', font=fuente('Bold', 30), fill=(90, 100, 110)); dr.text((x2, y), 'Ejemplo', font=fuente('Bold', 30), fill=(90, 100, 110))
    y += 56
    for i, (a, b, c) in enumerate(E.TABLA):
        if i % 2 == 0: dr.rectangle([x0 - 20, y - 12, x3 + 20, y + 54], fill=(255, 255, 255))
        dr.text((x0, y), a, font=fuente('Medium', 32), fill=(25, 35, 45)); dr.text((x1, y), b, font=fuente('Medium', 32), fill=(1, 79, 125))
        dr.text((x2, y), c, font=fuente('SemiBold', 32), fill=(25, 35, 45)); y += 70
    y += 30; dr.rounded_rectangle([x0 - 20, y, x3 + 20, y + 170], 18, fill=(255, 244, 222), outline=NARANJA, width=3)
    dr.text((x0 + 10, y + 26), 'Comprobación', font=fuente('Bold', 32), fill=(160, 90, 0))
    dr.text((x0 + 10, y + 74), E.COMPROBACION[0] + '      ' + E.COMPROBACION[1], font=fuente('SemiBold', 36), fill=(40, 30, 10))
    return np.array(im)[:, :, ::-1].copy()
def tarjeta_fin():
    im = degradado(); dr = ImageDraw.Draw(im)
    dr.text((140, 380), 'Siguiente', font=fuente('SemiBold', 40), fill=(160, 205, 230))
    dr.rectangle([140, 355, 260, 361], fill=NARANJA)
    dr.text((140, 440), E.SIGUIENTE, font=fuente('Bold', 70), fill=(255, 255, 255))
    dr.text((140, 560), 'La guía escrita tiene cada valor del ejemplo para comparar tus resultados.', font=fuente('Medium', 36), fill=(220, 232, 240))
    dr.text((140, 940), E.AUTOR, font=fuente('Medium', 30), fill=(180, 210, 228))
    return np.array(im)[:, :, ::-1].copy()

# ---------------- audio y subtítulos ----------------
SR = 24000; pista = np.zeros(int((TOTAL + 1) * SR), np.float32); CUES = []
def poner(sid, t):
    a, sr = sf.read(f'{C}/audio/{sid}.wav', dtype='float32'); i = int(t * SR); pista[i:i + len(a)] += a[:len(pista) - i]
    sub = TXT[sid][0]; frases = [f.strip() for f in re.split(r'(?<=[.:])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])', sub) if f.strip()]
    tot = sum(len(f) for f in frases); t0 = t + 0.08; dd = DUR[sid] - 0.25
    for f in frases:
        du = dd * len(f) / tot; CUES.append((t0, t0 + du, f)); t0 += du
poner('t0', 0.6)
for e in segs: poner(e['id'], out(vt(e['t'])))
poner('t1', T1 + 0.5); poner('t2', T2 + 0.5)
m = np.abs(pista).max(); pista = pista / m * 0.89 if m > 0 else pista
sf.write(C + '/narracion.wav', pista, SR)
def ts(x): h = int(x // 3600); mi = int(x % 3600 // 60); s = x % 60; return f'{h:02d}:{mi:02d}:{s:06.3f}'.replace('.', ',')
with open(C + '/subtitulos.srt', 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(CUES, 1): f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n')

# ---------------- render ----------------
salida = f'{C}/capitulo_{E.NUM}.mp4'
ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-i', C + '/narracion.wav', '-i', C + '/subtitulos.srt', '-map', '0:v', '-map', '1:a', '-map', '2:s',
                       '-c:v', 'libx264', '-preset', 'ultrafast' if RAPIDO else 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                       '-c:a', 'aac', '-b:a', '160k', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=spa', '-metadata', f'title={E.SERIE} · Capítulo {E.NUM}', salida], stdin=subprocess.PIPE)
def fundido(img, n, entrada=0.4, salida_=0.4):
    for i in range(n):
        t = i / FPS; a = min(1, t / entrada, (n / FPS - t) / salida_); ff.stdin.write((img * a).astype(np.uint8).tobytes())
fundido(tarjeta_titulo(), int(L0 * FPS))
cap = cv2.VideoCapture(C + '/bruto.mp4'); fps_b = cap.get(cv2.CAP_PROP_FPS)
cap.set(cv2.CAP_PROP_POS_FRAMES, int(A * fps_b)); n_scr = int((B - A) * FPS); ultimo = None
for i in range(n_scr):
    v = A + i / FPS; ok, fr = cap.read()
    if not ok: fr = ultimo
    ultimo = fr; x0, y0, s = camara(v)
    out_fr = cv2.warpAffine(fr, np.float32([[s, 0, -s * x0], [0, s, -s * y0]]), (W, H), flags=cv2.INTER_CUBIC if s > 1.01 else cv2.INTER_LINEAR)
    capa(out_fr, v)
    a = min(1, (i / FPS) / 0.4, (n_scr - i) / FPS / 0.4); ff.stdin.write((out_fr * a).astype(np.uint8).tobytes() if a < 1 else out_fr.tobytes())
fundido(tarjeta_tabla(), int(L1 * FPS)); fundido(tarjeta_fin(), int(L2 * FPS), salida_=1.0)
ff.stdin.close(); ff.wait(); print(salida, round(TOTAL, 1), 's')
