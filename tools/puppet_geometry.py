"""Shared read-only decoder for our authored weighted attachment meshes."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
DATA=json.loads((ROOT/'assets/animation/maid.spine-json').read_text())
REGIONS=json.loads((ROOT/'preview/rig-data.js').read_text().removeprefix('const RIG_DATA=').removesuffix(';\n'))['preview_regions']
MESHES={}
for slot,parts in DATA['skins'][0]['attachments'].items():
    for name,mesh in parts.items():
        uv=np.array(mesh['uvs']).reshape(-1,2);count=len(uv)
        indices=np.zeros((count,4),dtype=int);local=np.zeros((count,4,2));weights=np.zeros((count,4));cursor=0
        for i in range(count):
            n=mesh['vertices'][cursor];cursor+=1
            assert 1<=n<=4
            for j in range(n):
                index,x,y,w=mesh['vertices'][cursor:cursor+4];cursor+=4
                assert 0<=index<len(DATA['bones']) and w>=0
                indices[i,j]=index;local[i,j]=[x,y];weights[i,j]=w
        assert cursor==len(mesh['vertices']) and np.max(np.abs(weights.sum(axis=1)-1))<1e-6
        triangles=np.array(mesh['triangles']).reshape(-1,3)
        MESHES[slot,name]={'uv':uv,'tri':triangles,'indices':indices,'local':local,'weights':weights,'path':mesh['path']}

def points(mesh,pose):
    a,b,c,d,tx,ty=np.moveaxis(np.array(pose['bones'])[mesh['indices']],2,0)
    x,y=np.moveaxis(mesh['local'],2,0);w=mesh['weights']
    return np.stack([((a*x+b*y+tx)*w).sum(axis=1),((c*x+d*y+ty)*w).sum(axis=1)],axis=1)

def areas(p,tri):
    a,b,c=p[tri[:,0]],p[tri[:,1]],p[tri[:,2]]
    return (b[:,0]-a[:,0])*(c[:,1]-a[:,1])-(b[:,1]-a[:,1])*(c[:,0]-a[:,0])
