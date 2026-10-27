"""One approved palm-up rest pose and one visible rig for every action.

Existing drawings are viewing angles on shared attachment slots, never layers
of fading whole characters. Normal actions start/end at REST; death/revive use
the same figure and a dedicated floor drawing.
"""
import copy
import json
import math
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from reference_palm import ROOT,S,JOINTS,POLYGONS,HAND_POLYGONS,SEGMENTS,mesh_polygon,expanded_outline,registration
from reference_guard import curve_tracks

MASTER='offer-master-v0.8.5.png'
HAND_AXES={'default':{'front':10,'back':55},'palm0':{'front':90,'back':0},'palm1':{'front':78,'back':0},
           'palm2':{'front':45,'back':60},'guard0':{'front':90,'back':60},'guard1':{'front':90,'back':95},'gather':{'front':150,'back':10}}
REST=dict(head=(515,133),neck=(483,196),pelvis=(483,285),hem=(485,490),
 hair=(330,220),hair_tip=(195,250),tail=(280,430),tail_tip=(118,340),
 shoulder_front=(556,241),elbow_front=(612,311),wrist_front=(677,291),hand_front=(719,283),
 shoulder_back=(375,242),elbow_back=(372,292),wrist_back=(416,267),hand_back=(439,245),
 hip_front=(411,470),knee_front=(337,568),ankle_front=(299,642),toe_front=(302,698),
 hip_back=(562,470),knee_back=(600,562),ankle_back=(632,642),toe_back=(647,698))
REST={k:np.array(v,float) for k,v in REST.items()}
REST.update(hair_lower=np.array([300.,290.]),hair_lower_tip=np.array([145.,300.]),hair_crown=np.array([490.,45.]))
# Extra controls deform the existing master UVs; no extra painted pages/layers.
SEGMENTS={**SEGMENTS,**{name:(name,None) for name in ['hair_lower','hair_lower_tip','hair_crown']}}
HAIR_BONES=['hair','hair_tip','hair_lower','hair_lower_tip','hair_crown']
LEG_POLYGONS={
 'front':[(379,485),(420,495),(401,524),(376,556),(352,587),(325,623),(319,644),(324,664),(334,683),(339,703),(327,716),(302,721),(278,717),(266,707),(266,690),(276,663),(280,643),(293,615),(318,579),(342,540),(365,510)],
 'back':[(550,480),(583,478),(592,502),(604,535),(618,568),(631,605),(642,635),(649,654),(664,678),(683,693),(686,710),(673,719),(648,718),(631,708),(609,706),(602,693),(607,669),(615,647),(602,619),(584,586),(571,553),(558,521)]}

def world(p):return (np.array(p)-[470,718])*[S,-S]
def clone(p=REST):return {k:np.array(v,float).copy() for k,v in p.items()}
def body_pose(drop=0,lean=0):
    p=clone()
    for k in p:
        if k.startswith(('ankle','toe')):continue
        if k.startswith('knee'):
            p[k][1]+=drop*.35
            p[k][0]+=(-1 if k.endswith('front') else 1)*drop*.12
        else:p[k]+=[lean,drop]
    return p

LENGTHS={n:float(np.linalg.norm(world(REST[e])-world(REST[s]))) if e else 1. for n,(s,e) in SEGMENTS.items()}
PARENTS={}
for side in ['front','back']:
    for child,parent in [('fore','upper'),('hand','fore'),('shin','thigh'),('foot','shin')]:
        PARENTS['ref_'+child+'_'+side]='ref_'+parent+'_'+side
def transforms(p,hand_angles=None):
    out={};hand_angles=HAND_AXES['default'] if hand_angles is None else hand_angles
    for name,(start,end) in SEGMENTS.items():
        pos=world(p[start]);angle=0.;sx=1.
        if end:
            delta=world(p[end])-pos;angle=math.atan2(delta[1],delta[0]);sx=np.linalg.norm(delta)/LENGTHS[name]
        if name.startswith('hand'):angle=math.radians(hand_angles.get(name.split('_')[1],0))
        c,s=math.cos(angle),math.sin(angle)
        out['ref_'+name]=(pos,np.array([[c*sx,-s],[s*sx,c]]),angle,float(sx),1.)
    return out

def local_transforms(tf):
    out={}
    for name,(pos,mat,angle,sx,sy) in tf.items():
        parent=PARENTS.get(name)
        if parent:
            pp,pm,pa,*_=tf[parent]
            pos=np.linalg.solve(pm,pos-pp)
            # Spine noScale normalizes the parent's transformed rotation axis.
            # Its inverse depends on the parent's nonuniform scale as well.
            axis=np.linalg.solve(pm,np.array([math.cos(angle),math.sin(angle)]))
            angle=math.atan2(axis[1],axis[0])
        out[name]=(pos,angle,sx,sy)
    return out

def build_views():
    spell=json.loads((ROOT/'assets/animation/reference-spell-author.json').read_text())['views']
    guard=json.loads((ROOT/'assets/animation/reference-guard-author.json').read_text())['views']
    sources={'default':{**spell[1],'file':MASTER}}
    for i in range(3):
        sources['palm'+str(i)]={'file':f'reference-palm-{i}-v0.8.2.png','registration':[[1,0,0],[0,1,0]],
         'joints':{k:v for k,v in JOINTS[i].items() if k.startswith(('shoulder','elbow','wrist','hand'))},
         'polygons':{**{p:POLYGONS[p][i] for p in ['arm_front','arm_back']},**{'hand_'+s:HAND_POLYGONS[s][i] for s in ['front','back']}}}
    sources.update(guard0=guard[0],guard1=guard[1],gather=spell[0])
    shapes={'default':(0,0),'palm0':(6,-3),'palm1':(16,8),'palm2':(4,1),'guard0':(6,0),'guard1':(12,-4),'gather':(3,0)}
    for name,source in sources.items():
        p=body_pose(*shapes[name]);matrix=np.array(source['registration'],float)
        mapped={k:matrix[:,:2]@v+matrix[:,2] for k,v in source['joints'].items()}
        shifts={side:p['shoulder_'+side]-mapped['shoulder_'+side] for side in ['front','back']}
        for k,v in mapped.items():p[k]=v+shifts[k.split('_')[-1]]
        if name=='palm1':
            p['hip_front']+=[-18,0];p['knee_front']+=[-42,8];p['ankle_front'][0]-=48;p['toe_front'][0]-=48
            p['knee_back']+=[18,10];p['ankle_back'][0]+=20;p['toe_back'][0]+=20
        source.update(pose=p,matrix=matrix,shifts=shifts)
    # The default is the user's exact image, with no shoulder repositioning.
    sources['default']['pose']=clone();sources['default']['matrix']=np.array([[1,0,0],[0,1,0]],float)
    sources['default']['shifts']={s:np.zeros(2) for s in ['front','back']}
    return sources

def clipped_triangles(file,uv,tri):
    pixels=np.array(Image.open(ROOT/'assets/sprites'/file).convert('RGBA'));h,w=pixels.shape[:2];keep=[]
    for t in tri:
        px=uv[t]*[w,h];lo=np.maximum(0,np.floor(px.min(axis=0)).astype(int));hi=np.minimum([w-1,h-1],np.ceil(px.max(axis=0)).astype(int))
        if (hi<lo).any():continue
        mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
        cv2.fillConvexPoly(mask,np.round(px-lo).astype(np.int32),1)
        if np.any(pixels[lo[1]:hi[1]+1,lo[0]:hi[0]+1,3][mask.astype(bool)]>8):keep.append(t)
    return np.array(keep,int)

def body_weights(p):
    x,y=p
    def ramp(a,b,v):
        u=float(np.clip((v-a)/(b-a),0,1));return u*u*(3-2*u)
    def mix(a,b,u):return {k:a.get(k,0)*(1-u)+b.get(k,0)*u for k in a.keys()|b.keys()}
    w=mix({'ref_head':1},{'ref_torso':1},ramp(170,245,y))
    w=mix(w,{'ref_skirt':1},ramp(290,390,y))
    hair=(1-ramp(388,468,x))*(1-ramp(300,378,y))
    root=mix({'ref_hair':1},{'ref_hair_lower':1},ramp(185,285,y))
    tips=mix({'ref_hair_tip':1},{'ref_hair_lower_tip':1},ramp(185,285,y))
    hw=mix(tips,root,ramp(180,350,x))
    w=mix(w,hw,hair)
    w=mix(w,{'ref_tail':1},(1-ramp(270,355,x))*ramp(300,365,y))
    # Keep the headband and face still while the isolated crown curl springs.
    crown=(1-ramp(30,65,y))*ramp(425,455,x)*(1-ramp(550,580,x))
    return mix(w,{'ref_hair_crown':1},crown)

def body_grid(front):
    hx=[0,250,300,350,400,450,500,550,600,650,800];hy=[440,460,490,517,526,536,532,518,498,478,470]
    nx,ny=40,26 if front else 12;pts=[];tri=[]
    for j in range(ny+1):
        for i in range(nx+1):
            x=800*i/nx;hem=np.interp(x,hx,hy);y=hem*j/ny if front else hem+(724-hem)*j/ny;pts.append([x,y])
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1;tri.extend([[a,b,c],[b,d,c]])
    return np.array(pts),np.array(tri)

def extend(bones,slots,attachments,anims,regions):
    names=list(anims);bones.clear();slots.clear();attachments.clear();regions.clear()
    sources=build_views();rest_tf=transforms(REST)
    bones.append({'name':'ref_root'})
    local_rest=local_transforms(rest_tf)
    for name,(p,a,sx,sy) in local_rest.items():
        bone={'name':name,'parent':PARENTS.get(name,'ref_root'),'x':float(p[0]),'y':float(p[1]),'rotation':math.degrees(a),'scaleX':sx,'scaleY':sy,
              'length':LENGTHS[name.removeprefix('ref_')]}
        if name in PARENTS:bone['inherit']='noScale'
        bones.append(bone)
    bones.append({'name':'prone'})
    idx={b['name']:i for i,b in enumerate(bones)}
    info={'baseline':MASTER,'rest_joints':{k:v.tolist() for k,v in REST.items()},'bone_lengths':LENGTHS,
          'meshes':{},'clips':{},'canonical_canvas':[800,724],'origin':[470,718],'scale':S}
    def slot(name,attachment=None,visible=True,bone='ref_root'):
        s={'name':name,'bone':bone,'color':'ffffffff' if visible else 'ffffff00'}
        if attachment:s['attachment']=attachment
        slots.append(s);attachments[name]={}
    def mesh(slot_name,name,file,model,uv,tris,tf,weights,key=('idle_loop',0)):
        w,h=Image.open(ROOT/'assets/sprites'/file).size;regions[name]=(file,(0,0,w,h));verts=[]
        for p in model:
            ws=weights(p);ws={b:v for b,v in ws.items() if v>1e-6}
            if len(ws)>4:ws=dict(sorted(ws.items(),key=lambda kv:-kv[1])[:4])
            total=sum(ws.values());verts.append(len(ws))
            for b,weight in ws.items():
                pos,mat,*_=tf[b];local=np.linalg.solve(mat,world(p)-pos)
                verts.extend([idx[b],float(local[0]),float(local[1]),float(weight/total)])
        tris=clipped_triangles(file,uv,tris)
        attachments[slot_name][name]={'type':'mesh','path':name,'width':w,'height':h,'uvs':uv.ravel().tolist(),'triangles':tris.ravel().tolist(),'vertices':verts}
        info['meshes'][slot_name+'/'+name]={'source_geometry':[world(p).tolist() for p in model],'check_animation':key[0],'check_time':key[1]}
    body_file='offer-body-v0.8.5.png';bm=registration(ROOT/'assets/sprites'/MASTER,ROOT/'assets/sprites'/body_file)
    default=sources['default']
    holes=[expanded_outline(default['polygons']['arm_'+s],8) for s in ['front','back']]+[expanded_outline(LEG_POLYGONS[s],9) for s in ['front','back']]
    # Restore only occluded areas. Visible hair, face, dress and tail come from
    # the exact user-supplied master, rather than the reconstructed body layer.
    fill_points=[];fill_tris=[]
    for hole in holes:
        p,t=mesh_polygon(hole,12);offset=len(fill_points);fill_points.extend(p);fill_tris.extend(t+offset)
    fill_points=np.array(fill_points);fill_tris=np.array([t for t in fill_tris if fill_points[t].mean(axis=0)[1]<555])
    slot('body_fill','body_fill')
    image_pts=(fill_points-bm[:,2])@np.linalg.inv(bm[:,:2]).T
    mesh('body_fill','body_fill',body_file,fill_points,image_pts/[800,724],fill_tris,rest_tf,body_weights)
    master_body,master_tris=mesh_polygon([(0,0),(800,0),(800,724),(0,724)],13,holes)
    for front in [False,True]:
        if front:
            for side in ['back','front']:
                pts,tris=mesh_polygon(expanded_outline(LEG_POLYGONS[side],9),7)
                hip,knee,ankle=[REST[k+'_'+side] for k in ['hip','knee','ankle']]
                tangent=(knee-hip)/np.linalg.norm(knee-hip)+(ankle-knee)/np.linalg.norm(ankle-knee);tangent/=np.linalg.norm(tangent)
                for part in ['thigh','shin','foot']:
                    name='leg_'+part+'_'+side;slot(name,name)
                    keep=[]
                    for t in tris:
                        c=pts[t].mean(axis=0);at_knee=np.dot(c-knee,tangent)
                        if part=='thigh' and at_knee<=15:keep.append(t)
                        elif part=='shin' and at_knee>=-15 and c[1]<=ankle[1]+16:keep.append(t)
                        elif part=='foot' and c[1]>=ankle[1]-16:keep.append(t)
                    mesh(name,name,MASTER,pts,pts/[800,724],np.array(keep),rest_tf,lambda p,b='ref_'+part+'_'+side:{b:1})
        name='body_front' if front else 'body_back';slot(name,name)
        hx=[0,250,300,350,400,450,500,550,600,650,800];hy=[440,460,490,517,526,536,532,518,498,478,470]
        tris=[]
        for tri in master_tris:
            c=master_body[tri].mean(axis=0);above=c[1]<=np.interp(c[0],hx,hy)
            if above==front and (front or (c[0]<355 and c[1]<500)):tris.append(tri)
        mesh(name,name,MASTER,master_body,master_body/[800,724],np.array(tris),rest_tf,body_weights)
    source_keys={'default':('idle_loop',0),'palm0':('attack',.15),'palm1':('attack',.375),'palm2':('attack',.75),
                 'guard0':('guard',1.15*.26),'guard1':('guard',1.15*.46),'gather':('cast',1.25*.30)}
    for side in ['back','front']:
        for part in ['upper','fore','hand']:
            sn='arm_'+part+'_'+side;slot(sn,'arm_'+part+'_'+side+'_default')
            for view,source in sources.items():
                poly=source['polygons'][('hand_' if part=='hand' else 'arm_')+side]
                pts,tris=mesh_polygon(expanded_outline(poly,3 if part=='hand' else 8),4 if part=='hand' else 7,
                    [] if part=='hand' else [expanded_outline(source['polygons']['hand_'+side],3)])
                model=pts@source['matrix'][:,:2].T+source['matrix'][:,2]+source['shifts'][side]
                js=source['pose'];a,e,w=[js[k+'_'+side] for k in ['shoulder','elbow','wrist']]
                if part!='hand':
                    tangent=(e-a)/np.linalg.norm(e-a)+(w-e)/np.linalg.norm(w-e);tangent/=np.linalg.norm(tangent)
                    tris=np.array([t for t in tris if (np.dot(model[t].mean(axis=0)-e,tangent)<=15 if part=='upper' else np.dot(model[t].mean(axis=0)-e,tangent)>=-15)])
                name=sn+'_'+view;tf=transforms(js,HAND_AXES[view])
                mesh(sn,name,source['file'],model,pts/[800,724],tris,tf,lambda p,b='ref_'+part+'_'+side:{b:1},source_keys[view])
    slot('face',visible=True)
    face_pts=np.array([[475,108],[560,108],[475,178],[560,178]],float)
    for expression in ['blink','angry']:
        file='offer-'+expression+'-v0.8.5.png';fm=registration(ROOT/'assets/sprites'/MASTER,ROOT/'assets/sprites'/file)
        uv=((face_pts-fm[:,2])@np.linalg.inv(fm[:,:2]).T)/[800,724]
        mesh('face',expression,file,face_pts,uv,np.array([[0,1,2],[1,3,2]]),rest_tf,lambda p:{'ref_head':1})
    slot('prone','prone',False,'prone')
    file='offer-prone-v0.8.5.png';im=Image.open(ROOT/'assets/sprites'/file).convert('RGBA');w,h=im.size;box=im.getbbox();scale=500/(box[2]-box[0])
    # Prone uses a separate, ground-fixed root; geometry is in world units.
    pworld=np.array([[-w*scale/2,box[3]*scale],[w*scale/2,box[3]*scale],[-w*scale/2,(box[3]-h)*scale],[w*scale/2,(box[3]-h)*scale]])
    verts=[]
    for p in pworld:verts.extend([1,idx['prone'],float(p[0]),float(p[1]),1])
    regions['prone']=(file,(0,0,w,h));attachments['prone']['prone']={'type':'mesh','path':'prone','width':w,'height':h,'uvs':[0,0,1,0,0,1,1,1],'triangles':[0,1,2,1,3,2],'vertices':verts}
    info['meshes']['prone/prone']={'source_geometry':pworld.tolist(),'check_animation':'death','check_time':1.35}
    info['prone_height']=(box[3]-box[1])*scale
    for key,file in [('ref_water','reference-water-v0.8.2.png'),('guard_water','reference-shield-v0.8.3.png')]:
        regions[key]=(file,(0,0,*Image.open(ROOT/'assets/sprites'/file).size))
    # Motion authoring is below, shared by every route.
    author_motions(names,bones,slots,anims,info,sources,rest_tf)
    (ROOT/'assets/animation/common-state.json').write_text(json.dumps(info,separators=(',',':')),encoding='utf-8')
    return info

def rotate_arm(p,side,degrees):
    q=clone(p);a=q['shoulder_'+side];angle=math.radians(degrees);c,s=math.cos(angle),math.sin(angle)
    for k in ['elbow','wrist','hand']:
        v=q[k+'_'+side]-a;q[k+'_'+side]=a+np.array([c*v[0]+s*v[1],-s*v[0]+c*v[1]])
    return q

def key(t,p=None,view='default',hands=(0,0),head=0,root=(0,0,0),cloth=1,hair=(0,0,0,0,0)):
    return dict(t=t,p=clone(p or REST),view=view,hands=hands,head=head,root=root,cloth=cloth,hair=hair)

def author_motions(names,bones,slots,anims,info,sources,rest_tf):
    duration_map={}
    def write(name,duration,keys,view_schedule=None,face=None,loop=False,death=False,revive=False):
        timing=np.array([k['t'] for k in keys],float)
        joint_curves={j:[PchipInterpolator(timing,np.array([k['p'][j] for k in keys])[:,a]) for a in range(2)] for j in REST}
        polar={}
        for side in ['front','back']:
            for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                delta=np.array([k['p'][end+'_'+side]-k['p'][start+'_'+side] for k in keys])
                polar[start+'_'+side]=(PchipInterpolator(timing,np.unwrap(np.arctan2(-delta[:,1],delta[:,0]))),
                                         PchipInterpolator(timing,np.linalg.norm(delta,axis=1)))
        hand_curves=[PchipInterpolator(timing,[HAND_AXES[k['view']][side]+k['hands'][i] for k in keys]) for i,side in enumerate(['front','back'])]
        head_curve=PchipInterpolator(timing,[k['head'] for k in keys])
        hair_curves=[PchipInterpolator(timing,[k['hair'][i] for k in keys]) for i in range(len(HAIR_BONES))]
        cloth_curve=PchipInterpolator(timing,[k['cloth'] for k in keys])
        root_curves=[PchipInterpolator(timing,[k['root'][i] for k in keys]) for i in range(3)]
        times=np.unique(np.round(np.r_[np.linspace(0,duration,max(121,round(duration*120)+1)),timing],9))
        frames=[]
        for t in times:
            p={j:np.array([c[0](t),c[1](t)]) for j,c in joint_curves.items()}
            for side in ['front','back']:
                for start,end in [('shoulder','elbow'),('elbow','wrist')]:
                    ac,lc=polar[start+'_'+side];ang=float(ac(t));length=float(lc(t))
                    target=p[start+'_'+side]+np.array([math.cos(ang),-math.sin(ang)])*length
                    if end=='wrist':p['hand_'+side]+=target-p[end+'_'+side]
                    p[end+'_'+side]=target
            # One smooth follow-through, independent of dense sampling density.
            # Idle/celebration loops already contain their periodic motion.
            phase=t/duration
            follow=0 if loop else math.sin(math.pi*phase)**2*math.sin((phase-.30)*math.tau*1.5)
            p['hair_tip']+=[-3*follow,follow];p['tail_tip']+=[-2*follow,-2*follow]
            p['hair_lower_tip']+=[-4*follow,1.5*follow]
            tf=transforms(p,dict(front=float(hand_curves[0](t)),back=float(hand_curves[1](t))))
            sp,sm,sa,ssx,ssy=tf['ref_skirt'];ssy=float(cloth_curve(t));c,s=math.cos(sa),math.sin(sa)
            tf['ref_skirt']=(sp,np.array([[c*ssx,-s*ssy],[s*ssx,c*ssy]]),sa,ssx,ssy)
            angle=math.radians(float(head_curve(t)));pos=tf['ref_head'][0];c,s=math.cos(angle),math.sin(angle)
            tf['ref_head']=(pos,np.array([[c,-s],[s,c]]),angle,1.,1.)
            for hair_name,hair_curve in zip(HAIR_BONES,hair_curves):
                pos= tf['ref_'+hair_name][0];angle=math.radians(float(hair_curve(t)))
                c,s=math.cos(angle),math.sin(angle)
                tf['ref_'+hair_name]=(pos,np.array([[c,-s],[s,c]]),angle,1.,1.)
            frames.append(tf)
        clip={'bones':{},'slots':{}}
        local_frames=[local_transforms(f) for f in frames]
        local_rest=local_transforms(rest_tf)
        for bone in rest_tf:
            pos,angle,sx,sy=local_rest[bone]
            ps=np.array([f[bone][0] for f in local_frames]);angles=np.unwrap([f[bone][1] for f in local_frames])*180/math.pi-math.degrees(angle)
            vs={'translatex':ps[:,0]-pos[0],'translatey':ps[:,1]-pos[1],'rotate':angles,
                'scalex':np.array([f[bone][2]/sx for f in local_frames]),'scaley':np.array([f[bone][3]/sy for f in local_frames])}
            clip['bones'][bone]=curve_tracks(times,vs)
        clip['bones']['ref_root']=curve_tracks(times,{'translatex':np.array(root_curves[0](times)),
            'translatey':np.array(root_curves[1](times)),'rotate':np.array(root_curves[2](times))})
        clip['bones']['prone']={'scalex':[{'time':0,'value':1}], 'scaley':[{'time':0,'value':1}]}
        schedule=view_schedule or [(0,k['view']) for k in keys]
        if view_schedule is None:
            schedule=[(k['t'],k['view']) for k in keys]
        def visible(changes):return [{'time':float(t),'color':'ffffffff' if on else 'ffffff00','curve':'stepped'} for t,on in changes]
        for slot in slots:
            sn=slot['name'];body_changes=[(0,True)]
            if death:body_changes+=[(duration*.80,False)]
            if revive:body_changes=[(0,False),(duration*.20,True)]
            if sn=='prone':body_changes=[(0,False),(duration*.80,True)] if death else [(0,True),(duration*.20,False)] if revive else [(0,False)]
            clip['slots'][sn]={'rgba':visible(body_changes)}
            if sn.startswith('arm_'):
                clip['slots'][sn]['attachment']=[{'time':float(t),'name':sn+'_'+v} for t,v in schedule]
            elif sn=='face':
                if face is None:face=[(0,None)]
                clip['slots'][sn]['attachment']=[{'time':float(t),'name':v} for t,v in face]
            else:clip['slots'][sn]['attachment']=[{'time':0,'name':sn}]
        anims[name]=clip;duration_map[name]=duration
        info['clips'][name]={'duration':duration,'loop':loop,'start':'prone' if revive else 'rest','end':'prone' if death else 'rest'}
    # All idle variants retain the exact palm-up pose at the loop boundary.
    for name in names:
        if not name.startswith('idle_'):continue
        duration=3.0 if name=='idle_angry_loop' else 6.0
        ks=[]
        for t in np.linspace(0,duration,73):
            phase=t/duration*math.tau;p=clone();breath=(1.8 if name=='idle_breathe_loop' else 1.0)*math.sin(phase)
            for j in p:
                if not j.startswith(('knee','ankle','toe')):p[j][1]-=breath
            # Phase-offset waves all meet the common rest at each loop boundary.
            # Soft upper/lower strand masks produce a traveling bend, not one
            # rigid translation of the entire hair silhouette.
            def wave(lag=0,harmonic=1):return math.sin(phase*harmonic-lag)+math.sin(lag)
            strength=.55 if name=='idle_angry_loop' else 1.2 if name=='idle_hair_loop' else 1.
            p['hair']+=strength*np.array([1.3*wave(),.7*wave(.20)])
            p['hair_tip']+=strength*np.array([7.0*wave(.42)+1.2*wave(0,2),3.5*wave(.78)])
            p['hair_lower']+=strength*np.array([1.8*wave(.35),1.4*wave(.65)])
            p['hair_lower_tip']+=strength*np.array([8.0*wave(.88)+wave(0,2),5.8*wave(1.15)])
            p['hair_crown']+=strength*np.array([1.2*wave(.2,2),.5*wave(.45,2)])
            p['tail_tip']+=[2.8*wave(.55),2.2*wave(.90)]
            hair_angles=tuple(strength*v for v in [.30*wave(),.65*wave(.55),-.35*wave(.30),-.85*wave(.95),1.6*wave(.4,2)])
            if name=='idle_look_loop':p['head'][0]+=1.8*math.sin(phase)
            if name=='idle_hand_loop':
                for j in ['wrist_front','hand_front']:p[j]+=[1.2*math.sin(phase),1.4*math.sin(phase)]
            if name=='idle_tail_loop':p['tail_tip'][1]+=3*math.sin(phase)
            ks.append(key(t,p,head=.18*math.sin(phase),hair=hair_angles))
        face=[(0,'angry')] if name=='idle_angry_loop' else [(0,None),(duration*.34,'blink'),(duration*.34+.09,None),(duration*.78,'blink'),(duration*.78+.09,None)]
        write(name,duration,ks,[(0,'default')],face,loop=True)
    # The approved palm-strike sequence now begins and ends in the palm-up rest.
    a,b,c=[sources['palm'+str(i)]['pose'] for i in range(3)]
    write('attack',1.10,[key(0),key(.15,a,'palm0'),key(.375,b,'palm1'),key(.50,b,'palm1'),key(.75,c,'palm2'),key(.98),key(1.10)],
          [(0,'default'),(.09,'palm0'),(.27,'palm1'),(.61,'palm2'),(.93,'default')])
    attacks={'attack_jab':(.92,0),'attack_cross':(1.08,-8),'attack_sweep':(1.15,-20),'attack_uppercut':(1.12,48),
             'attack_double':(1.30,0),'attack_triple':(1.55,0),'attack_ranged':(1.15,3),'attack_palm':(1.15,0),'attack_overhead':(1.20,65)}
    for name,(d,angle) in attacks.items():
        peak=rotate_arm(b,'front',angle);wind=clone(a);hands=(angle,0)
        if name=='attack_cross':
            peak['wrist_back']+=[80,-35];peak['hand_back']+=[80,-35]
        if name in ['attack_double','attack_triple']:
            count=2 if name=='attack_double' else 3;ks=[key(0)];vs=[(0,'default')]
            for i in range(count):
                t=(.12+i*.68/count)*d;end=(.12+(i+.62)*.68/count)*d
                ks+=[key(t,wind,'palm0'),key(end,peak,'palm1',hands=hands)]
                vs+=[(t*.95,'palm0'),(t+(end-t)*.5,'palm1')]
            ks+=[key(d*.94),key(d)];vs+=[(d*.9,'default')]
        else:
            ks=[key(0),key(d*.22,wind,'palm0'),key(d*.48,peak,'palm1',hands=hands),key(d*.62,peak,'palm1',hands=hands),key(d*.94),key(d)]
            vs=[(0,'default'),(d*.12,'palm0'),(d*.35,'palm1'),(d*.88,'default')]
        write(name,d,ks,vs)
    from reference_guard import PROFILES as guards
    for name,(d,strength) in guards.items():
        ready=sources['guard0']['pose'];block=clone(sources['guard1']['pose']);brace=clone(block)
        for j in brace:
            if not j.startswith(('ankle','toe')):brace[j][0]-=2*strength
        write(name,d,[key(0),key(d*.26,ready,'guard0'),key(d*.46,block,'guard1'),key(d*.60,brace,'guard1'),key(d*.80,ready,'guard0'),key(d)],
              [(0,'default'),(d*.12,'guard0'),(d*.355,'guard1'),(d*.72,'guard0'),(d*.94,'default')])
    from reference_spell import PROFILES as spells
    for name,(d,gesture) in spells.items():
        gather=clone(sources['gather']['pose']);release=body_pose(1,3)
        for j in ['wrist_front','hand_front']:release[j]+=[18,-10]
        if gesture=='arc':release=rotate_arm(release,'front',25)
        elif gesture=='dual':
            for j in ['wrist_back','hand_back']:release[j]+=[35,8]
        elif gesture=='guide':
            for j in ['elbow_front','wrist_front','hand_front']:release[j]+=[12,0]
        elif gesture=='overdrive':
            for j in ['wrist_front','hand_front']:release[j]+=[15,-12]
        if gesture in ['gather','pulse','circle']:
            ks=[key(0),key(d*.30,gather,'gather')]
            for t in np.linspace(.40,.82,8):
                p=clone(gather);wave=math.sin((t-.30)*math.tau*(4 if gesture=='pulse' else 2))
                for j in ['wrist_front','hand_front']:p[j]+=[4*wave,3*wave]
                for j in ['wrist_back','hand_back']:p[j]+=[-2*wave,-2*wave]
                ks.append(key(d*t,p,'gather'))
            ks+=[key(d*.98),key(d)];vs=[(0,'default'),(d*.12,'gather'),(d*.94,'default')]
        else:
            ks=[key(0),key(d*.30,gather,'gather'),key(d*.54,release),key(d*.66,release),key(d*.96),key(d)]
            vs=[(0,'default'),(d*.12,'gather'),(d*.43,'default')]
        write(name,d,ks,vs)
    # A short, assertive reaction returns to the same pose, then looks annoyed.
    hurts={'hurt':(.58,6),'hurt_recover':(.65,5),'hurt_recoil':(.55,7),'hurt_stagger':(.70,6),'hurt_counter':(.60,4)}
    for name,(d,recoil) in hurts.items():
        p=body_pose(1,-recoil);p['head'][0]-=2
        for j in ['wrist_front','hand_front']:p[j]+=[-10,-3]
        write(name,d,[key(0),key(.085,p,head=2),key(.21,body_pose(0,-1)),key(d*.76),key(d)],
              [(0,'default')],[(0,None),(.025,'blink'),(.10,None),(.15,'angry')])
    for name in ['greeting','greeting_wave','greeting_bow']:
        d=1.20;p=body_pose(0,0);h=(0,0);head=0
        if name=='greeting_wave':p=rotate_arm(p,'front',25);h=(45,0)
        elif name=='greeting_bow':
            p['head']+=[3,9];p['neck']+=[2,3];head=-4
        else:p['head'][1]+=3
        write(name,d,[key(0),key(d*.30,p,hands=h,head=head),key(d*.55,p,hands=h,head=head),key(d*.94),key(d)])
    for name in ['victory_loop','victory_wave_loop','victory_pose_loop','meditate_loop','rest_sleep_loop']:
        d=4.0 if name.startswith('victory') else 6.0;ks=[]
        for t in np.linspace(0,d,73):
            phase=t/d;env=math.sin(math.pi*phase)**2;p=body_pose(-3*env if name.startswith('victory') else 2*env,0)
            angle=(30 if name=='victory_pose_loop' else 45)*env if name.startswith('victory') else -12*env
            p=rotate_arm(p,'front',angle)
            if name.startswith('victory'):
                p['tail_tip'][1]+=6*math.sin(phase*math.tau)*env
            else:
                p['head'][1]+=6*env
            hand_angle=(40+8*math.sin(phase*math.tau*3))*env if name=='victory_wave_loop' else 20*env if name.startswith('victory') else -10*env
            ks.append(key(t,p,hands=(hand_angle,0),head=-3*env if not name.startswith('victory') else 0))
        face=[(0,None),(.12*d,'blink'),(.92*d,None)] if not name.startswith('victory') else [(0,None)]
        write(name,d,ks,[(0,'default')],face,loop=True)
    # Same figure tips forward, braces, then rests flat on a dedicated floor view.
    falling=body_pose(10,0)
    falling['elbow_front']=[530,280];falling['wrist_front']=[530,190];falling['hand_front']=[550,150]
    falling['elbow_back']=[440,285];falling['wrist_back']=[475,215];falling['hand_back']=[495,175]
    for side,x in [('front',455),('back',485)]:
        falling['hip_'+side]=np.array([x,480]);falling['knee_'+side]=np.array([x-4,590])
        falling['ankle_'+side]=np.array([x,710]);falling['toe_'+side]=np.array([x+5,766])
    fallen_root=(-155,45,-83)
    write('death',1.35,[key(0),key(.25,body_pose(5,0),head=-2),key(.64,falling,hands=(65,45),head=-4,root=(-45,12,-35),cloth=.75),
          key(1.04,falling,hands=(65,45),head=-4,root=fallen_root,cloth=.45),key(1.35,falling,hands=(65,45),head=-4,root=fallen_root,cloth=.45)],
          [(0,'default')],[(0,None),(.10,'blink')],death=True)
    write('revive',1.20,[key(0,falling,hands=(65,45),head=-4,root=fallen_root,cloth=.45),key(.24,falling,hands=(65,45),head=-4,root=fallen_root,cloth=.45),
          key(.65,body_pose(10,-2),hands=(10,0),root=(-30,12,-25),cloth=.8),key(1.08),key(1.20)],
          [(0,'default')],[(0,'blink'),(.90,None)],revive=True)
    assert set(anims)==set(names) and len(anims)==50,('Missing routed actions',set(names)-set(anims))
    info['default_animation']='idle_loop';info['action_count']=len(anims)
    info['idle_detail']={'hair_controls':['ref_'+n for n in HAIR_BONES],
        'soft_regions':['upper long hair','lower curls','crown curl'],
        'period_seconds':6,'phase_delayed_strands':True,'original_master_unchanged':True}
