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
