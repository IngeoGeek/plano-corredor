SERIE = 'Del plano de QGIS a la maqueta 3D'
NUM = 4
TITULO = 'Mapa de alturas y medidas para Blender'
AUTOR = 'Osney Izaquita'
SIGUIENTE = 'Capítulo 5 · Construir la maqueta en Blender'
SECCIONES = {'s02': '4.1  Convertir el DEM en relieve.png'}
TABLA_TITULO = '4.2  Medidas de la maqueta'
COL1 = 'Qué y cómo se calcula'; COL2 = ''
TABLA = [
    ('Escala E = (X máx − X mín) ÷ (ancho mapa mm ÷ 1000)', '', '65 000'),
    ('Exageración vertical VE (se elige: 2 a 3)', '', '2,5'),
    ('Fuerza del relieve = (z máx − z mín) × VE ÷ E', '', '0,07308 m'),
    ('Posición X = x + ancho ÷ 2 − ancho hoja ÷ 2', '', '−102,86 mm'),
    ('Posición Y = alto hoja ÷ 2 − (y + alto ÷ 2)', '', '0,00 mm'),
    ('Posición Z (fija)', '', '0,5 mm'),
]
COMPROBACION = ('Fuerza: 1 900 × 2,5 ÷ 65 000 = 0,07308 m (7,3 cm de alto)', 'Posición X: 20,57 + 326,57 − 450 = −102,86 mm')
