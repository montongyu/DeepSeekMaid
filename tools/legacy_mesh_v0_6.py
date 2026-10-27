"""Author original Spine 4.2 mesh, weights and timelines. Never read another mod's art."""
import json
import math
import base64
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/animation'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 443
# All pivots are in the approved combat atlas's first cell, measured from top left.
PIVOTS = {
    'root': (221.5, 443), 'body': (260, 288), 'chest': (262, 205),
    'head': (264, 161), 'hair': (212, 126), 'hair_tip': (137, 252),
    'tail': (157, 333), 'tail_tip': (77, 310),
    'arm_back': (212, 206), 'arm_front': (307, 206),
    'elbow_back': (190, 246), 'elbow_front': (323, 243),
    'wrist_back': (173, 269), 'wrist_front': (340, 270),
    'hand_back': (162, 282), 'hand_front': (350, 279),
    'fingers_back': (153, 289), 'fingers_front': (356, 288),
    'eye_left': (253, 122), 'eye_right': (285, 126),
}
PARENTS = {
    'body':'root', 'chest':'body', 'head':'chest', 'hair':'chest',
    'hair_tip':'hair', 'tail':'root', 'tail_tip':'tail',
    'arm_back':'chest', 'arm_front':'chest',
    'elbow_back':'arm_back', 'elbow_front':'arm_front',
    'wrist_back':'elbow_back', 'wrist_front':'elbow_front',
    'hand_back':'wrist_back', 'hand_front':'wrist_front',
    'fingers_back':'hand_back', 'fingers_front':'hand_front',
    'eye_left':'head', 'eye_right':'head',
}
names = list(PIVOTS)
world = {n: (p[0]-SIZE/2, SIZE-p[1]) for n,p in PIVOTS.items()}
bones = []
for n in names:
    parent = PARENTS.get(n)
    px,py = world[parent] if parent else (0,0)
    x,y = world[n]
    bone = {'name':n, 'x':round(x-px,5), 'y':round(y-py,5)}
    if parent: bone['parent'] = parent
    bones.append(bone)

def smooth(a,b,x):
    t = max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)

def gaussian(x,y,cx,cy,rx,ry):
    return math.exp(-2*((x-cx)**2/rx**2+(y-cy)**2/ry**2))

def weights(x,y):
    # Continuous fields keep adjacent vertices welded. Feet retain root weight.
    foot = smooth(350,405,y)
    torso = smooth(155,195,y)*(1-smooth(310,390,y))*smooth(170,226,x)*(1-smooth(304,350,x))
    head = gaussian(x,y,265,104,93,111)
    hair = (1-smooth(185,246,x))*smooth(120,195,y)*(1-smooth(318,370,y))
    tail = (1-smooth(130,202,x))*smooth(242,282,y)*(1-smooth(380,421,y))
    # Continue the front-arm field through empty space to the right edge;
    # fading it horizontally behind the moving palm would fold the margin.
    front = gaussian(min(x,324),y,324,236,30,43)
    back = gaussian(x,y,190,242,29,42)
    eye_l = gaussian(x,y,253,122,15,11)*1.7
    eye_r = gaussian(x,y,285,126,13,10)*1.7
    fields = {
        'root':.12+foot*5, 'body':torso*.9, 'chest':gaussian(x,y,265,208,72,69),
        'head':head*3, 'hair':hair*.65, 'hair_tip':hair*smooth(158,258,y)*2,
        'tail':tail*.6, 'tail_tip':tail*(1-smooth(70,162,x))*4,
        'arm_back':back*1.1, 'arm_front':front*1.1,
        'elbow_back':gaussian(x,y,183,256,32,42)*2.5,
        'elbow_front':gaussian(min(x,332),y,332,254,34,42)*2.5,
        'wrist_back':gaussian(x,y,171,272,30,32)*4,
        'wrist_front':gaussian(min(x,341),y,341,271,30,32)*4,
        'hand_back':gaussian(x,y,160,283,32,35)*5,
        'hand_front':gaussian(min(x,351),y,351,281,32,35)*5,
        'fingers_back':gaussian(x,y,151,292,28,25)*4,
        'fingers_front':gaussian(min(x,360),y,360,291,28,25)*4,
        'eye_left':eye_l*8, 'eye_right':eye_r*8,
    }
    # Stop hand movement above the skirt hem instead of pulling the dress with
    # the palm. Add stationary support through the smooth transition strip.
    arm_mask=1-smooth(287,337,y)
    for name in fields:
        if name.endswith('_front') and name.startswith(('arm_','elbow_','wrist_','hand_','fingers_')):
            fields[name]*=arm_mask
    fields['root']+=(1-arm_mask)*3*smooth(285,322,x)
    # The native renderer supports four bone influences per vertex.
    chosen = sorted(fields.items(), key=lambda v:v[1], reverse=True)[:4]
    total = sum(v for _,v in chosen)
    return [(names.index(n),v/total) for n,v in chosen]

# Add extra mesh rows/columns around the eyes; the rest of the silhouette is coarser.
xs = sorted(set([0,SIZE]+list(range(12,SIZE,14))+list(range(228,307,4))+list(range(140,375,6))))
ys = sorted(set([0,SIZE]+list(range(12,SIZE,14))+list(range(102,145,4))+list(range(228,305,6))))
uvs,vertices,triangles = [],[],[]
for y in ys:
    for x in xs:
        uvs += [round(x/SIZE,7),round(y/SIZE,7)]
        influences = weights(x,y)
        vertices.append(len(influences))
        wx,wy = x-SIZE/2,SIZE-y
        for index,weight in influences:
            bx,by = world[names[index]]
            vertices += [index,round(wx-bx,6),round(wy-by,6),round(weight,8)]
for row in range(len(ys)-1):
    for col in range(len(xs)-1):
        a = row*len(xs)+col; b=a+1; c=a+len(xs); d=c+1
        triangles += [a,c,b,b,c,d]

def timeline(points):
    """Spine 4.2 Bezier controls use absolute time/value coordinates."""
    result = []
    for i,(time,value) in enumerate(points):
        key = {'time':time,'value':value}
        if i+1<len(points):
            end,next_value = points[i+1]; dt=end-time
            key['curve']=[round(time+dt*.37,6),value,round(end-dt*.37,6),next_value]
        result.append(key)
    return result

def wave(amplitude,phase=0,base=0,duration=4.8):
    # Analytic samples, with exact end-to-start value and tangent continuity.
    keys=[]
    for i in range(17):
        t=duration*i/16
        angle=2*math.pi*i/16+phase
        value=base+amplitude*math.sin(angle)
        key={'time':round(t,6),'value':round(value,6)}
        if i<16:
            dt=duration/16; end=t+dt; angle2=angle+2*math.pi/16
            next_value=base+amplitude*math.sin(angle2)
            derivative=amplitude*2*math.pi/duration*math.cos(angle)
            derivative2=amplitude*2*math.pi/duration*math.cos(angle2)
            key['curve']=[round(t+dt/3,6),round(value+derivative*dt/3,6),
                          round(end-dt/3,6),round(next_value-derivative2*dt/3,6)]
        keys.append(key)
    return keys

idle = {'bones':{
    'root':{'translatex':wave(0),'translatey':wave(0),'rotate':wave(0)},
    'body':{'rotate':wave(.45), 'translatey':wave(1.25), 'scaley':wave(.006,base=1)},
    'chest':{'rotate':wave(.55,.45)}, 'head':{'rotate':wave(.7,.8)},
    'hair':{'rotate':wave(1.4,-.65)}, 'hair_tip':{'rotate':wave(2.5,-1.1)},
    'tail':{'rotate':wave(1.6,-1.15)}, 'tail_tip':{'rotate':wave(3.8,-1.65)},
    'arm_back':{'rotate':wave(.65,.7)}, 'arm_front':{'rotate':wave(.85,1.15)},
    'hand_back':{'rotate':wave(.5,-.45)}, 'hand_front':{'rotate':wave(.6,-.8)},
    'elbow_back':{'rotate':wave(.4,.8)}, 'elbow_front':{'rotate':wave(.5,1.1)},
    'wrist_back':{'rotate':wave(.65,-.7)}, 'wrist_front':{'rotate':wave(.8,-1)},
    'fingers_back':{'rotate':wave(.6,.9),'scaley':wave(.01,base=1)},
    'fingers_front':{'rotate':wave(.75,.6),'scaley':wave(.012,base=1)},
}}
blink = timeline([(0,1),(2.35,1),(2.43,.12),(2.48,.12),(2.6,1),(4.8,1)])
idle['bones']['eye_left']={'scaley':blink}
idle['bones']['eye_right']={'scaley':blink}

def action(duration,poses):
    animated={}
    # Explicit keys for every animated property restore pose and eyelid state.
    # This avoids leaving hair/arms from an interrupted action on the next track.
    for bone,tracks in idle['bones'].items():
        animated[bone]={kind:timeline([(0,1 if kind.startswith('scale') else 0),
                                      (duration,1 if kind.startswith('scale') else 0)]) for kind in tracks}
    for bone,tracks in poses.items():
        animated.setdefault(bone,{}).update({kind:timeline([(round(t*duration,6),value) for t,value in points]) for kind,points in tracks.items()})
    return {'bones':animated}

ATTACK=.52
animations={'idle_loop':idle}
animations['attack']=action(ATTACK,{
    'root':{'translatex':[(0,0),(.18,-5),(.46,35),(1,0)]},
    'body':{'rotate':[(0,0),(.18,2),(.46,-4),(1,0)]},
    'chest':{'rotate':[(0,0),(.18,1),(.46,-3),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.18,-5),(.46,15),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.18,-3),(.46,14),(1,0)],'translatey':[(0,0),(.46,11),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.26,4),(.58,-6),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.32,5),(.65,-6),(1,0)]},
})
animations['cast']=action(.75,{
    'chest':{'rotate':[(0,0),(.36,-1.8),(.65,-1.8),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.35,12),(.66,12),(1,0)]},
    'hand_front':{'translatey':[(0,0),(.35,14),(.66,14),(1,0)]},
    'head':{'rotate':[(0,0),(.4,1.4),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.4,-3),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.45,5),(1,0)]},
})
animations['guard']=action(.68,{
    'arm_front':{'rotate':[(0,0),(.3,9),(.7,9),(1,0)]},
    'arm_back':{'rotate':[(0,0),(.3,-5.6),(.7,-5.6),(1,0)]},
    'body':{'translatey':[(0,0),(.32,-3),(.7,-3),(1,0)]},
})
animations['channel']=action(1.05,{
    'chest':{'translatey':[(0,0),(.5,2),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.4,-6),(.7,-6),(1,0)]},
    'hand_back':{'translatex':[(0,0),(.4,6),(.7,6),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.3,5),(.65,-5),(1,0)]},
})
animations['hurt']=action(.4,{
    'root':{'translatex':[(0,0),(.28,-18),(1,0)]},
    'body':{'rotate':[(0,0),(.28,3.5),(1,0)]},
    'head':{'rotate':[(0,0),(.28,-3),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.4,7),(1,0)]},
})
animations['death']=action(.9,{
    'root':{'rotate':[(0,0),(.5,20),(1,58)],'translatey':[(0,0),(1,-8)]},
    'body':{'rotate':[(0,0),(1,4)],'translatey':[(0,0),(1,-3)]},
    'chest':{'rotate':[(0,0),(1,2)]},
    'head':{'rotate':[(0,0),(1,-7)]},
    'eye_left':{'scaley':[(0,1),(.5,.12),(1,.12)]},
    'eye_right':{'scaley':[(0,1),(.5,.12),(1,.12)]},
    'tail_tip':{'rotate':[(0,0),(1,-5)]},
})
animations['victory_loop']=action(2.4,{
    'body':{'translatey':[(0,0),(.25,2.5),(.5,0),(.75,2.5),(1,0)]},
    'arm_front':{'rotate':[(0,7),(.25,11),(.5,7),(.75,11),(1,7)]},
    'tail_tip':{'rotate':[(0,0),(.25,5),(.5,0),(.75,-5),(1,0)]},
})

# Longer idle cycles contain deliberate gestures over continuous breathing.
def idle_cycle(duration):
    # Copy per bone: the two eye timelines share the original blink list.
    # A whole-graph deepcopy would preserve that alias and retime it twice.
    result={'bones':{bone:copy.deepcopy(tracks) for bone,tracks in idle['bones'].items()}}
    factor=duration/4.8
    for tracks in result['bones'].values():
        for keys in tracks.values():
            for key in keys:
                key['time']=round(key['time']*factor,6)
                if 'curve' in key:
                    key['curve'][0]=round(key['curve'][0]*factor,6)
                    key['curve'][2]=round(key['curve'][2]*factor,6)
    # Keep breathing at a natural rate while the larger gesture cycle is longer.
    for bone,kind,amplitude,phase,base in [
        ('body','translatey',1.25,0,0),('body','scaley',.006,0,1),
        ('hair_tip','rotate',2.5,-1.1,0),('tail_tip','rotate',3.8,-1.65,0)]:
        keys=[]
        for repeat in range(2):
            part=wave(amplitude,phase,base,duration/2)
            for key in part:
                key['time']=round(key['time']+repeat*duration/2,6)
                if 'curve' in key:
                    key['curve'][0]=round(key['curve'][0]+repeat*duration/2,6)
                    key['curve'][2]=round(key['curve'][2]+repeat*duration/2,6)
            keys.extend(part[:-1] if repeat==0 else part)
        result['bones'][bone][kind]=keys
    return result

def gesture(clip,bone,kind,points):
    clip['bones'].setdefault(bone,{})[kind]=timeline(points)

look=idle_cycle(8.4)
gesture(look,'head','rotate',[(0,0),(1.5,0),(2.2,2.2),(2.8,2.2),(3.5,0),(5.4,0),(6.1,-1.6),(6.7,-1.6),(7.5,0),(8.4,0)])
gesture(look,'hand_front','rotate',[(0,0),(1.8,0),(2.5,3.5),(3.3,0),(8.4,0)])
animations['idle_look_loop']=look
ready=idle_cycle(7.2)
gesture(ready,'arm_front','rotate',[(0,2),(1.6,2),(2.2,5),(3.1,2),(5.2,2),(5.8,4),(6.5,2),(7.2,2)])
gesture(ready,'chest','rotate',[(0,-.5),(1.8,-.5),(2.8,-1.5),(3.6,-.5),(7.2,-.5)])
animations['idle_ready_loop']=ready
relax=idle_cycle(9.6)
gesture(relax,'head','rotate',[(0,0),(2.4,0),(3.2,-1.6),(3.8,-1.6),(4.5,0),(9.6,0)])
gesture(relax,'hand_back','rotate',[(0,0),(4.8,0),(5.5,-3.5),(6.3,0),(9.6,0)])
gesture(relax,'tail','rotate',[(0,0),(5.1,0),(5.7,2),(6.25,-1.7),(6.9,1),(7.5,0),(9.6,0)])
animations['idle_relax_loop']=relax

animations['attack_sweep']=action(.66,{
    'root':{'translatex':[(0,0),(.2,-6),(.5,27),(.72,17),(1,0)]},
    'body':{'rotate':[(0,0),(.2,2.5),(.5,-3),(.72,-1),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.22,-4),(.5,12),(.76,5),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.5,11),(1,0)],'translatey':[(0,0),(.28,7),(.58,2),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.32,4),(.62,-5),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.3,5),(.7,-5),(1,0)]},
})
animations['attack_double']=action(.84,{
    'root':{'translatex':[(0,0),(.14,-3),(.32,22),(.46,9),(.66,32),(1,0)]},
    'chest':{'rotate':[(0,0),(.32,-2),(.46,1),(.66,-3),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.32,10),(.46,2),(.66,14),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.32,10),(.46,0),(.66,14),(1,0)]},
    'hand_back':{'rotate':[(0,0),(.34,-2),(.58,3),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.35,4),(.7,-5),(1,0)]},
})
animations['attack_ranged']=action(.8,{
    'root':{'translatex':[(0,0),(.25,-2),(.48,9),(.62,4),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.3,10),(.52,14),(.7,8),(1,0)]},
    'hand_front':{'translatey':[(0,0),(.3,10),(.52,13),(1,0)],'translatex':[(0,0),(.5,10),(1,0)]},
    'head':{'rotate':[(0,0),(.3,1),(.55,-1),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.38,-2),(.6,5),(1,0)]},
})
animations['cast_arc']=action(.95,{
    'hand_front':{'translatey':[(0,0),(.25,7),(.5,14),(.7,7),(1,0)],'translatex':[(0,0),(.3,-3),(.6,7),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.25,5),(.5,11),(.7,6),(1,0)]},
    'arm_back':{'rotate':[(0,0),(.4,-3),(.65,2),(1,0)]},
    'head':{'rotate':[(0,0),(.4,1.8),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.3,4),(.65,-4),(1,0)]},
})
animations['cast_release']=action(.92,{
    'chest':{'translatey':[(0,0),(.3,1.6),(.62,0),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.3,4),(.55,13),(.75,7),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.3,-3),(.55,11),(1,0)],'translatey':[(0,0),(.55,10),(1,0)]},
    'head':{'rotate':[(0,0),(.3,-1),(.6,1),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.35,3),(.65,-4),(1,0)]},
})
animations['guard_brace']=action(.9,{
    'root':{'translatex':[(0,0),(.25,-4),(.5,-6),(.7,-3),(1,0)]},
    'body':{'translatey':[(0,0),(.25,-2),(.5,-4),(.7,-2),(1,0)]},
    'arm_front':{'rotate':[(0,0),(.25,7),(.5,11),(.7,7),(1,0)]},
    'arm_back':{'rotate':[(0,0),(.25,-4.2),(.5,-6.3),(.7,-4.2),(1,0)]},
    'head':{'rotate':[(0,0),(.4,-1.2),(1,0)]},
})
animations['channel_release']=action(1.25,{
    'chest':{'translatey':[(0,0),(.25,1),(.55,2.2),(.72,-.6),(1,0)]},
    'hand_front':{'translatex':[(0,0),(.3,-5),(.55,-6),(.75,6),(1,0)],'translatey':[(0,0),(.55,5),(1,0)]},
    'hand_back':{'translatex':[(0,0),(.3,5),(.55,6),(.75,-2),(1,0)]},
    'head':{'rotate':[(0,0),(.45,-1.8),(.75,.8),(1,0)]},
    'eye_left':{'scaley':[(0,1),(.2,.35),(.55,.35),(.72,1),(1,1)]},
    'eye_right':{'scaley':[(0,1),(.2,.35),(.55,.35),(.72,1),(1,1)]},
    'tail_tip':{'rotate':[(0,0),(.3,4),(.55,-4),(.8,3),(1,0)]},
})
animations['hurt_recover']=action(.62,{
    'root':{'translatex':[(0,0),(.2,-16),(.42,-10),(.7,2),(1,0)]},
    'body':{'rotate':[(0,0),(.2,3),(.45,1.5),(.72,-.6),(1,0)]},
    'head':{'rotate':[(0,0),(.22,-2.5),(.5,-1),(.8,.8),(1,0)]},
    'hair_tip':{'rotate':[(0,0),(.32,5),(.62,-2),(1,0)]},
})
animations['greeting']=action(1.35,{
    'body':{'rotate':[(0,0),(.3,-1.5),(.55,-1.5),(.78,.5),(1,0)]},
    'head':{'rotate':[(0,0),(.3,-3),(.55,-3),(.8,1),(1,0)]},
    'hand_front':{'rotate':[(0,0),(.3,4),(.55,4),(.8,-1),(1,0)]},
    'eye_left':{'scaley':[(0,1),(.3,.35),(.55,.35),(.8,1),(1,1)]},
    'eye_right':{'scaley':[(0,1),(.3,.35),(.55,.35),(.8,1),(1,1)]},
})
meditate=idle_cycle(8.4)
gesture(meditate,'eye_left','scaley',[(0,.12),(8.4,.12)])
gesture(meditate,'eye_right','scaley',[(0,.12),(8.4,.12)])
gesture(meditate,'hand_front','translatex',[(0,-4),(2.1,-5),(4.2,-4),(6.3,-5),(8.4,-4)])
gesture(meditate,'hand_back','translatex',[(0,4),(2.1,5),(4.2,4),(6.3,5),(8.4,4)])
animations['meditate_loop']=meditate
animations['victory_wave_loop']=action(3.6,{
    'body':{'translatey':[(0,0),(.2,3),(.4,0),(.65,2),(1,0)]},
    'head':{'rotate':[(0,0),(.25,1.8),(.55,-1),(1,0)]},
    'arm_front':{'rotate':[(0,7),(.2,11),(.4,7),(.65,11),(1,7)]},
    'hand_front':{'rotate':[(0,0),(.25,3),(.45,-2),(.7,2),(1,0)]},
    'tail_tip':{'rotate':[(0,0),(.25,5),(.5,0),(.75,-5),(1,0)]},
})

# 0.6: independently articulate shoulder, elbow, wrist, palm and fingertips.
# Reference observation: hunter's attack is ~0.57s, with a short early impulse
# and a longer recovery. All curves below are authored for this character.
attack_profiles={
    'attack':(.57,[0,.12,.28,.34,.52,.78,1]),
    'attack_sweep':(.63,[0,.15,.31,.39,.58,.82,1]),
    'attack_double':(.82,[0,.10,.24,.36,.52,.60,.78,1]),
    'attack_ranged':(.72,[0,.18,.37,.46,.62,.84,1]),
}
for clip,(duration,phases) in attack_profiles.items():
    if clip=='attack_double':
        root=[0,-3,16,5,24,19,5,0]
        arm=[0,-5,12,1,15,8,2,0]
        elbow=[0,-4,10,-1,12,6,1,0]
        wrist=[0,-8,13,-5,17,5,-2,0]
        reach=[0,-6,18,1,27,18,4,0]
        lift=[0,3,14,5,20,12,3,0]
        fingers=[1,.82,.96,.83,.94,.98,1,1]
    elif clip=='attack_sweep':
        root=[0,-4,20,17,9,2,0]
        arm=[0,-6,14,11,5,1,0]
        elbow=[0,-4,8,6,3,0,0]
        wrist=[0,-10,18,11,1,-3,0]
        reach=[0,-6,25,21,12,2,0]
        lift=[0,5,22,14,4,0,0]
        fingers=[1,.82,.94,.98,1,1,1]
    elif clip=='attack_ranged':
        root=[0,-2,7,6,2,0,0]
        arm=[0,2,13,12,6,1,0]
        elbow=[0,-3,9,8,4,0,0]
        wrist=[0,-5,13,10,2,-1,0]
        reach=[0,-4,20,18,8,1,0]
        lift=[0,5,20,17,6,1,0]
        fingers=[1,.9,1.06,1.04,1,1,1]
    else:
        root=[0,-4,22,21,11,2,0]
        arm=[0,-6,16,13,6,1,0]
        elbow=[0,-5,11,9,4,1,0]
        wrist=[0,-9,17,13,3,-2,0]
        reach=[0,-7,28,25,13,2,0]
        lift=[0,2,18,15,6,1,0]
        fingers=[1,.8,.94,.98,1,1,1]
    # A continuous illustration needs a broad, modest deformation field around
    # the forearm. Keep the silhouette welded instead of dragging the palm away.
    arm=[v*.6 for v in arm]
    elbow=[v*.45 for v in elbow]
    wrist=[v*.45 for v in wrist]
    reach=[v*.4 for v in reach]
    lift=[v*.45 for v in lift]
    points=lambda values:list(zip(phases,values))
    animations[clip]=action(duration,{
        'root':{'translatex':points(root)},
        'body':{'rotate':points([v*-.12 for v in root])},
        'chest':{'rotate':points([v*-.08 for v in root])},
        'arm_front':{'rotate':points(arm)},
        'elbow_front':{'rotate':points(elbow)},
        'wrist_front':{'rotate':points(wrist)},
        'hand_front':{'translatex':points(reach),'translatey':points(lift),'rotate':points([v*.32 for v in wrist])},
        'fingers_front':{'scaley':points(fingers),'rotate':points([v*.26 for v in wrist])},
        'arm_back':{'rotate':points([v*-.22 for v in arm])},
        'elbow_back':{'rotate':points([v*.25 for v in elbow])},
        'wrist_back':{'rotate':points([v*-.2 for v in wrist])},
        'hand_back':{'translatey':points([v*.3 for v in lift])},
        'hair_tip':{'rotate':[(min(1,t+.06) if t not in (0,1) else t,v*.18) for t,v in zip(phases,root)]},
        'tail_tip':{'rotate':[(min(1,t+.09) if t not in (0,1) else t,v*-.2) for t,v in zip(phases,root)]},
    })

for name in ['cast','cast_arc','cast_release','channel','channel_release']:
    clip=animations[name]
    duration=max(keys[-1]['time'] for tracks in clip['bones'].values() for keys in tracks.values())
    # Keep the two hands in distinct roles: the back hand supports the charge;
    # the front hand rises, turns outward, opens and settles after release.
    for bone,kind,values in [
        ('elbow_front','rotate',[(0,0),(.25,-3),(.58,7),(.76,4),(1,0)]),
        ('wrist_front','rotate',[(0,0),(.25,-7),(.58,12),(.76,5),(1,0)]),
        ('fingers_front','scaley',[(0,1),(.25,.86),(.58,1.08),(.76,1.02),(1,1)]),
        ('wrist_back','rotate',[(0,0),(.25,5),(.58,-4),(.76,-2),(1,0)]),
        ('fingers_back','scaley',[(0,1),(.25,.91),(.58,1.02),(1,1)]),
    ]:
        if bone.endswith('_back'):
            values=[(t,value*.55) for t,value in values]
        gesture(clip,bone,kind,[(round(t*duration,6),value) for t,value in values])

for name in ['guard','guard_brace']:
    clip=animations[name]
    duration=max(keys[-1]['time'] for tracks in clip['bones'].values() for keys in tracks.values())
    for bone,kind,values in [
        ('elbow_front','rotate',[(0,0),(.2,5),(.48,7),(.7,4),(1,0)]),
        ('elbow_back','rotate',[(0,0),(.2,-4),(.48,-6),(.7,-3),(1,0)]),
        ('wrist_front','rotate',[(0,0),(.2,-6),(.48,-8),(.7,-4),(1,0)]),
        ('wrist_back','rotate',[(0,0),(.2,6),(.48,8),(.7,4),(1,0)]),
        ('hand_front','translatey',[(0,0),(.2,8),(.48,12),(.7,7),(1,0)]),
        ('hand_back','translatey',[(0,0),(.2,6),(.48,10),(.7,6),(1,0)]),
        ('fingers_front','scaley',[(0,1),(.2,.88),(.48,.88),(.7,.95),(1,1)]),
    ]:
        if bone.endswith('_back'):
            values=[(t,value*.55) for t,value in values]
        gesture(clip,bone,kind,[(round(t*duration,6),value) for t,value in values])

for name in ['hurt','hurt_recover']:
    clip=animations[name]
    duration=max(keys[-1]['time'] for tracks in clip['bones'].values() for keys in tracks.values())
    for bone,kind,values in [
        ('elbow_front','rotate',[(0,0),(.18,-4),(.4,-2),(.7,1),(1,0)]),
        ('wrist_front','rotate',[(0,0),(.18,-8),(.4,-3),(.7,2),(1,0)]),
        ('wrist_back','rotate',[(0,0),(.18,6),(.4,3),(.7,-1),(1,0)]),
    ]:
        gesture(clip,bone,kind,[(round(t*duration,6),value) for t,value in values])

for name in ['idle_look_loop','idle_ready_loop','idle_relax_loop','meditate_loop','victory_wave_loop','greeting']:
    clip=animations[name]
    duration=max(keys[-1]['time'] for tracks in clip['bones'].values() for keys in tracks.values())
    amplitude=3.0 if name=='victory_wave_loop' else 1.2
    clip['bones']['wrist_front']={'rotate':wave(amplitude,.6,duration=duration)}
    clip['bones']['wrist_back']={'rotate':wave(amplitude*.65,-.8,duration=duration)}
    clip['bones']['fingers_front']={'rotate':wave(amplitude*.6,1.1,duration=duration),'scaley':wave(.035,.4,base=1,duration=duration)}

mesh={'type':'mesh','path':'maid','width':SIZE,'height':SIZE,
      'uvs':uvs,'triangles':triangles,'vertices':vertices}
document={
    'skeleton':{'spine':'4.2.43','x':-SIZE/2,'y':0,'width':SIZE,'height':SIZE,'fps':60,'images':'./'},
    'bones':bones,'slots':[{'name':'character','bone':'root','attachment':'maid'}],
    'skins':[{'name':'default','attachments':{'character':{'maid':mesh}}}],
    'animations':animations,
}
(OUT/'maid.spine-json').write_text(json.dumps(document,separators=(',',':')),encoding='utf-8')
(ROOT/'preview/rig-data.js').write_text('const RIG_DATA='+json.dumps(document,separators=(',',':'))+';\n',encoding='utf-8')
# A data URL keeps the local-file WebGL preview origin-clean without a server.
encoded=base64.b64encode((ROOT/'assets/sprites/deepseek-poses-v0.3.png').read_bytes()).decode('ascii')
(ROOT/'preview/rig-texture.js').write_text('const RIG_TEXTURE="data:image/png;base64,'+encoded+'";\n',encoding='utf-8')
(OUT/'maid.atlas').write_text('''deepseek-poses-v0.3.png
size: 1774,887
format: RGBA8888
filter: Linear,Linear
repeat: none
pma: false
maid
  rotate: false
  xy: 0,0
  size: 443,443
  orig: 443,443
  offset: 0,0
  index: -1
''',encoding='utf-8')
print(f'Authored {len(bones)} original bones, {len(uvs)//2} weighted vertices, {len(triangles)//3} triangles, {len(animations)} continuous animations.')
