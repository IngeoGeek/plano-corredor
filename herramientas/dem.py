import json, numpy as np, sys
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
W=sys.argv[1]
g=json.load(open(f'{W}/curvas.geojson'))
pts=[];z=[]
for f in g['features']:
    e=f['properties']['elev']; geom=f['geometry']
    lines=geom['coordinates'] if geom['type']=='MultiLineString' else [geom['coordinates']]
    for l in lines:
        for c in l: pts.append(c[:2]); z.append(e)
pts=np.array(pts); z=np.array(z,float); print('vertices',len(z))
# rejilla de 30 m sobre el marco del mapa (+1 celda)
E0,E1,N0,N1=4885966.64,4928420.74,2241436.91,2278431.04
res=30.0
xs=np.arange(E0,E1+res,res); ys=np.arange(N1,N0-res,-res)
X,Y=np.meshgrid(xs,ys)
Z=griddata(pts,z,(X,Y),method='linear')
Zn=griddata(pts,z,(X,Y),method='nearest'); Z=np.where(np.isnan(Z),Zn,Z)
Z=gaussian_filter(Z,1.2)
np.save(f'{W}/dem30.npy',Z.astype(np.float32)); json.dump({'E0':E0,'E1':E1,'N0':N0,'N1':N1,'res':res,'shape':Z.shape},open(f'{W}/dem30.json','w'))
print(Z.shape, float(Z.min()), float(Z.max()))
