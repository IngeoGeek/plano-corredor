# Fotogrametría (DJI Terra) → maqueta 3D, RA, GPS y QR

Se usa con el kit `kit-manual/` (la página se configura con `config.js`). Orden, desde una carpeta de trabajo `W`:

1. `python parametros.py PROYECTO W [escala]` → `params.json` (EPSG, origen del OBJ, extensión de la ortofoto, escala).
2. `python texturas_obj.py PROYECTO/models/pc/0/terra_obj W/tex 8` → texturas a 1/8 con bordes rellenos.
3. Por bloque: `blender -b --factory-startup --python bloque.py -- Bloque.obj W/dec_NOMBRE 0.025` (ratio ≈ 250 000 caras ÷ caras totales).
4. `blender -b --factory-startup --python unir.py -- W` → `W/sitio/plano_relieve.glb`, `info.json`, `vert_real.npy`.
5. `python alturas.py W` → `W/sitio/relieve.png`. `python plano2d.py PROYECTO W` → `W/sitio/plano.jpg`.
6. `python ../glb2usdz.py W/sitio/plano_relieve.glb W/sitio/plano_relieve.usdz`.
7. Copiar `kit-manual/` en `W/sitio` y llenar `config.js` con `params.json` e `info.json` (hoja = marco = extensión de la ortofoto, `x_mm: 0, y_mm: 0`, exageración 1).

Ejemplo: acopio Carboland (EPSG:3116, 1:500, 382 fotos) → github.com/IngeoGeek/Carboland_octubre.
