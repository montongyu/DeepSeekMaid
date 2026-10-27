"""Continuous native defense using approved raised-arm artwork and ready body.

Each sleeve is skinned independently; palms are rigid. The two painted arm
views have inverse binds at their own guard key, never full-figure crossfades.
"""
import json
import math
import copy
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from reference_palm import ROOT,S,JOINTS,SEGMENTS,POLYGONS,HAND_POLYGONS,world,transforms,mesh_polygon,expanded_outline

PROFILES={'guard':(1.15,1.0),'guard_brace':(1.25,1.16),'guard_raise':(1.15,.92),
          'guard_cross':(1.20,1.04),'guard_push':(1.10,1.0)}

def neutral_joints():
    js={k:np.array(v,float) for k,v in JOINTS[0].items()}
    for k in js:
        if k.startswith(('hip','knee','ankle','toe')):js[k][0]=470+(js[k][0]-470)*.52
        elif k not in ['tail','tail_tip']:js[k][1]-=15
    return js

def raised_body(base,drop,lean):
    js=copy.deepcopy(base)
    for k in js:
        if k.startswith(('ankle','toe')):continue
        if k.startswith('knee'):
            js[k][1]+=drop*.35
            js[k][0]+=(-1 if k.endswith('front') else 1)*drop*.20
        else:
            js[k][1]+=drop
            js[k][0]+=lean*(.4 if k.startswith('hip') or k in ['pelvis','hem','tail','tail_tip'] else 1)
    return js

def pose_transform(js,lengths):
    tf=transforms({k:world(v) for k,v in js.items()},lengths)
    # These palms remain upright throughout a block; wrist perspective is not
    # a reason to squeeze their fingers into an edge-on attack silhouette.
    for side in ['front','back']:
        name='ref_hand_'+side
        p=tf[name][0]
        tf[name]=(p,np.eye(2),0.,1.,1.)
    return tf

def curve_tracks(times,values):
    tracks={}
    for kind,ys in values.items():
        derivative=np.gradient(ys,times)
        keys=[]
        for j,(t,v) in enumerate(zip(times,ys)):
            key={'time':round(float(t),7),'value':round(float(v),7)}
            if j+1<len(times):
                dt=times[j+1]-t
                key['curve']=[float(t+dt/3),float(v+derivative[j]*dt/3),
                              float(times[j+1]-dt/3),float(ys[j+1]-derivative[j+1]*dt/3)]
            keys.append(key)
        tracks[kind]=keys
    return tracks

def rgba(schedule):
    return [{'time':round(float(t),7),'color':'ffffff'+f'{round(a*255):02x}','curve':'stepped'} for t,a in schedule]

def extend(bones,slots,attachments,anims,regions):
    config=json.loads((ROOT/'assets/animation/reference-guard-author.json').read_text())
    config['views'].append({'file':'reference-palm-0-v0.8.2.png','registration':[[1,0,0],[0,1,0]],
        'joints':{k:v for k,v in JOINTS[0].items() if k.startswith(('shoulder','elbow','wrist','hand'))},
        'polygons':{**{part:POLYGONS[part][0] for part in ['arm_front','arm_back']},
                    **{'hand_'+side:HAND_POLYGONS[side][0] for side in ['front','back']}}})
    base=neutral_joints()
    bind={k:world(v) for k,v in JOINTS[0].items()}
    lengths={n:np.linalg.norm(bind[e]-bind[s]) if e else 1 for n,(s,e) in SEGMENTS.items()}
    origins={b['name']:np.array([b.get('x',0),b.get('y',0)]) for b in bones}
    indices={b['name']:i for i,b in enumerate(bones)}
    source_poses=[];mappings=[]
    for i,source in enumerate(config['views']):
        js=raised_body(base,[8,15,0][i],[-2,-8,0][i])
        matrix=np.array(source['registration'],float)
        mapped={k:matrix[:,:2]@v+matrix[:,2] for k,v in source['joints'].items()}
        shifts={side:js['shoulder_'+side]-mapped['shoulder_'+side] for side in ['front','back']}
        for k in mapped:
            side=k.split('_')[-1]
            js[k]=mapped[k]+shifts[side]
        mappings.append((matrix,shifts));source_poses.append(js)
    source_tf=[pose_transform(js,lengths) for js in source_poses]
    info={'duration':PROFILES['guard'][0],'key_times':[.26*1.15,.46*1.15,0],
          'meshes':{},'profiles':{n:{'duration':d,'recoil':v} for n,(d,v) in PROFILES.items()},
          'uniform_body_model':'reference-palm-0-v0.8.2.png','arm_source_views':2}
    old_slot_names=[s['name'] for s in slots]
    for part in ['arm_back','hand_back','arm_front','fore_front','hand_front']:
        side=part.split('_')[1]
        for view,source in enumerate(config['views']):
            file=source['file'];width,height=Image.open(ROOT/'assets/sprites'/file).size
            region=f'guard_{part}_{view}'
            regions[region]=(file,(0,0,width,height))
            outline=source['polygons']['arm_front' if part=='fore_front' else part]
            poly=expanded_outline(outline,3 if part.startswith('hand') else 7)
            holes=[expanded_outline(source['polygons']['hand_'+side],3)] if part.startswith(('arm','fore')) else []
            pts,tris=mesh_polygon(poly,4 if part.startswith('hand') else 7,holes)
            matrix,shifts=mappings[view]
            model=pts@matrix[:,:2].T+matrix[:,2]+shifts[side]
            pixels=np.array(Image.open(ROOT/'assets/sprites'/file).convert('RGBA'))
            # Omit fully transparent triangles, preserving the painted edge.
            keep=[]
            import cv2
            for tri in tris:
                px=pts[tri]/[800,724]*[width,height]
                lo=np.maximum(0,np.floor(px.min(axis=0)).astype(int));hi=np.minimum([width-1,height-1],np.ceil(px.max(axis=0)).astype(int))
                if (hi<lo).any():continue
                mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
                cv2.fillConvexPoly(mask,np.round(px-lo).astype(np.int32),1)
                if np.any(pixels[lo[1]:hi[1]+1,lo[0]:hi[0]+1,3][mask.astype(bool)]>8):keep.append(tri)
            vertices=[]
            js=source_poses[view]
            a,e,wrist=[js[k+'_'+side] for k in ['shoulder','elbow','wrist']]
            tangent=(e-a)/np.linalg.norm(e-a)+(wrist-e)/np.linalg.norm(wrist-e)
            tangent/=np.linalg.norm(tangent)
            if side=='front' and not part.startswith('hand'):
                # Overlapping rigid sleeve halves preserve cuff and puff-sleeve
                # volume at an acute elbow. Never blend opposite rotations
                # across the whole sleeve, which pinches into a bow tie.
                keep=[tri for tri in keep if (np.dot(model[tri].mean(axis=0)-e,tangent)<=14 if part=='arm_front' else np.dot(model[tri].mean(axis=0)-e,tangent)>=-14)]
            for p in model:
                wp=world(p)
                if part.startswith('hand'):ws={'ref_hand_'+side:1.}
                elif side=='front':ws={'ref_'+('upper_front' if part=='arm_front' else 'fore_front'):1.}
                else:
                    u=float(np.clip((np.dot(p-e,tangent)+75)/150,0,1));u=u*u*(3-2*u)
                    ws={'ref_upper_'+side:1-u,'ref_fore_'+side:u}
                    ws={k:v for k,v in ws.items() if v>1e-6}
                vertices.append(len(ws))
                for bone,weight in ws.items():
                    pos,mat,*_=source_tf[view][bone]
                    local=np.linalg.solve(mat,wp-pos)
                    vertices.extend([indices[bone],round(float(local[0]),6),round(float(local[1]),6),round(weight,8)])
            mesh={'type':'mesh','path':region,'width':width,'height':height,'uvs':(pts/[800,724]).ravel().tolist(),
                  'triangles':np.array(keep).ravel().astype(int).tolist(),'vertices':vertices}
            slots.append({'name':region,'bone':'ref_root','attachment':region,'color':'ffffff00'})
            attachments[region]={region:mesh}
            info['meshes'][region]={'pose':view,'key_time':info['key_times'][view],
                                   'source_geometry':[world(p).tolist() for p in model]}
    for animation in anims.values():
        for slot in info['meshes']:animation['slots'][slot]={'rgba':rgba([(0,0)])}
    for name,(duration,intensity) in PROFILES.items():
        times=np.unique(np.round(np.r_[np.linspace(0,duration,round(duration*120)+1),np.array([0,.26,.46,.58,.78,.94,1])*duration],9))
        timing=np.array([0,.26,.46,.58,.76,.94,1])*duration
        block=copy.deepcopy(source_poses[1]);recovery=copy.deepcopy(source_poses[0])
        # Braced response is small and controlled; shoes remain fixed.
        for k in block:
            if not k.startswith(('ankle','toe')):
                block[k][0]-=3*(intensity-1)
                block[k][1]+=2*(intensity-1)
        path=[base,source_poses[0],source_poses[1],block,recovery,base,base]
        curves={k:[PchipInterpolator(timing,np.array([p[k] for p in path])[:,axis]) for axis in range(2)] for k in base}
        frames=[]
        for t in times:
            js={k:np.array([cs[0](t),cs[1](t)],float) for k,cs in curves.items()}
            phase=t/duration
            # Elbows rise on arcs; the return palm follows the elbow instead of
            # cutting a straight line through the sleeve.
            for start,end,height in [(0,.26,36),(.76,.94,36)]:
                if start<phase<end:
                    lift=height*math.sin(math.pi*(phase-start)/(end-start))**2
                    for k in ['wrist_front','hand_front']:js[k][1]-=lift
            secondary=math.sin(max(0,phase-.26)*math.tau*2)*math.exp(-max(0,phase-.26)*5) if phase>.26 else 0
            # Zero lag at the two reconstruction keys.
            secondary*=math.sin(math.pi*(phase-.46))**2
            js['hair_tip']+=np.array([-6,2])*secondary
            js['tail_tip']+=np.array([-4,-3])*secondary
            frames.append(pose_transform(js,lengths))
        clip=anims[name]
        for bone in source_tf[0]:
            p=np.array([tf[bone][0] for tf in frames]);angles=np.unwrap([tf[bone][2] for tf in frames])*180/math.pi
            values={'translatex':p[:,0]-origins[bone][0],'translatey':p[:,1]-origins[bone][1],'rotate':angles,
                    'scalex':np.array([tf[bone][3] for tf in frames]),'scaley':np.array([tf[bone][4] for tf in frames])}
            clip['bones'][bone]=curve_tracks(times,values)
        for slot in old_slot_names:
            clip['slots'][slot]={'rgba':rgba([(0,0)])}
        # Same body, hair, tail, petticoat and legs as the ready/attack model.
        for part in ['body_back','leg_back','leg_front','body_front']:
            clip['slots'][f'ref_{part}_0']={'rgba':rgba([(0,1)])}
        clip['slots']['ref_fill_front_0']={'rgba':rgba([(0,1),(.10*duration,0),(.88*duration,1)])}
        for slot,meta in info['meshes'].items():
            schedule=([[(0,0),(.10*duration,1),(.355*duration,0),(.66*duration,1),(.88*duration,0)],
                       [(0,0),(.355*duration,1),(.66*duration,0)],
                       [(0,1),(.10*duration,0),(.88*duration,1)]][meta['pose']])
            clip['slots'][slot]={'rgba':rgba(schedule)}
    file='reference-shield-v0.8.3.png';width,height=Image.open(ROOT/'assets/sprites'/file).size
    regions['guard_water']=(file,(0,0,width,height))
    (ROOT/'assets/animation/reference-guard.json').write_text(json.dumps(info,separators=(',',':')),encoding='utf-8')
    return info
