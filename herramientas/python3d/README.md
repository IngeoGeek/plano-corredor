# Maqueta 3D sin Blender (Python puro)

`maqueta_python.py` reemplaza a `../maqueta_blender.py` + `../chinchetas_blender.py` con los mismos insumos y la misma salida:
relieve en 4 mosaicos de textura, paredes del bloque, hoja con canto, rótulo en alta, chinchetas con letreros de doble cara y
`alturas.json` para el GPS. Probado con el Corredor Carbonífero (1:65 000, VE 2,5): 9 s en lugar de minutos, GLB de 17,2 MB
(Blender: 17,6 MB), 340 000 caras de relieve, misma rejilla de alturas y misma apariencia en model-viewer.

    pip install --break-system-packages trimesh pyfqmr pillow numpy
    python3 maqueta_python.py W SALIDA [--esc 65000 --ve 2.5 --zmin 100 --zocalo 0.004 --caras 340000 --sin-chinchetas]
    python3 -I ../glb2usdz.py SALIDA/plano_relieve.glb SALIDA/plano_relieve.usdz   # y borrar SALIDA/usd_tmp

Cómo resuelve lo que hacía Blender:
- Decimate → `pyfqmr` (simplificación cuádrica) por mosaico con `preserve_border=True`: los bordes entre mosaicos y el contorno
  quedan intactos, así no hace falta el `bisect` y las paredes se arman con el contorno completo de la rejilla.
- Cortes de mosaico: la columna y la fila más cercanas a la mitad del mapa se mueven exactamente a la mitad (menos de media celda)
  interpolando su altura.
- Paredes: el contorno se recorre en sentido horario y se baja a z = 0; caras planas (vértices sin compartir).
- Materiales: rugosidad 1, metálico 0 y `KHR_materials_specular` = 0 parchado en el JSON del GLB; texturas en JPEG
  (no copiar mallas con `copy()`: se pierde el formato y trimesh las guarda en PNG). Colores planos convertidos a lineal.
- Normales: exportar con `include_normals=True` (sin ellas el relieve se ve facetado).
