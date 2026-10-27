"""Bind the approved right-facing illustration in its ORIGINAL pixel coordinates.

Raster extraction/painting is image_gen's work. This script authors geometry,
UV clipping, normalized skin weights, and native Spine animation curves only.
All upright surfaces share ONE scale and bind transform; no resized puppet parts.
"""
import base64
import copy
import json
import math
from pathlib import Path
import cv2
import numpy as np
from scipy.spatial import Delaunay
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'assets/animation'
SCALE=443/1518
def world(x,y):return ((x-600)*SCALE,(1518-y)*SCALE)
pixel_pivots={
 'body':(660,610),'chest':(670,440),'head':(650,300),
 'hair':(540,230),'hair_tip':(340,550),'tail':(330,940),'tail_tip':(160,730),
 'skirt':(650,610),'skirt_hem':(640,1000),
 'leg_back':(685,800),'leg_front':(570,800),
 'arm_back':(750,427),'elbow_back':(791,530),'wrist_back':(864,469),'hand_back':(899,440),
 'arm_front':(550,405),'elbow_front':(506,550),'wrist_front':(427,721),'hand_front':(410,762),
 'knee_front':(517.5,1067.5),'knee_back':(715,1052.5),
 'foot_front':(465,1335),'foot_back':(745,1305),
}
positions={'root':(0,0),**{n:world(*p) for n,p in pixel_pivots.items()},'prone':(20,0)}
parents={'body':'root','chest':'body','head':'chest','hair':'head','hair_tip':'hair',
 'tail':'body','tail_tip':'tail','skirt':'body','skirt_hem':'skirt',
 'leg_back':'root','leg_front':'root','arm_back':'chest','arm_front':'chest',
 'elbow_back':'arm_back','elbow_front':'arm_front','wrist_back':'elbow_back',
 'wrist_front':'elbow_front','hand_back':'wrist_back','hand_front':'wrist_front',
 'knee_front':'leg_front','knee_back':'leg_back','foot_front':'root','foot_back':'root'}
names=list(positions)
bones=[]
for name,(x,y) in positions.items():
 px,py=positions.get(parents.get(name),(0,0))
 b={'name':name,'x':round(x-px,6),'y':round(y-py,6)}
 if name in parents:b['parent']=parents[name]
 bones.append(b)

master='right-master-v0.8.png';base='right-body-nolegs-v0.8.1.png'
regions={'body':(base,(0,0,1024,1536)),
 'front_arm':(master,(0,0,1024,1536)),'back_arm':(master,(0,0,1024,1536)),
 'front_hand':(master,(0,0,1024,1536)),'back_hand':(master,(0,0,1024,1536)),
 'head_normal':(base,(0,0,1024,1536)),'head_focus':(base,(0,0,1024,1536)),
 'leg_front':('right-body-v0.8.png',(0,0,1024,1536)),
 'leg_back':('right-body-v0.8.png',(0,0,1024,1536)),
 'thigh_front':('right-legs-v0.8.1.png',(0,0,1024,1536)),
 'thigh_back':('right-legs-v0.8.1.png',(0,0,1024,1536)),
 'head_closed':('right-blink-v0.8.png',(0,0,1024,1536)),
 'head_angry':('right-angry-v0.8.png',(0,0,1024,1536))}
prone='right-prone-v0.8.png'
prone_image=np.array(Image.open(ROOT/'assets/sprites'/prone))
stats=cv2.connectedComponentsWithStats((prone_image[:,:,3]>96).astype('uint8'))[2][1:]
prone_rect=tuple(int(v) for v in max(stats,key=lambda s:s[4])[:4])
regions['prone']=(prone,prone_rect)
slots=[];attachments={}

def smooth(a,b,v):
 t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
def combine(a,b,t):
 out={k:a.get(k,0)*(1-t)+b.get(k,0)*t for k in a.keys()|b.keys()}
 return {k:v for k,v in out.items() if v>1e-7}
def body_weights(x,y):
 # Continuous spatial fields, including across transparent gaps. Hard weight
 # boundaries in an intact painting would pinch at the neck or skirt.
 if y<440:base_weights=combine({'head':1},{'chest':1},smooth(320,440,y))
 elif y<610:base_weights=combine({'chest':1},{'skirt':1},smooth(440,610,y))
 elif y<1000:base_weights=combine({'skirt':1},{'skirt_hem':1},smooth(650,1000,y))
 else:base_weights={'skirt_hem':1}
 hair=smooth(570,360,x)*smooth(280,420,y)*(1-smooth(700,840,y))*.9
 tail=smooth(390,210,x)*smooth(510,670,y)*(1-smooth(940,990,y))
 result=combine(base_weights,{'hair_tip':1},hair)
 return combine(result,{'tail_tip':1},tail)

def arm_weights(side,x,y,radius=40):
 a=np.array(pixel_pivots['arm_'+side],float);e=np.array(pixel_pivots['elbow_'+side],float)
 w=np.array(pixel_pivots['wrist_'+side],float);p=np.array([x,y])
 # Bisector of the two limb segments works for the already-bent rear arm;
 # projection onto its returning forearm incorrectly weights the sleeve cap.
 tangent=(e-a)/np.linalg.norm(e-a)+(w-e)/np.linalg.norm(w-e)
 tangent/=np.linalg.norm(tangent)
 blend=smooth(-radius,radius,float(np.dot(p-e,tangent)))
 return combine({'arm_'+side:1},{'elbow_'+side:1},blend)

def leg_weights(side,x,y):
 h=np.array(pixel_pivots['leg_'+side],float);k=np.array(pixel_pivots['knee_'+side],float)
 f=np.array(pixel_pivots['foot_'+side],float);p=np.array([x,y])
 tangent=(k-h)/np.linalg.norm(k-h)+(f-k)/np.linalg.norm(f-k)
 tangent/=np.linalg.norm(tangent)
 knee=smooth(-100,100,float(np.dot(p-k,tangent)))
 result=combine({'leg_'+side:1},{'knee_'+side:1},knee)
 return combine(result,{'foot_'+side:1},smooth(f[1]-35,f[1]+5,y))

def add_mesh(slot,bone,region,vertices,triangles,weight_fn,default=True,name=None,texture_transform=None):
 name=name or region
 if slot not in attachments:
  slots.append({'name':slot,'bone':bone,**({'attachment':name} if default else {})});attachments[slot]={}
 # Delete triangles containing no painted pixels. They would bridge the empty
 # space between independent legs and could invert there without drawing art.
 if slot in ['torso','petticoat_back','leg_front','leg_back']:
  alpha=np.array(Image.open(ROOT/'assets/sprites'/regions[region][0]))[:,:,3]
  kept=[]
  for tri in triangles:
   p=np.array([vertices[i] for i in tri])
   if texture_transform:p=(p-np.array(texture_transform[1:]))/texture_transform[0]
   lo=np.floor(p.min(axis=0)).astype(int);hi=np.ceil(p.max(axis=0)).astype(int)
   lo=np.maximum(lo,[0,0]);hi=np.minimum(hi,[alpha.shape[1]-1,alpha.shape[0]-1])
   if (hi<lo).any():continue
   mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
   cv2.fillConvexPoly(mask,np.round(p-lo).astype(np.int32),1)
   if np.any(alpha[lo[1]:hi[1]+1,lo[0]:hi[0]+1]*mask>1):kept.append(tri)
  triangles=kept
 uv=[];weighted=[]
 rx,ry,rw,rh=regions[region][1]
 for x,y in vertices:
  ux,uy=((np.array([x,y])-texture_transform[1:])/texture_transform[0]) if texture_transform else (x,y)
  uv.extend([round((ux-rx)/rw,8),round((uy-ry)/rh,8)])
  wx,wy=world(x,y);ws=weight_fn(x,y)
  assert 1<=len(ws)<=4 and abs(sum(ws.values())-1)<1e-6,(slot,ws)
  weighted.append(len(ws))
  for b,w in ws.items():
   bx,by=positions[b];weighted.extend([names.index(b),round(wx-bx,6),round(wy-by,6),round(w,8)])
 attachments[slot][name]={'type':'mesh','path':region,'width':rw,'height':rh,
  'uvs':uv,'triangles':list(map(int,np.array(triangles).flatten())),'vertices':weighted}

def polygon_mesh(poly,step=18):
 contour=np.array(poly,np.float32)
 def inside(p):return cv2.pointPolygonTest(contour,tuple(map(float,p)),False)>=-.001
 pts=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  p=np.array(p);q=np.array(q);n=max(1,math.ceil(np.linalg.norm(q-p)/step))
  pts.extend((p+(q-p)*i/n).tolist() for i in range(n))
 lo=np.min(contour,axis=0);hi=np.max(contour,axis=0)
 pts.extend([x,y] for y in np.arange(lo[1]+step/2,hi[1],step) for x in np.arange(lo[0]+step/2,hi[0],step) if inside((x,y)))
 pts=np.unique(np.round(pts,5),axis=0);tris=[]
 for t in Delaunay(pts).simplices:
  a,b,c=pts[t]
  if not all(inside(p) for p in [(a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2]):continue
  ab=b-a;ac=c-a
  if ab[0]*ac[1]-ab[1]*ac[0]<0:t=t[::-1]
  tris.append(t)
 return pts,tris

# All outlines below refer to the SAME original master coordinates. Arm caps
# overlap the repainted shoulder socket; wrist overlap sits under the cuff.
back_arm=[(738,399),(775,423),(794,458),(801,492),(828,484),(850,453),(883,466),(884,489),(853,531),(813,564),(781,572),(758,552),(742,502)]
back_hand=[(855,466),(853,450),(872,427),(896,411),(919,398),(938,381),(945,384),(941,399),(927,414),(951,406),(969,397),(975,401),(969,409),(951,421),(974,421),(980,426),(975,431),(953,433),(970,449),(970,455),(961,454),(934,439),(917,457),(898,472),(875,482)]
front_arm=[(530,342),(563,345),(590,381),(604,424),(604,456),(579,490),(551,525),(545,559),(524,608),(494,662),(482,688),(477,714),(451,743),(426,740),(398,728),(386,700),(403,667),(422,645),(439,602),(463,550),(482,499),(480,469),(472,433),(478,394),(494,365)]
front_hand=[(399,718),(428,721),(449,741),(434,757),(427,788),(414,811),(403,824),(397,820),(402,802),(408,783),(397,798),(384,821),(377,824),(375,816),(383,791),(379,794),(373,808),(367,805),(369,783),(374,763),(389,743)]
for slot,side,poly,hand in [('arm_back','back',back_arm,False),('hand_back','back',back_hand,True)]:
 vs,ts=polygon_mesh(poly)
 add_mesh(slot,'arm_'+side if not hand else 'hand_'+side,'back_hand' if hand else 'back_arm',vs,ts,
          (lambda x,y:{'hand_back':1}) if hand else lambda x,y:arm_weights('back',x,y))

hem_x=[0,300,400,500,600,700,800,900,1024]
hem_y=[1000,945,945,970,985,985,965,925,1000]
def body_surface(front):
 vs=[];ts=[];nx,ny=40,48 if front else 20
 for row in range(ny+1):
  for col in range(nx+1):
   x=1024*col/nx;hem=float(np.interp(x,hem_x,hem_y))
   y=hem*row/ny if front else hem+(1536-hem)*row/ny
   vs.append((x,y))
 for row in range(ny):
  for col in range(nx):
   a=row*(nx+1)+col;b=a+1;c=a+nx+1;d=c+1;ts.extend([[a,b,c],[b,d,c]])
 return vs,ts

# Back petticoat sits BEHIND the legs. The front dress hem will cover their
# extended thighs, keeping the source's original occlusion and proportions.
vs,ts=body_surface(False)
add_mesh('petticoat_back','body','body',vs,ts,body_weights,name='body_back')

# Preserve the ORIGINAL visible legs, bows, ankle frills and shoes. The painted
# extension is used only above the old hem, where the source art had no skin.
for side,x0,x1 in [('back',620,745),('front',490,620)]:
 vs=[];ts=[];nx,ny=12,12
 for row in range(ny+1):
  for col in range(nx+1):vs.append((x0+(x1-x0)*col/nx,840+(975-840)*row/ny))
 for row in range(ny):
  for col in range(nx):
   a=row*(nx+1)+col;b=a+1;c=a+nx+1;d=c+1;ts.extend([[a,b,c],[b,d,c]])
 add_mesh('thigh_'+side,'leg_'+side,'thigh_'+side,vs,ts,lambda x,y,s=side:{'leg_'+s:1},texture_transform=(.45,330,840))
leg_outlines={
 'front':[(505,966),(620,966),(620,1000),(605,1050),(575,1100),(550,1150),(535,1200),(510,1250),(486,1300),(485,1325),(500,1350),(530,1400),(555,1450),(565,1500),(540,1523),(490,1515),(450,1490),(410,1460),(401,1410),(411,1375),(425,1335),(428,1300),(436,1250),(439,1200),(439,1150),(465,1100),(485,1060),(453,1048),(445,1022),(469,996)],
 'back':[(650,970),(735,970),(742,1000),(770,1020),(777,1057),(749,1070),(747,1120),(754,1190),(769,1270),(777,1300),(781,1320),(815,1350),(850,1380),(878,1400),(875,1438),(852,1450),(780,1450),(731,1424),(704,1395),(703,1340),(708,1310),(689,1250),(674,1200),(662,1140),(668,1080),(659,1020)]}
for side in ['back','front']:
 vs,ts=polygon_mesh(leg_outlines[side],14)
 add_mesh('leg_'+side,'leg_'+side,'leg_'+side,vs,ts,lambda x,y,s=side:leg_weights(s,x,y))

# Same-coordinate front body, hair, skirt and tail. Legs are separate surfaces.
vs,ts=body_surface(True)
add_mesh('torso','body','body',vs,ts,body_weights)

# Only a fully opaque small facial patch switches expression. No head resizing.
face=[(568,188),(711,188),(711,297),(568,297)]
vs,ts=polygon_mesh(face,18)
for region in ['head_normal','head_focus','head_closed','head_angry']:
 add_mesh('head','head',region,vs,ts,body_weights,name=region)
for slot,side,poly,hand in [('hand_front','front',front_hand,True),('arm_front','front',front_arm,False)]:
 vs,ts=polygon_mesh(poly)
 add_mesh(slot,'hand_'+side if hand else 'arm_'+side,'front_hand' if hand else 'front_arm',vs,ts,
          (lambda x,y:{'hand_front':1}) if hand else lambda x,y:arm_weights('front',x,y))
 if not hand:
  add_mesh(slot,'arm_front','front_arm',vs,ts,lambda x,y:arm_weights('front',x,y,110),name='front_arm_attack')

# Keep selector-compatible palm/fist attachment names. The approved drawn open
# hands are retained; do not introduce mismatched generated fists.
for slot in ['hand_front','hand_back']:
 normal=next(iter(attachments[slot].values()))
 for n in (['fist','cast_palm'] if slot=='hand_front' else ['fist']):attachments[slot][n]=copy.deepcopy(normal)

# Prone texture has its own purpose-drawn final silhouette. Map on floor y=0.
x,y,w,h=prone_rect;prone_width=460;prone_height=prone_width*h/w
px,py=positions['prone']
coords=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
add_mesh('prone','prone','prone',coords,[[0,1,2],[0,2,3]],lambda x,y:{'prone':1},default=False)
m=attachments['prone']['prone'];m['vertices']=[]
for u,v in [(0,0),(1,0),(1,1),(0,1)]:
 m['vertices'].extend([1,names.index('prone'),(u-.5)*prone_width,(1-v)*prone_height,1])

# Reuse the established action names and timings; retarget every curve to the
# new illustration's actual rest pose. This legacy module is data authoring only.
legacy=(ROOT/'tools/legacy_parts_v0_7.py').read_text(encoding='utf-8')
section=legacy[legacy.index('def timeline('):legacy.index("document={'skeleton'")]
exec(section,globals())
old_neutral=neutral.copy()

def remap_keys(keys,fn):
 for k in keys:
  k['value']=round(fn(k['value']),6)
  if 'curve' in k:
   k['curve'][1]=round(fn(k['curve'][1]),6);k['curve'][3]=round(fn(k['curve'][3]),6)
for name,clip in anims.items():
 for bone,tracks in clip['bones'].items():
  for kind,keys in tracks.items():
   if kind!='rotate':continue
   if bone in old_neutral:
    gain=1.45 if bone=='arm_front' else .42 if bone=='arm_back' else .36 if bone.startswith('elbow') else .4
    limit=118 if bone=='arm_front' else 42 if bone=='arm_back' else 25 if bone=='elbow_back' else 42 if bone=='elbow_front' else 17
    base_angle=old_neutral[bone]
    remap_keys(keys,lambda v,g=gain,l=limit,b=base_angle:max(-l,min(l,(v-b)*g)))
   elif bone in ['hair','hair_tip','tail','tail_tip','skirt','skirt_hem','head','chest','body']:
    factor=.45 if bone in ['tail','hair','skirt','chest'] else .6
    remap_keys(keys,lambda v,f=factor:v*f)

# Drawing-specific attack path: chamber hand near waist, extend toward right,
# then recover. The original palm is part of the continuous limb chain.
for name,(duration,phases,arm,elbow) in profiles.items():
 clip=anims[name]
 if name in ['attack','attack_palm','attack_ranged','attack_jab','attack_cross']:
  peak=108 if name!='attack_jab' else 95
  set_track(clip,'arm_front','rotate',[(0,0),(.16,25),(.34,peak),(.44,peak-2),(.72,28),(1,0)])
  set_track(clip,'elbow_front','rotate',[(0,0),(.16,-38),(.34,-4),(.44,-4),(.72,-16),(1,0)])
  set_track(clip,'wrist_front','rotate',[(0,0),(.16,-8),(.34,64),(.44,64),(.72,12),(1,0)])
  set_track(clip,'root','translatex',[(0,0),(.16,-2),(.34,18),(.44,18),(.72,5),(1,0)])
  set_track(clip,'root','translatey',[(0,0),(.16,-3),(.34,-6),(.44,-6),(.72,-2),(1,0)])
  set_track(clip,'body','rotate',[(0,0),(.16,1),(.34,-3),(.44,-3),(.72,-1),(1,0)])
  set_track(clip,'chest','rotate',[(0,0),(.16,1),(.34,-2),(.44,-2),(.72,-1),(1,0)])
 # The body participates in every strike; bend knees and shift the lead foot.
 set_track(clip,'leg_front','rotate',[(0,0),(.17,-2),(.36,-5),(.5,-5),(.8,-1),(1,0)])
 set_track(clip,'knee_front','rotate',[(0,0),(.17,2),(.36,8),(.5,8),(.8,1),(1,0)])
 set_track(clip,'foot_front','translatex',[(0,0),(.16,0),(.35,7),(.5,7),(.8,2),(1,0)])
 # Rear shoe remains planted while torso moves forward, feet stay on baseline.
 for axis in ['x','y']:
  src=clip['bones']['root']['translate'+axis]
  dst=copy.deepcopy(src);remap_keys(dst,lambda v:-v)
  clip['bones']['foot_back']['translate'+axis]=dst
  if axis=='y':clip['bones']['foot_front']['translatey']=copy.deepcopy(dst)

# New source-pose-specific gestures. Arms start in the approved natural pose;
# shoulder angles above zero lift the foreground hand toward the enemy.
# Full-body reference attack. Solve both two-bone legs against fixed shoe
# targets, so a wide crouch/lunge bends at knees instead of stretching calves.
def solve_leg(side,hip,ankle):
 h=np.array(positions['leg_'+side]);k=np.array(positions['knee_'+side]);f=np.array(positions['foot_'+side])
 upper=k-h;lower=f-k;l1=np.linalg.norm(upper);l2=np.linalg.norm(lower)
 delta=np.array(ankle)-hip;distance=np.linalg.norm(delta)
 assert distance<l1+l2+.1,(side,'unreachable attack foot',distance,l1+l2)
 along=delta/max(distance,.0001);distance=min(distance,l1+l2-.00001)
 a=(l1*l1-l2*l2+distance*distance)/(2*distance)
 height=math.sqrt(max(0,l1*l1-a*a));perp=np.array([-along[1],along[0]])
 knee=np.array(hip)+along*a+perp*height*(-1 if side=='front' else 1)
 angle=lambda v:math.degrees(math.atan2(v[1],v[0]))
 wrap=lambda a:(a+180)%360-180
 thigh=wrap(angle(knee-hip)-angle(upper))
 shin=wrap(angle(np.array(ankle)-knee)-angle(lower)-thigh)
 return thigh,shin

attack_durations={'attack':.94,'attack_palm':.96,'attack_ranged':1.0,'attack_jab':.78,'attack_cross':.98}
for name in profiles:
 clip=anims[name]
 old_duration=max(k[-1]['time'] for tracks in clip['bones'].values() for k in tracks.values())
 duration=attack_durations.get(name,old_duration)
 if duration!=old_duration:
  ratio=duration/old_duration
  for tracks in clip['bones'].values():
   for keys in tracks.values():
    for key in keys:
     key['time']=round(key['time']*ratio,6)
     if isinstance(key.get('curve'),list):key['curve'][0]*=ratio;key['curve'][2]*=ratio
  for tracks in clip['slots'].values():
   for keys in tracks.values():
    for key in keys:key['time']=round(key['time']*ratio,6)
 # Root stays on its floor anchor. The hip/torso moves independently of shoes.
 phases=[0,.18,.38,.52,.72,.86,1]
 x_values=[0,0,20,20,4,0,0]
 y_values=[0,-55,-65,-65,-45,-18,0]
 lean=[0,1,-8,-8,1,0,0]
 spread=[0,.96,1.06,1.06,.93,.35,0]
 for axis in ['x','y']:set_track(clip,'root','translate'+axis,[(0,0),(1,0)])
 set_track(clip,'body','translatex',list(zip(phases,x_values)))
 set_track(clip,'body','translatey',list(zip(phases,y_values)))
 set_track(clip,'body','rotate',list(zip(phases,lean)))
 set_track(clip,'chest','rotate',list(zip(phases,[0,1,-1,-1,1,0,0])))
 set_track(clip,'head','rotate',list(zip(phases,[0,-1,3,3,-1,0,0])))
 # Source hands stay connected, foreground palm is vertical at impact.
 if name in attack_durations:
  clip['slots']['arm_front']['attachment']=[{'time':0,'name':'front_arm_attack'}]
  set_track(clip,'arm_front','rotate',list(zip(phases,[0,15,116,116,32,14,0])))
  set_track(clip,'elbow_front','rotate',list(zip(phases,[0,100,8,8,80,28,0])))
  set_track(clip,'wrist_front','rotate',list(zip(phases,[0,55,66,66,48,15,0])))
 set_track(clip,'arm_back','rotate',list(zip(phases,[0,-95,-128,-128,-80,-25,0])))
 set_track(clip,'elbow_back','rotate',list(zip(phases,[0,18,15,15,15,5,0])))
 for side in ['front','back']:
  leg='leg_'+side;knee='knee_'+side;foot='foot_'+side
  hip0=np.array(positions[leg]);foot0=np.array(positions[foot]);pivot=np.array(positions['body'])
  tracks={leg:{'rotate':[],'translatex':[],'translatey':[]},knee:{'rotate':[]},foot:{'translatex':[],'translatey':[]}}
  def evaluate(values,t):
   if t<=0:return values[0]
   if t>=1:return values[-1]
   j=next(j for j in range(len(phases)-1) if phases[j]<=t<=phases[j+1])
   u=(t-phases[j])/(phases[j+1]-phases[j]);lo=0;hi=1
   for _ in range(22):
    s=(lo+hi)/2;r=1-s;x=3*r*r*s*.34+3*r*s*s*.66+s*s*s
    if x<u:lo=s
    else:hi=s
   s=(lo+hi)/2;e=s*s*(3-2*s)
   return values[j]+(values[j+1]-values[j])*e
  for phase in np.linspace(0,1,97):
   tx=evaluate(x_values,phase);ty=evaluate(y_values,phase);theta=evaluate(lean,phase);width=evaluate(spread,phase)
   a=math.radians(theta);rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
   hip=pivot+rot@(hip0-pivot)+[tx,ty]
   target_x=foot0[0]+(-72 if side=='front' else 60)*width
   target_y=foot0[1]+(-24 if side=='back' else 0)*min(1,width)
   ankle=np.array([target_x,target_y])
   thigh,shin=solve_leg(side,hip,ankle)
   if phase in (0,1):thigh=shin=0
   tracks[leg]['rotate'].append((phase,thigh));tracks[knee]['rotate'].append((phase,shin))
   for axis,idx in [('x',0),('y',1)]:
    tracks[leg]['translate'+axis].append((phase,hip[idx]-hip0[idx]))
    tracks[foot]['translate'+axis].append((phase,ankle[idx]-foot0[idx]))
  for bone,ts in tracks.items():
   for kind,points in ts.items():
    # C1 Hermite interpolation of dense exact IK samples. Interpolating only
    # endpoint angles would detach the calf from the independently planted shoe.
    times=np.array([p[0]*duration for p in points]);values=np.array([p[1] for p in points])
    slopes=np.gradient(values,times);keys=[]
    for j,(t,v) in enumerate(zip(times,values)):
     key={'time':round(float(t),6),'value':round(float(v),6)}
     if j+1<len(points):
      dt=times[j+1]-t
      key['curve']=[float(t+dt/3),float(v+slopes[j]*dt/3),float(times[j+1]-dt/3),float(values[j+1]-slopes[j+1]*dt/3)]
     keys.append(key)
    clip['bones'][bone][kind]=keys
 set_track(clip,'hair_tip','rotate',[(0,0),(.18,2),(.43,-7),(.6,-9),(.8,2),(1,0)])
 set_track(clip,'tail_tip','rotate',[(0,0),(.18,3),(.44,8),(.62,10),(.83,-2),(1,0)])

def arms_pose(name,front,elbow,back,back_elbow,wrist=10):
 clip=anims[name]
 for bone,peak in [('arm_front',front),('elbow_front',elbow),('arm_back',back),('elbow_back',back_elbow),('wrist_front',wrist)]:
  set_track(clip,bone,'rotate',[(0,0),(.2,peak*.5),(.45,peak),(.64,peak),(.83,peak*.25),(1,0)])
for name,a,e,b,be,w in [
 ('cast',85,-8,8,5,30),('cast_arc',112,-18,15,8,15),('cast_release',105,-4,4,-8,45),
 ('cast_dual',93,12,25,15,25),('cast_point',78,-12,0,-5,25),('cast_circle',105,-25,22,10,30),
 ('guard',80,20,-8,-12,38),('guard_brace',87,18,-12,-15,42),('guard_raise',105,16,-4,-10,40),
 ('guard_cross',74,25,-18,-20,20),('guard_push',104,4,2,-5,55),
 ('channel',58,25,-14,-18,15),('channel_release',108,8,25,10,45),('channel_gather',55,30,-18,-20,10),
 ('channel_pulse',90,10,18,12,30),('channel_overdrive',118,18,38,12,15),
 ('greeting',18,12,0,0,8),('greeting_wave',112,20,0,0,20),('greeting_bow',5,5,0,-5,0),
 ('revive',94,20,28,12,25),
]:arms_pose(name,a,e,b,be,w)
for name in ['cast_arc','cast_circle','channel_pulse','greeting_wave']:
 set_track(anims[name],'wrist_front','rotate',[(0,0),(.3,12),(.42,32),(.53,-3),(.64,25),(.76,4),(1,0)])
for name in ['idle_ready_loop','idle_angry_loop','meditate_loop','rest_sleep_loop']:
 d=5 if name=='idle_ready_loop' else 4 if name=='idle_angry_loop' else 6
 for bone,v in [('arm_front',38 if name=='idle_ready_loop' else 15),('elbow_front',10),('arm_back',-7),('elbow_back',-8)]:
  anims[name]['bones'][bone]['rotate']=wave(1.1,.3,v,d)
for name in ['victory_loop','victory_wave_loop','victory_pose_loop']:
 for bone,v in [('arm_front',110 if name!='victory_pose_loop' else 80),('elbow_front',18),('arm_back',25),('elbow_back',12)]:
  anims[name]['bones'][bone]['rotate']=wave(3,.4,v,4)
 anims[name]['bones']['wrist_front']['rotate']=wave(18 if name=='victory_wave_loop' else 4,0,20,4,3 if name=='victory_wave_loop' else 1)

# Every looping action closes in pose AND first derivative. Reject accidental
# noncyclic one-shot gesture tracks inherited in a loop.
for name,clip in anims.items():
 if not name.endswith('_loop'):continue
 for tracks in clip['bones'].values():
  for keys in tracks.values():
   assert abs(keys[0]['value']-keys[-1]['value'])<1e-4,(name,keys)

# Death collapses the unified body forward, hands brace, then switches once to
# the dedicated floor pose. Avoid several translucent bodies at contact.
death=anims['death']
for b in ['body','chest','head','hair','hair_tip','tail','tail_tip','skirt','skirt_hem','leg_front','leg_back','knee_front','knee_back','foot_front','foot_back']:
 for k in ['rotate','translatex','translatey','scalex','scaley']:
  death['bones'][b][k]=timeline([(0,1 if k.startswith('scale') else 0),(1.35,1 if k.startswith('scale') else 0)])
set_track(death,'root','translatex',[(0,0),(.3,0),(.55,-30),(.73,-140),(1,-140)])
set_track(death,'root','translatey',[(0,0),(.2,0),(.5,30),(.73,85),(1,85)])
set_track(death,'root','rotate',[(0,0),(.22,-3),(.5,-40),(.73,-88),(1,-88)])
set_track(death,'body','rotate',[(0,0),(.22,-2),(.5,-4),(.73,0),(1,0)])
set_track(death,'chest','rotate',[(0,0),(.3,-1),(.6,-2),(1,0)])
set_track(death,'arm_front','rotate',[(0,0),(.3,35),(.6,80),(.73,92),(1,92)])
set_track(death,'elbow_front','rotate',[(0,0),(.5,-10),(.73,-32),(1,-32)])
set_track(death,'arm_back','rotate',[(0,0),(.4,8),(.73,25),(1,25)])
set_track(death,'elbow_back','rotate',[(0,0),(.5,-10),(1,-20)])
set_track(death,'leg_front','rotate',[(0,0),(.35,-2),(.6,-3),(1,0)])
set_track(death,'leg_back','rotate',[(0,0),(.35,-1),(.6,-2),(1,0)])
set_track(death,'knee_front','rotate',[(0,0),(.35,1),(.6,2),(1,0)])
set_track(death,'knee_back','rotate',[(0,0),(.35,1),(.6,2),(1,0)])
# Separate native root keeps the dedicated floor pose fixed during collapse.
set_track(death,'prone','translatex',[(0,0),(1,0)])
set_track(death,'prone','translatey',[(0,0),(1,0)])
set_track(death,'prone','scaley',[(0,1),(.73,1),(.79,.96),(.88,1.012),(1,1)])
contact=.99
for slot in slots:
 n=slot['name']
 if n=='prone':
  death['slots'][n]['attachment']=[{'time':0,'name':'prone'}]
  death['slots'][n]['rgba']=[{'time':0,'color':'ffffff00','curve':'stepped'},{'time':contact,'color':'ffffffff'},{'time':1.35,'color':'ffffffff'}]
 else:death['slots'][n]['rgba']=[{'time':0,'color':'ffffffff','curve':'stepped'},{'time':contact,'color':'ffffff00'},{'time':1.35,'color':'ffffff00'}]

from reference_palm import extend as extend_reference_palm
reference_palm_info=extend_reference_palm(bones,slots,attachments,anims,regions)
from reference_guard import extend as extend_reference_guard
reference_guard_info=extend_reference_guard(bones,slots,attachments,anims,regions)
from reference_spell import extend as extend_reference_spell
reference_spell_info=extend_reference_spell(bones,slots,attachments,anims,regions)
from common_state import extend as extend_common_state
common_state_info=extend_common_state(bones,slots,attachments,anims,regions)
prone_height=common_state_info['prone_height']
water_file='reference-water-v0.8.2.png'
water_size=Image.open(ROOT/'assets/sprites'/water_file).size
regions['ref_water']=(water_file,(0,0,*water_size))
pages={}
for n,(f,r) in regions.items():pages.setdefault(f,[]).append((n,r))
atlas=[]
for file,entries in pages.items():
 w,h=Image.open(ROOT/'assets/sprites'/file).size
 atlas.extend([file,f'size: {w},{h}','format: RGBA8888','filter: Linear,Linear','repeat: none','pma: false'])
 for n,(x,y,w,h) in entries:
  atlas.extend([n,'  rotate: false',f'  xy: {x},{y}',f'  size: {w},{h}',f'  orig: {w},{h}','  offset: 0,0','  index: -1'])
 atlas.append('')
OUT.mkdir(exist_ok=True)
(OUT/'maid.atlas').write_text('\n'.join(atlas),encoding='utf-8')
document={'skeleton':{'spine':'4.2.43','x':-260,'y':0,'width':520,'height':443,'fps':60,'images':'./'},
 'bones':bones,'slots':slots,'skins':[{'name':'default','attachments':attachments}],'animations':anims}
(OUT/'maid.spine-json').write_text(json.dumps(document,separators=(',',':')),encoding='utf-8')
preview={**document,'preview_regions':{n:{'page':f,'rect':r,**({'source_to_model':[.45,330,840]} if n.startswith('thigh_') else {})} for n,(f,r) in regions.items()}}
(ROOT/'preview/rig-data.js').write_text('const RIG_DATA='+json.dumps(preview,separators=(',',':'))+';\n',encoding='utf-8')
textures={f:'data:image/png;base64,'+base64.b64encode((ROOT/'assets/sprites'/f).read_bytes()).decode('ascii') for f in pages}
(ROOT/'preview/rig-texture.js').write_text('const RIG_TEXTURES='+json.dumps(textures,separators=(',',':'))+';\n',encoding='utf-8')
payload={'textures':list(pages),'height':443,'slots':len(slots),'attachments':sum(map(len,attachments.values())),
 'source_coordinate_system':{'width':800,'height':724,'origin_x':470,'floor_y':718,'uniform_scale':common_state_info['scale']},
 'prone_height':prone_height,'animation_author':'common_state.py (earlier authoring modules retained as source history)',
 'reference_palm':{'duration':reference_palm_info['duration'],'source_views':3,'key_times':reference_palm_info['key_times'],'continuous_native_skinning':True},
 'reference_guard':{'duration':reference_guard_info['duration'],'source_views':2,'ready_view':1,'key_times':reference_guard_info['key_times'][:2],'continuous_native_skinning':True},
 'reference_spell':{'duration':reference_spell_info['duration'],'source_views':2,'profiles':reference_spell_info['profiles'],'continuous_native_skinning':True},
 'common_state':{'baseline':common_state_info['baseline'],'default_animation':'idle_loop','actions':common_state_info['clips'],'shared_attachment_slots':True}}
(OUT/'payload.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(f'Authored approved right-facing figure: {len(bones)} bones, {len(slots)} layers, {len(anims)} continuous clips; original image proportions preserved.')
