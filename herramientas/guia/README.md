# Guía manual con capturas (QGIS y Blender)

Herramientas con que se hizo la «Guía manual: del plano de QGIS a la maqueta 3D con realidad aumentada, GPS y QR»
(documento de Claude Docs; su texto está en `guia_corredor_texto.txt` como modelo de estructura y redacción).
Las rutas absolutas de los scripts apuntan al scratchpad de la sesión original: cambiar `OUT`/`C`/`F` al usarlos.

## Capturas de QGIS (`qcap_base.py`)
- QGIS se abre bajo Xvfb con el proyecto y `--code script.py`. El script encadena pasos con `@paso(ms)`:
  cada paso abre un diálogo o panel (PyQGIS: `iface.showProjectPropertiesDialog('mProjOptsCRS')`, `processing.createAlgorithmDialog(alg, params)`,
  `iface.openLayoutDesigner(lay)`, `d.showItemOptions(item, True)`…) y `foto(nombre, recorte, marcas)` guarda la captura y los rectángulos a resaltar.
- Las marcas se toman de los widgets reales: `rect(widget) + ['1']` (posición global y número del recuadro). `volcar(w, archivo)` lista
  los widgets visibles con su nombre, texto y rectángulo: hacerlo primero para saber qué resaltar.
- Diálogos modales: abrirlos y capturarlos con `QTimer.singleShot` antes de cerrarlos con `cerrar_modales()`.
- `ejemplo_qgis/`: SRC del proyecto, diseño (escala, extensión, posición y tamaño, página), TIN, Combar, Traducir, etiquetas CSV, menús de un botón.

## Capturas de Blender (`ejemplo_blender/gui_cap.py` + `pasos.py`)
- Blender con interfaz bajo Xvfb y `--python gui_cap.py`; pasos con `bpy.app.timers` (registrar con `persistent=True` si algo carga archivos).
  `pasos.py` reproduce con bpy exactamente lo que la guía manda hacer a mano, para que las capturas muestren el estado correcto.
- Captura con `import -window root`. Cambiar de editor y pestaña con `area.type`, `area.spaces[0].context`, panel N con `show_region_ui`.
- Las marcas de Blender se escriben a mano en `lista_b.py` (no hay coordenadas de botones en bpy): medirlas sobre la captura.

## Anotar (`anotar.py`)
- `anotar(nombre, recorte, marcas, escala)`: recuadros rojos redondeados de 4 px y círculo numerado; recorta alrededor de las marcas
  (o la región dada) y guarda en `fin/`. `lista_q.py` y `lista_b.py` son las listas de capturas de la guía del Corredor.
- Ojo: el factor 1.0425 compensa la escala de Qt con que se tomaron esas capturas. Si QGIS corre con `QT_SCALE_FACTOR=1`,
  `QT_AUTO_SCREEN_SCALE_FACTOR=0` (como en `herramientas/video/rec/grabar.sh`), usar factor 1.

## Estructura de la guía (ver `guia_corredor_texto.txt`)
Qué vas a construir (resultado, kit, programas, datos, tiempo y carpetas, recorrido) → pasos numerados (título con verbo, subpasos
1.1, 1.2…, listas numeradas de clics con la ruta de menús en negrita, «recuadro N» que coincide con la captura, valor del ejemplo
en cada campo) → hoja de anotaciones (tabla dato · dónde se lee · ejemplo) con comprobaciones aritméticas → solución de problemas →
replicarlo en cualquier zona → lista de verificación final → enlaces.
