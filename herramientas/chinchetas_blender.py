"""Agrega a la maqueta las chinchetas de títulos mineros y municipios (alfiler + letrero de doble cara)."""
import bpy, bmesh, json, sys, math
argv = sys.argv[sys.argv.index('--') + 1:]; M, OUT = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath=f'{OUT}/Plano_Corredor_Carbonifero_relieve.blend')
for o in [o for o in bpy.data.objects if o.name.startswith('Chincheta')]: bpy.data.objects.remove(o)
sc = bpy.context.scene
et = json.load(open(f'{M}/etiquetas.json')); at = json.load(open(f'{M}/atlas.json'))
def mat_color(nombre, rgb):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = 0.6
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = 0.0
    return m
def lin(c): return ((c/255) / 12.92) if c/255 <= 0.04045 else (((c/255) + 0.055) / 1.055) ** 2.4
azul = mat_color('Chincheta_azul', tuple(lin(c) for c in (1, 79, 125)))
negro = mat_color('Chincheta_negra', tuple(lin(c) for c in (17, 21, 24)))
metal = mat_color('Chincheta_aguja', (0.75, 0.75, 0.75))
mt = bpy.data.materials.new('Chincheta_letreros'); mt.use_nodes = True
b = mt.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 1.0
if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = 0.0
tx = mt.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(f'{M}/tex2/etiquetas_atlas.png'); tx.interpolation = 'Linear'
mt.node_tree.links.new(tx.outputs['Color'], b.inputs['Base Color'])

ALTO_TXT = 0.013   # alto del letrero: 13 mm
bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
mats = [metal, azul, negro, mt]
def cilindro(x, y, z0, z1, r, mi):
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=z1 - z0)
    for v in g['verts']: v.co.x += x; v.co.y += y; v.co.z += (z0 + z1) / 2
    for f in {f for v in g['verts'] for f in v.link_faces}: f.material_index = mi
def esfera(x, y, z, r, mi):
    g = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    for v in g['verts']: v.co.x += x; v.co.y += y; v.co.z += z
    for f in {f for v in g['verts'] for f in v.link_faces}: f.material_index = mi; f.smooth = True
def letrero(x, y, z, fila, ancho_px):
    H, n = at['H'], at['n']; w = ALTO_TXT * ancho_px / H
    v0, v1 = 1 - (fila + 1) / n, 1 - fila / n; u1 = ancho_px / at['W']
    for cara, dy in (('sur', -0.0004), ('norte', 0.0004)):
        if cara == 'sur': pts = [(x - w/2, y + dy, z), (x + w/2, y + dy, z), (x + w/2, y + dy, z + ALTO_TXT), (x - w/2, y + dy, z + ALTO_TXT)]
        else: pts = [(x + w/2, y + dy, z), (x - w/2, y + dy, z), (x - w/2, y + dy, z + ALTO_TXT), (x + w/2, y + dy, z + ALTO_TXT)]
        vs = [bm.verts.new(p) for p in pts]; f = bm.faces.new(vs); f.material_index = 3
        for l, c in zip(f.loops, [(0, v0), (u1, v0), (u1, v1), (0, v1)]): l[uv].uv = c
    # canto del letrero
    vs = [bm.verts.new(p) for p in [(x - w/2, y - 0.0004, z), (x - w/2, y + 0.0004, z), (x - w/2, y + 0.0004, z + ALTO_TXT), (x - w/2, y - 0.0004, z + ALTO_TXT)]]
k = 0
for grupo, alto, mi in (('titulos', 0.034, 1), ('municipios', 0.026, 2)):
    for it in et[grupo]:
        gx, gy, gz = it['pos']; x, y, zb = gx, -gz, gy     # glTF -> Blender
        top = zb + alto
        cilindro(x, y, zb - 0.001, top, 0.0007, 0)
        esfera(x, y, top, 0.0032, mi)
        fila = next(i for i in at['items'] if i['nombre'] == it['nombre'] and i['grupo'] == grupo)
        letrero(x, y, top + 0.004, fila['fila'], fila['ancho_px'])
        cilindro(x, y, top, top + 0.004, 0.0006, 0)
        k += 1
me = bpy.data.meshes.new('Chinchetas'); bm.to_mesh(me); bm.free()
for m in mats: me.materials.append(m)
ob = bpy.data.objects.new('Chinchetas', me); sc.collection.objects.link(ob)
print('chinchetas', k)
bpy.ops.object.select_all(action='SELECT')
for o in bpy.data.objects:
    if o.type in ('LIGHT', 'CAMERA'): o.select_set(False)
bpy.ops.export_scene.gltf(filepath=f'{OUT}/plano_relieve.glb', export_format='GLB', export_yup=True, export_apply=True,
                          export_image_format='AUTO', use_selection=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/Plano_Corredor_Carbonifero_relieve.blend', compress=True)
print('LISTO')
