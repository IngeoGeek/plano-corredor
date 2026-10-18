"""Lista los elementos de los diseños de un proyecto QGIS (.qgz) para tomar las medidas del marco del mapa y del rótulo.
Uso: python3 diseno_qgis.py proyecto.qgz [nombre_diseño]"""
import sys, zipfile, xml.etree.ElementTree as ET
z = zipfile.ZipFile(sys.argv[1]); r = ET.fromstring(z.read([n for n in z.namelist() if n.endswith('.qgs')][0]))
for lay in r.iter('Layout'):
    if len(sys.argv) > 2 and lay.get('name') != sys.argv[2]: continue
    print('DISEÑO', lay.get('name'))
    for it in lay.iter('LayoutItem'):
        if it.get('type') == '65639':
            e = it.find('Extent'); print('  MAPA', it.get('id'), 'tamaño', it.get('size'), 'posición', it.get('position'), 'extensión', e.attrib if e is not None else '')
        elif it.get('id'): print('  ', it.get('type'), it.get('id'), it.get('size'), it.get('position'))
