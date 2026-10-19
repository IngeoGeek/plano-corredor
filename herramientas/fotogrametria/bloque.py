"""Importa un bloque OBJ (Z arriba) y lo simplifica. Uso:
blender -b --factory-startup --python bloque.py -- BLOQUE.obj SALIDA_SIN_EXTENSION RATIO"""
import bpy, sys, json, time
obj, out, ratio = sys.argv[-3], sys.argv[-2], float(sys.argv[-1]); T = time.time()
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=obj, forward_axis='Y', up_axis='Z')
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
if len(objs) > 1: bpy.ops.object.join()
o = bpy.context.view_layer.objects.active; n0 = len(o.data.polygons)
m = o.modifiers.new('d', 'DECIMATE'); m.ratio = ratio; bpy.ops.object.modifier_apply(modifier='d')
zs = [v.co.z for v in o.data.vertices]
info = dict(caras0=n0, caras=len(o.data.polygons), zmin=min(zs), zmax=max(zs), t=round(time.time() - T, 1))
print('INFO', json.dumps(info)); json.dump(info, open(out + '.json', 'w'))
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=out + '.blend', compress=True)
