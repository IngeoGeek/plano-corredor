# Capítulo 5, parte B (5.3 levantar el relieve y 5.4 paredes). Abre maqueta_parte_a.blend.
import bpy, sys, os, time
V = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/video'; C = V + '/cap5/'
src = open(C + 'grabar_a.py').read(); src = src[:src.index('def guion():')].replace("m = MB.MotorB(C + 'eventos_a.jsonl', C + 'duraciones.json')", ''); exec(src, globals())
m = MB.MotorB(C + 'eventos_b.jsonl', C + 'duraciones.json')
TAB.update(modifiers=708, material=868, texture=907, data=835)

def menu_cursor(pasos, ancho=False):
    ok = yield from menu_ruta(pasos, ancho); return ok
def menu_modificador(cat, item):
    r = buscar(cat, (1550, 360, 370, 420))
    if not r: aviso('sin categoría ' + cat); return False
    cx, cy = m.centro(r)
    for dy in (0, -10, 10):
        yield from m.mover(cx, cy + dy, 0.4); yield 0.9
        q = buscar(item, (1150, 360, 560, 700))
        if q: yield from m.clic(*m.centro(q)); return True
    aviso('sin ' + item); m.xdo('key', 'Escape'); yield 0.3; m.xdo('key', 'Escape'); yield 0.3
    return False
def desplegable_etiqueta(etiqueta, opcion=None, tecla=None):
    r = buscar(etiqueta, PROP)
    if not r: aviso('sin etiqueta ' + etiqueta); return None
    y = m.centro(r)[1]
    yield from m.clic(FX, y); yield 0.7
    if tecla: m.xdo('key', tecla); yield 0.6
    else:
        ok = yield from menu_ruta([opcion])
        if not ok: m.xdo('key', 'Escape'); yield 0.3
    return y
def aplicar_mod(nombre, etiqueta):
    rel = bpy.data.objects['Relieve']
    n0 = len(rel.modifiers)
    r = buscar(etiqueta, PROP)
    if r: yield from m.mover(*m.centro(r), 0.5)
    yield 0.4
    yield from m.tecla('ctrl+a', 'Ctrl + A'); yield 1.5
    if len(rel.modifiers) == n0 and rel.modifiers.get(nombre):
        aviso('aplicar por bpy ' + nombre)
        with MB.ov(): bpy.ops.object.modifier_apply(modifier=nombre)
def desplegable(x, y, opcion, ancho=False):
    yield from m.clic(x, y); yield 0.6
    ok = yield from menu_ruta([opcion], ancho)
    if not ok: m.xdo('key', 'Escape'); yield 0.3
    return ok

def guion():
    yield 3.0
    bpy.context.preferences.view.ui_scale = 1.15
    bpy.context.preferences.filepaths.texture_directory = T
    rel = bpy.data.objects['Relieve']
    for o in bpy.context.view_layer.objects: o.select_set(False)
    rel.select_set(True); bpy.context.view_layer.objects.active = rel
    MB.area('VIEW_3D').spaces[0].show_region_ui = False
    MB.area('VIEW_3D').spaces[0].shading.color_type = 'TEXTURE'
    yield 1.0
    m.xdo('mousemove', 700, 560); yield 0.3
    m.xdo('key', 'KP_Decimal'); yield 0.8
    for _ in range(2): m.xdo('click', 5); yield 0.15
    yield 1.0
    yield from m.destello()
    # s17 Displace
    yield from m.seg('s17')
    yield from m.zoom(PROP)
    yield from tab('modifiers')
    yield from clic_texto('Add Modifier', PROP); yield 0.8
    yield from menu_modificador('Deform', 'Displace')
    yield 1.0
    if not rel.modifiers: aviso('displace por bpy'); rel.modifiers.new('Displace', 'DISPLACE')
    D = lambda: rel.modifiers.get('Displace')
    # s18 New, UV, Z, fuerza
    yield from m.seg('s18')
    yield from clic_texto('New', PROP); yield 1.0
    if D() and not D().texture: aviso('textura por bpy'); D().texture = bpy.data.textures.new('Texture', 'IMAGE')
    yield from desplegable_etiqueta('Coordinates', 'UV')
    yield from desplegable_etiqueta('Direction', tecla='z')
    a = yield from campo_derecha('Strength', '0.07308')
    b = yield from campo_derecha('Midlevel', '0')
    if a and b: yield from m.resaltar((a[0], a[1], a[2], b[1] + b[3] - a[1]), 3, '4')
    if D(): D().texture_coords = 'UV'; D().direction = 'Z'; D().strength = 0.07308; D().mid_level = 0.0
    tex = D().texture if D() else bpy.data.textures[0]
    # s19 pestaña Texture, Open relieve.png
    yield from m.seg('s19')
    yield from tab('texture')
    yield 0.8
    r = yield from clic_texto('Open', PROP)
    yield 2.0
    f = None
    for _ in (range(5) if r else []):
        f = buscar('relieve.png', (0, 0, 1920, 1080))
        if f: break
        yield 0.5
    if f: yield from m.clic(*m.centro(f), doble=True); yield 1.5
    elif r: m.xdo('key', 'Escape'); yield 0.5
    t = tex
    if not t.image: aviso('imagen relieve por bpy'); t.image = bpy.data.images.load(T + 'relieve.png')
    # s20 Non-Color y Extend
    yield from m.seg('s20')
    cs = buscar('Color Space', PROP)
    if cs: yield from desplegable(1825, m.centro(cs)[1], 'Non-Color', ancho=True)
    if t.image.colorspace_settings.name != 'Non-Color': aviso('non-color por bpy'); t.image.colorspace_settings.name = 'Non-Color'
    m.xdo('mousemove', 1760, 820); yield 0.3
    for _ in range(12): m.xdo('click', 5); yield 0.1
    yield 0.6
    mp = buscar('Mapping', PROP)
    if mp: yield from m.clic(*m.centro(mp)); yield 0.8
    ex = buscar('Extension', PROP)
    if ex: yield from desplegable(1810, m.centro(ex)[1], 'Extend')
    if t.extension != 'EXTEND': aviso('extend por bpy'); t.extension = 'EXTEND'
    m.xdo('mousemove', 1760, 820)
    for _ in range(14): m.xdo('click', 4); yield 0.08
    yield from m.alejar()
    # s21 Decimate
    yield from m.seg('s21')
    yield from m.zoom(PROP)
    yield from tab('modifiers')
    yield from clic_texto('Add Modifier', PROP); yield 0.8
    yield from menu_modificador('Generate', 'Decimate')
    yield 1.0
    if len(rel.modifiers) < 2: aviso('decimate por bpy'); rel.modifiers.new('Decimate', 'DECIMATE')
    ra = buscar('Ratio', PROP)
    if ra: yield from m.editar_campo(1807, m.centro(ra)[1], '0.5')
    if rel.modifiers.get('Decimate'): rel.modifiers['Decimate'].ratio = 0.5
    if ra: yield from m.resaltar((1700, m.centro(ra)[1] - 12, 215, 24), 3, '5')
    # s22 aplicar en orden
    yield from m.seg('s22')
    yield from aplicar_mod('Displace', 'Strength')
    yield 1.0
    yield from aplicar_mod('Decimate', 'Ratio')
    yield 1.0
    yield from m.alejar()
    m.ev('info', caras=len(rel.data.polygons))
    # s23 edición, vértices, nada seleccionado
    yield from m.seg('s23')
    yield from m.mover(700, 560, 0.6)
    yield from m.tecla('Tab', 'Tab'); yield 1.5
    yield from m.tecla('1', '1'); yield 0.5
    yield from m.tecla('alt+a', 'Alt + A'); yield 1.0
    # s24 Select → Select All by Trait → Non Manifold
    yield from m.seg('s24')
    sel = buscar('Select', (180, 45, 500, 35))
    if sel: yield from m.clic(*m.centro(sel)); yield 0.8
    yield from menu_ruta(['Select All by Trait', 'Non Manifold'])
    yield 1.5
    m.xdo('mousemove', 700, 560); yield 0.3
    yield from m.tecla('KP_Decimal', 'Num .'); yield 1.5
    # s25 E Z, S Z 0
    yield from m.seg('s25')
    yield from m.mover(760, 520, 0.4)
    yield from m.tecla('e', 'E'); yield 0.4
    yield from m.tecla('z', 'Z'); yield 0.4
    yield from m.mover(760, 600, 0.8); yield 0.4
    yield from m.clic(760, 600, mover=False); yield 0.6
    yield from m.tecla('s', 'S'); yield 0.3
    yield from m.tecla('z', 'Z'); yield 0.3
    yield from m.tecla('0', '0'); yield 0.3
    yield from m.tecla('Return', 'Enter'); yield 1.0
    # s26 panel N, Global, Median Z = 0
    yield from m.seg('s26')
    yield from m.tecla('n', 'N'); yield 1.0
    yield from m.zoom(SIDE)
    gl = buscar('Global', SIDE)
    if gl: yield from m.clic(*m.centro(gl)); yield 0.6
    md = buscar('Median', SIDE)
    if md: yield from m.editar_campo(1450, m.centro(md)[1] + 23 * 3, '0'); yield from m.resaltar((1355, m.centro(md)[1] + 58, 190, 22), 3, '1')
    import bmesh
    bm = bmesh.from_edit_mesh(rel.data); zs = [v.co.z for v in bm.verts if v.select]
    if zs and abs(sum(zs) / len(zs) - (-0.0005)) > 1e-4:
        aviso('median z por bpy')
        for v in bm.verts:
            if v.select: v.co.z = -0.0005
        bmesh.update_edit_mesh(rel.data)
    yield from m.alejar()
    # s27 Ctrl Num+, 3, material Pared, Assign
    yield from m.seg('s27')
    yield from m.mover(700, 560, 0.6)
    yield from m.tecla('ctrl+KP_Add', 'Ctrl + Num +'); yield 0.8
    yield from m.tecla('3', '3'); yield 0.8
    yield from m.zoom(PROP)
    yield from tab('material')
    pa = buscar('Pared', PROP)
    if pa: yield from m.clic(*m.centro(pa)); yield 0.5
    rel.active_material_index = 1
    asg = buscar('Assign', PROP)
    if asg: yield from m.clic(*m.centro(asg)); yield 0.8
    else:
        aviso('assign por bpy')
        with MB.ov(): bpy.ops.object.material_slot_assign()
    yield from m.alejar()
    # s28 A, Shift N, Tab
    yield from m.seg('s28')
    yield from m.mover(700, 560, 0.6)
    yield from m.tecla('a', 'A'); yield 0.8
    yield from m.tecla('shift+n', 'Shift + N'); yield 1.5
    yield from m.tecla('Tab', 'Tab'); yield 1.5
    if rel.mode != 'OBJECT':
        aviso('modo objeto por bpy')
        with MB.ov(): bpy.ops.object.mode_set(mode='OBJECT')
    # s29 Shade Smooth y Auto Smooth
    yield from m.seg('s29')
    yield from m.clic(700, 560, boton=3); yield 0.8
    yield from menu_ruta(['Shade Smooth'])
    yield 1.0
    yield from m.zoom(PROP)
    yield from tab('data')
    nr = buscar('Normals', PROP)
    if nr: yield from m.clic(*m.centro(nr)); yield 0.8
    au = buscar('Auto Smooth', PROP)
    if au: yield from m.clic(au[0] - 14, m.centro(au)[1]); yield 0.8
    if not rel.data.use_auto_smooth:
        aviso('auto smooth por bpy'); rel.data.use_auto_smooth = True
    rel.data.auto_smooth_angle = 0.5235988
    if not any(p.use_smooth for p in rel.data.polygons[:50]):
        aviso('shade smooth por bpy')
        with MB.ov(): bpy.ops.object.shade_smooth()
    yield from m.alejar()
    # s30 File → Save As
    yield from m.seg('s30')
    fm = buscar('File', (0, 20, 200, 30))
    yield from m.clic(*(m.centro(fm) if fm else (50, 33))); yield 0.8
    yield from menu_ruta(['Save As'])
    yield 2.0
    nm = None
    for _ in range(5):
        nm = buscar('maqueta_parte_a.blend', (0, 0, 1920, 1080))
        if nm: break
        yield 0.5
    if nm:
        yield from m.editar_campo(*m.centro(nm), 'maqueta.blend'); yield 2.0
    else: aviso('guardar por bpy'); m.xdo('key', 'Escape')
    if not os.path.exists(T + 'maqueta.blend'): bpy.ops.wm.save_as_mainfile(filepath=T + 'maqueta.blend')
    m.xdo('mousemove', 700, 560)
    for _ in range(3): m.xdo('click', 5); yield 0.15
    yield from m.hasta(m.fin)
    yield 2.0
    m.ev('info', caras=len(rel.data.polygons), mats=[s.material.name for s in rel.material_slots])

m.correr(guion(), lambda: os._exit(0))
