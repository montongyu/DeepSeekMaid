"""Original layered Spine puppet. Art is image_gen cutouts, curves are authored here."""
if __name__=='__main__':
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name('unified_rig.py')),run_name='__main__')
    raise SystemExit(0)

# Historical implementation below; the runnable entry now uses unified_rig.py.
import base64
import copy
import json
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'assets/animation';OUT.mkdir(exist_ok=True)
SIZE=443
# All bone positions are in character space, feet on y=0. Bind rotations are zero.
positions={
    'root':(0,0),'body':(0,211),'chest':(0,324),'head':(0,340),
    'hair':(0,395),'hair_tip':(0,221),'tail':(58,130),'tail_tip':(151,236),
    'skirt':(0,280),'skirt_hem':(0,143),'leg_back':(-21,149),'leg_front':(21,149),
    'arm_back':(-42,333),'elbow_back':(-42,289),'wrist_back':(-42,247),'hand_back':(-42,247),
    'arm_front':(42,333),'elbow_front':(42,289),'wrist_front':(42,247),'hand_front':(42,247),
    'prone':(38,0),
}
parents={'body':'root','chest':'body','head':'chest','hair':'head','hair_tip':'hair',
         'tail':'body','tail_tip':'tail','skirt':'body','skirt_hem':'skirt',
         'leg_back':'root','leg_front':'root','arm_back':'chest','arm_front':'chest',
         'elbow_back':'arm_back','elbow_front':'arm_front','wrist_back':'elbow_back',
         'wrist_front':'elbow_front','hand_back':'wrist_back','hand_front':'wrist_front','prone':'root'}
names=list(positions); bones=[]
for name,(x,y) in positions.items():
    px,py=positions.get(parents.get(name),(0,0))
    b={'name':name,'x':x-px,'y':y-py}
    if name in parents:b['parent']=parents[name]
    bones.append(b)

# Atlas rectangles select separate painted parts; pixels/alpha are never repainted.
sheet='portrait-body-v0.8-final.png'
arms='portrait-arms-v0.8-final.png'
regions={
    'hair_back':(sheet,(917,512,277,286)), 'torso':(sheet,(99,517,195,254)),
    'head_normal':(sheet,(51,91,324,282)), 'head_closed':(sheet,(473,93,323,280)),
    'head_focus':(sheet,(888,91,318,283)), 'head_angry':(sheet,(888,91,318,283)),
    'upper_back':(arms,(135,88,215,346)), 'upper_front':(arms,(150,510,220,343)),
    'fore_back':(arms,(559,92,146,339)), 'fore_front':(arms,(546,505,150,345)),
    'palm_back':(arms,(949,129,147,284)), 'palm_front':(arms,(939,547,139,289)),
    'casting_front':(arms,(132,936,254,278)),
    'fist_front':(arms,(544,956,162,220)), 'fist_back':(arms,(927,952,151,227)),
    'leg_back':(sheet,(178,879,94,300)), 'leg_front':(sheet,(593,883,89,297)),
    'skirt':(sheet,(438,531,380,260)), 'tail':(sheet,(927,910,264,269)),
    'prone':('portrait-prone-v0.8.png',(0,0,1,1)),
}
# Locate the whole prone painting; only the largest painted component defines
# the atlas rectangle, so stray transparent-margin speckles are not framed.
import cv2
import numpy as np
prone_image=np.array(Image.open(ROOT/'assets/sprites/portrait-prone-v0.8.png'))
stats=cv2.connectedComponentsWithStats((prone_image[:,:,3]>96).astype('uint8'))[2][1:]
regions['prone']=('portrait-prone-v0.8.png',tuple(int(v) for v in max(stats,key=lambda s:s[4])[:4]))
pages={}
for name,(file,rect) in regions.items():pages.setdefault(file,[]).append((name,rect))
atlas=[]
for file,entries in pages.items():
    w,h=Image.open(ROOT/'assets/sprites'/file).size
    atlas.extend([file,f'size: {w},{h}','format: RGBA8888','filter: Linear,Linear','repeat: none','pma: false'])
    for name,(x,y,w,h) in entries:
        atlas.extend([name,'  rotate: false',f'  xy: {x},{y}',f'  size: {w},{h}',f'  orig: {w},{h}','  offset: 0,0','  index: -1'])
    atlas.append('')
(OUT/'maid.atlas').write_text('\n'.join(atlas),encoding='utf-8')

slots=[];attachments={}
def part(slot,bone,region,width,height,cx=0,cy=0,secondary=None,cols=1,rows=1,mirror=False,default=True,attachment_name=None,reverse_weights=False):
    attachment_name=attachment_name or region
    if slot not in attachments:
        slots.append({'name':slot,'bone':bone,'attachment':attachment_name if default else None})
        attachments[slot]={}
    uv=[];verts=[];tris=[]
    for row in range(rows+1):
        v=row/rows
        for col in range(cols+1):
            u=col/cols;uv.extend([1-u if mirror else u,v])
            wx=positions[bone][0]+cx+(u-.5)*width
            wy=positions[bone][1]+cy+(.5-v)*height
            influences=[(bone,1)]
            if secondary:
                t=max(0,min(1,((1-v if reverse_weights else v)-.2)/.7));t=t*t*(3-2*t)
                influences=[(bone,1-t),(secondary,t)]
            influences=[(b,w) for b,w in influences if w>0]
            verts.append(len(influences))
            for b,w in influences:
                bx,by=positions[b];verts.extend([names.index(b),round(wx-bx,6),round(wy-by,6),round(w,8)])
    for row in range(rows):
        for col in range(cols):
            a=row*(cols+1)+col;b=a+1;c=a+cols+1;d=c+1;tris.extend([a,c,b,b,c,d])
    source_w,source_h=regions[region][1][2:]
    attachments[slot][attachment_name]={'type':'mesh','path':region,'width':source_w,'height':source_h,'uvs':uv,'triangles':tris,'vertices':verts}

# Ordered painter layers, with arm joints overlapping underneath their sleeve caps.
part('hair_back','hair','hair_back',228,247,0,-112,'hair_tip',6,10)
part('tail','tail','tail',168,171,84,85.5,'tail_tip',6,8,reverse_weights=True)
part('leg_back','leg_back','leg_back',40,154,0,-72)
part('leg_front','leg_front','leg_front',40,154,0,-72)
part('upper_back','arm_back','upper_back',28,48,0,-20)
part('torso','chest','torso',81,99,0,-20)
part('skirt','skirt','skirt',228,161,0,-73.5,'skirt_hem',8,6)
for region in ['head_normal','head_closed','head_focus','head_angry']:
    part('head','head',region,126,110,0,48)
part('upper_front','arm_front','upper_front',29,48,0,-20)
part('fore_back','elbow_back','fore_back',20,47,0,-21)
part('hand_back','hand_back','palm_back',14,27,0,-10)
part('hand_back','hand_back','fist_back',16,23,0,-8,attachment_name='fist')
part('fore_front','elbow_front','fore_front',20,47,0,-21)
part('hand_front','hand_front','palm_front',14,27,0,-10)
part('hand_front','hand_front','casting_front',25,27,0,-10,attachment_name='cast_palm')
part('hand_front','hand_front','fist_front',17,23,0,-8,attachment_name='fist')
prone_rect=regions['prone'][1];prone_height=480*prone_rect[3]/prone_rect[2]
part('prone','prone','prone',480,prone_height,-5,prone_height/2,default=False)

def timeline(points):
    result=[]
    for i,(t,v) in enumerate(points):
        key={'time':round(t,6),'value':round(v,6)}
        if i+1<len(points):
            end,next_value=points[i+1];dt=end-t
            key['curve']=[round(t+dt*.34,6),round(v,6),round(end-dt*.34,6),round(next_value,6)]
        result.append(key)
    return result

def wave(amp,phase=0,base=0,duration=5,cycles=1):
    keys=[];omega=2*math.pi*cycles/duration
    for i in range(33):
        t=duration*i/32;a=omega*t+phase;v=base+amp*math.sin(a)
        key={'time':round(t,6),'value':round(v,6)}
        if i<32:
            dt=duration/32;v2=base+amp*math.sin(a+omega*dt)
            key['curve']=[round(t+dt/3,6),round(v+amp*omega*math.cos(a)*dt/3,6),round(t+dt*2/3,6),round(v2-amp*omega*math.cos(a+omega*dt)*dt/3,6)]
        keys.append(key)
    return keys

neutral={'arm_front':18,'elbow_front':-12,'wrist_front':-6,'arm_back':-18,'elbow_back':12,'wrist_back':6}
def default_slots(duration,blink=False):
    result={}
    for slot in slots:
        name=slot['name'];attachment=slot.get('attachment')
        result[name]={'attachment':[{'time':0,'name':attachment}],
                      'rgba':[{'time':0,'color':'ffffffff'},{'time':duration,'color':'ffffffff'}]}
    if blink:
        result['head']['attachment']=[{'time':0,'name':'head_normal'},{'time':round(duration*.46,6),'name':'head_closed'},
                                     {'time':round(duration*.46+.11,6),'name':'head_normal'}]
    return result

def action(duration,poses=None,hands='open',face='head_normal'):
    clip={'bones':{},'slots':default_slots(duration)}
    for b in names:
        clip['bones'][b]={k:timeline([(0,neutral.get(b,0) if k=='rotate' else 1 if k.startswith('scale') else 0),
                                      (duration,neutral.get(b,0) if k=='rotate' else 1 if k.startswith('scale') else 0)])
                            for k in ['rotate','translatex','translatey','scalex','scaley']}
    for b,tracks in (poses or {}).items():
        for kind,values in tracks.items():
            clip['bones'][b][kind]=timeline([(p*duration,v) for p,v in values])
    if hands=='fist':
        for slot in ['hand_back','hand_front']:clip['slots'][slot]['attachment']=[{'time':0,'name':'fist'}]
    if hands=='cast':clip['slots']['hand_front']['attachment']=[{'time':0,'name':'cast_palm'}]
    clip['slots']['head']['attachment']=[{'time':0,'name':face}]
    return clip

def idle(duration=6,mood='neutral'):
    clip=action(duration);clip['slots']=default_slots(duration,True)
    for b,a,p in [('body',.7,0),('chest',.9,.5),('head',1.6,.9),('hair',1.1,-.4),('hair_tip',3.8,-1),
                   ('tail',2.5,-.7),('tail_tip',5,-1.4),('skirt',.7,-.3),('skirt_hem',1.7,-.7),
                   ('arm_front',1.7,.8),('arm_back',1.4,-.6),('elbow_front',1.8,1.1),('elbow_back',1.4,-1),
                   ('wrist_front',3.5,-.8),('wrist_back',2.7,.6)]:
        clip['bones'][b]['rotate']=wave(a,p,neutral.get(b,0),duration,2 if duration>=8 else 1)
    clip['bones']['body']['translatey']=wave(1.8,0,duration=duration,cycles=2 if duration>=8 else 1)
    if mood=='ready':
        for b,value in [('arm_front',35),('elbow_front',-75),('arm_back',-28),('elbow_back',72)]:
            clip['bones'][b]['rotate']=wave(2,.6,value,duration)
        for slot in ['hand_back','hand_front']:clip['slots'][slot]['attachment']=[{'time':0,'name':'fist'}]
    if mood=='angry':
        clip['slots']['head']['attachment']=[{'time':0,'name':'head_angry'}]
        clip['bones']['head']['rotate']=wave(1.5,.4,-3,duration)
        for b,value in [('arm_front',22),('elbow_front',-62),('arm_back',-22),('elbow_back',60)]:
            clip['bones'][b]['rotate']=wave(2,0,value,duration)
        for slot in ['hand_back','hand_front']:clip['slots'][slot]['attachment']=[{'time':0,'name':'fist'}]
    return clip

anims={
    'idle_loop':idle(6), 'idle_look_loop':idle(8), 'idle_ready_loop':idle(5,'ready'),
    'idle_relax_loop':idle(9),'idle_breathe_loop':idle(7), 'idle_hair_loop':idle(8),
    'idle_hand_loop':idle(7),'idle_tail_loop':idle(8),'idle_angry_loop':idle(4,'angry'),
}
def set_track(clip,bone,kind,points):
    d=max(k[-1]['time'] for ts in clip['bones'].values() for k in ts.values())
    clip['bones'][bone][kind]=timeline([(t*d,v) for t,v in points])
set_track(anims['idle_look_loop'],'head','rotate',[(0,0),(.18,0),(.3,9),(.42,9),(.56,0),(.72,-7),(.84,0),(1,0)])
set_track(anims['idle_hair_loop'],'arm_back','rotate',[(0,-18),(.18,-18),(.32,-75),(.62,-75),(.8,-18),(1,-18)])
set_track(anims['idle_hair_loop'],'elbow_back','rotate',[(0,12),(.18,12),(.32,132),(.62,126),(.8,12),(1,12)])
set_track(anims['idle_hand_loop'],'arm_front','rotate',[(0,18),(.2,18),(.35,60),(.6,60),(.8,18),(1,18)])
set_track(anims['idle_hand_loop'],'elbow_front','rotate',[(0,-12),(.2,-12),(.35,-95),(.6,-95),(.8,-12),(1,-12)])
set_track(anims['idle_hand_loop'],'wrist_front','rotate',[(0,-6),(.35,-6),(.42,15),(.5,-15),(.58,12),(.72,-6),(1,-6)])
anims['idle_tail_loop']['bones']['tail_tip']['rotate']=wave(14,0,duration=8,cycles=2)
anims['idle_breathe_loop']['bones']['chest']['scaley']=wave(.018,0,1,7)

# Each attack has distinct shoulder/elbow geometry, not merely different timing.
# values are absolute local angles; a positive shoulder angle extends a right arm forward.
profiles={
 'attack':(.58,[0,.13,.29,.38,.7,1],[18,-12,85,80,35,18],[-12,-105,-10,-8,-35,-12]),
 'attack_jab':(.48,[0,.1,.26,.34,.66,1],[18,8,70,68,30,18],[-12,-88,4,4,-28,-12]),
 'attack_cross':(.66,[0,.18,.36,.44,.74,1],[18,-30,92,87,32,18],[-12,-112,-2,-6,-40,-12]),
 'attack_sweep':(.72,[0,.15,.34,.5,.75,1],[18,-38,112,68,28,18],[-12,-72,-22,16,-32,-12]),
 'attack_uppercut':(.7,[0,.17,.34,.43,.72,1],[18,-18,140,133,43,18],[-12,-65,-45,-38,-55,-12]),
 'attack_double':(.83,[0,.1,.23,.35,.5,.61,.8,1],[18,4,82,12,94,65,28,18],[-12,-92,-5,-85,2,-12,-30,-12]),
 'attack_triple':(1.02,[0,.08,.19,.29,.4,.5,.62,.7,.86,1],[18,2,73,10,88,3,102,75,28,18],[-12,-90,-2,-85,6,-94,2,-8,-32,-12]),
 'attack_ranged':(.76,[0,.2,.46,.56,.8,1],[18,35,80,83,38,18],[-12,-110,-6,-6,-35,-12]),
 'attack_palm':(.68,[0,.17,.36,.46,.76,1],[18,-12,95,90,35,18],[-12,-100,-12,-10,-40,-12]),
 'attack_overhead':(.84,[0,.2,.39,.52,.77,1],[18,160,155,62,28,18],[-12,-55,-15,-5,-35,-12]),
}
for name,(duration,phases,arm,elbow) in profiles.items():
    n=len(phases);peak=max(range(n),key=lambda i:arm[i] if name!='attack_overhead' else i==3)
    impulse=[0]*n
    for i in range(1,n-1):impulse[i]=-4 if arm[i]<30 else min(28,(arm[i]-18)*.26)
    if name=='attack_overhead':impulse=[0,-3,-2,26,8,0]
    pts=lambda vs:list(zip(phases,vs))
    anims[name]=action(duration,{
        'root':{'translatex':pts(impulse),'translatey':pts([max(0,v)*.13 for v in impulse])},
        'body':{'rotate':pts([-v*.13 for v in impulse])},
        'chest':{'rotate':pts([-v*.16 for v in impulse])},
        'arm_front':{'rotate':pts(arm)},'elbow_front':{'rotate':pts(elbow)},
        'wrist_front':{'rotate':pts([-6]+[-15 if a>60 else 12 for a in arm[1:-1]]+[-6])},
        'arm_back':{'rotate':pts([-18]+[-36 if a>60 else -18 for a in arm[1:-1]]+[-18])},
        'elbow_back':{'rotate':pts([12]+[80 if a>60 else 35 for a in arm[1:-1]]+[12])},
        'skirt_hem':{'rotate':pts([v*.16 for v in impulse])},
        'hair_tip':{'rotate':[(min(1,t+.06) if t not in (0,1) else t,-v*.3) for t,v in zip(phases,impulse)]},
        'tail_tip':{'rotate':[(min(1,t+.08) if t not in (0,1) else t,v*.45) for t,v in zip(phases,impulse)]},
    },hands='cast' if name in ['attack_ranged','attack_palm'] else 'fist',face='head_angry' if name=='attack_palm' else 'head_focus')
    if name in ['attack_cross','attack_double','attack_triple']:
        # The rear arm supplies the alternating blows, at a different phase.
        vals=[-18 if i in (0,n-1) else -72 if i%2 else 68 for i in range(n)]
        anims[name]['bones']['arm_back']['rotate']=timeline([(t*duration,v) for t,v in zip(phases,vals)])
        anims[name]['bones']['elbow_back']['rotate']=timeline([(t*duration,12 if i in (0,n-1) else 5 if i%2==0 else 100) for i,t in enumerate(phases)])

def gesture(duration,front,elbow,back=-28,back_elbow=75,face='head_normal',hands='cast'):
    phase=[0,.22,.46,.64,.78,1]
    track=lambda base,peak:list(zip(phase,[base,peak*.55+base*.45,peak,peak,base*.7+peak*.3,base]))
    return action(duration,{
        'arm_front':{'rotate':track(18,front)},'elbow_front':{'rotate':track(-12,elbow)},
        'arm_back':{'rotate':track(-18,back)},'elbow_back':{'rotate':track(12,back_elbow)},
        'wrist_front':{'rotate':track(-6,-22)},'wrist_back':{'rotate':track(6,20)},
        'head':{'rotate':track(0,-4)},'body':{'translatey':track(0,3)},
        'skirt_hem':{'rotate':track(0,2)},'hair_tip':{'rotate':track(0,-5)},'tail_tip':{'rotate':track(0,7)},
    },hands,face)

for name,duration,f,e,b,be in [
 ('cast',.9,82,-8,-32,82),('cast_arc',1,140,-45,-28,78),('cast_release',.86,100,-5,-22,80),
 ('cast_dual',1.05,110,-25,-110,25),('cast_point',.82,65,16,-18,70),('cast_circle',1.1,125,-75,-80,95),
 ('guard',.7,10,-130,-10,130),('guard_brace',.84,32,-125,-35,120),('guard_raise',.8,85,-95,-70,110),
 ('guard_cross',.85,-8,-120,8,120),('guard_push',.84,80,-10,-65,20),
 ('channel',1.15,28,-115,-28,115),('channel_release',1.25,115,-28,-110,32),
 ('channel_gather',1.2,-25,-100,25,100),('channel_pulse',1.05,82,-42,-82,42),
 ('channel_overdrive',1.35,155,-25,-155,25),
]:
    anims[name]=gesture(duration,f,e,b,be,face='head_angry' if name.endswith('overdrive') else 'head_normal')
    if name.startswith('guard'):
        set_track(anims[name],'body','rotate',[(0,0),(.22,3),(.5,3),(.76,1),(1,0)])
        set_track(anims[name],'root','translatex',[(0,0),(.22,-5),(.5,-5),(.76,-2),(1,0)])
    if name in ['cast_arc','cast_circle','channel_pulse']:
        set_track(anims[name],'wrist_front','rotate',[(0,-6),(.3,-45),(.5,35),(.67,-20),(.8,12),(1,-6)])

# Hurt remains upright: a short recoil, feet planted, then an annoyed recovery.
for i,name in enumerate(['hurt','hurt_recover','hurt_recoil','hurt_stagger','hurt_counter']):
    d=[.32,.4,.36,.44,.5][i]
    anims[name]=action(d,{
        'root':{'translatex':[(0,0),(.18,-7-i),(.4,-3),(.7,1),(1,0)]},
        'body':{'rotate':[(0,0),(.18,2.5),(.42,1),(1,0)]},
        'head':{'rotate':[(0,0),(.2,2),(.5,-4),(1,-2)]},
        'arm_front':{'rotate':[(0,18),(.18,8),(.48,30),(1,26)]},
        'elbow_front':{'rotate':[(0,-12),(.18,-28),(.5,-70),(1,-62)]},
        'arm_back':{'rotate':[(0,-18),(.2,-12),(.5,-27),(1,-22)]},
        'elbow_back':{'rotate':[(0,12),(.2,24),(.5,70),(1,60)]},
        'tail_tip':{'rotate':[(0,0),(.3,-8),(.65,6),(1,0)]},
    },'fist','head_angry')
    if name=='hurt_counter':
        set_track(anims[name],'wrist_front','rotate',[(0,-6),(.3,-15),(.6,12),(1,-6)])

for name in ['greeting','greeting_wave','greeting_bow']:
    anims[name]=gesture(1.2,125,-65,-25,60) if name=='greeting_wave' else gesture(1.2,28,-78,-18,60)
    if name=='greeting_wave':set_track(anims[name],'wrist_front','rotate',[(0,-6),(.26,-6),(.38,25),(.5,-20),(.62,25),(.74,-15),(1,-6)])
    else:
        set_track(anims[name],'body','rotate',[(0,0),(.3,-7 if name=='greeting_bow' else -3),(.6,-7 if name=='greeting_bow' else -3),(1,0)])
        set_track(anims[name],'head','rotate',[(0,0),(.3,-10),(.6,-10),(1,0)])
        anims[name]['slots']['head']['attachment']=[{'time':0,'name':'head_normal'},{'time':.3,'name':'head_closed'},{'time':.85,'name':'head_normal'}]

for name in ['victory_loop','victory_wave_loop','victory_pose_loop']:
    clip=idle(4);anims[name]=clip
    for b,base in [('arm_front',145 if name!='victory_pose_loop' else 70),('elbow_front',-45),('arm_back',-35),('elbow_back',92)]:
        clip['bones'][b]['rotate']=wave(5,0,base,4)
    clip['bones']['wrist_front']['rotate']=wave(22 if name=='victory_wave_loop' else 3,0,-6,4,3 if name=='victory_wave_loop' else 1)
    if name=='victory_loop':
        for b,base in [('arm_front',145),('elbow_front',-35),('arm_back',-145),('elbow_back',35)]:
            clip['bones'][b]['rotate']=wave(7,0,base,4,2)
        for slot in ['hand_front','hand_back']:clip['slots'][slot]['attachment']=[{'time':0,'name':'fist'}]
        set_track(clip,'root','translatey',[(0,0),(.18,0),(.25,8),(.4,0),(.6,0),(.7,7),(.85,0),(1,0)])
    if name=='victory_pose_loop':
        clip['bones']['arm_front']['rotate']=wave(2,0,45,4)
        clip['bones']['elbow_front']['rotate']=wave(2,0,-125,4)
        clip['bones']['head']['rotate']=wave(1,.7,5,4)
        clip['slots']['hand_front']['attachment']=[{'time':0,'name':'fist'}]

for name in ['meditate_loop','rest_sleep_loop']:
    clip=idle(6);anims[name]=clip
    clip['slots']['head']['attachment']=[{'time':0,'name':'head_closed'}]
    for b,v in [('arm_front',-16),('elbow_front',-100),('arm_back',16),('elbow_back',100)]:
        clip['bones'][b]['rotate']=wave(1,0,v,6)
    if name=='rest_sleep_loop':clip['bones']['head']['rotate']=wave(2,0,-12,6)

anims['death']=action(1.35,{
    'root':{'translatex':[(0,0),(.25,2),(.52,35),(.72,85),(1,85)],'translatey':[(0,0),(.3,0),(.55,-70),(.75,-161),(1,-161)]},
    'body':{'rotate':[(0,0),(.2,-8),(.48,-35),(.72,-80),(1,-85)]},
    'chest':{'rotate':[(0,0),(.3,-4),(.6,-18),(1,-18)]},
    'head':{'rotate':[(0,0),(.32,-8),(.55,35),(.72,90),(1,90)],'translatex':[(0,0),(.4,0),(.72,35),(1,35)],'translatey':[(0,0),(.4,0),(.72,5),(1,5)]},
    'arm_front':{'rotate':[(0,18),(.2,35),(.48,105),(.72,-10),(1,-10)]},
    'elbow_front':{'rotate':[(0,-12),(.4,-20),(.72,168),(1,168)]},
    'arm_back':{'rotate':[(0,-18),(.35,30),(.72,98),(1,98)]},
    'elbow_back':{'rotate':[(0,12),(.4,25),(.72,0),(1,0)]},
    'hair':{'rotate':[(0,0),(.4,0),(.72,-75),(1,-75)],'translatey':[(0,0),(.4,0),(.72,40),(1,40)]},
    'hair_tip':{'rotate':[(0,0),(.4,8),(.7,18),(1,10)]},
    'tail_tip':{'rotate':[(0,0),(.45,12),(.8,-12),(1,-8)]},
    'tail':{'rotate':[(0,0),(.4,0),(.72,85),(1,85)],'translatex':[(0,0),(.4,0),(.72,-35),(1,-35)]},
    'skirt':{'rotate':[(0,0),(.4,0),(.72,65),(1,65)],'translatex':[(0,0),(.4,0),(.72,-40),(1,-40)],'scaley':[(0,1),(.4,1),(.72,.45),(1,.45)]},
    'leg_front':{'rotate':[(0,0),(.3,-8),(.55,-50),(.75,-80),(1,-80)],'translatey':[(0,0),(.3,1.3),(.55,32.1),(.75,57.6),(1,57.6)],'translatex':[(0,0),(.4,0),(.75,-70),(1,-70)]},
    'leg_back':{'rotate':[(0,0),(.3,-10),(.55,-54),(.75,-82),(1,-82)],'translatey':[(0,0),(.3,1.2),(.55,24.8),(.75,52.5),(1,52.5)],'translatex':[(0,0),(.4,0),(.75,-90),(1,-90)]},
    # Prone attachment stays on the floor while the upright body falls into it.
    'prone':{'translatex':[(0,0),(.52,-35),(.72,-85),(1,-85)],'translatey':[(0,0),(.55,70),(.75,161),(1,161)],'scaley':[(0,1),(.72,1),(.79,.94),(.86,1.015),(.96,1),(1,1)]},
},face='head_closed')
for slot in slots:
    name=slot['name']
    if name=='prone':
        anims['death']['slots'][name]['attachment']=[{'time':0,'name':'prone'}]
        anims['death']['slots'][name]['rgba']=[{'time':0,'color':'ffffff00'},{'time':.98,'color':'ffffff00'},{'time':1.06,'color':'ffffffff'},{'time':1.35,'color':'ffffffff'}]
    else:anims['death']['slots'][name]['rgba']=[{'time':0,'color':'ffffffff'},{'time':.98,'color':'ffffffff'},{'time':1.06,'color':'ffffff00'},{'time':1.35,'color':'ffffff00'}]

anims['revive']=gesture(1.2,135,-60,-115,65)
assert len(anims)==50,len(anims)
document={'skeleton':{'spine':'4.2.43','x':-245,'y':0,'width':490,'height':443,'fps':60,'images':'./'},
          'bones':bones,'slots':slots,'skins':[{'name':'default','attachments':attachments}],'animations':anims}
(OUT/'maid.spine-json').write_text(json.dumps(document,separators=(',',':')),encoding='utf-8')
preview={**document,'preview_regions':{n:{'page':f,'rect':r} for n,(f,r) in regions.items()}}
(ROOT/'preview/rig-data.js').write_text('const RIG_DATA='+json.dumps(preview,separators=(',',':'))+';\n',encoding='utf-8')
textures={f:'data:image/png;base64,'+base64.b64encode((ROOT/'assets/sprites'/f).read_bytes()).decode('ascii') for f in pages}
(ROOT/'preview/rig-texture.js').write_text('const RIG_TEXTURES='+json.dumps(textures,separators=(',',':'))+';\n',encoding='utf-8')
(OUT/'payload.json').write_text(json.dumps({'textures':list(pages),'height':443,'slots':len(slots),'attachments':sum(map(len,attachments.values()))},indent=2),encoding='utf-8')
print(f'Authored layered puppet: {len(bones)} bones, {len(slots)} slots, {sum(map(len,attachments.values()))} attachments, {len(anims)} animations, {len(pages)} atlas pages.')
