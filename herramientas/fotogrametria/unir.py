# blender -b --factory-startup --python unir.py -- W
# Une los bloques dec_*.blend, los lleva a metros de maqueta (centro de la ortofoto en el origen, Z desde 0,5 mm),
# cambia las texturas por las de W/tex (texturas_obj.py), exporta W/sitio/plano_relieve.glb y guarda W/vert_real.npy e info.json.
import bpy, sys, json, glob, os, numpy as np
W = sys.argv[-1]; P = json.load(open(W + '/params.json'))
Ec, Nc, ESC, BASE = (P['E0'] + P['E1']) / 2, (P['N0'] + P['N1']) / 2, P['ESC'], 0.0005
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
inf = [json.load(open(f)) for f in sorted(glob.glob(W + '/dec_*.json'))]
zmin = min(i['zmin'] for i in inf); zmax = max(i['zmax'] for i in inf)
objs = []
for f in sorted(glob.glob(W + '/dec_*.blend')):
    with bpy.data.libraries.load(f) as (src, dst): dst.objects = src.objects
    for o in dst.objects:
        if o and o.type == 'MESH': bpy.context.scene.collection.objects.link(o); objs.append(o)
for o in objs:
    o.location = ((P['oE'] - Ec) / ESC, (P['oN'] - Nc) / ESC, -zmin / ESC + BASE); o.scale = (1 / ESC,) * 3
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for im in bpy.data.images:
    p = W + '/tex/' + im.name
    if os.path.exists(p):
        if im.packed_file: im.unpack(method='REMOVE')
        im.filepath = p; im.reload(); im.pack()
for m in bpy.data.materials:
    if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
for o in objs:
    for p_ in o.data.polygons: p_.use_smooth = True
V = np.concatenate([np.array([(v.co.x, v.co.y, v.co.z) for v in o.data.vertices]) for o in objs])
np.save(W + '/vert_real.npy', np.c_[V[:, 0] * ESC + Ec, V[:, 1] * ESC + Nc, (V[:, 2] - BASE) * ESC + zmin + P['oZ']])
json.dump(dict(E0=P['E0'], E1=P['E1'], N0=P['N0'], N1=P['N1'], zmin=zmin + P['oZ'], zmax=zmax + P['oZ']), open(W + '/info.json', 'w'))
print('INFO caras', sum(len(o.data.polygons) for o in objs), 'z', zmin + P['oZ'], zmax + P['oZ'])
bpy.ops.wm.save_as_mainfile(filepath=W + '/maqueta.blend', compress=True)
os.makedirs(W + '/sitio', exist_ok=True)
bpy.ops.export_scene.gltf(filepath=W + '/sitio/plano_relieve.glb', export_format='GLB', use_selection=False, export_apply=True, export_yup=True, export_image_format='JPEG')
