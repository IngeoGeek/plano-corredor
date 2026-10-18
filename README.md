# Corredor Carbonífero de Santander · Plano en relieve

Visor web de la maqueta 3D del plano general (1:65 000, exageración vertical 2,5×, 90 × 60 cm).
Página publicada: https://ingeogeek.github.io/plano-corredor/

| Archivo | Para qué |
| --- | --- |
| index.html | Visor 3D. «Ver en tu espacio» usa el visor nativo (ARCore / iPhone) y, si no existe, el motor en el navegador |
| ver.html | Mismo visor, pero «Ver en tu espacio» usa siempre el motor en el navegador (celulares sin ARCore) |
| ra.html | Modo de respaldo con marcador impreso (marcador_10cm_carta.pdf) |
| plano_relieve.glb / .usdz | Maqueta 3D (Android y web / iPhone) |
| alturas.json | Rejilla de alturas de la maqueta para ubicar el GPS |
| sw.js | Guarda el visor en el celular para abrirlo sin internet |
| lib/ | model-viewer (Apache 2.0), three.js r147 (MIT), AR.js + A-Frame (MIT) y el motor 8th Wall de Niantic Spatial, distribuido sin modificar bajo su XR Engine License Agreement (lib/8thwall/LICENSE) |

Relieve reconstruido a partir de las curvas de nivel del proyecto (c/50 m) en una rejilla de 30 m.
Coordenadas: MAGNA-SIRGAS 2018 / Origen-Nacional (EPSG:9377). Elaboró: Msc. Ing. Osney Izaquita.

## Versión 2 (carpeta v2/)
Página: https://ingeogeek.github.io/plano-corredor/v2/ (y v2/ver.html para celulares sin ARCore).
Agrega el cambio entre el plano 2D (PDF en mosaicos de zoom profundo, OpenSeadragon, BSD-3) y la maqueta 3D,
el GPS sobre ambas vistas, materiales mates y luz moderada. No modifica los archivos de la versión 1.
