"""Construye en Blender el plano del Corredor Carbonífero en relieve (escala 1:65 000, VE 3x).
Uso: blender -b --factory-startup --python build_blend.py -- <carpeta_trabajo> <carpeta_salida>
Sistema de la escena: metros, Z arriba, norte = +Y, origen en el centro de la hoja de 900 x 600 mm."""
import bpy, bmesh, json, sys, os
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
W, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
ESC, VE, ZOCALO, ZMIN = 65000.0, 2.5, 0.004, 100.0     # escala, exageración, zócalo (m), cota de referencia
lay = json.load(open(f'{W}/layout.json'))
MX, MY, MW, MH = lay['map']; RX, RY, RW, RH = lay['rot']; PW, PH = lay['page']
meta = json.load(open(f'{W}/dem30.json'))
E0, E1, N0, N1, res = meta['E0'], meta['E1'], meta['N0'], meta['N1'], meta['res']

def px(xmm): return (xmm - PW / 2) / 1000.0          # mm de la hoja -> X de la escena
def py(ymm): return (PH / 2 - ymm) / 1000.0          # mm desde arriba -> Y de la escena
x0, x1, ytop, ybot = px(MX), px(MX + MW), py(MY), py(MY + MH)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0

def material(nombre, imagen=None, color=(0.95, 0.94, 0.91, 1), rugosidad=1.0):
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = rugosidad
    if 'Specular IOR Level' in bsdf.inputs: bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif 'Specular' in bsdf.inputs: bsdf.inputs['Specular'].default_value = 0.0
    if imagen:
        tx = m.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(imagen)
        tx.interpolation = 'Linear'; tx.extension = 'EXTEND'
        m.node_tree.links.new(tx.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = color
    return m

# ---------- 1. Relieve desde el DEM de 30 m ----------
Z = np.load(f'{W}/dem30f.npy').astype(np.float64)
ny, nx = Z.shape
E = E0 + np.arange(nx) * res; E[-1] = E1
N = N1 - np.arange(ny) * res; N[-1] = N0
Xs = x0 + (E - E0) / ESC
Ys = ytop - (N1 - N) / ESC
XX, YY = np.meshgrid(Xs, Ys)
ZZ = ZOCALO + (Z - ZMIN) * VE / ESC
verts = np.column_stack([XX.ravel(), YY.ravel(), ZZ.ravel()]).astype(np.float32)
idx = np.arange(nx * ny).reshape(ny, nx)
a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]   # orden antihorario visto desde arriba
quads = np.stack([a, b, c, d], axis=-1).reshape(-1, 4)

me = bpy.data.meshes.new('Relieve')
me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', (np.arange(len(quads)) * 4).astype(np.int32))
try: me.polygons.foreach_set('loop_total', np.full(len(quads), 4, np.int32))
except Exception: pass
me.update(calc_edges=True); me.validate()
ob = bpy.data.objects.new('Relieve', me); sc.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
dec = ob.modifiers.new('Decimar', 'DECIMATE'); dec.decimate_type = 'COLLAPSE'
dec.ratio = 340000 / (2 * len(quads)); dec.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier='Decimar')
print('caras tras decimar:', len(ob.data.polygons))

# cortes en los límites de los cuatro mosaicos de textura y UV por mosaico
xm, ym = (x0 + x1) / 2, (ytop + ybot) / 2
bm = bmesh.new(); bm.from_mesh(ob.data)
for co, no in (((xm, 0, 0), (1, 0, 0)), ((0, ym, 0), (0, 1, 0))):
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=g, plane_co=co, plane_no=no)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])

mats = {}
for j in range(2):
    for i in range(2):
        mats[(j, i)] = material(f'Mapa_{j}{i}', f'{W}/tex2/mapa_{j}{i}.jpg')
pared = material('Paredes', f'{W}/tex2/pared.png', rugosidad=0.95)
orden = [mats[(0, 0)], mats[(0, 1)], mats[(1, 0)], mats[(1, 1)], pared]
for m in orden: ob.data.materials.append(m)
uv = bm.loops.layers.uv.new('UVMap')
tw, th = (x1 - x0) / 2, (ytop - ybot) / 2
for f in bm.faces:
    cx = sum(v.co.x for v in f.verts) / len(f.verts); cy = sum(v.co.y for v in f.verts) / len(f.verts)
    i = 0 if cx < xm else 1; j = 0 if cy > ym else 1
    f.material_index = j * 2 + i
    tx0 = x0 + i * tw; ty0 = ytop - (j + 1) * th
    for l in f.loops:
        l[uv].uv = (min(max((l.vert.co.x - tx0) / tw, 0), 1), min(max((l.vert.co.y - ty0) / th, 0), 1))

# paredes del bloque: extruir el borde hasta la hoja (z = 0)
borde = [e for e in bm.edges if e.is_boundary]
ext = bmesh.ops.extrude_edge_only(bm, edges=borde)
nuevos = [g for g in ext['geom'] if isinstance(g, bmesh.types.BMVert)]
for v in nuevos: v.co.z = 0.0
caras_pared = [g for g in ext['geom'] if isinstance(g, bmesh.types.BMFace)]
zt = max(v.co.z for v in bm.verts)
for f in caras_pared:
    f.material_index = 4
    for l in f.loops: l[uv].uv = (0.5, min(l.vert.co.z / zt, 1.0))
bmesh.ops.recalc_face_normals(bm, faces=caras_pared)
bm.to_mesh(ob.data); bm.free()
for p in ob.data.polygons: p.use_smooth = (p.material_index != 4)   # paredes planas, relieve suave
try:
    ob.data.use_auto_smooth = True; ob.data.auto_smooth_angle = 1.05
except Exception: pass

# ---------- 2. Hoja del plano (base de 900 x 600 mm, 4 mm de grosor) ----------
def quad(nombre, xa, xb, ya, yb, z, mat):
    m = bpy.data.meshes.new(nombre)
    m.from_pydata([(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], [], [(0, 1, 2, 3)])
    u = m.uv_layers.new(name='UVMap')
    for k, uvv in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]): u.data[k].uv = uvv
    m.materials.append(mat); o = bpy.data.objects.new(nombre, m); sc.collection.objects.link(o); return o

hoja = material('Hoja', f'{W}/tex2/hoja.jpg')
quad('Hoja', -PW / 2000, PW / 2000, -PH / 2000, PH / 2000, 0.0, hoja)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.00205))
canto = bpy.context.active_object; canto.name = 'Canto_hoja'; canto.scale = (PW / 1000, PH / 1000, 0.0039)
bpy.ops.object.transform_apply(scale=True); canto.data.materials.append(material('Canto', color=(0.93, 0.92, 0.89, 1)))

# ---------- 3. Rótulo en alta resolución (dos mosaicos) ----------
half = RH / 2
quad('Rotulo_superior', px(RX), px(RX + RW), py(RY + half), py(RY), 0.0004, material('Rotulo_0', f'{W}/tex2/rotulo_0.jpg'))
quad('Rotulo_inferior', px(RX), px(RX + RW), py(RY + RH), py(RY + half), 0.0004, material('Rotulo_1', f'{W}/tex2/rotulo_1.jpg'))

# ---------- 4. Luz y cámara para revisar en Blender ----------
sol = bpy.data.lights.new('Sol', 'SUN'); sol.energy = 3.0; sol.angle = 0.05
so = bpy.data.objects.new('Sol', sol); sc.collection.objects.link(so); so.rotation_euler = (0.95, 0.0, 0.79)
cam = bpy.data.cameras.new('Camara'); cam.lens = 40
co = bpy.data.objects.new('Camara', cam); sc.collection.objects.link(co)
co.location = (0.05, -0.95, 0.75); co.rotation_euler = (0.92, 0, 0.0); sc.camera = co
sc.world = bpy.data.worlds.new('Mundo'); sc.world.color = (0.75, 0.77, 0.78)

# ---------- 5. Rejilla de alturas para el GPS (coordenadas glTF: x, y arriba, z = -Y) ----------
gx, gy = 160, 140
ii = np.linspace(0, nx - 1, gx).round().astype(int); jj = np.linspace(0, ny - 1, gy).round().astype(int)
alt = (ZZ[np.ix_(jj, ii)] * 1e4).round().astype(int)   # décimas de milímetro
json.dump({'ESC': ESC, 'VE': VE, 'E0': E0, 'E1': E1, 'N0': N0, 'N1': N1,
           'x0': x0, 'x1': x1, 'ytop': ytop, 'ybot': ybot, 'gx': gx, 'gy': gy,
           'alt_01mm': alt.tolist()}, open(f'{OUT}/alturas.json', 'w'), separators=(',', ':'))

# ---------- 6. Exportar ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=f'{OUT}/plano_relieve.glb', export_format='GLB', export_yup=True,
                          export_apply=True, export_image_format='AUTO', export_cameras=False, export_lights=False)
try:
    bpy.ops.wm.usd_export(filepath=f'{OUT}/plano_relieve.usdz', export_materials=True,
                          generate_preview_surface=True, export_textures=True, selected_objects_only=False)
except Exception as e:
    print('USDZ no exportado:', e)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/Plano_Corredor_Carbonifero_relieve.blend', compress=True)
print('LISTO')
