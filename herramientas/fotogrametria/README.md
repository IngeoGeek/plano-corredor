# Fotogrametría (DJI Terra) → maqueta 3D, RA, GPS, sin internet y QR

Usa la página del kit `../../kit-manual/` (todo se configura en `config.js`). Probado con el acopio Carboland
(EPSG:3116, 382 fotos RTK FIX, 8,9 ha, 1:500) → github.com/IngeoGeek/Carboland_octubre.

Carpeta de trabajo `W`; `P` = carpeta del proyecto de DJI Terra (la que tiene `map/` y `models/`).

| Paso | Comando | Sale |
|---|---|---|
| 1 | `python3 leer_dji.py P W [escala]` | `W/proyecto.json`: EPSG, origen del OBJ, extensión de la ortofoto, escala, proyección para el GPS, ficha |
| 2 | `python3 texturas.py P/models/pc/0/terra_obj W/tex 8` | texturas a 1/8 con el fondo negro rellenado |
| 3 | por bloque: `blender -b --factory-startup --python bloque.py -- Bloque.obj W/dec_NOMBRE RATIO` | `dec_*.blend` + `.json` (RATIO ≈ 450 000 ÷ caras totales) |
| 4 | `blender -b --factory-startup --python unir.py -- W [ratio_final]` | `W/sitio/plano_relieve.glb` (≤ 30 MB), `info.json`, `vert_real.npy`, `maqueta.blend` |
| 5 | `python3 alturas.py W` | `W/sitio/relieve.png` (16 bits, rejilla 0,5 m) para el GPS |
| 6 | `python3 plano2d.py W [ortofoto_liviana.tif]` | `W/sitio/plano.jpg` |
| 7 | `python3 -I ../glb2usdz.py W/sitio/plano_relieve.glb W/sitio/plano_relieve.usdz` | modelo para iPhone (borrar `usd_tmp/` después) |
| 8 | `python3 config_web.py W "Título" "Subtítulo"` y copiar `kit-manual/` (sin `config.js` ni `LEEME.txt`) en `W/sitio` | página lista |

Prueba: `python3 -m http.server` dentro de `W/sitio` y abrir `/?prueba=lat,lon` (GPS simulado) y `/?modo=navegador`.
