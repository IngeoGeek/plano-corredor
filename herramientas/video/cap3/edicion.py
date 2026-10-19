SERIE = 'Del plano de QGIS a la maqueta 3D'
NUM = 3
TITULO = 'Exportar las imágenes del plano'
AUTOR = 'Osney Izaquita'
SIGUIENTE = 'Capítulo 4 · Mapa de alturas y medidas para Blender'
SECCIONES = {
    's02': 'ppp = píxeles ÷ (ancho en mm ÷ 25,4)',
    's03': '3.1  La hoja completa (dos veces)',
    's07': '3.2  Solo el mapa principal',
}
TABLA_TITULO = 'Resultado del capítulo 3'
COL1 = 'Imagen'
TABLA = [
    ('plano_hoja.jpg · hoja completa, base de la maqueta', '3.1', '116 ppp · 4 110 × 2 740 px'),
    ('plano_hoja_hd.jpg · hoja completa, plano 2D con zoom', '3.1', '254 ppp · 9 000 × 6 000 px'),
    ('plano_mapa.jpg · solo el mapa, piel del relieve', '3.2', '160 ppp · ≈ 4 114 × 3 585 px'),
]
COMPROBACION = ('Las texturas de la maqueta no deben pasar de unos 4 100 px por lado', 'plano_hoja.jpg y plano_mapa.jpg cumplen; la HD solo se usa para el plano 2D')
