# Herramientas: plano QGIS → plano 2D, maqueta 3D y realidad aumentada

Scripts con los que se hizo `v2/`. Se corren en este orden desde una carpeta de trabajo `W`:

| # | Script | Entrada → salida | Qué ajustar para otro plano |
|---|---|---|---|
| 1 | `diseno_qgis.py proyecto.qgz` | Lista los elementos del diseño | Tomar marco del mapa (posición, tamaño, extensión) y caja del rótulo → `W/layout.json` `{"map":[x,y,w,h],"rot":[x,y,w,h],"page":[ancho_mm,alto_mm]}` |
| 2 | `dem.py W` | Curvas (`curvas.geojson`) → `dem30.npy`, `dem30.json` | Extensión `E0,E1,N0,N1` del marco; si hay DEM real, remuestrearlo a 30 m y saltar este paso. Luego el suavizado adaptativo → `dem30f.npy` (ver guía) |
| 3 | `pdftoppm -r 255 -png -singlefile plano.pdf W/tex/page255` + `texturas.py W` | PDF → mosaicos `tex2/` | Nada (usa `layout.json`) |
| 4 | `blender -b --factory-startup --python maqueta_blender.py -- W W/out2` | Maqueta GLB + .blend | `ESC` (escala), `VE` (exageración), `ZMIN` (cota mínima) |
| 5 | `etiquetas.py W` | Capas del GeoPackage → `etiquetas.json` | Nombres de capas/campos de títulos, municipios, fallas, pliegues, puntos |
| 6 | `atlas_letreros.py W` + `blender -b --factory-startup --python chinchetas_blender.py -- W W/out2` | Chinchetas 3D en el GLB | Grupos que van dentro del modelo |
| 7 | `glb2usdz.py W/out2/plano_relieve.glb W/out2/plano_relieve.usdz` | GLB → USDZ (iPhone) | Nada |
| 8 | `dzi.py W/tex/page255.png v2/plano2d` | Teselas del plano 2D | Nada |
| 9 | `plantilla_v2.html` → `index.html` (`__MODO__`=auto) y `ver.html` (`__MODO__`=navegador); `sw_plantilla.js` → `sw.js` | Página | Títulos, ficha técnica, membrete, constantes `MARCO` e `IMG`, nombre de la caché |

Dependencias: GDAL/ogr2ogr, Python (numpy, scipy, pillow, shapely, trimesh, usd-core, qrcode), Blender ≥ 4.0, poppler (pdftoppm).
Librerías web ya incluidas en `lib/` y `v2/lib/`. Ver la guía técnica para el porqué de cada decisión.
