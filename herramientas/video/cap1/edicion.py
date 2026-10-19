# Configuración de la edición del capítulo 1
SERIE = 'Del plano de QGIS a la maqueta 3D'
NUM = 1
TITULO = 'Preparar el proyecto en QGIS y anotar las medidas'
AUTOR = 'Osney Izaquita'
SIGUIENTE = 'Capítulo 2 · Modelo digital de elevación (DEM)'
# Rótulo de sección que aparece arriba a la izquierda al empezar ciertos segmentos (coincide con la guía escrita)
SECCIONES = {
    's02': '1.1  Revisar que el proyecto esté en metros',
    's07': '1.2  Copiar los parámetros de la proyección',
    's12': '1.3  Leer la escala y la extensión del mapa',
    's16': '1.4  Posición y tamaño del mapa en la hoja',
    's18': '1.5  Tamaño de la hoja',
}
# Tarjeta de resumen (segmento t1)
TABLA_TITULO = 'Hoja de anotaciones'
TABLA = [
    ('Proyección (lat_0 · lon_0 · k · x_0 · y_0 · elipsoide)', '1.2', '4 · −73 · 0.9992 · 5000000 · 2000000 · GRS80'),
    ('Escala del mapa', '1.3', '1:65 000'),
    ('X mín · X máx', '1.3', '4885966.641 · 4928420.741'),
    ('Y mín · Y máx', '1.3', '2241436.912 · 2278431.036'),
    ('Posición del mapa  x · y (mm)', '1.4', '20.57 · 15.43'),
    ('Tamaño del mapa  ancho · alto (mm)', '1.4', '653.14 · 569.14'),
    ('Tamaño de la hoja  ancho · alto (mm)', '1.5', '900 · 600'),
]
COMPROBACION = '(X máx − X mín) ÷ (ancho del mapa en mm ÷ 1000) = escala',  '42 454,1 ÷ 0,65314 = 65 000  ✓'
