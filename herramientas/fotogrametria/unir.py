"""Une los bloques simplificados, los ubica en metros de maqueta (centro de la ortofoto en el origen, norte +Y,
cota mínima 0,5 mm sobre el piso), cambia las texturas por las reducidas y exporta el GLB.
Uso: blender -b --factory-startup --python unir.py -- W [RATIO_FINAL]   (escala: la de proyecto.json; RATIO_FINAL < 1 simplifica otra vez)"""
import bpy, json, glob, os, sys, numpy as np
args = sys.argv[sys.argv.index('--') + 1:]; W = args[0]; RAT = float(args[1]) if len(args) > 1 else 1.0
P = json.load(open(W + '/proyecto.json')); ESC, BASE = P['escala'], 0.0005
Ec, Nc = (P['E0'] + P['E1']) / 2, (P['N0'] + P['N1']) / 2
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
infos = [json.load(open(f)) for f in sorted(glob.glob(W + '/dec_*.json'))]
zmin = min(i['zmin'] for i in infos); zmax = max(i['zmax'] for i in infos)
objs = []
for f in sorted(glob.glob(W + '/dec_*.blend')):
    with bpy.data.libraries.load(f) as (src, dst): dst.objects = src.objects
    for o in dst.objects:
        if o and o.type == 'MESH': bpy.context.scene.collection.objects.link(o); objs.append(o)
for o in objs:
    o.location = ((P['oE'] - Ec) / ESC, (P['oN'] - Nc) / ESC, -zmin / ESC + BASE); o.scale = (1 / ESC,) * 3; o.rotation_euler = (0, 0, 0)
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
V = np.concatenate([np.array([(v.co.x, v.co.y, v.co.z) for v in o.data.vertices]) for o in objs])
np.save(W + '/vert_real.npy', np.c_[V[:, 0] * ESC + Ec, V[:, 1] * ESC + Nc, (V[:, 2] - BASE) * ESC + zmin + P['oZ']])
if RAT < 1:
    for o in objs:
        bpy.context.view_layer.objects.active = o; m = o.modifiers.new('d', 'DECIMATE'); m.ratio = RAT; bpy.ops.object.modifier_apply(modifier='d')
for m in bpy.data.materials:
    if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
for o in objs:
    for p in o.data.polygons: p.use_smooth = True
for im in bpy.data.images:
    p = W + '/tex/' + im.name
    if os.path.exists(p):
        if im.packed_file: im.unpack(method='REMOVE')
        im.filepath = p; im.reload(); im.pack()
info = dict(E0=P['E0'], E1=P['E1'], N0=P['N0'], N1=P['N1'], zmin=zmin + P['oZ'], zmax=zmax + P['oZ'], escala=ESC,
            caras=sum(len(o.data.polygons) for o in objs), alto_m=float((V[:, 2].max() - BASE)))
json.dump(info, open(W + '/info.json', 'w')); print('INFO', json.dumps(info))
os.makedirs(W + '/sitio', exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=W + '/maqueta.blend', compress=True)
bpy.ops.export_scene.gltf(filepath=W + '/sitio/plano_relieve.glb', export_format='GLB', use_selection=False, export_apply=True, export_yup=True, export_image_format='JPEG')
