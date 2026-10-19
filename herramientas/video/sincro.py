"""Encuentra el destello rojo en el video: devuelve el desfase (segundo del video en que ocurrió el evento 'destello')."""
import sys, json, cv2
def desfase(video, eventos):
    ev = [json.loads(l) for l in open(eventos)]; td = [e['t'] for e in ev if e['tipo'] == 'destello'][0]
    cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS); i = 0; primero = None
    while True:
        ok, f = cap.read()
        if not ok: break
        b, g, r = [float(x) for x in cv2.mean(f[::8, ::8])[:3]]
        if r > 200 and g < 40 and b < 40:
            primero = i; break
        i += 1
    # el evento se anota 0,25 s después de mostrar el destello
    return primero / fps + 0.25 - 0, td, ev
if __name__ == '__main__':
    d, td, ev = desfase(sys.argv[1], sys.argv[2]); print(d)
