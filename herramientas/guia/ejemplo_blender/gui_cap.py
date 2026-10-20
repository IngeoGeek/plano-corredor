import bpy, os, sys, subprocess, math
sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/blender')
import pasos as P
OUT = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm/bcap/'
def win(): return bpy.context.window_manager.windows[0]
def area(t):
    return [a for a in win().screen.areas if a.type == t][0]
def region(a, t='WINDOW'): return [r for r in a.regions if r.type == t][0]
def ov(t='VIEW_3D'):
    a = area(t); return bpy.context.temp_override(window=win(), area=a, region=region(a))
def foto(n):
    for a in win().screen.areas: a.tag_redraw()
    subprocess.run(['import', '-window', 'root', OUT + n + '.png'])
def log(*a): open(OUT + 'log.txt', 'a').write(' '.join(map(str, a)) + '\n')
def vista(obj=None, rx=55, rz=-20, dist=None, sel=True):
    a = area('VIEW_3D'); sp = a.spaces[0]; sp.shading.type = 'MATERIAL'; sp.overlay.show_floor = True
    r3 = sp.region_3d
    if obj is not None:
        for o in bpy.context.view_layer.objects: o.select_set(False)
        obj.select_set(True); bpy.context.view_layer.objects.active = obj
        with ov(): bpy.ops.view3d.view_selected()
    import mathutils
    r3.view_rotation = mathutils.Euler((math.radians(rx), 0, math.radians(rz))).to_quaternion()
    if dist: r3.view_distance = dist
def panel_n(on=True, tab='Item'):
    sp = area('VIEW_3D').spaces[0]; sp.show_region_ui = on
    try:
        for r in area('VIEW_3D').regions:
            if r.type == 'UI': r.active_panel_category = tab
    except Exception as e: log('tab', e)
def props(ctx):
    a = area('PROPERTIES'); a.spaces[0].context = ctx
G = {}
PASOS = []
def paso(espera=2.0):
    def d(f): PASOS.append((f, espera)); return f
    return d
def correr():
    if not PASOS: os._exit(0)
    f, e = PASOS.pop(0)
    try: f()
    except Exception:
        import traceback; log(f.__name__, traceback.format_exc())
    return e
@paso(3)
def s0():
    P.paso0_limpiar(); h = P.paso1_hoja(); G['h'] = h
    vista(h, 0, 0); panel_n(True, 'Item'); props('MATERIAL')
@paso(4)
def s0b(): foto('b01_hoja')
@paso(3)
def s1():
    a = area('VIEW_3D'); G['a3'] = a; a.type = 'NODE_EDITOR'; a.ui_type = 'ShaderNodeTree'
@paso(2)
def s1b():
    a = [x for x in win().screen.areas if x.type == 'NODE_EDITOR'][0]
    with bpy.context.temp_override(window=win(), area=a, region=region(a)): bpy.ops.node.view_all()
@paso(1.5)
def s1c(): foto('b02_material')
@paso(2)
def s2():
    a = [x for x in win().screen.areas if x.type == 'NODE_EDITOR'][0]; a.type = 'VIEW_3D'
@paso(3)
def s2b():
    with ov():
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=600, y_subdivisions=522, size=1, location=(P.CX, P.CY, P.Z_REL))
    r = bpy.context.active_object; r.name = 'Relieve'; G['r'] = r
    r.dimensions = (P.MARCO['w'] / 1000, P.MARCO['h'] / 1000, 0)
    with ov(): bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    r.data.materials.append(P.material_imagen('Mapa', P.W + '/plano_mapa.jpg')); r.data.materials.append(P.material_color('Pared', (0.42, 0.40, 0.37)))
    panel_n(True, 'Item'); vista(r, 0, 0)
@paso(1.5)
def s2r():
    for a in win().screen.areas: a.tag_redraw()
@paso(1.5)
def s2c(): foto('b03_rejilla')
@paso(3)
def s3():
    r = G['r']
    P.paso3_desplazar(r); P.paso4_simplificar(r); props('MODIFIER'); vista(r, 58, -18); panel_n(False)
@paso(4)
def s3b(): foto('b04_modificadores')
@paso(2)
def s4(): props('TEXTURE')
@paso(2)
def s4b(): foto('b05_textura')
@paso(4)
def s5():
    r = G['r']
    with ov():
        for m in list(r.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='VERT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.mesh.select_non_manifold()
    vista(None, 62, -25); a = area('VIEW_3D'); a.spaces[0].shading.type = 'SOLID'
    r3 = a.spaces[0].region_3d; import mathutils; r3.view_location = mathutils.Vector((P.CX - 0.28, P.CY - 0.25, 0.02)); r3.view_distance = 0.16; a.spaces[0].overlay.show_wireframes = False
@paso(2)
def s5b(): foto('b06_borde')
@paso(3)
def s6():
    r = G['r']
    with ov():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT'); r.select_set(True); bpy.context.view_layer.objects.active = r
    with ov(): P.paso5_paredes(r)
    a = area('VIEW_3D'); a.spaces[0].shading.type = 'MATERIAL'
@paso(3)
def s6b():
    P.paso6_chinchetas()
    t = [o for o in bpy.data.objects if o.name.startswith('Landázuri · Text')][0]
    vista(t, 75, -12); a = area('VIEW_3D'); a.spaces[0].region_3d.view_distance = 0.22; panel_n(True, 'Item'); props('OBJECT')
@paso(2)
def s6c(): foto('b07_chinchetas')
@paso(3)
def s7():
    panel_n(False); bpy.ops.object.select_all(action='DESELECT')
    vista(G['h'], 52, -10); area('VIEW_3D').spaces[0].region_3d.view_distance = 1.25
    area('VIEW_3D').spaces[0].overlay.show_floor = False; area('VIEW_3D').spaces[0].overlay.show_axis_x = False; area('VIEW_3D').spaces[0].overlay.show_axis_y = False
@paso(2)
def s7b(): foto('b09_final')
@paso(4)
def s8():
    import bpy as B
    for n in ['GLTF_PT_export_include', 'GLTF_PT_export_transform', 'GLTF_PT_export_data', 'GLTF_PT_export_data_mesh', 'GLTF_PT_export_data_material', 'GLTF_PT_export_data_compression']:
        c = getattr(B.types, n, None)
        if c is None: log('no', n); continue
        try: B.utils.unregister_class(c); c.bl_options = {o for o in getattr(c, 'bl_options', set()) if o != 'DEFAULT_CLOSED'}; B.utils.register_class(c)
        except Exception as e: log('panel', n, e)
    with ov():
        bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath='/tmp/plano_relieve.glb', export_format='GLB', export_apply=True, export_image_format='JPEG', use_visible=True)
@paso(2)
def s8b(): foto('b08_gltf')
bpy.app.timers.register(correr, first_interval=4)
