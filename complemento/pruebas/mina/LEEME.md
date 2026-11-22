# Pruebas del modo «Mina subterránea»

Datos ficticios: `hacer_mina.py` genera una mina sintética en EPSG:9377 (inclinado y tambores en 3D, niveles en 2D con
textos de cota, cruzada, chimenea, labores abandonadas y proyectadas, límite del título y curvas de nivel) y un DEM.

```
python3 hacer_mina.py mina_sintetica.dxf dem_sintetico.tif R2000
dxf2dwg -y -o mina_sintetica.dwg mina_sintetica.dxf          # LibreDWG, para probar la ruta DWG
python3 probar_mina.py mina_sintetica.dxf dem_sintetico.tif salida   # núcleo sin ventana
QT_QPA_PLATFORM=offscreen python3 prueba_desde_zip.py <carpeta con el ZIP descomprimido> <carpeta de datos> <salida>
python3 capturas.py salida/sitio capturas                     # Playwright, escritorio y Pixel 7
```
