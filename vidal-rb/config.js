/* Vidal RB · maqueta 3D del pozo PAD1 y los mantos de más de 1 m. Único archivo que se edita a mano. */
self.PLANO = {
  version: 1,
  titulo: 'Vidal RB',
  subtitulo: 'Pozo PAD1 · mantos M80, M90, M100 y M120 · línea L-0 · 1:2 000',
  color: '#2f3133',
  hoja: { ancho_mm: 755.39, alto_mm: 757.70 },
  marco: { x_mm: 0, y_mm: 0, ancho_mm: 755.39, alto_mm: 757.70,
    E_min: 1031220.681, E_max: 1032731.460, N_min: 1206520.700, N_max: 1208036.099 },
  relieve: { imagen: 'relieve.png', z_min: -110.0, z_max: 274.0, exageracion: 1 },
  proyeccion: { lat_0: 4.59620041666667, lon_0: -74.0775079166667, k: 1, x_0: 1000000, y_0: 1000000, elipsoide: 'GRS80' },
  archivos: { modelo: 'plano_relieve.glb', modelo_iphone: 'plano_relieve.usdz', plano2d: 'plano.jpg', poster: '' },
  etiquetas: [
    { archivo: 'etiquetas/mantos.csv', campo: 'nombre', grupo: 'Subafloramiento de mantos > 1 m', color: '#1d1f21' },
    { archivo: 'etiquetas/pozos.csv', campo: 'nombre', grupo: 'Pozos', color: '#9c3d1f' }
  ],
  ficha: [
    ['Escala', '1:2 000 · sin exageración vertical'],
    ['Bloque', '1,2 × 0,94 km cortado por la línea L-0 · base a −110 msnm'],
    ['Cara L-0', 'Sección con el PAD1 y los mantos que corta'],
    ['Mitad NE', 'Terreno transparente: se ven M120, M100, M90 y M80 como planos'],
    ['Mantos', 'Rumbo N33–43E, buzamiento 45–46° SE (trazas GDB y sección L-0)'],
    ['Terreno', 'Curvas c/2 m (GDB FHD-161) y DSM del vuelo donde no hay curvas'],
    ['Ortomosaico', 'DJI Terra · 24 nov. 2026 · 1 321 fotos RTK FIX'],
    ['Sistema', 'MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116)']
  ],
  elaboro: {
    nombre: 'Osney Izaquita',
    titulos: [
      ['Ingeniero Geólogo', 'Universidad Pedagógica y Tecnológica de Colombia'],
      ['Especialista en Aplicación de TIC para la Enseñanza', 'Universidad de Santander'],
      ['Magíster en Gestión de Cuencas Hidrográficas', 'Universidad Santo Tomás'],
      ['Candidato a Magíster en Recursos Digitales Aplicados a la Educación', 'Universidad de Cartagena'],
      ['Piloto de drones', '']
    ]
  },
  pie: { logo: '', texto: 'Grupo Invercoal' }
};
