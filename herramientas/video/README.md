# Video tutorial de la guía manual (grabación real de QGIS + voz Kokoro)

Capítulo 1 hecho con estas herramientas (3 min 18 s, 1080p). Rutas absolutas de los scripts apuntan al scratchpad de la sesión original: ajustarlas.

Preparación del entorno (Linux):
- `apt-get install openbox qttranslations5-l10n` (ventanas con barra de título y diálogos de Qt en español).
- `pip install kokoro-onnx soundfile sherpa-onnx` + modelos de GitHub: `thewh1teagle/kokoro-onnx` (model-files-v1.0: kokoro-v1.0.onnx, voices-v1.0.bin) y `k2-fsa/sherpa-onnx` (asr-models: sherpa-onnx-whisper-small) para verificar la pronunciación.
- Perfil de QGIS copiado aparte (`--profiles-path`), con `[locale] userLocale=es`, `stylesheet\fontPointSize=11`, sin `recentProjects\*` ni `LayoutDesigner\state` (paneles por defecto).
- Proyecto en `/home/osney/Plano3D/` (qgz + gpkg).

Orden por capítulo (carpeta capN con guion.py, grabar_capN.py, edicion.py):
1. `python3 tts.py capN` → audio/*.wav y duraciones.json (voz em_alex). `python3 asr.py MODELO capN` para revisar lo que se entiende.
2. `rec/grabar.sh capN/grabar_capN.py capN/bruto.mp4` → Xvfb 1920×1080 + openbox + ffmpeg x11grab; el script mueve el cursor y hace clics reales con QTest y anota eventos (eventos.jsonl). Un destello rojo sincroniza video y registro.
3. `python3 editar.py capN [--rapido]` → tarjetas, zoom, recuadros numerados, anillos de clic, rótulos de sección, narración, subtítulos (pista mov_text + .srt).

Lecciones: los clics que abren ventanas modales se lanzan con QTimer.singleShot(0) para no bloquear el guion; el menú contextual del diseño se abre con clic derecho real (mousePress); los QgsCollapsibleGroupBox llegan como QGroupBox en Python (usar sip.cast o el botón collapseButton); el texto del menú es «Propiedades de la página…».

## Blender (capítulo 5) — lo aprendido

- `grabar_b.sh` + `motor_b.py`: entrada real con **xdotool** (mover, clic, teclas, escribir) y botones por **OCR** (tesseract): captura de la región, ×3, gris, negativo, umbral 55 %, `--psm 11`. Palabras de 1–2 letras se comparan exactas. Siempre buscar en una **región** (panel N `1345,100,220,880`; propiedades `1590,380,330,680`); pantalla completa es lenta.
- `ui_scale` 1.15, ventana maximizada con openbox (desfase Y de 19 px). Pestañas de propiedades (x 1605): escena 565, modificadores 708, datos 835, material 868, textura 907. Tras hacer clic en una pestaña, **sacar el cursor** (la ayuda emergente tapa el texto) y verificar `space.context`; si no cambió, ponerlo por bpy.
- Temporizador con `persistent=True` (elegir «General» en la bienvenida carga un archivo nuevo y borra los temporizadores no persistentes). No guardar referencias Python a modificadores entre acciones de la interfaz (si la interfaz los borra, Blender se cae): buscarlos por nombre.
- Campos: doble clic, Ctrl+A, Backspace, escribir con unidad (`900mm`), Enter. Campos de propiedades: localizar la **etiqueta** por OCR y hacer clic en x 1820 en esa fila (resiste a que el panel se mueva). Panel N: filas cada 22–23 px bajo la etiqueta (Location, Dimensions, Median).
- Menús: Shift+A y submenús por OCR alrededor del cursor (±450 px); el de nodos (Image Texture) es ancho, buscar hasta 1050 px a la izquierda. Add Modifier: OCR de la categoría (Generate/Deform) a la derecha y del elemento a la izquierda; si no aparece, reintentar ±10 px.
- Desplegables de una letra (Direction → Z): abrir y pulsar la tecla `z`. Aplicar modificadores: cursor sobre su panel y **Ctrl+A**.
- Panel «Add Grid» abajo a la izquierda: clic en (119, 960); campos X/Y Subdivisions y Size en (306, 699/725/751). Material: campo de nombre en (1735, 559) con un hueco y (1735, 605) con dos; botón + de huecos (1900, 464).
- Specular está fuera de la vista: rueda del ratón sobre el panel (botón 5 baja, 4 sube).
- `editar.py`: los tramos en que la pantalla tarda más de 1,25 × la narración se aceleran (máx. ×4, rótulo «Acelerado ×N»). `--bruto/--eventos/--salida/--sin-titulo/--sin-final` para grabar un capítulo en partes y unirlas con `ffmpeg -f concat`.
- Antes de grabar en serio: una calibración que solo tome capturas de los estados (barata) y medir posiciones; cada toma fallida de Blender cuesta ~6 min.
