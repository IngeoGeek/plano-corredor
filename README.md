PLANO EN REALIDAD AUMENTADA - PUBLICACIÓN GRATUITA EN GITHUB PAGES

Contenido:
  index.html        página del visor (model-viewer de Google)
  plano_90x60.glb   modelo 3D para Android y navegadores (90 x 60 cm reales)
  plano_90x60.usdz  modelo 3D para iPhone/iPad (AR Quick Look)
  poster.jpg        imagen que se muestra mientras carga

Pasos:
 1. Crear una cuenta gratuita en github.com.
 2. New repository -> nombre corto (ej. plano-corredor) -> Public -> Create.
 3. "uploading an existing file" -> arrastrar los 4 archivos -> Commit changes.
 4. Settings -> Pages -> Source: Deploy from a branch -> Branch: main, carpeta / (root) -> Save.
 5. En 1-3 minutos la página queda en https://USUARIO.github.io/plano-corredor/
 6. Abrir esa dirección en el celular y probar el botón "Ver en tu espacio".
 7. Generar el QR con esa dirección exacta (QR estático, corrección de errores M o Q)
    e insertarlo en el rótulo del plano en QGIS (Diseño -> Añadir imagen). Tamaño mínimo impreso: 2,5 x 2,5 cm.

Para cambiar el plano: reemplazar los archivos .glb y .usdz con el mismo nombre. La URL y el QR no cambian.

MODO CON MARCADOR (cualquier celular con cámara, sin ARCore)
  ra.html                    página que abre la cámara (AR.js + A-Frame, en lib/)
  marcador_10cm_carta.pdf    hoja para imprimir al 100 %: el cuadro negro debe medir 10 x 10 cm
  marcador_10cm.png          el mismo marcador a 300 ppp, para insertarlo en el rótulo del plano
  marcador.patt              patrón que reconoce la cámara (no editar)
El QR del marcador abre directamente ra.html. Si el marcador se imprime a otro tamaño, el plano
se verá proporcionalmente más grande o más pequeño (10 cm de marcador = 90 x 60 cm de plano).

MODO NAVEGADOR SIN MARCADOR (celulares sin ARCore)
  ver.html        realidad aumentada en el piso a escala real (motor 8th Wall, en lib/8thwall)
  lib/8thwall     motor de Niantic Spatial, distribuido sin modificar bajo su XR Engine License Agreement (lib/8thwall/LICENSE)
  lib/three       three.js r147 (licencia MIT)
index.html envía a ver.html cuando el celular no tiene el visor nativo. El QR del plano no cambia.
