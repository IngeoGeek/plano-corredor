# -*- coding: utf-8 -*-
"""Instala la primera vez las librerías que QGIS no trae (trimesh, pyfqmr, qrcode; usd-core es opcional)."""
import importlib, os, subprocess, sys

NECESARIAS = {'trimesh': 'trimesh', 'pyfqmr': 'pyfqmr', 'qrcode': 'qrcode'}
OPCIONALES = {'pxr': 'usd-core'}


def faltantes(opcionales=False):
    lista = dict(NECESARIAS, **(OPCIONALES if opcionales else {}))
    out = []
    for mod, pkg in lista.items():
        try: importlib.import_module(mod)
        except Exception: out.append(pkg)
    return out


def python_de_qgis():
    """En Windows sys.executable es qgis-bin.exe: el intérprete está junto a él o en sys.exec_prefix."""
    exe = sys.executable
    if os.path.basename(exe).lower().startswith('python'): return exe
    for cand in (os.path.join(sys.exec_prefix, 'python.exe'), os.path.join(sys.exec_prefix, 'python3.exe'),
                 os.path.join(os.path.dirname(exe), 'python3.exe'), os.path.join(os.path.dirname(exe), 'python.exe'),
                 os.path.join(sys.exec_prefix, 'bin', 'python3')):
        if os.path.exists(cand): return cand
    return 'python3'


def instalar(paquetes, registro=print):
    cmd = [python_de_qgis(), '-m', 'pip', 'install', '--user', *paquetes]
    registro('Instalando: ' + ' '.join(paquetes))
    flags = 0x08000000 if os.name == 'nt' else 0   # sin ventana negra en Windows
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    if r.returncode != 0 and '--user' in cmd:    # algunos QGIS no aceptan --user
        r = subprocess.run([c for c in cmd if c != '--user'], capture_output=True, text=True, creationflags=flags)
    registro(r.stdout[-800:] + r.stderr[-800:])
    import site; importlib.invalidate_caches()
    try:
        u = site.getusersitepackages()
        if u not in sys.path: sys.path.append(u)
    except Exception: pass
    return r.returncode == 0
