SERIE = 'Del plano de QGIS a la maqueta 3D'
NUM = 2
TITULO = 'Modelo digital de elevación (DEM)'
AUTOR = 'Osney Izaquita'
SIGUIENTE = 'Capítulo 3 · Exportar las imágenes del plano'
SECCIONES = {
    's02': '2.1  Interpolar desde curvas de nivel',
    's10': '2.3  Suavizar el relieve',
    's16': '2.4  Leer la cota mínima y la máxima',
}
TABLA_TITULO = 'Resultado del capítulo 2'
TABLA = [
    ('Interpolación TIN (curvas como líneas de estructura)', '2.1', 'dem_tin.tif · celdas de 30 m'),
    ('Combar a 90 m con Media', '2.3', 'dem90.tif'),
    ('Combar a 30 m con Cubic B-Spline y extensión del mapa', '2.3', 'dem_suave.tif · 1415 × 1233 celdas'),
    ('Cota mínima y máxima (precisión Real)', '2.4', '103,78 m · 1 983,76 m'),
    ('Cotas redondeadas para la hoja de anotaciones', '2.4', 'z mín = 100 · z máx = 2000'),
]
COMPROBACION = ('Extensión de dem_suave = extensión del mapa principal', '4885966.641 · 4928420.741 · 2241436.912 · 2278431.036')
