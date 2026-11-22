import sys, time, json; sys.path.insert(0, '/home/claude/plano-corredor/complemento')
from osgeo import gdal; gdal.UseExceptions()
from maqueta3dweb.nucleo import mina
t = time.time()
plano, dem, salida = sys.argv[1], sys.argv[2], sys.argv[3]
D = mina.analizar(plano)
M = mina.preparar(D, D['tabla'], {'eje': 'piso'})
lect = {'FRENTE N2 NORTE': (1.2, None), 'FRENTE N2 SUR': (0.6, None), 'FRENTE N1 NORTE': (0.3, None), 'AVANCE INCLINADO': (0.9, 0.25), 'FRENTE CRUZADA M2': (0.2, None)}
filas = [{'E': f['E'], 'N': f['N'], 'nombre': f['nombre'], 'mostrar': True, 'ch4': lect.get(f['nombre'], (None,))[0], 'fecha': '18/11/2026',
          'u': lect.get(f['nombre'], (None, None))[1]} for f in M['frentes']]
from osgeo import osr
s = osr.SpatialReference(); s.ImportFromEPSG(9377)
r = mina.procesar(dict(plano=plano, datos=D, tabla=D['tabla'], eje='piso', superficie={'dem': dem}, crs_wkt=s.ExportToWkt(), crs_nombre='MAGNA-SIRGAS / Origen-Nacional (EPSG:9377)',
                       proyeccion=dict(lat_0=4, lon_0=-73, k=0.9992, x_0=5000000, y_0=2000000, elipsoide='GRS80'),
                       frentes_cfg=filas, metano={'E': 2.0, 'u': 0.3, 'retorno': 'BOCAMINA 2 VENTILACION'}, salida=salida,
                       titulo='Mina sintética de prueba', subtitulo='Plano de labores de prueba · socialización de instrucciones técnicas',
                       elaboro={'nombre': 'Msc. Ing. Osney Izaquita', 'titulos': [['Ingeniero Geólogo', 'UPTC']]}, pie='Grupo Invercoal',
                       funciones={'gps': True, 'sin_internet': True, 'instalar': True}, url='https://ejemplo.org/mina-prueba/', plano_carta=True))
print('LISTO', f'{time.time() - t:.1f} s', r['escala'], [c['material'] + ':' + c['capa'] for c in r['capas']])
