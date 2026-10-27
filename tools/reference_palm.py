"""Native multi-view skinning for the approved three-stage palm strike.

The three painted views share anatomical joints. Each view stores its own
inverse joint transforms, so a source pose reconstructs at its own key time.
Joint paths are continuous; only the painted viewing angle is mixed briefly.
No optical-flow pixels, low-rate sprite playback, or full-frame morph is used.
"""
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.spatial import Delaunay
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1]
S=443/710
DURATION=1.10
KEY_TIMES=[.15,.375,.75]
OFFSETS=[0,9,0]

JOINTS=[
 dict(head=(494,150),neck=(454,211),pelvis=(446,310),hem=(460,492),hair=(320,230),hair_tip=(180,245),tail=(280,478),tail_tip=(130,382),
      shoulder_front=(536,242),elbow_front=(582,299),wrist_front=(551,323),hand_front=(516,302),
      shoulder_back=(374,250),elbow_back=(330,284),wrist_back=(343,310),hand_back=(365,299),
      hip_front=(405,455),knee_front=(309,575),ankle_front=(246,644),toe_front=(255,700),
      hip_back=(510,455),knee_back=(605,577),ankle_back=(671,646),toe_back=(709,700)),
 dict(head=(485,150),neck=(460,204),pelvis=(467,306),hem=(463,473),hair=(315,211),hair_tip=(155,225),tail=(275,451),tail_tip=(118,365),
      shoulder_front=(475,223),elbow_front=(559,231),wrist_front=(648,237),hand_front=(690,225),
      shoulder_back=(410,246),elbow_back=(354,267),wrist_back=(308,281),hand_back=(292,286),
      hip_front=(374,430),knee_front=(238,541),ankle_front=(134,615),toe_front=(142,691),
      hip_back=(512,437),knee_back=(578,491),ankle_back=(595,627),toe_back=(628,694)),
 dict(head=(497,131),neck=(500,189),pelvis=(524,288),hem=(518,479),hair=(347,223),hair_tip=(205,244),tail=(348,482),tail_tip=(233,389),
      shoulder_front=(451,213),elbow_front=(474,281),wrist_front=(551,254),hand_front=(577,223),
      shoulder_back=(526,218),elbow_back=(555,294),wrist_back=(590,291),hand_back=(605,274),
      hip_front=(458,432),knee_front=(376,553),ankle_front=(327,634),toe_front=(342,702),
      hip_back=(531,433),knee_back=(554,547),ankle_back=(573,638),toe_back=(610,700)),
]

# Tight UV silhouettes over the master cutouts. Armless body layers supply the
# unobscured blouse and petticoat behind these continuously skinned limbs.
POLYGONS={
 'arm_front':[
  [(494,205),(536,211),(558,236),(573,258),(598,270),(610,294),(605,319),(583,344),(558,350),(537,337),(509,335),(479,315),(481,299),(500,302),(494,282),(495,268),(502,265),(508,288),(507,260),(515,259),(522,289),(524,263),(531,266),(534,294),(543,282),(551,285),(545,308),(555,322),(568,310),(567,293),(550,278),(531,273),(510,252)],
  [(426,199),(464,196),(494,204),(509,217),(561,215),(595,202),(615,204),(634,216),(648,214),(663,206),(678,180),(688,173),(692,179),(683,201),(699,175),(706,175),(708,182),(699,205),(713,187),(719,190),(713,211),(704,226),(716,220),(727,222),(725,229),(705,242),(681,248),(659,247),(651,253),(631,258),(616,272),(596,273),(569,261),(524,258),(503,257),(487,264),(465,260),(444,245)],
  [(431,178),(454,178),(478,193),(489,217),(490,246),(505,258),(532,250),(548,241),(553,223),(560,213),(567,202),(574,198),(580,201),(570,216),(589,201),(597,204),(582,219),(598,215),(605,217),(600,223),(579,229),(566,242),(565,257),(557,274),(540,284),(523,300),(489,303),(469,299),(451,282),(439,258),(428,230)],
 ],
 'arm_back':[
  [(386,224),(398,238),(391,261),(379,285),(389,289),(394,297),(378,313),(367,326),(347,328),(330,318),(319,306),(316,290),(322,272),(342,250),(361,236)],
  [(408,225),(420,247),(405,264),(382,284),(357,294),(334,296),(319,300),(301,304),(290,296),(282,293),(278,283),(281,275),(293,269),(308,270),(313,252),(333,246),(357,246),(383,233)],
  [(527,219),(547,233),(560,256),(568,270),(581,262),(588,256),(599,251),(611,251),(619,259),(621,272),(616,285),(608,298),(593,310),(572,316),(554,309),(537,294),(526,269)],
 ],
 'leg_front':[
  [(358,492),(406,502),(400,526),(371,557),(339,583),(304,613),(277,640),(273,654),(265,666),(265,684),(274,699),(273,716),(246,721),(223,714),(216,701),(218,677),(229,648),(236,630),(259,598),(284,565),(315,540),(345,511)],
  [(309,450),(359,472),(344,496),(309,522),(271,548),(224,575),(185,602),(155,624),(155,644),(161,669),(168,692),(159,706),(135,710),(111,703),(99,689),(97,671),(107,638),(117,613),(141,589),(185,559),(228,521),(273,486)],
  [(408,472),(449,487),(439,511),(409,543),(382,582),(352,624),(350,647),(360,666),(369,692),(363,714),(339,720),(313,714),(292,701),(287,682),(292,659),(302,638),(317,607),(342,569),(369,530),(389,498)],
 ],
 'leg_back':[
  [(515,498),(554,493),(582,518),(611,548),(642,587),(675,622),(686,645),(697,665),(724,686),(741,695),(744,711),(725,721),(698,719),(677,712),(654,705),(650,683),(649,659),(641,641),(610,615),(578,588),(550,557),(530,532)],
  [(543,453),(574,452),(592,464),(601,485),(599,517),(603,556),(608,596),(611,620),(617,642),(637,664),(660,681),(669,693),(666,705),(638,711),(610,702),(584,697),(568,682),(565,659),(574,631),(570,602),(564,565),(557,531),(552,497)],
  [(515,474),(550,477),(555,505),(557,537),(564,571),(574,607),(582,633),(588,653),(608,677),(634,689),(641,704),(634,717),(609,721),(588,714),(564,706),(553,693),(550,668),(556,642),(548,617),(537,578),(531,543),(526,509)],
 ],
}


def world(p,pose=0):
    x,y=p
    return np.array([(x-470)*S,(718-y-OFFSETS[pose])*S],float)


def joint_world(pose):return {k:world(v,pose) for k,v in JOINTS[pose].items()}


SEGMENTS={'torso':('pelvis','neck'),'skirt':('pelvis','hem'),'head':('head',None),
          'hair':('hair',None),'hair_tip':('hair_tip',None),'tail':('tail','tail_tip')}
for side in ['front','back']:
    SEGMENTS.update({f'upper_{side}':(f'shoulder_{side}',f'elbow_{side}'),f'fore_{side}':(f'elbow_{side}',f'wrist_{side}'),
                     f'hand_{side}':(f'wrist_{side}',f'hand_{side}'),f'thigh_{side}':(f'hip_{side}',f'knee_{side}'),
                     f'shin_{side}':(f'knee_{side}',f'ankle_{side}'),f'foot_{side}':(f'ankle_{side}',None)})
    # Finger direction stays upright during the push. Wrist-to-palm direction
    # reverses in perspective and must not be used as the hand's rotation axis.
    SEGMENTS[f'hand_{side}']=(f'hand_{side}',None)

HAND_POLYGONS={
 'front':[
  [(480,298),(491,288),(500,293),(493,278),(495,266),(502,262),(508,287),(507,260),(514,257),(522,287),(524,263),(532,265),(535,294),(542,282),(551,284),(551,295),(543,311),(545,326),(531,335),(511,331),(493,319)],
  [(647,214),(662,204),(678,177),(690,170),(694,178),(686,202),(701,172),(709,173),(713,184),(703,207),(716,184),(724,190),(717,212),(708,225),(719,217),(730,222),(726,231),(705,246),(679,252),(652,248)],
  [(550,241),(552,221),(560,212),(568,200),(578,194),(584,199),(575,213),(590,199),(600,202),(587,218),(602,211),(608,216),(604,225),(580,233),(565,251)],
 ],
 'back':[
  [(339,286),(351,279),(367,279),(382,289),(396,292),(393,302),(379,309),(371,320),(353,321),(341,313)],
  [(276,274),(292,268),(307,274),(313,286),(304,301),(292,305),(278,293)],
  [(585,256),(596,249),(609,249),(620,258),(624,270),(616,286),(605,298),(590,300),(581,288)],
 ]}


def transforms(joints,base_lengths):
    out={}
    for name,(start,end) in SEGMENTS.items():
        p=joints[start]
        if end:
            v=joints[end]-p;length=np.linalg.norm(v)
            angle=math.atan2(v[1],v[0]);sx=length/base_lengths[name]
        else:angle=0;sx=1
        sy=1
        if name=='hand_front':
            delta=joints['wrist_front']-p
            sx=max(.16,abs(delta[0])/(35*S))
            sy=max(.45,abs(delta[1])/(21*S))
        c,s=math.cos(angle),math.sin(angle)
        out['ref_'+name]=(p,np.array([[c*sx,-s*sy],[s*sx,c*sy]]),angle,sx,sy)
    return out


def weights(part,p,pose):
    x,y=p;js=JOINTS[pose]
    def ramp(a,b,v):
        u=np.clip((v-a)/(b-a),0,1);return float(u*u*(3-2*u))
    def mix(a,b,u):return {k:a.get(k,0)*(1-u)+b.get(k,0)*u for k in a.keys()|b.keys()}
    if part.startswith('body'):
        w=mix({'ref_torso':1},{'ref_head':1},1-ramp(175,245,y))
        w=mix(w,{'ref_skirt':1},ramp(290,390,y))
        hair=(1-ramp(js['neck'][0]-95,js['neck'][0]-15,x))*(1-ramp(310,382,y))
        hw=mix({'ref_hair':1},{'ref_hair_tip':1},1-ramp(180,330,x))
        w=mix(w,hw,hair)
        tail=(1-ramp(270,350,x))*ramp(300,365,y)
        return mix(w,{'ref_tail':1},tail)
    side=part.split('_')[1]
    if part.startswith('hand'):return {'ref_hand_'+side:1}
    if part.startswith('fill'):return {'ref_upper_'+side:1}
    if part.startswith('arm'):
        a,e,wrist=[np.array(js[k+'_'+side],float) for k in ['shoulder','elbow','wrist']]
        tan=(e-a)/np.linalg.norm(e-a)+(wrist-e)/np.linalg.norm(wrist-e);tan/=np.linalg.norm(tan)
        radius=80 if side=='front' else 60
        u=ramp(-radius,radius,np.dot(np.array(p)-e,tan))
        ws=mix({'ref_upper_'+side:1},{'ref_fore_'+side:1},u)
        return ws
    a,knee,ankle=[np.array(js[k+'_'+side],float) for k in ['hip','knee','ankle']]
    d=(knee-a)/np.linalg.norm(knee-a)+(ankle-knee)/np.linalg.norm(ankle-knee);d/=np.linalg.norm(d)
    u=ramp(-24,24,np.dot(np.array(p)-knee,d))
    ws=mix({'ref_thigh_'+side:1},{'ref_shin_'+side:1},u)
    return mix(ws,{'ref_foot_'+side:1},ramp(ankle[1]-18,ankle[1]+5,y))


def mesh_polygon(poly,step=16,holes=None):
    contour=np.array(poly,np.float32)
    holes=[np.array(h,np.float32) for h in holes or []]
    def inside(p):
        point=tuple(map(float,p))
        return cv2.pointPolygonTest(contour,point,False)>=-.01 and all(cv2.pointPolygonTest(h,point,False)<=0 for h in holes)
    points=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        a,b=np.array(a),np.array(b);n=max(1,math.ceil(np.linalg.norm(b-a)/step))
        points.extend(a+(b-a)*j/n for j in range(n))
    for hole in holes:
        for a,b in zip(hole,np.roll(hole,-1,axis=0)):
            n=max(1,math.ceil(np.linalg.norm(b-a)/step))
            points.extend(a+(b-a)*j/n for j in range(n))
    lo,hi=contour.min(axis=0),contour.max(axis=0)
    points.extend([x,y] for y in np.arange(lo[1]+step/2,hi[1],step) for x in np.arange(lo[0]+step/2,hi[0],step) if inside((x,y)))
    points=np.unique(np.round(points,5),axis=0);tri=[]
    for t in Delaunay(points).simplices:
        a,b,c=points[t]
        if not all(inside(p) for p in [(a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2]):continue
        if abs(float(np.cross(b-a,c-a)))<.02:continue
        if np.cross(b-a,c-a)<0:t=t[::-1]
        tri.append(t)
    return points,np.array(tri)


def expanded_outline(poly,radius):
    # Offset a UV clipping outline, not the artwork. This gives skin and cuffs
    # overlap under adjoining painted surfaces instead of cutting their edges.
    margin=32
    mask=np.zeros((724+margin*2,800+margin*2),np.uint8)
    cv2.fillPoly(mask,[np.round(np.array(poly)+margin).astype(np.int32)],255)
    mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1)))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour=max(contours,key=cv2.contourArea)
    return (cv2.approxPolyDP(contour,1.0,True)[:,0,:]-margin).tolist()


def registration(master,body):
    # Only estimate a uniform scale/rotation/translation. Never stretch body parts.
    def pixels(path):return np.array(Image.open(path).convert('RGBA').resize((800,724)))
    a,b=pixels(master),pixels(body)
    sift=cv2.SIFT_create(nfeatures=2500)
    ka,da=sift.detectAndCompute(cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY),a[:,:,3])
    kb,db=sift.detectAndCompute(cv2.cvtColor(b[:,:,:3],cv2.COLOR_RGB2GRAY),b[:,:,3])
    matches=cv2.BFMatcher().knnMatch(db,da,k=2)
    good=[m for m,n in matches if m.distance<.68*n.distance]
    if len(good)<8:raise ValueError('Body registration has too few unchanged painted details')
    src=np.float32([kb[m.queryIdx].pt for m in good]);dst=np.float32([ka[m.trainIdx].pt for m in good])
    matrix,inliers=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=2,maxIters=5000)
    assert matrix is not None and inliers.sum()>12,'Body layer changed too much to register'
    # The editor can enlarge the remaining torso after removing limbs. Restore
    # that one uniform canvas scale using unchanged embroidery/face features.
    assert .55<np.linalg.norm(matrix[:,0])<1.4,'Body extraction cannot be aligned by a uniform transform'
    return matrix


def body_surface(pose,front):
    hx=[0,250,300,350,400,450,500,550,600,650,800]
    hy=[
        [490,490,505,517,525,529,527,511,495,478,470],
        [420,428,451,479,500,509,498,478,457,444,420],
        [470,478,483,493,498,508,508,499,487,475,455],
    ][pose]
    nx,ny=48,30 if front else 12
    vertices=[];tri=[]
    for j in range(ny+1):
        for i in range(nx+1):
            x=800*i/nx;hem=np.interp(x,hx,hy)
            y=hem*j/ny if front else hem+(724-hem)*j/ny
            vertices.append([x,y])
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1
            tri.extend([[a,b,c],[b,d,c]])
    return np.array(vertices),np.array(tri)


def extend(bones,slots,attachments,anims,regions):
    bind_j=joint_world(0)
    lengths={n:np.linalg.norm(bind_j[e]-bind_j[s]) if e else 1 for n,(s,e) in SEGMENTS.items()}
    source_tf=[transforms(joint_world(i),lengths) for i in range(3)]
    bones.append({'name':'ref_root'})
    for name,(pos,mat,angle,sx,sy) in source_tf[0].items():
        bones.append({'name':name,'parent':'ref_root','x':float(pos[0]),'y':float(pos[1])})
    indices={b['name']:i for i,b in enumerate(bones)}
    oldslots=[s['name'] for s in slots]
    info={'source_canvas':[800,724],'uniform_scale':S,'origin':[470,718],'floor_offsets':OFFSETS,'key_times':KEY_TIMES,'duration':DURATION,'meshes':{},'registration':{}}
    # Render rear arm and legs behind the restored body; foreground arm above it.
    for part in ['body_back','leg_back','leg_front','body_front','arm_back','hand_back','fill_front','arm_front','hand_front']:
        for pose in range(3):
            if part=='fill_front' and pose!=0:continue
            master=f'reference-palm-{pose}-v0.8.2.png'
            file=f'reference-body-{pose}-v0.8.2.png' if part.startswith('body') else master
            path=ROOT/'assets/sprites'/file
            im=np.array(Image.open(path).convert('RGBA'));height,width=im.shape[:2]
            matrix=registration(ROOT/'assets/sprites'/master,path) if part.startswith('body') else np.array([[1,0,0],[0,1,0]],float)
            if part.startswith('body'):info['registration'][str(pose)]=matrix.tolist()
            region=f'ref_{part}_{pose}'
            regions[region]=(file,(0,0,width,height))
            if part.startswith('body'):poly=[(0,0),(800,0),(800,724),(0,724)]
            elif part.startswith('hand'):poly=expanded_outline(HAND_POLYGONS[part.split('_')[1]][pose],3)
            elif part=='fill_front':poly=[(507,264),(535,267),(545,287),(544,313),(519,320),(500,308)]
            else:
                outline=POLYGONS[part][pose]
                if part=='arm_front' and pose==1:outline=outline[:-1]+[(424,286),(412,266),(407,238),(410,216)]
                poly=expanded_outline(outline,14 if part.startswith('leg') else 12)
            holes=[expanded_outline(HAND_POLYGONS[part.split('_')[1]][pose],3)] if part.startswith('arm') else []
            points,tris=mesh_polygon(poly,3 if part.startswith('hand') else 7,holes) if not part.startswith('body') else (None,None)
            # Body geometry is authored in its own image coordinates then uniformly
            # registered to the corresponding unchanged master cutout.
            if part.startswith('body'):
                model,tris=body_surface(pose,part=='body_front')
                points=(model-matrix[:,2])@np.linalg.inv(matrix[:,:2]).T
            else:model=points@matrix[:,:2].T+matrix[:,2]
            uv=points/np.array([800,724])
            if part.startswith('fill'):
                # A small original navy-sleeve patch reconstructs the part
                # hidden behind the original palm. It remains behind the hand.
                lo,hi=points.min(axis=0),points.max(axis=0)
                uv=(np.array([560,275])+(points-lo)/(hi-lo)*[22,20])/[800,724]
            keep=[]
            for t in tris:
                px=uv[t]*[width,height]
                lo=np.maximum(0,np.floor(px.min(axis=0)).astype(int));hi=np.minimum([width-1,height-1],np.ceil(px.max(axis=0)).astype(int))
                if (hi<lo).any():continue
                mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
                cv2.fillConvexPoly(mask,np.round(px-lo).astype(np.int32),1)
                if np.any(im[lo[1]:hi[1]+1,lo[0]:hi[0]+1,3][mask.astype(bool)]>8):keep.append(t)
            vertices=[]
            for p in model:
                wp=world(p,pose);ws=weights(part,p,pose)
                ws={k:v for k,v in ws.items() if v>1e-6}
                if len(ws)>4:
                    ws=dict(sorted(ws.items(),key=lambda kv:-kv[1])[:4])
                total=sum(ws.values());vertices.append(len(ws))
                for name,weight in ws.items():
                    pos,mat,*_=source_tf[pose][name]
                    local=np.linalg.solve(mat,wp-pos)
                    vertices.extend([indices[name],round(float(local[0]),6),round(float(local[1]),6),round(weight/total,8)])
            mesh={'type':'mesh','path':region,'width':width,'height':height,'uvs':uv.ravel().tolist(),'triangles':np.array(keep).ravel().astype(int).tolist(),'vertices':vertices}
            slots.append({'name':region,'bone':'ref_root','attachment':region,'color':'ffffff00'})
            attachments[region]={region:mesh}
            info['meshes'][region]={'pose':pose,'key_time':KEY_TIMES[pose],'source_geometry':[[round(float(v),6) for v in world(p,pose)] for p in model]}
    # Anatomical paths. Both the joint origin and the segment endpoint are
    # sampled together, keeping wrists/elbows/ankles connected between keys.
    neutral={k:np.array(v,float) for k,v in JOINTS[0].items()}
    for k in neutral:
        if k.startswith(('hip','knee','ankle','toe')):
            neutral[k][0]=470+(neutral[k][0]-470)*.52
        elif k not in ['tail','tail_tip']:neutral[k][1]-=15
    timing=np.array([0,.15,.375,.48,.75,.95,DURATION])
    pathposes=[neutral,JOINTS[0],JOINTS[1],JOINTS[1],JOINTS[2],neutral,neutral]
    path_offsets=[0,0,9,9,0,0,0]
    joint_curves={}
    for k in JOINTS[0]:
        coords=np.array([[*p[k]] for p in pathposes],float)
        coords[:,1]+=path_offsets
        joint_curves[k]=[PchipInterpolator(timing,coords[:,axis]) for axis in range(2)]
    times=np.unique(np.round(np.concatenate([np.linspace(0,DURATION,133),timing]),9))
    tf=[]
    for t in times:
        js={k:world((curves[0](t),curves[1](t)),0) for k,curves in joint_curves.items()}
        # Coming around the body is an arc, not a straight line through the
        # elbow. Keep forearm length and sleeve volume through both turns.
        for side,start,end,height in [('back',.48,.75,52),('front',.75,.95,48)]:
            if start<t<end:
                lift=height*S*math.sin(math.pi*(t-start)/(end-start))**2
                js['wrist_'+side][1]-=lift
                js['hand_'+side][1]-=lift
        # Secondary motion starts after extension, then decays before settling.
        age=max(0,t-.375)
        lag=math.sin(age*math.pi*8)*math.exp(-age*7) if t>.375 else 0
        js['hair_tip']+=np.array([-8,3])*lag
        js['tail_tip']+=np.array([-5,-4])*lag
        tf.append(transforms(js,lengths))
    clip=anims['attack']
    for name in source_tf[0]:
        origin=source_tf[0][name][0]
        pos=np.array([f[name][0] for f in tf]);angle=np.unwrap([f[name][2] for f in tf])*180/math.pi
        sx=np.array([f[name][3] for f in tf])
        sy=np.array([f[name][4] for f in tf])
        values={'translatex':pos[:,0]-origin[0],'translatey':pos[:,1]-origin[1],'rotate':angle,'scalex':sx,'scaley':sy}
        clip['bones'][name]={}
        for kind,ys in values.items():
            derivative=np.gradient(ys,times)
            keys=[]
            for j,(t,v) in enumerate(zip(times,ys)):
                key={'time':round(float(t),7),'value':round(float(v),7)}
                if j+1<len(times):
                    dt=times[j+1]-t
                    key['curve']=[float(t+dt/3),float(v+derivative[j]*dt/3),float(times[j+1]-dt/3),float(ys[j+1]-derivative[j+1]*dt/3)]
                keys.append(key)
            clip['bones'][name][kind]=keys
    def alpha(keys):return [{'time':t,'color':'ffffff'+f'{round(a*255):02x}'} for t,a in keys]
    for name,animation in anims.items():
        for slot in info['meshes']:
            animation['slots'][slot]={'rgba':alpha([(0,0)])}
    # View mixing happens only after the geometry is registered at the joints.
    # A viewing-angle substitution is stepped, not an opacity crossfade. The
    # geometry continues moving at render delta; two translucent silhouettes
    # must never be visible at once.
    turn_time=round(brentq(lambda t:joint_curves['wrist_front'][0](t)-joint_curves['hand_front'][0](t),.15,.375),7)
    hand_return_time=round(brentq(lambda t:joint_curves['wrist_front'][0](t)-joint_curves['hand_front'][0](t),.75,.95),7)
    info['view_turn_time']=turn_time
    envelopes=[[(0,1),(turn_time,0),(.89,1)],[(0,0),(turn_time,1),(.585,0)],[(0,0),(.585,1),(.89,0)]]
    for slot,meta in info['meshes'].items():
        envelope=envelopes[meta['pose']]
        if slot.startswith('ref_hand_front_'):
            envelope=[(hand_return_time if t==.89 else t,a) for t,a in envelope]
        elif slot.startswith(('ref_arm_front_','ref_fill_front_')):
            envelope=[(.85 if t==.89 else t,a) for t,a in envelope]
        keys=alpha(envelope)
        for key in keys:key['curve']='stepped'
        clip['slots'][slot]['rgba']=keys
    for slot in oldslots:
        if slot=='prone':continue
        clip['slots'][slot]['rgba']=alpha([(0,0)])
    # Use the same ready figure for idle and attack, avoiding a full-character
    # image swap at the beginning and end of every Strike. Preserve angry idle's
    # dedicated expression and all unrelated action clips.
    for name,animation in anims.items():
        if not name.startswith('idle_') or name=='idle_angry_loop':continue
        duration=max(keys[-1]['time'] for tracks in animation['bones'].values() for keys in tracks.values())
        lt=np.linspace(0,duration,61)
        idle_tf=[]
        for t in lt:
            phase=t/duration*math.tau
            js={k:world(v) for k,v in neutral.items()}
            amplitude=2.1 if name=='idle_breathe_loop' else .8 if name=='idle_ready_loop' else 1.2
            breath=amplitude*math.sin(phase)
            for k in js:
                if not k.startswith(('knee','ankle','toe')):js[k][1]+=breath
            js['hair'][0]+=math.sin(phase)*.8
            js['hair_tip'][0]+=math.sin(phase)*2.2
            js['tail_tip'][1]+=math.sin(phase)*1.7
            if name=='idle_look_loop':js['head'][0]+=math.sin(phase)*2
            elif name=='idle_hand_loop':
                for joint in ['wrist_front','hand_front']:js[joint]+=np.array([1.6,2.7])*math.sin(phase)
            elif name=='idle_hair_loop':js['hair_tip'][0]+=math.sin(phase)*3
            elif name=='idle_tail_loop':js['tail_tip']+=np.array([2,2])*math.sin(phase)
            idle_tf.append(transforms(js,lengths))
        for bone in source_tf[0]:
            origin=source_tf[0][bone][0]
            ps=np.array([f[bone][0] for f in idle_tf])
            angles=np.unwrap([f[bone][2] for f in idle_tf])*180/math.pi
            scalex=np.array([f[bone][3] for f in idle_tf])
            scaley=np.array([f[bone][4] for f in idle_tf])
            tracks={'translatex':ps[:,0]-origin[0],'translatey':ps[:,1]-origin[1],'rotate':angles,'scalex':scalex,'scaley':scaley}
            animation['bones'][bone]={kind:[{'time':round(float(t),7),'value':round(float(v),7)} for t,v in zip(lt,vs)] for kind,vs in tracks.items()}
        for slot in oldslots:
            if slot!='prone':animation['slots'][slot]['rgba']=alpha([(0,0)])
        for slot,meta in info['meshes'].items():animation['slots'][slot]['rgba']=alpha([(0,1 if meta['pose']==0 else 0)])
    # Unrelated actions fade this figure out toward a valid neutral transform.
    # Leaving the new bones without tracks would blend them toward zero-angle
    # setup transforms and twist visible sleeves during the 100ms mix.
    for name,animation in anims.items():
        if name=='attack' or (name.startswith('idle_') and name!='idle_angry_loop'):continue
        for bone in source_tf[0]:
            animation['bones'][bone]={kind:[{'time':0,'value':keys[-1]['value']}] for kind,keys in clip['bones'][bone].items()}
    # Preserve blinking on the new ready figure; only the registered eye/face
    # patch is used from the matching image, so the head never changes size.
    blink='reference-blink-v0.8.2.png'
    blink_path=ROOT/'assets/sprites'/blink
    bm=registration(ROOT/'assets/sprites/reference-palm-0-v0.8.2.png',blink_path)
    bw,bh=Image.open(blink_path).size
    region='ref_blink'
    regions[region]=(blink,(0,0,bw,bh))
    bp=np.array([[453,120],[541,120],[453,191],[541,191]],float)
    uv=((bp-bm[:,2])@np.linalg.inv(bm[:,:2]).T)/[800,724]
    weighted=[]
    pos,mat,*_=source_tf[0]['ref_head']
    for p in bp:
        local=np.linalg.solve(mat,world(p)-pos)
        weighted.extend([1,indices['ref_head'],float(local[0]),float(local[1]),1])
    attachments[region]={region:{'type':'mesh','path':region,'width':bw,'height':bh,'uvs':uv.ravel().tolist(),'triangles':[0,1,2,1,3,2],'vertices':weighted}}
    slots.append({'name':region,'bone':'ref_root','attachment':region,'color':'ffffff00'})
    info['meshes'][region]={'pose':0,'key_time':KEY_TIMES[0],'source_geometry':[world(p).tolist() for p in bp]}
    for name,animation in anims.items():
        keys=[(0,0)]
        if name.startswith('idle_') and name!='idle_angry_loop':
            duration=max(ks[-1]['time'] for ts in animation['bones'].values() for ks in ts.values())
            keys+=[(duration*.34,1),(duration*.34+.09,0),(duration*.78,1),(duration*.78+.09,0)]
        animation['slots'][region]={'rgba':alpha(keys)}
        for key in animation['slots'][region]['rgba']:key['curve']='stepped'
    (ROOT/'assets/animation/reference-palm.json').write_text(json.dumps(info,separators=(',',':')),encoding='utf-8')
    return info
