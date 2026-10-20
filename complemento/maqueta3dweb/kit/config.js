/* =====================================================================
   CONFIGURACIÓN DEL PLANO · es el ÚNICO archivo que se edita a mano.
   Escribe los números con punto decimal (2.5, no 2,5) y deja las comas
   del final de cada línea. Los textos van entre comillas simples '…'.
   Ejemplo lleno: Plano general del Corredor Carbonífero de Santander.
   ===================================================================== */
self.PLANO = {

  // Súbelo (1 → 2 → 3…) cada vez que cambies archivos ya publicados,
  // para que los celulares que guardaron el plano descarguen la versión nueva.
  version: 1,

  // ---------- Textos de la página ----------
  titulo: 'Corredor Carbonífero de Santander',
  subtitulo: 'Plano general · Cimitarra – Landázuri – Vélez · 1:65 000',
  color: '#014f7d',                     // color principal (barra, botones)

  // ---------- Medidas del diseño de QGIS (Paso 1 de la guía) ----------
  hoja: { ancho_mm: 900, alto_mm: 600 },  // tamaño de la página del diseño
  marco: {                               // el mapa principal dentro de la hoja
    x_mm: 20.57, y_mm: 15.43,            // Posición X e Y (esquina superior izquierda)
    ancho_mm: 653.14, alto_mm: 569.14,   // Ancho y Alto
    E_min: 4885966.641, E_max: 4928420.741, // Extensión: X mín y X máx
    N_min: 2241436.912, N_max: 2278431.036  // Extensión: Y mín e Y máx
  },

  // ---------- Relieve (Pasos 2 a 5) ----------
  relieve: {
    imagen: 'relieve.png',               // el mapa de alturas en escala de grises
    z_min: 100,                          // cota que quedó en negro (m)
    z_max: 2000,                         // cota que quedó en blanco (m)
    exageracion: 2.5                     // la misma que usaste en Blender
  },

  // ---------- Sistema de coordenadas del proyecto (Paso 1) ----------
  // Copia los valores de la línea PROJ: +lat_0 +lon_0 +k +x_0 +y_0 +ellps
  proyeccion: { lat_0: 4, lon_0: -73, k: 0.9992, x_0: 5000000, y_0: 2000000, elipsoide: 'GRS80' },

  // ---------- Archivos ----------
  archivos: {
    modelo: 'plano_relieve.glb',         // maqueta para Android y computador
    modelo_iphone: 'plano_relieve.usdz', // maqueta para iPhone ('' si no la tienes)
    plano2d: 'plano2d/plano.dzi',        // teselas (Paso 8) o una sola imagen, por ejemplo 'plano.jpg'
    poster: ''                           // imagen mientras carga la maqueta ('' = ninguna)
  },

  // ---------- Etiquetas que se prenden y apagan sobre la maqueta (opcional) ----------
  // Un CSV por grupo, exportado desde QGIS con «Geometría: AS_XY» (Paso 6).
  // campo = columna que tiene el nombre que se muestra.
  etiquetas: [
    { archivo: 'etiquetas/fallas.csv', campo: 'nombre', grupo: 'Fallas', color: '#c62828' },
    { archivo: 'etiquetas/pliegues.csv', campo: 'nombre', grupo: 'Pliegues', color: '#6a1b9a' },
    { archivo: 'etiquetas/operadores.csv', campo: 'nombre', grupo: 'Operadores FEL-165', color: '#e65100' },
    { archivo: 'etiquetas/proyectos_piloto.csv', campo: 'etiqueta', grupo: 'Proyectos Piloto FHD-161', color: '#f2b705' }
  ],

  // ---------- Ficha técnica (pares «título, valor»; agrega o quita filas) ----------
  ficha: [
    ['Escala horizontal', '1:65 000'],
    ['Exageración vertical', '2,5 ×'],
    ['Relieve', 'Curvas c/50 m · rejilla 30 m'],
    ['Sistema', 'MAGNA-SIRGAS 2018 · Origen-Nacional'],
    ['Plano', '90 × 60 cm · 1 de 1']
  ],

  // ---------- Elaboró ('' en nombre para ocultar el recuadro) ----------
  elaboro: {
    nombre: 'Osney Izaquita',
    titulos: [
      ['Ingeniero Geólogo', 'Universidad Pedagógica y Tecnológica de Colombia'],
      ['Especialista en Aplicación de TIC para la Enseñanza', 'Universidad de Santander'],
      ['Magíster en Gestión de Cuencas Hidrográficas', 'Universidad Santo Tomás'],
      ['Estudiante de Maestría en Recursos Digitales Aplicados a la Educación', 'Universidad de Cartagena'],
      ['Piloto de drones', '']
    ]
  },

  // ---------- Pie de página ('' para ocultar) ----------
  pie: { logo: 'logo.png', texto: 'Grupo Invercoal' }
};
