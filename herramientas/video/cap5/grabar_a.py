# Capítulo 5, parte A (5.1 la hoja y 5.2 la rejilla) grabado en Blender con entrada real (xdotool) y OCR.
import bpy, sys, os, time
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap5/'
sys.path.insert(0, V + '/rec')
import motor_b as MB
MB.OFFSET_Y = 19
T = '/home/osney/Plano3D/trabajo/'
m = MB.MotorB(C + 'eventos_a.jsonl', C + 'duraciones.json')
PROP = (1590, 380, 330, 680)      # editor de propiedades (pantalla)
SIDE = (1345, 100, 220, 880)      # panel N
VISTA = (64, 120, 1270, 850)
FX = 1820                         # columna de los valores en el editor de propiedades
TAB = dict(scene=565, modifiers=708, material=868, data=836, texture=908)
CTX = dict(scene='SCENE', modifiers='MODIFIER', material='MATERIAL', data='DATA', texture='TEXTURE')

def aviso(t): m.ev('aviso', txt=t)
def buscar(t, reg, todos=False): return m.buscar(t, reg, todos)
def clic_texto(t, reg, dx=0, dy=0, doble=False):
    r = buscar(t, reg)
    if not r: aviso('no encontré ' + t); return None
    x, y = m.centro(r); yield from m.clic(x + dx, y + dy, doble=doble); return r
def menu_ruta(pasos, ancho=False):
    """Recorre un menú emergente: pasa por cada opción (OCR alrededor del cursor) y hace clic en la última."""
    for i, t in enumerate(pasos):
        x, y = m.pos()
        if ancho: x0 = max(0, x - 1050); reg = (x0, max(0, y - 450), min(1920 - x0, 1500), 900)
        else: reg = (max(0, x - 450), max(0, y - 420), 900, 840)
        r = None
        for _ in range(6):
            r = buscar(t, reg)
            if r: break
            yield 0.3
        if not r: aviso('menú sin ' + t); return False
        cx, cy = m.centro(r)
        if i < len(pasos) - 1: yield from m.mover(cx, cy, 0.5); yield 0.8
        else: yield from m.clic(cx, cy)
    return True
def campo_bajo(etiqueta, fila, valor, reg=SIDE, fx=1450, paso=22):
    r = buscar(etiqueta, reg)
    if not r: aviso('sin etiqueta ' + etiqueta); return None
    y = m.centro(r)[1] + paso * fila
    yield from m.editar_campo(fx, y, valor); return (fx - 95, y - 10, 190, 20)
def campo_derecha(etiqueta, valor, reg=PROP, fx=FX):
    r = buscar(etiqueta, reg)
    if not r: aviso('sin etiqueta ' + etiqueta); return None
    y = m.centro(r)[1]
    yield from m.editar_campo(fx, y, valor); return (fx - 75, y - 11, 150, 22)
def tab(n):
    yield from m.clic(1605, TAB[n]); yield 0.3
    yield from m.mover(1760, 980, 0.4); yield 0.5      # quitar el cursor para que no tape con la ayuda emergente
    sp = MB.area('PROPERTIES').spaces[0]
    if sp.context != CTX[n]: aviso('pestaña por bpy ' + n); sp.context = CTX[n]; yield 0.4
def material_nuevo(nombre, primero=True):
    if not primero:
        yield from m.clic(1900, 464); yield 0.6
    r = yield from clic_texto('New', PROP)
    yield 0.8
    yield from m.editar_campo(1735, 559 if primero else 605, nombre)
    mat = bpy.context.object.active_material
    if mat is None:
        aviso('material por bpy'); mat = bpy.data.materials.new(nombre); mat.use_nodes = True
        if len(bpy.context.object.material_slots) == 0 or primero: bpy.context.object.data.materials.append(mat)
        else: bpy.context.object.material_slots[bpy.context.object.active_material_index].material = mat
    if mat.name != nombre: aviso('nombre por bpy'); mat.name = nombre

def imagen_base(ruta, nombre):
    r = buscar('Base Color', PROP)
    if r:
        x, y = m.centro(r); yield from m.clic(r[0] + r[2] + 22, y); yield 0.8
        ok = yield from menu_ruta(['Image Texture'], ancho=True)
        yield 1.0
        r2 = yield from clic_texto('Open', PROP) if ok else None
        yield 2.0
        f = None
        for _ in (range(5) if r2 else []):
            f = buscar(nombre, (0, 0, 1920, 1080))
            if f: break
            yield 0.5
        if f: yield from m.clic(*m.centro(f), doble=True); yield 1.5
        elif r2: aviso('sin archivo en navegador ' + nombre); m.xdo('key', 'Escape'); yield 0.5
        else: m.xdo('key', 'Escape'); yield 0.3
    mat = bpy.context.object.active_material
    tex = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
    if not tex or not tex[0].image:
        aviso('imagen por bpy ' + nombre)
        b = mat.node_tree.nodes['Principled BSDF']; t = tex[0] if tex else mat.node_tree.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(ruta); mat.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
def rugosidad_especular():
    reg = yield from campo_derecha('Roughness', '1')
    if reg: yield from m.resaltar(reg, 3, '4')
    m.xdo('mousemove', 1760, 820); yield 0.3
    for _ in range(5): m.xdo('click', 5); yield 0.12
    yield 0.5
    r = yield from clic_texto('Specular', PROP)
    yield 0.8
    m.xdo('mousemove', 1760, 820)
    for _ in range(3): m.xdo('click', 5); yield 0.12
    yield 0.5
    q = yield from campo_derecha('IOR Level', '0')
    if q: yield from m.resaltar(q, 2.5, '5')
    b = bpy.context.object.active_material.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
    r = buscar('Specular', PROP)
    if r: yield from m.clic(*m.centro(r)); yield 0.5    # cerrar el subpanel
    m.xdo('mousemove', 1760, 820)
    for _ in range(10): m.xdo('click', 4); yield 0.08

def guion():
    yield 3.0
    bpy.context.preferences.view.ui_scale = 1.15
    bpy.context.preferences.filepaths.texture_directory = T
    yield 1.0
    yield from m.destello()
    # s01: pantalla de bienvenida
    yield from m.seg('s01')
    yield from m.mover(700, 600, 1.2)
    # s02: General y borrar el cubo
    yield from m.seg('s02')
    r = None
    for _ in range(5):
        r = buscar('General', (500, 300, 900, 600))
        if r: break
        yield 0.3
    if r: yield from m.clic(*m.centro(r))
    yield 1.5
    cubo = bpy.data.objects.get('Cube')
    if cubo:
        x, y = MB.punto_3d(cubo.location); yield from m.clic(x, y); yield 0.5
        yield from m.tecla('x', 'X'); yield 0.6
        x2, y2 = m.pos(); r = buscar('Delete', (x2 - 200, y2 - 120, 400, 240))
        if r: yield from m.clic(*m.centro(r))
        else: m.xdo('key', 'Return')
        yield 0.8
        if bpy.data.objects.get('Cube'): aviso('cubo por bpy'); bpy.data.objects.remove(bpy.data.objects['Cube'])
    # s03: unidades
    yield from m.seg('s03')
    yield from m.zoom(PROP)
    yield from tab('scene')
    u = buscar('Units', PROP)
    if u: yield from m.clic(*m.centro(u)); yield 0.8
    r = buscar('Length', PROP)
    if r:
        x, y = m.centro(r); yield from m.clic(FX, y); yield 0.6
        yield from menu_ruta(['Millimeters'])
    if bpy.context.scene.unit_settings.length_unit != 'MILLIMETERS':
        aviso('unidades por bpy'); bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'
    r = buscar('Length', PROP)
    if r: yield from m.resaltar((r[0] - 10, r[1] - 8, 300, 26), 3, '1')
    yield 1.0
    yield from m.alejar()
    # s04: plano
    yield from m.seg('s04')
    yield from m.mover(700, 560, 0.8)
    yield from m.tecla('shift+a', 'Shift + A'); yield 0.8
    ok = yield from menu_ruta(['Mesh', 'Plane'])
    yield 1.0
    if not bpy.context.object or bpy.context.object.type != 'MESH':
        aviso('plano por bpy')
        with MB.ov(): bpy.ops.mesh.primitive_plane_add(size=1)
    hoja = bpy.context.object; hoja.name = 'Hoja'
    yield from m.tecla('KP_Decimal', 'Num .'); yield 0.8
    for _ in range(4): m.xdo('click', 5); yield 0.15
    # s05: N y dimensiones
    yield from m.seg('s05')
    yield from m.tecla('n', 'N'); yield 1.0
    yield from m.zoom(SIDE)
    rx = yield from campo_bajo('Dimensions', 1, '900mm')
    ry = yield from campo_bajo('Dimensions', 2, '600mm')
    if rx and ry: yield from m.resaltar((rx[0], rx[1], rx[2], ry[1] + ry[3] - rx[1]), 3.5, '1')
    if abs(hoja.dimensions.x - 0.9) > 1e-4: aviso('dim hoja por bpy'); hoja.dimensions = (0.9, 0.6, 0)
    # s06: Ctrl A → Scale
    yield from m.seg('s06')
    yield from m.alejar()
    yield from m.mover(700, 560, 0.8)
    yield from m.tecla('ctrl+a', 'Ctrl + A'); yield 0.8
    yield from menu_ruta(['Scale'])
    yield 0.8
    if abs(hoja.scale.x - 1) > 1e-6:
        aviso('escala por bpy')
        with MB.ov(): bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # s07: material Hoja
    yield from m.seg('s07')
    yield from m.zoom(PROP)
    yield from tab('material')
    yield from material_nuevo('Hoja')
    # s08: imagen
    yield from m.seg('s08')
    yield from m.alejar()
    yield from imagen_base(T + 'plano_hoja.jpg', 'plano_hoja.jpg')
    MB.area('VIEW_3D').spaces[0].shading.color_type = 'TEXTURE'
    yield from m.zoom(PROP)
    # s09: rugosidad y especular
    yield from m.seg('s09')
    yield from rugosidad_especular()
    # s10: material Canto
    yield from m.seg('s10')
    yield from material_nuevo('Canto', primero=False)
    r = buscar('Base Color', PROP)
    if r: yield from m.mover(FX, m.centro(r)[1], 0.6)
    b = bpy.context.object.active_material.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.85, 0.85, 0.83, 1)
    b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
    yield 1.0
    # s11: Solidify
    yield from m.seg('s11')
    yield from tab('modifiers')
    r = yield from clic_texto('Add Modifier', PROP)
    yield 0.8
    yield from menu_ruta(['Generate', 'Solidify'])
    yield 1.0
    if not hoja.modifiers:
        aviso('solidify por bpy'); hoja.modifiers.new('Solidify', 'SOLIDIFY')
    sol = hoja.modifiers[0]
    # s12: valores del solidify
    yield from m.seg('s12')
    r1 = yield from campo_derecha('Thickness', '4mm')
    r2 = yield from campo_derecha('Offset', '-1')
    r = yield from clic_texto('Materials', PROP); yield 0.6
    r3 = yield from campo_derecha('Rim', '1')
    sol.thickness = 0.004; sol.offset = -1; sol.material_offset_rim = 1
    yield from m.alejar()
    yield 1.0
    # s13: rejilla
    yield from m.seg('s13')
    yield from m.mover(700, 560, 0.8)
    yield from m.tecla('shift+a', 'Shift + A'); yield 0.8
    yield from menu_ruta(['Mesh', 'Grid'])
    yield 1.2
    rej = bpy.context.object
    if rej is None or rej == hoja:
        aviso('grid por bpy')
        with MB.ov(): bpy.ops.mesh.primitive_grid_add()
        rej = bpy.context.object
    rej.name = 'Relieve'
    # s14: panel Add Grid
    yield from m.seg('s14')
    yield from m.clic(119, 960); yield 1.0
    yield from m.zoom((60, 640, 420, 140))
    for (x, y), val in (((306, 699), '600'), ((306, 725), '522'), ((306, 751), '1m')):
        yield from m.editar_campo(x, y, val); yield 1.2
    yield from m.resaltar((236, 686, 140, 78), 3, '1')
    m.xdo('mousemove', 520, 900); yield 0.8
    yield from m.alejar()
    rej = bpy.context.object
    if len(rej.data.polygons) < 300000:
        aviso('grid 600x522 por bpy')
        bpy.data.objects.remove(rej)
        with MB.ov(): bpy.ops.mesh.primitive_grid_add(x_subdivisions=600, y_subdivisions=522, size=1)
        rej = bpy.context.object
    rej.name = 'Relieve'
    # s15: posición, dimensiones, aplicar escala
    yield from m.seg('s15')
    yield from m.zoom(SIDE)
    a = yield from campo_bajo('Location', 1, '-102.86mm')
    yield from campo_bajo('Location', 2, '0mm')
    c = yield from campo_bajo('Location', 3, '0.5mm')
    if a and c: yield from m.resaltar((a[0], a[1], a[2], c[1] + c[3] - a[1]), 3, '1')
    d1 = yield from campo_bajo('Dimensions', 1, '653.14mm')
    d2 = yield from campo_bajo('Dimensions', 2, '569.14mm')
    if d1 and d2: yield from m.resaltar((d1[0], d1[1], d1[2], d2[1] + d2[3] - d1[1]), 3, '2')
    if abs(rej.location.x + 0.10286) > 1e-5 or abs(rej.dimensions.x - 0.65314) > 1e-5:
        aviso('posición rejilla por bpy'); rej.location = (-0.10286, 0, 0.0005); rej.dimensions = (0.65314, 0.56914, 0)
    yield from m.alejar()
    yield from m.mover(700, 560, 0.8)
    yield from m.tecla('ctrl+a', 'Ctrl + A'); yield 0.8
    yield from menu_ruta(['Scale'])
    yield 0.8
    if abs(rej.scale.x - 1) > 1e-6:
        aviso('escala rejilla por bpy')
        with MB.ov(): bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # s16: materiales Mapa y Pared
    yield from m.seg('s16')
    yield from m.zoom(PROP)
    yield from tab('material')
    yield from material_nuevo('Mapa')
    yield from m.alejar()
    yield from imagen_base(T + 'plano_mapa.jpg', 'plano_mapa.jpg')
    b = rej.active_material.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
    yield from material_nuevo('Pared', primero=False)
    b = rej.active_material.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.42, 0.40, 0.37, 1)
    b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
    rej.active_material_index = 0
    yield from m.hasta(m.fin)
    with MB.ov():
        bpy.ops.view3d.view_all()
    yield 2.0
    m.ev('info', objetos=[(o.name, list(o.dimensions), len(o.data.polygons) if o.type == 'MESH' else 0, [s.material.name for s in o.material_slots if s.material]) for o in bpy.data.objects])

def salir():
    try: bpy.ops.wm.save_as_mainfile(filepath=T + 'maqueta_parte_a.blend')
    except Exception as e: m.log = open(C + 'eventos_a.jsonl', 'a'); m.ev('error', txt=str(e))
    os._exit(0)
m.correr(guion(), salir)
