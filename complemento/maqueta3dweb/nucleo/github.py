# -*- coding: utf-8 -*-
"""Publicar el sitio en GitHub Pages: conexión con un token guardado en el gestor de autenticación de QGIS,
crear el repositorio (o una carpeta vN si ya existe), subir, activar Pages, esperar a que esté en línea y hacer el QR."""
import base64, json, os, time, urllib.request, urllib.error, webbrowser
from concurrent.futures import ThreadPoolExecutor
from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsSettings

API = 'https://api.github.com'
CLAVE = 'maqueta3dweb/github_authcfg'
URL_TOKEN = 'https://github.com/settings/tokens/new?scopes=repo&description=Maqueta%203D%20Web%20(QGIS)'


def _pedir(metodo, ruta, token, datos=None, crudo=False):
    req = urllib.request.Request(ruta if ruta.startswith('http') else API + ruta, method=metodo,
                                 data=json.dumps(datos).encode() if datos is not None else None,
                                 headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                                          'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Maqueta3DWeb-QGIS'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            cuerpo = r.read(); return r.status, (cuerpo if crudo else (json.loads(cuerpo) if cuerpo else {}))
    except urllib.error.HTTPError as e:
        cuerpo = e.read()
        try: return e.code, json.loads(cuerpo)
        except Exception: return e.code, {'message': cuerpo[:300]}


def token_guardado():
    cid = QgsSettings().value(CLAVE, '')
    if not cid: return None, None
    cfg = QgsAuthMethodConfig()
    if not QgsApplication.authManager().loadAuthenticationConfig(cid, cfg, True): return None, None
    return cfg.config('password'), cfg.config('username')


def guardar_token(token, usuario):
    am = QgsApplication.authManager(); cfg = QgsAuthMethodConfig('Basic')
    cfg.setName('GitHub · Maqueta 3D Web'); cfg.setConfig('username', usuario); cfg.setConfig('password', token)
    viejo = QgsSettings().value(CLAVE, '')
    if viejo: am.removeAuthenticationConfig(viejo)
    ok = am.storeAuthenticationConfig(cfg)
    if isinstance(ok, tuple): ok = ok[0]
    if not ok or not cfg.id():
        raise RuntimeError('QGIS no pudo guardar el permiso (revisa la contraseña maestra de autenticación).')
    QgsSettings().setValue(CLAVE, cfg.id())


def verificar(token):
    st, u = _pedir('GET', '/user', token)
    if st != 200: raise RuntimeError('GitHub no aceptó el permiso: ' + str(u.get('message')))
    return u['login']


def conectar(parent):
    """Ventana sencilla: abrir GitHub para crear el permiso, pegarlo y comprobarlo."""
    from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox, QLineEdit
    t, u = token_guardado()
    if t:
        try:
            login = verificar(t)
            if QMessageBox.question(parent, 'GitHub', f'Ya estás conectado como «{login}».\n¿Quieres cambiar de cuenta o de permiso?') != QMessageBox.Yes: return login
        except Exception: pass
    QMessageBox.information(parent, 'Conectar con GitHub',
                            'Se abrirá GitHub para crear el permiso del complemento (ya va con la casilla «repo» marcada).\n\n'
                            '1. Inicia sesión si te lo pide.\n2. Elige la caducidad (por ejemplo, «No expiration» o 1 año).\n'
                            '3. Pulsa «Generate token» al final de la página.\n4. Copia el código que empieza por «ghp_» y pégalo en la siguiente ventana.')
    webbrowser.open(URL_TOKEN)
    token, ok = QInputDialog.getText(parent, 'Conectar con GitHub', 'Pega aquí el permiso (ghp_…):', QLineEdit.Password)
    if not ok or not token.strip(): return None
    login = verificar(token.strip()); guardar_token(token.strip(), login)
    QMessageBox.information(parent, 'GitHub', f'Conectado como «{login}». El permiso queda guardado cifrado en QGIS.')
    return login


def nombre_valido(n):
    import re, unicodedata
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()
    n = re.sub(r'[^A-Za-z0-9._-]+', '-', n.strip()).strip('-.')
    return n[:100] or 'maqueta-3d'


def publicar(parent, carpeta, repo, registro=print, privado=False):
    token, _ = token_guardado()
    if not token:
        if not conectar(parent): raise RuntimeError('No hay conexión con GitHub.')
        token, _ = token_guardado()
    login = verificar(token); repo = nombre_valido(repo or os.path.basename(carpeta))
    st, info = _pedir('GET', f'/repos/{login}/{repo}', token); prefijo = ''
    if st == 404:
        st, info = _pedir('POST', '/user/repos', token, {'name': repo, 'private': privado, 'auto_init': True,
                                                        'description': 'Página con plano 2D, maqueta 3D, RA y QR (Maqueta 3D Web)'})
        if st not in (200, 201): raise RuntimeError('No se pudo crear el repositorio: ' + str(info.get('message')))
        registro(f'Repositorio creado: {login}/{repo}'); time.sleep(2)
    else:   # ya existe: nunca se pisa lo publicado, va en una carpeta vN nueva
        st, cont = _pedir('GET', f'/repos/{login}/{repo}/contents/', token)
        usados = {c['name'] for c in cont} if isinstance(cont, list) else set()
        k = 2
        while f'v{k}' in usados: k += 1
        prefijo = f'v{k}/'; registro(f'El repositorio ya existe: se publica en la carpeta nueva {prefijo}')
    rama = info.get('default_branch', 'main')
    st, ref = _pedir('GET', f'/repos/{login}/{repo}/git/ref/heads/{rama}', token)
    base = ref['object']['sha']; st, com = _pedir('GET', f'/repos/{login}/{repo}/git/commits/{base}', token)

    archivos = []
    for raiz, _, nombres in os.walk(carpeta):
        for a in nombres:
            p = os.path.join(raiz, a); archivos.append((p, prefijo + os.path.relpath(p, carpeta).replace(os.sep, '/')))
    registro(f'Subiendo {len(archivos)} archivos…'); hechos = [0]

    def blob(par):
        p, ruta = par
        with open(p, 'rb') as f: b64 = base64.b64encode(f.read()).decode()
        for intento in range(4):
            st, r = _pedir('POST', f'/repos/{login}/{repo}/git/blobs', token, {'content': b64, 'encoding': 'base64'})
            if st == 201: hechos[0] += 1; return {'path': ruta, 'mode': '100644', 'type': 'blob', 'sha': r['sha']}
            time.sleep(2 + 3 * intento)
        raise RuntimeError(f'No se pudo subir {ruta}: {r.get("message")}')
    with ThreadPoolExecutor(6) as ex:
        futuros = [ex.submit(blob, a) for a in archivos]; arbol = []
        for i, f in enumerate(futuros):
            arbol.append(f.result())
            if i % 100 == 0: registro(f'  {hechos[0]} de {len(archivos)}')
    st, tree = _pedir('POST', f'/repos/{login}/{repo}/git/trees', token, {'base_tree': com['tree']['sha'], 'tree': arbol})
    if st != 201: raise RuntimeError('No se pudo armar el árbol de archivos: ' + str(tree.get('message')))
    st, c = _pedir('POST', f'/repos/{login}/{repo}/git/commits', token, {'message': 'Publicar maqueta 3D (complemento Maqueta 3D Web de QGIS)', 'tree': tree['sha'], 'parents': [base]})
    st, r = _pedir('PATCH', f'/repos/{login}/{repo}/git/refs/heads/{rama}', token, {'sha': c['sha']})
    if st != 200: raise RuntimeError('No se pudo actualizar la rama: ' + str(r.get('message')))
    registro('Archivos subidos.')

    st, pg = _pedir('GET', f'/repos/{login}/{repo}/pages', token)
    if st == 404:
        st, pg = _pedir('POST', f'/repos/{login}/{repo}/pages', token, {'source': {'branch': rama, 'path': '/'}})
        if st not in (200, 201): raise RuntimeError('No se pudo activar GitHub Pages: ' + str(pg.get('message')) + ('\n(Con repositorios privados, Pages exige un plan de pago.)' if privado else ''))
    base_url = (pg.get('html_url') or f'https://{login.lower()}.github.io/{repo}/').rstrip('/') + '/'
    url = base_url + prefijo
    registro('GitHub Pages activado. Esperando a que la página esté en línea (1 a 3 minutos)…')
    lista = False
    for _ in range(60):
        try:
            with urllib.request.urlopen(urllib.request.Request(url + 'config.js', headers={'User-Agent': 'Maqueta3DWeb', 'Cache-Control': 'no-cache'}), timeout=20) as r:
                if r.status == 200: lista = True; break
        except Exception: pass
        time.sleep(5)
    if not lista: registro('Aviso: la página aún no responde; GitHub puede tardar unos minutos más. El QR ya sirve con esta dirección.')
    from . import sitio
    salida = os.path.dirname(carpeta.rstrip('/\\'))
    sitio.qr(url, os.path.join(salida, 'QR.png'))
    registro(f'{"En línea" if lista else "Dirección"}: {url}\nQR guardado en {os.path.join(salida, "QR.png")}')
    return url
