# Maqueta 3D Web (complemento de QGIS)

Convierte un plano de QGIS, un vuelo de fotogrametría o el plano de labores de una mina subterránea (DWG o DXF)
en una página web con plano 2D, maqueta 3D, realidad aumentada, GPS, uso sin internet y un solo QR que funciona
en cualquier celular.

## Instalar
QGIS → Complementos → Administrar e instalar complementos → **Instalar a partir de ZIP** → `maqueta3dweb.zip`.
Queda en el menú **Maqueta 3D Web** y en la barra de herramientas. La primera vez que se pulsa «Generar»
pide permiso para instalar trimesh, pyfqmr y qrcode (y usd-core, opcional, para el iPhone); el modo de mina añade
ezdxf (y scipy y matplotlib si la instalación de QGIS no los trae). No usa Blender.

## Uso
1. **Insumo**
   - *GeoPackage*: el .gpkg con el proyecto guardado dentro (Proyecto → Guardar en → GeoPackage). Elige el diseño,
     el mapa principal y el DEM (dentro del proyecto o un archivo aparte). En la tabla se marcan las capas que
     van como etiquetas en la página o como chinchetas 3D.
   - *Fotogrametría*: solo la carpeta del vuelo procesado. Reconoce DJI Terra, WebODM, Pix4D y, en general,
     cualquier carpeta con un OBJ (Metashape u otros). Busca solo la malla (también bloques en .zip), el sistema de
     coordenadas, la ortofoto y los reportes (fotos, RTK, GSD, área). Si no hay ortofoto, la arma con las texturas de la malla.
   - *Mina subterránea*: el plano de labores en DWG o DXF, donde cada capa es un tipo de labor (nivel, inclinado,
     cruzada, tambor, sobreguía, patio, frente, labor abandonada o proyectada) y sus líneas son los ejes que levanta el
     topógrafo. «Leer el plano» llena la tabla de capas con el tipo sugerido por el nombre, el color del plano y la
     sección típica (ancho × alto), todo editable; las capas que no son labores (curvas de nivel, rótulo, cuadrícula)
     quedan sin marcar. Ver la sección «Mina subterránea» más abajo.
2. **Autor y empresa**: perfiles guardados (empresa, logo, color, nombre y títulos). Se editan cuando cambie algo
   (otra empresa, un título nuevo) y se guardan para la próxima vez.
3. **Textos del plano**: título y subtítulo de la página.
4. **Publicar**
   - *Solo carpeta y .zip*: deja `sitio/` y `sitio.zip`; si se escribe la dirección donde quedará, también hace el QR.
   - *GitHub*: «Conectar con GitHub…» una sola vez (abre la página del permiso con la casilla «repo» ya marcada;
     se pega el código `ghp_…` y queda guardado cifrado en QGIS). Después basta escribir el nombre del repositorio:
     lo crea, sube todo, activa GitHub Pages y deja `QR.png`. Si el repositorio ya existe, **no pisa nada**: publica en
     una carpeta nueva `v2/`, `v3/`… con su propio QR.

## Mina subterránea (DWG o DXF)
- **Cotas.** Si los ejes son polilíneas 3D, se usa su cota. Si están en 2D, los textos de cota cercanos (capa de cotas,
  p. ej. «845,32» o «Cota 845.3») se proyectan sobre el eje y la cota se interpola a lo largo de él; un eje sin textos
  toma la de sus vecinos. También se puede poner una cota fija a una capa. Un nivel dibujado de lado a lado que
  atraviesa el inclinado se une a él si ambos tienen la misma cota en el cruce; si no, una labor pasa sobre la otra.
- **Qué se calcula.** Red de galerías con sus uniones, bocaminas (bloque o texto «BOCAMINA») y frentes (extremos
  activos); longitud e inclinación de cada tramo, recorrido desde la bocamina, cubierta de roca sobre cada frente
  (con superficie) y distancia en planta al límite del título (capa del límite).
- **Superficie.** Opcional: un DEM (capa o archivo, con ortofoto si hay) o la carpeta de un vuelo con dron. En la página
  la superficie es transparente y se puede apagar; el límite del título se dibuja como una pared vertical.
- **Colores.** La Resolución 40600 de 2015 recomienda diferenciar con colores los niveles de explotación (numeral 2.6,
  literal m), pero no asigna un color a cada tipo de labor. Por eso se ofrecen los colores del plano o una convención
  de la empresa (nivel y patio en amarillo, inclinado en gris…), editable en la tabla.
- **Metano (modelo ilustrativo).** En la tabla de frentes se anota el % de CH₄ medido (y, si se midieron, la velocidad
  del aire o el caudal); también se puede importar un CSV con columnas `frente;ch4;fecha;velocidad;caudal`. El aire de
  cada frente se lleva por el camino más corto hasta la bocamina de salida; sin caudales, sin diluirse (caso
  desfavorable), y con ellos se mezcla en las uniones. Contra la corriente retrocede según C·e^(−u·x/E), con E ≈ 2 m²/s
  por defecto (fórmula de Taylor para galerías rectas; Bahrami et al., 2019, *Mining, Metallurgy & Exploration*, 36,
  513–521, doi:10.1007/s42461-019-0058-6). Con el caudal del frente se calcula el aire necesario para no pasar de 1,0 %
  y el número de estratificación de Bakke y Leach. Las clases de color siguen el artículo 53 del Decreto 1886 de 2015
  (0,5 %, 1,0 %, 1,5 % y 2,0 %). Es un apoyo para socializar el riesgo: no reemplaza la medición con el detector ni el
  estudio de ventilación.
- **Página.** Encender o apagar cada capa, transparencia de la superficie, longitudes de los tramos, frentes con su
  metano, profundidad, medir entre dos puntos (distancia, planta y desnivel), tabla de frentes que acerca la cámara,
  «Mi ubicación» en superficie (dice qué labor pasa debajo y a qué profundidad), plano 2D, modo anotación y uso sin
  internet. Además se genera `plano_carta.pdf` (carta horizontal con convenciones, metano medido y el QR).
- **Abrir un DWG.** Se convierte a DXF con lo que haya en el equipo: ODA File Converter (gratuito; revise sus
  condiciones de uso en la empresa), LibreDWG `dwg2dxf` (libre, GPL-3; en Windows el complemento ofrece descargarlo,
  unos 13 MB, y verifica su huella SHA-256) o, como último recurso, el controlador CAD de GDAL (solo DWG R2000 y lee
  poco). Si nada sirve, guarde el plano como DXF desde AutoCAD o Civil 3D.
- **Privacidad.** El plano de una mina activa no debería quedar en un repositorio público: el complemento pide
  confirmar antes de publicarlo en GitHub Pages. Para uso interno, «Solo carpeta y .zip» y un servidor propio.

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
- Mina subterránea (0.4.0): mina sintética con inclinado y tambores en 3D, niveles en 2D con textos de cota, cruzada,
  chimenea de ventilación, labores abandonadas y proyectadas, límite del título, curvas de nivel y DEM; 15 capas,
  7 frentes, 3 con metano, 1:500, unos 3 s. Probado en QGIS 3.34 sin pantalla desde el ZIP con la ventana completa, con
  DXF y con el mismo plano en DWG (LibreDWG), y lectura de DWG de AutoCAD 2000 a 2018. Página revisada en escritorio y
  en un Android simulado. Falta probarlo con un plano real de Km4 o Corinto y en QGIS de Windows.
