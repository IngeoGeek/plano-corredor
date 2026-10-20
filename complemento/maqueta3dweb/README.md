# Maqueta 3D Web (complemento de QGIS)

Convierte un plano de QGIS o un vuelo de fotogrametría en una página web con plano 2D, maqueta 3D,
realidad aumentada a tamaño real, GPS, uso sin internet y un solo QR que funciona en cualquier celular.

## Instalar
QGIS → Complementos → Administrar e instalar complementos → **Instalar a partir de ZIP** → `maqueta3dweb.zip`.
Queda en el menú **Maqueta 3D Web** y en la barra de herramientas. La primera vez que se pulsa «Generar»
pide permiso para instalar trimesh, pyfqmr y qrcode (y usd-core, opcional, para el iPhone). No usa Blender.

## Uso
1. **Insumo**
   - *GeoPackage*: el .gpkg con el proyecto guardado dentro (Proyecto → Guardar en → GeoPackage). Elige el diseño,
     el mapa principal y el DEM (dentro del proyecto o un archivo aparte). En la tabla se marcan las capas que
     van como etiquetas en la página o como chinchetas 3D.
   - *Fotogrametría*: solo la carpeta del vuelo procesado. Reconoce DJI Terra, WebODM, Pix4D y, en general,
     cualquier carpeta con un OBJ (Metashape u otros). Busca solo la malla (también bloques en .zip), el sistema de
     coordenadas, la ortofoto y los reportes (fotos, RTK, GSD, área). Si no hay ortofoto, la arma con las texturas de la malla.
2. **Autor y empresa**: perfiles guardados (empresa, logo, color, nombre y títulos). Se editan cuando cambie algo
   (otra empresa, un título nuevo) y se guardan para la próxima vez.
3. **Textos del plano**: título y subtítulo de la página.
4. **Publicar**
   - *Solo carpeta y .zip*: deja `sitio/` y `sitio.zip`; si se escribe la dirección donde quedará, también hace el QR.
   - *GitHub*: «Conectar con GitHub…» una sola vez (abre la página del permiso con la casilla «repo» ya marcada;
     se pega el código `ghp_…` y queda guardado cifrado en QGIS). Después basta escribir el nombre del repositorio:
     lo crea, sube todo, activa GitHub Pages y deja `QR.png`. Si el repositorio ya existe, **no pisa nada**: publica en
     una carpeta nueva `v2/`, `v3/`… con su propio QR.

## Un solo QR para todos los celulares
La página intenta primero la realidad aumentada del propio celular (ARCore en Android, Quick Look en iPhone).
Si no arranca o el celular no tiene ARCore, pasa sola al modo alternativo en el navegador; también hay un enlace
«¿No funciona la realidad aumentada? Usar modo alternativo». Si el QR se abre dentro de WhatsApp, Instagram u
otra app, la página ofrece abrirla en Chrome o Safari.

## Probado
- GeoPackage del Corredor Carbonífero: 1:65 000, 17,6 s, página revisada en un Android simulado.
- Carboland (DJI Terra, 4 bloques, 10,4 millones de caras, uno en .zip, sin result.tif): 1:500, 300 000 caras,
  maqueta de 12,4 MB, 83 s.
- Publicación en GitHub: flujo completo probado contra una API simulada; falta la primera prueba con una cuenta real.
