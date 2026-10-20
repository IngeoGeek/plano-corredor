# -*- coding: utf-8 -*-
"""GLB → USDZ para AR Quick Look del iPhone (necesita usd-core: pip install usd-core)."""
import os, shutil
import numpy as np


def glb_a_usdz(src, out):
    import trimesh
    from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt, UsdUtils
    tmp = os.path.join(os.path.dirname(out), 'usd_tmp'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    scene = trimesh.load(src, force='scene')
    meshes = scene.dump(concatenate=False)
    st = Usd.Stage.CreateNew(os.path.join(tmp, 'plano.usdc'))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.y); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, '/Plano'); st.SetDefaultPrim(root.GetPrim())
    mats = {}
    for n, m in enumerate(meshes):
        vis = m.visual; mat = getattr(vis, 'material', None)
        name = f'm{n}'
        pts = m.vertices; faces = m.faces
        g = UsdGeom.Mesh.Define(st, f'/Plano/{name}')
        g.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(pts.astype(np.float32)))
        g.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(faces), 3, np.int32)))
        g.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(faces.astype(np.int32).ravel()))
        g.CreateSubdivisionSchemeAttr('none')
        g.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(m.vertex_normals.astype(np.float32))); g.SetNormalsInterpolation('vertex')
        g.CreateExtentAttr([Gf.Vec3f(*pts.min(0)), Gf.Vec3f(*pts.max(0))])
        uv = getattr(vis, 'uv', None)
        if uv is not None and len(uv) == len(pts):
            pv = UsdGeom.PrimvarsAPI(g).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
            pv.Set(Vt.Vec2fArray.FromNumpy(uv.astype(np.float32)))
        key = id(mat)
        if key not in mats:
            k = len(mats); M = UsdShade.Material.Define(st, f'/Plano/Mat{k}')
            sh = UsdShade.Shader.Define(st, f'/Plano/Mat{k}/PBR'); sh.CreateIdAttr('UsdPreviewSurface')
            sh.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(1.0)
            sh.CreateInput('useSpecularWorkflow', Sdf.ValueTypeNames.Int).Set(1)
            sh.CreateInput('specularColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0)); sh.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.0)
            img = getattr(mat, 'baseColorTexture', None) if mat is not None else None
            if img is not None:
                fn = f'tex{k}.jpg'; img.convert('RGB').save(os.path.join(tmp, fn), quality=88)
                rd = UsdShade.Shader.Define(st, f'/Plano/Mat{k}/st'); rd.CreateIdAttr('UsdPrimvarReader_float2')
                rd.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('st')
                tx = UsdShade.Shader.Define(st, f'/Plano/Mat{k}/tex'); tx.CreateIdAttr('UsdUVTexture')
                tx.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(fn)
                tx.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), 'result')
                tx.CreateInput('wrapS', Sdf.ValueTypeNames.Token).Set('clamp'); tx.CreateInput('wrapT', Sdf.ValueTypeNames.Token).Set('clamp')
                tx.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
                sh.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(tx.ConnectableAPI(), 'rgb')
            else:
                c = (np.array(getattr(mat, 'baseColorFactor', [240, 238, 232, 255])[:3], float) / 255.0) if mat is not None else np.array([0.94, 0.93, 0.9])
                sh.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*c))
            M.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), 'surface'); mats[key] = M
        UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mats[key])
    st.GetRootLayer().Save()
    ok = UsdUtils.CreateNewARKitUsdzPackage(Sdf.AssetPath(os.path.join(tmp, 'plano.usdc')), out)
    _ = ('usdz', ok, len(meshes), 'mallas', len(mats), 'materiales', os.path.getsize(out) // 1024, 'KB')
    shutil.rmtree(tmp, ignore_errors=True)
    return ok
