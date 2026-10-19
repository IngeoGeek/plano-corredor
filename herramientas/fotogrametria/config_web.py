"""Escribe W/sitio/config.js a partir de proyecto.json e info.json. Uso: python3 config_web.py W "Título" "Subtítulo" [fecha]"""
import sys, json
W, tit, sub = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(W + '/proyecto.json')); I = json.load(open(W + '/info.json')); ESC = I['escala']
aw = (I['E1'] - I['E0']) / ESC * 1000; ah = (I['N1'] - I['N0']) / ESC * 1000; pr = P['proyeccion']
ficha = [['Escala de la maqueta', f"1:{ESC:,.0f}".replace(',', ' ')], ['Exageración vertical', '1 × (alturas reales)']]
if P.get('fotos'): ficha.append(['Fotografías', f"{P['fotos']}" + (f" · RTK FIX en {P['fix']}" if P.get('fix') else '')])
if P.get('gsd'): ficha.append(['Ortofoto', f"GSD {P['gsd'] * 100:.2f} cm".replace('.', ',')])
if P.get('area_ha'): ficha.append(['Área levantada', f"{P['area_ha']} ha".replace('.', ',')])
ficha.append(['Sistema', P['epsg']])
cfg = {'version': 1, 'titulo': tit, 'subtitulo': sub, 'color': '#014f7d',
       'hoja': {'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3)},
       'marco': {'x_mm': 0, 'y_mm': 0, 'ancho_mm': round(aw, 3), 'alto_mm': round(ah, 3), 'E_min': I['E0'], 'E_max': I['E1'], 'N_min': I['N0'], 'N_max': I['N1']},
       'relieve': {'imagen': 'relieve.png', 'z_min': I['zmin'], 'z_max': I['zmax'], 'exageracion': 1},
       'proyeccion': pr, 'archivos': {'modelo': 'plano_relieve.glb', 'modelo_iphone': 'plano_relieve.usdz', 'plano2d': 'plano.jpg', 'poster': ''},
       'etiquetas': [], 'ficha': ficha,
       'elaboro': {'nombre': 'Osney Izaquita', 'titulos': [['Ingeniero Geólogo', 'Universidad Pedagógica y Tecnológica de Colombia'],
                   ['Especialista en Aplicación de TIC para la Enseñanza', 'Universidad de Santander'], ['Magíster en Gestión de Cuencas Hidrográficas', 'Universidad Santo Tomás'],
                   ['Estudiante de Maestría en Recursos Digitales Aplicados a la Educación', 'Universidad de Cartagena'], ['Piloto de drones', '']]},
       'pie': {'logo': 'logo.png', 'texto': 'Grupo Invercoal'}}
open(W + '/sitio/config.js', 'w', encoding='utf-8').write('/* Generado por config_web.py: se puede editar a mano */\nself.PLANO = ' + json.dumps(cfg, ensure_ascii=False, indent=1) + ';\n')
print('config.js', round(aw), 'x', round(ah), 'mm')
