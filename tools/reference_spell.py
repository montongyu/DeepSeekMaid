"""Gather, guide and release spells on the approved ready character.

Polar joint paths keep the forearm from collapsing when a hand crosses the
elbow. Both sleeves have overlapping rigid upper/fore surfaces and rigid palms.
"""
import copy
import json
import math
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from reference_palm import ROOT,S,JOINTS,SEGMENTS,POLYGONS,HAND_POLYGONS,world,mesh_polygon,expanded_outline
from reference_guard import neutral_joints,raised_body,pose_transform,curve_tracks,rgba

PROFILES={
 'cast':(1.25,'release'),'cast_arc':(1.35,'arc'),'cast_release':(1.15,'quick'),
 'cast_dual':(1.45,'dual'),'cast_point':(1.20,'guide'),'cast_circle':(1.40,'circle'),
 'channel':(1.65,'gather'),'channel_release':(1.50,'release'),
 'channel_gather':(1.75,'gather'),'channel_pulse':(1.60,'pulse'),'channel_overdrive':(1.90,'overdrive')}
PARTS=['arm_back','fore_back','hand_back','arm_front','fore_front','hand_front']

def extend(bones,slots,attachments,anims,regions):
    config=json.loads((ROOT/'assets/animation/reference-spell-author.json').read_text())
    config['views'].append({'file':'reference-palm-0-v0.8.2.png','registration':[[1,0,0],[0,1,0]],
        'joints':{k:v for k,v in JOINTS[0].items() if k.startswith(('shoulder','elbow','wrist','hand'))},
        'polygons':{**{p:POLYGONS[p][0] for p in ['arm_front','arm_back']},
                    **{'hand_'+s:HAND_POLYGONS[s][0] for s in ['front','back']}}})
    base=neutral_joints();bind={k:world(v) for k,v in JOINTS[0].items()}
    lengths={n:np.linalg.norm(bind[e]-bind[s]) if e else 1 for n,(s,e) in SEGMENTS.items()}
    origins={b['name']:np.array([b.get('x',0),b.get('y',0)]) for b in bones}
    indices={b['name']:i for i,b in enumerate(bones)}
    poses=[];mappings=[]
    for i,source in enumerate(config['views']):
        js=raised_body(base,[6,2,0][i],[-2,5,0][i])
        matrix=np.array(source['registration'],float)
        mapped={k:matrix[:,:2]@v+matrix[:,2] for k,v in source['joints'].items()}
        shifts={s:js['shoulder_'+s]-mapped['shoulder_'+s] for s in ['front','back']}
        for k,p in mapped.items():js[k]=p+shifts[k.split('_')[-1]]
        mappings.append((matrix,shifts));poses.append(js)
    source_tf=[pose_transform(js,lengths) for js in poses]
    info={'duration':1.25,'key_times':[.30*1.25,.54*1.25,0],
          'meshes':{},'profiles':{n:{'duration':d,'gesture':v} for n,(d,v) in PROFILES.items()},
          'body_model':'reference-palm-0-v0.8.2.png','new_painted_views':2,'ready_views':1}
    oldslots=[s['name'] for s in slots]
    for part in PARTS:
        side=part.split('_')[1]
        for view,source in enumerate(config['views']):
            file=source['file'];width,height=Image.open(ROOT/'assets/sprites'/file).size
            region=f'spell_{part}_{view}';regions[region]=(file,(0,0,width,height))
            outline=source['polygons']['arm_'+side if part.startswith('fore') else part]
            poly=expanded_outline(outline,3 if part.startswith('hand') else 7)
            holes=[] if part.startswith('hand') else [expanded_outline(source['polygons']['hand_'+side],3)]
            pts,tris=mesh_polygon(poly,4 if part.startswith('hand') else 8,holes)
            matrix,shifts=mappings[view];model=pts@matrix[:,:2].T+matrix[:,2]+shifts[side]
            js=poses[view];a,e,w=[js[k+'_'+side] for k in ['shoulder','elbow','wrist']]
            tangent=(e-a)/np.linalg.norm(e-a)+(w-e)/np.linalg.norm(w-e);tangent/=np.linalg.norm(tangent)
            pixels=np.array(Image.open(ROOT/'assets/sprites'/file).convert('RGBA'));keep=[]
            for tri in tris:
                if not part.startswith('hand'):
                    signed=np.dot(model[tri].mean(axis=0)-e,tangent)
                    if (part.startswith('arm') and signed>14) or (part.startswith('fore') and signed<-14):continue
                px=pts[tri]/[800,724]*[width,height]
                lo=np.maximum(0,np.floor(px.min(axis=0)).astype(int));hi=np.minimum([width-1,height-1],np.ceil(px.max(axis=0)).astype(int))
                if (hi<lo).any():continue
                mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
                cv2.fillConvexPoly(mask,np.round(px-lo).astype(np.int32),1)
                if np.any(pixels[lo[1]:hi[1]+1,lo[0]:hi[0]+1,3][mask.astype(bool)]>8):keep.append(tri)
            bone='ref_'+('hand_' if part.startswith('hand') else 'upper_' if part.startswith('arm') else 'fore_')+side
            pos,mat,*_=source_tf[view][bone];vertices=[]
            for p in model:
                local=np.linalg.solve(mat,world(p)-pos)
                vertices.extend([1,indices[bone],round(float(local[0]),6),round(float(local[1]),6),1])
            attachments[region]={region:{'type':'mesh','path':region,'width':width,'height':height,
                'uvs':(pts/[800,724]).ravel().tolist(),'triangles':np.array(keep).ravel().astype(int).tolist(),'vertices':vertices}}
            slots.append({'name':region,'bone':'ref_root','attachment':region,'color':'ffffff00'})
            info['meshes'][region]={'pose':view,'key_time':info['key_times'][view],'source_geometry':[world(p).tolist() for p in model]}
    for clip in anims.values():
        for slot in info['meshes']:clip['slots'][slot]={'rgba':rgba([(0,0)])}
    for name,(duration,gesture) in PROFILES.items():
        gather,release=copy.deepcopy(poses[0]),copy.deepcopy(poses[1])
        if gesture=='arc':
            for k in ['wrist_front','hand_front']:release[k]+=[-6,-38]
            release['elbow_front']+=[-4,-16]
        elif gesture=='dual':
            for k in ['wrist_back','hand_back']:release[k]+=[38,-12]
            release['elbow_back']+=[10,0]
        elif gesture=='guide':
            for k in ['elbow_front','wrist_front','hand_front']:release[k]+=[22,-8]
        elif gesture=='overdrive':
            for k in ['wrist_front','hand_front']:release[k]+=[26,-18]
            for k in ['wrist_back','hand_back']:release[k]+=[-10,-20]
        if gesture in ['gather','pulse','circle']:release=copy.deepcopy(gather)
        timing=np.array([0,.30,.54,.66,.84,.96,1])*duration
        path=[base,gather,release,release,gather,base,base]
        coords={k:np.array([p[k] for p in path]) for k in base}
        curves={k:[PchipInterpolator(timing,xy[:,axis]) for axis in range(2)] for k,xy in coords.items()}
        polar={}
        for side in ['front','back']:
            for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                delta=coords[end+'_'+side]-coords[start+'_'+side]
                angle=np.unwrap(np.arctan2(delta[:,1],delta[:,0]));length=np.linalg.norm(delta,axis=1)
                polar[start+'_'+side]=(PchipInterpolator(timing,angle),PchipInterpolator(timing,length))
        times=np.unique(np.round(np.r_[np.linspace(0,duration,round(duration*120)+1),timing],9))
        frames=[]
        for t in times:
            phase=t/duration;js={k:np.array([c[0](t),c[1](t)]) for k,c in curves.items()}
            for side in ['front','back']:
                for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                    ac,lc=polar[start+'_'+side];ang=float(ac(t));length=float(lc(t))
                    if start=='elbow' and gesture in ['circle','pulse']:
                        envelope=math.sin(math.pi*min(1,max(0,(phase-.12)/.76)))**2
                        ang+=math.radians(9 if gesture=='circle' else 4)*math.sin(phase*math.tau*(1 if gesture=='circle' else 3))*envelope
                    p=js[start+'_'+side]+length*np.array([math.cos(ang),math.sin(ang)])
                    if end=='wrist':
                        # Keep the rigid palm in the same local wrist offset.
                        js['hand_'+side]+=p-js[end+'_'+side]
                    js[end+'_'+side]=p
            envelope=math.sin(math.pi*phase)**2
            lag=math.sin((phase-.54)*math.tau*2)*envelope
            js['hair_tip']+=np.array([-5,2])*lag
            js['tail_tip']+=np.array([-4,-3])*lag
            frames.append(pose_transform(js,lengths))
        clip=anims[name]
        for bone in source_tf[0]:
            p=np.array([f[bone][0] for f in frames]);ang=np.unwrap([f[bone][2] for f in frames])*180/math.pi
            values={'translatex':p[:,0]-origins[bone][0],'translatey':p[:,1]-origins[bone][1],'rotate':ang,
                    'scalex':np.array([f[bone][3] for f in frames]),'scaley':np.array([f[bone][4] for f in frames])}
            clip['bones'][bone]=curve_tracks(times,values)
        for slot in oldslots:clip['slots'][slot]={'rgba':rgba([(0,0)])}
        for part in ['body_back','leg_back','leg_front','body_front']:clip['slots']['ref_'+part+'_0']={'rgba':rgba([(0,1)])}
        clip['slots']['ref_fill_front_0']={'rgba':rgba([(0,1),(.12*duration,0),(.94*duration,1)])}
        envelopes=[[(0,0),(.12,1),(.43,0),(.76,1),(.94,0)],[(0,0),(.43,1),(.76,0)],[(0,1),(.12,0),(.94,1)]]
        if gesture in ['gather','pulse','circle']:envelopes=[[(0,0),(.12,1),(.94,0)],[(0,0)],envelopes[2]]
        for slot,meta in info['meshes'].items():clip['slots'][slot]={'rgba':rgba([(t*duration,a) for t,a in envelopes[meta['pose']]])}
    (ROOT/'assets/animation/reference-spell.json').write_text(json.dumps(info,separators=(',',':')),encoding='utf-8')
    return info
