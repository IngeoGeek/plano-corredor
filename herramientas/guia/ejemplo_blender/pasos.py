# Reproduce con bpy exactamente los pasos manuales de la guía (cada función = clics de la guía)
import bpy, bmesh, json, math, os
W = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/trabajo'
HOJA = (0.900, 0.600)                      # m (hoja 900 x 600 mm)
MARCO = dict(x=20.57, y=15.43, w=653.14, h=569.14)   # mm desde la esquina superior izquierda
EXT = (4885966.641, 4928420.741, 2241436.912, 2278431.036)
ESC, VE, ZMIN, ZMAX = 65000, 2.5, 100, 2000
FUERZA = (ZMAX - ZMIN) * VE / ESC          # 0.07308 m
CX = (MARCO['x'] + MARCO['w'] / 2 - HOJA[0] * 500) / 1000
CY = (HOJA[1] * 500 - (MARCO['y'] + MARCO['h'] / 2)) / 1000
Z_REL = 0.0005

def material_imagen(nombre, ruta):
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    tex = m.node_tree.nodes.new('ShaderNodeTexImage'); tex.location = (-400, 250)
    tex.image = bpy.data.images.load(ruta)
    m.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    return m

def material_color(nombre, rgb, rough=1.0):
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = 0.0
    return m

def paso0_limpiar():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    bpy.context.scene.unit_settings.system = 'METRIC'; bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'

def paso1_hoja():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = 'Hoja'
    o.dimensions = (HOJA[0], HOJA[1], 0); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material_imagen('Hoja', W + '/plano_hoja.jpg'))
    o.data.materials.append(material_color('Canto', (0.85, 0.85, 0.83)))
    s = o.modifiers.new('Solidify', 'SOLIDIFY'); s.thickness = 0.004; s.offset = -1; s.material_offset_rim = 1
    return o

def paso2_rejilla():
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=600, y_subdivisions=522, size=1, location=(CX, CY, Z_REL))
    o = bpy.context.active_object; o.name = 'Relieve'
    o.dimensions = (MARCO['w'] / 1000, MARCO['h'] / 1000, 0); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material_imagen('Mapa', W + '/plano_mapa.jpg'))
    o.data.materials.append(material_color('Pared', (0.42, 0.40, 0.37)))
    return o

def paso3_desplazar(o):
    t = bpy.data.textures.new('Relieve', 'IMAGE'); t.image = bpy.data.images.load(W + '/relieve.png')
    t.image.colorspace_settings.name = 'Non-Color'; t.extension = 'EXTEND'
    d = o.modifiers.new('Displace', 'DISPLACE'); d.texture = t; d.texture_coords = 'UV'; d.direction = 'Z'
    d.mid_level = 0.0; d.strength = FUERZA
    return d

def paso4_simplificar(o):
    m = o.modifiers.new('Decimate', 'DECIMATE'); m.ratio = 0.5
    return m

def aplicar(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)

def paso5_paredes(o):
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.mesh.select_non_manifold()
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={'value': (0, 0, -0.01)})
    bpy.ops.transform.resize(value=(1, 1, 0))
    bm = bmesh.from_edit_mesh(o.data)
    for v in bm.verts:
        if v.select: v.co.z = -Z_REL
    bmesh.update_edit_mesh(o.data)
    bpy.ops.mesh.select_more()                      # Ctrl + NumPad +
    bpy.ops.mesh.select_mode(type='FACE')           # tecla 3: quedan seleccionadas solo las paredes
    o.active_material_index = 1; bpy.ops.object.material_slot_assign()
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth(); o.data.use_auto_smooth = True; o.data.auto_smooth_angle = math.radians(30)

def altura(E, N):
    img = bpy.data.images['relieve.png']; w, h = img.size
    px = img.pixels[:] if not hasattr(altura, 'px') else altura.px; altura.px = px
    i = min(w - 1, max(0, int((E - EXT[0]) / (EXT[1] - EXT[0]) * (w - 1))))
    j = min(h - 1, max(0, int((N - EXT[2]) / (EXT[3] - EXT[2]) * (h - 1))))
    return px[(j * w + i) * 4] * FUERZA + Z_REL

def a_blender(E, N):
    x = (MARCO['x'] + (E - EXT[0]) / (EXT[1] - EXT[0]) * MARCO['w'] - HOJA[0] * 500) / 1000
    y = (HOJA[1] * 500 - (MARCO['y'] + (EXT[3] - N) / (EXT[3] - EXT[2]) * MARCO['h'])) / 1000
    return x, y

def paso6_chinchetas():
    pines = json.load(open(W + '/pines.json'))
    rojo = material_color('Chincheta', (0.82, 0.13, 0.10), 0.5); blanco = material_color('Aguja', (0.95, 0.95, 0.95), 0.5)
    azul = material_color('Letrero', (0.004, 0.31, 0.49))
    col = bpy.data.collections.new('Chinchetas'); bpy.context.scene.collection.children.link(col)
    for tipo, nombre, E, N in pines:
        x, y = a_blender(E, N); z = altura(E, N)
        nombre = nombre.title() if tipo == 'm' else nombre
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0006, depth=0.03, location=(x, y, z + 0.015)); a = bpy.context.active_object; a.data.materials.append(blanco)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.004, location=(x, y, z + 0.032)); c = bpy.context.active_object; c.data.materials.append(rojo); bpy.ops.object.shade_smooth()
        bpy.ops.object.text_add(location=(x, y, z + 0.042), rotation=(math.radians(90), 0, 0)); t = bpy.context.active_object
        t.data.body = nombre; t.data.size = 0.011; t.data.extrude = 0.0004; t.data.align_x = 'CENTER'; t.data.materials.append(azul)
        bpy.ops.object.convert(target='MESH')
        for ob in (a, c, t):
            for cc in ob.users_collection: cc.objects.unlink(ob)
            col.objects.link(ob); ob.name = f'{nombre} · {ob.name.split(".")[0]}'

def exportar(dest):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=dest + '/plano_relieve.glb', export_format='GLB', use_selection=False, export_apply=True,
        export_yup=True, export_image_format='JPEG', export_jpeg_quality=85 if 'export_jpeg_quality' in bpy.ops.export_scene.gltf.get_rna_type().properties else 75)
    bpy.ops.wm.usd_export(filepath=dest + '/plano_relieve.usdz', selected_objects_only=False, export_materials=True, generate_preview_surface=True, export_uvmaps=True, export_normals=True)
