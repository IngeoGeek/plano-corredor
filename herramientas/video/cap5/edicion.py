SERIE = 'Del plano de QGIS a la maqueta 3D'
NUM = 5
TITULO = 'Construir la maqueta en Blender'
AUTOR = 'Osney Izaquita'
SIGUIENTE = 'Capítulo 6 · Chinchetas y rótulos'
SECCIONES = {
    's04': '5.1  La hoja',
    's13': '5.2  La rejilla del relieve',
    's17': '5.3  Levantar el relieve',
    's23': '5.4  Las paredes del bloque',
}
TABLA_TITULO = 'Resultado del capítulo 5'
COL1 = 'Pieza'; COL2 = ''
TABLA = [
    ('Hoja 900 × 600 mm · materiales Hoja y Canto', '', 'Solidify 4 mm'),
    ('Rejilla 600 × 522 · X −102,86 · Y 0 · Z 0,5 mm', '', '653,14 × 569,14 mm'),
    ('Displace: relieve.png, Non-Color, Extend, UV, Z', '', 'Strength 0,07308'),
    ('Decimate Collapse', '', 'Ratio 0,5 · ≈ 313 000 caras'),
    ('Paredes hasta Z = 0 con material Pared', '', 'Shift + N · Auto Smooth 30°'),
]
COMPROBACION = ('La escena queda guardada como maqueta.blend en la carpeta de trabajo', 'Siguiente paso: chinchetas, rótulos y exportar a .glb y .usdz')
