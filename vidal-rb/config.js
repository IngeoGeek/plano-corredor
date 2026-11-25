/* Vidal RB · maqueta 3D del pozo PAD1 y los mantos de más de 1 m. Único archivo que se edita a mano. */
self.PLANO = {
  version: 4,
  titulo: 'Vidal RB · Pozo PAD1',
  subtitulo: 'Mantos de carbón de más de 1 m · línea de sección L-0 · predio Vidal (Río Blanco), contrato FHD-161',
  color: '#014f7d',
  hoja: { ancho_mm: 755.39, alto_mm: 757.70 },
  marco: { x_mm: 0, y_mm: 0, ancho_mm: 755.39, alto_mm: 757.70,
    E_min: 1031220.681, E_max: 1032731.460, N_min: 1206520.700, N_max: 1208036.099 },
  relieve: { imagen: 'relieve.png', z_min: -110.0, z_max: 274.0, exageracion: 1 },
  // EPSG:3116 · MAGNA-SIRGAS / Colombia Bogotá zone
  proyeccion: { lat_0: 4.59620041666667, lon_0: -74.0775079166667, k: 1, x_0: 1000000, y_0: 1000000, elipsoide: 'GRS80' },
  archivos: { modelo: 'plano_relieve.glb', modelo_iphone: 'plano_relieve.usdz', plano2d: 'plano.jpg', poster: '' },
  etiquetas: [
    { archivo: 'etiquetas/mantos.csv', campo: 'nombre', grupo: 'Subafloramiento de mantos > 1 m', color: '#1c252b' },
    { archivo: 'etiquetas/pozos.csv', campo: 'nombre', grupo: 'Pozos', color: '#b23a1c' }
  ],
  ficha: [
    ['Escala', '1:2 000, sin exageración vertical'],
    ['Bloque', '1,2 × 0,94 km cortado por la línea L-0, base a −110 m s. n. m.'],
    ['Cara L-0', 'Sección con el PAD1 y los mantos que corta'],
    ['Mitad NE', 'Terreno transparente: se ven M120, M100, M90 y M80 como planos'],
    ['Mantos', 'Rumbo N33–43E, buzamiento 45–46° al SE (trazas GDB y sección L-0)'],
    ['Límites', 'Predio Vidal en amarillo y licencia ambiental en verde'],
    ['Terreno', 'Curvas c/2 m (GDB FHD-161) y DSM del vuelo donde no hay curvas'],
    ['Ortomosaico', 'DJI Terra, 24 nov. 2026, 1 321 fotos con RTK FIX'],
    ['Sistema', 'MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116)']
  ],
  elaboro: {
    nombre: 'Msc. Ing. Osney Izaquita',
    titulos: [
      ['Ingeniero Geólogo', 'Universidad Pedagógica y Tecnológica de Colombia'],
      ['Especialista en Aplicación de TIC para la Enseñanza', 'Universidad de Santander'],
      ['Magíster en Gestión de Cuencas Hidrográficas', 'Universidad Santo Tomás'],
      ['Candidato a Magíster en Recursos Digitales Aplicados a la Educación', 'Universidad de Cartagena'],
      ['Piloto de drones', '']
    ]
  },
  pie: { logo: 'logo_invercoal.png', texto: 'Grupo Invercoal' },
  // Registro de quién revisa. Pega en «url» la dirección de la aplicación web de Google Apps Script
  // (termina en /exec). Mientras esté vacía, el visor pide el nombre pero no envía nada.
  registro: { url: '', pedir_nombre: true }
};
