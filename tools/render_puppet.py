"""Software render of native animation samples for contact sheets and GIF QA."""
import json
import argparse
from concurrent.futures import ProcessPoolExecutor
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from puppet_geometry import ROOT,DATA,REGIONS,MESHES,points

samples=json.loads((ROOT/'work/spine-mesh-samples.json').read_text())
pages={r['page']:np.array(Image.open(ROOT/'assets/sprites'/r['page']).convert('RGBA')) for r in REGIONS.values()}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
VERSION='0.8.6'
def render(sample,label='',scale=.85):
    w,h=510,440;frame=Image.new('RGBA',(w,h),(17,27,46,255))
    ImageDraw.Draw(frame).line([(0,416),(w,416)],fill=(50,68,90,255),width=1)
    for slot in DATA['slots']:
        name,alpha=sample['slots'][slot['name']]
        if not name or alpha<.001:continue
        mesh=MESHES[slot['name'],name];p=points(mesh,sample)*scale+np.array([250,416])
        region=REGIONS[mesh['path']];rx,ry,rw,rh=region['rect'];uv=mesh['uv']*np.array([rw,rh])+[rx,ry]
        mx=np.full((h,w),-1,dtype=np.float32);my=mx.copy()
        for t in mesh['tri']:
            dst=p[t];src=uv[t]
            x0,y0=np.maximum(0,np.floor(dst.min(axis=0)).astype(int));x1,y1=np.minimum([w-1,h-1],np.ceil(dst.max(axis=0)).astype(int))
            if x1<x0 or y1<y0:continue
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
            v0=dst[1]-dst[0];v1=dst[2]-dst[0];den=v0[0]*v1[1]-v1[0]*v0[1]
            if abs(den)<1e-8:continue
            dx=xx-dst[0,0];dy=yy-dst[0,1]
            u=(dx*v1[1]-dy*v1[0])/den;v=(dy*v0[0]-dx*v0[1])/den
            mask=(u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001)
            sx=src[0,0]+u*(src[1,0]-src[0,0])+v*(src[2,0]-src[0,0]);sy=src[0,1]+u*(src[1,1]-src[0,1])+v*(src[2,1]-src[0,1])
            mx[y0:y1+1,x0:x1+1][mask]=sx[mask];my[y0:y1+1,x0:x1+1][mask]=sy[mask]
        pixels=cv2.remap(pages[region['page']],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        pixels[:,:,3]=(pixels[:,:,3]*alpha).astype(np.uint8)
        frame.alpha_composite(Image.fromarray(pixels))
    age=sample.get('anger_age',-1)
    if 0<=age<1.20:
        overlay=Image.new('RGBA',frame.size);draw=ImageDraw.Draw(overlay)
        hi=next(i for i,b in enumerate(DATA['bones']) if b['name']=='ref_head');ti=next(i for i,b in enumerate(DATA['bones']) if b['name']=='ref_torso')
        hx,hy=np.array(sample['bones'][hi][4:6])+[43,-53]
        opacity=max(0,min(1,(age-.14)/.08,(1.17-age)/.22));growth=.45+.55*(1-(1-np.clip((age-.14)/.14,0,1))**3)
        for angle in range(4):
            a=angle*np.pi/2;c,s=np.cos(a),np.sin(a)
            p=[(250+(hx+(x*c-y*s)*growth)*scale,416+(hy+(x*s+y*c)*growth)*scale) for x,y in [(3,-2),(3,-9),(10,-9)]]
            draw.line(p,fill=(255,242,217,round(opacity*255)),width=4);draw.line(p,fill=(255,103,83,round(opacity*255)),width=2)
        for i,sx in enumerate([-32,16]):
            rise=-9*np.clip((age-.20-i*.05)/.55,0,1);fade=1-np.clip((age-.65-i*.05)/.28,0,1)
            p=[(250+(hx+sx+x)*scale,416+(hy+rise+y)*scale) for x,y in [(0,5),(-3,-1),(2,-7),(-1,-13),(3,-19)]]
            draw.line(p,fill=(255,243,227,round(opacity*fade*255)),width=1)
        if age<.19:
            tx,ty=np.array(sample['bones'][ti][4:6])+[45,-28];growth=.5+.85*np.clip(age/.18,0,1);fade=1-np.clip((age-.04)/.15,0,1)
            for i in range(4):
                a=-1.1+i*.7;direction=np.array([np.cos(a),np.sin(a)])
                p=[tuple(np.array([250,416])+(np.array([tx,ty])+direction*r*growth)*scale) for r in [8,20]]
                draw.line(p,fill=(*( (171,240,255) if i%2==0 else (103,201,255)),round(fade*255)),width=2)
        frame.alpha_composite(overlay)
    # Software approximation of ThemeVfx.HandPulse. Bone positions/mixing are
    # native samples; Line2D/Tween effects still require combat-scene QA.
    if sample.get('hand_pulse') and sample.get('painted_pulse'):
        hx,hy,age=sample['hand_pulse']
        if age<.14:
            u=1-(1-age/.14)**3;sx=.52+.48*u;sy=.75+.25*u;opacity=.975
        else:
            u=np.sin(min(1,(age-.14)/.24)*np.pi/2);sx=1+.18*u;sy=1+.10*u
            opacity=.975*max(0,1-(age-.14)/.24)
        art=Image.fromarray(pages['reference-water-v0.8.2.png'])
        factor=190/art.height*scale
        art=art.resize((max(1,round(art.width*factor*sx)),max(1,round(art.height*factor*sy))),Image.Resampling.LANCZOS)
        art.putalpha(art.getchannel('A').point(lambda a:round(a*opacity)))
        cx=250+(hx+10)*scale;cy=416+(hy+4)*scale
        frame.alpha_composite(art,(round(cx-art.width/2),round(cy-art.height/2)))
    elif sample.get('hand_pulse'):
        hx,hy,age=sample['hand_pulse'];growth=.4+.85*(1-(1-age/.32)**2)
        draw=ImageDraw.Draw(frame);cx=250+(hx+22)*scale;cy=416+hy*scale
        def fade(rgb,alpha=1):
            opacity=.975*(1-max(0,age-.10)/.22)*alpha
            return tuple(round(ground+(value-ground)*opacity) for value,ground in zip(rgb,(17,27,46)))+(255,)
        for i in range(24):
            a=i*2*np.pi/24;b=(i+1)*2*np.pi/24
            pa=np.array([np.cos(a)*18,np.sin(a)*46])*(1.06+.055*np.sin(a*5))*scale*growth
            pb=np.array([np.cos(b)*18,np.sin(b)*46])*(1.06+.055*np.sin(b*5))*scale*growth
            poly=[tuple(np.array([cx,cy])+v) for v in [pa,pb,pb*(.73+.08*np.sin(b*3)),pa*(.73+.08*np.sin(a*3))]]
            draw.polygon(poly,fill=fade((83,216,255) if i%3==0 else (35,127,222),.75))
        for ring,radius,color in [(0,1,(143,233,255)),(1,.82,(229,251,255)),(2,1.13,(55,180,250))]:
            contour=[]
            for a in np.linspace(0,2*np.pi,65):
                ripple=1+.06*np.sin(a*5+ring)+.025*np.sin(a*9-ring)
                contour.append((cx+np.cos(a)*18*scale*growth*radius*ripple,cy+np.sin(a)*46*scale*growth*radius*ripple))
            if ring==0:draw.line(contour,fill=fade((67,191,255),.3),width=8)
            draw.line(contour,fill=fade(color),width=3 if ring==0 else 2)
        for i in range(9):
            a=i*2*np.pi/9+.13;dx,dy=np.cos(a)*23*scale*growth,np.sin(a)*54*scale*growth
            draw.ellipse((cx+dx-1.5,cy+dy-2,cx+dx+1.5,cy+dy+2),fill=fade((75,195,255)),outline=fade((220,250,255)),width=1)
    if sample.get('guard_shield'):
        hx,hy,phase=sample['guard_shield']
        opacity=.98
        if phase<.32:
            u=1-(1-max(0,(phase-.17)/.15))**3;sx=.30+.70*u;sy=.55+.45*u
        elif phase<.46:sx=sy=1
        elif phase<.505:
            u=1-(1-(phase-.46)/.045)**2;sx=1-.1*u;sy=1+.035*u
        elif phase<.58:
            u=np.sin((phase-.505)/.075*np.pi/2);sx=.90+.10*u;sy=1.035-.035*u
        else:
            u=np.sin(min(1,(phase-.58)/.23)*np.pi/2);sx=1+.13*u;sy=1+.05*u
            opacity*=max(0,1-(phase-.58)/.23)
        art=Image.fromarray(pages['reference-shield-v0.8.3.png'])
        factor=290/art.height*scale
        art=art.resize((max(1,round(art.width*factor*sx)),max(1,round(art.height*factor*sy))),Image.Resampling.LANCZOS)
        art.putalpha(art.getchannel('A').point(lambda a:round(a*opacity)))
        cx=250+(hx+58)*scale;cy=416+(hy+60)*scale
        frame.alpha_composite(art,(round(cx-art.width/2),round(cy-art.height/2)))
    if sample.get('spell_weave'):
        front,rear,phase,power,centered=sample['spell_weave']
        def ramp(a,b,x):
            u=float(np.clip((x-a)/(b-a),0,1));return u*u*(3-2*u)
        release=0 if centered else ramp(.40,.60,phase)
        center=(np.array(front)+rear)*.5+[0,-5]
        center=center*(1-release)+(np.array(front)+[18,-14])*release
        center=center*scale+[250,416]
        charge=ramp(.12,.46,phase)
        radius=(12+charge*(21 if power else 15))*(1+(.08 if power else .035)*np.sin(phase*np.pi*6))
        alpha=ramp(.12,.22,phase)*(1-ramp(.70,.88,phase))
        rgb=(182,155,255) if power else (109,227,255)
        fx=Image.new('RGBA',frame.size);draw=ImageDraw.Draw(fx)
        def ring(rx,ry,angle,color,width):
            points=[];c,s=np.cos(angle),np.sin(angle)
            for a in np.linspace(0,np.pi*2,41):
                x,y=np.cos(a)*rx,np.sin(a)*ry
                points.append(tuple(center+np.array([x*c-y*s,x*s+y*c])*scale))
            draw.line(points,fill=color,width=width)
        ring(radius,radius,0,(*rgb,round(alpha*.24*255)),4)
        ring(radius*1.12,radius*.48,phase*np.pi*2*1.3,(*rgb,round(alpha*.9*255)),2)
        ring(radius*.62,radius*1.08,-phase*np.pi*2*1.1,(232,250,255,round(alpha*.8*255)),1)
        cr=8*(.6+charge*.75);ring(cr,cr,0,(*rgb,round(alpha*.8*255)),2)
        for i in range(8):
            a=i*np.pi/4+phase*np.pi*2*(1.4 if power else 1.1)
            pos=center+np.array([np.cos(a)*radius*1.25,np.sin(a)*radius*.78])*scale
            c,s=np.cos(a),np.sin(a)
            poly=[tuple(pos+np.array([x*c-y*s,x*s+y*c])*scale) for x,y in [(0,-3),(2,0),(0,3),(-2,0),(0,-3)]]
            draw.line(poly,fill=(*( (255,227,166) if i%3==0 else rgb),round(alpha*.85*255)),width=1)
        frame.alpha_composite(fx)
    ImageDraw.Draw(frame).text((16,12),label,font=font,fill=(225,235,249))
    return frame.convert('RGB')

def nearest(name,phase):return min((s for s in samples if s['animation']==name),key=lambda s:abs(s['phase']-phase))
def render_job(job):
    sample,label=job
    return render(sample,label).resize((510,440),Image.Resampling.LANCZOS)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sheet-only',action='store_true');parser.add_argument('--groups',nargs='*');args=parser.parse_args()
    poses=[('idle_loop',0,'掌心向上 · 默认待机'),('attack',.34,'收掌后推击'),('guard',.46,'抬手水盾防御'),('cast',.30,'双手聚拢'),('idle_angry_loop',.1,'受击后短暂恼火'),('greeting_wave',.4,'同一姿势入场动作'),('death',.72,'向前倒下'),('death',1,'同一人物趴地终态'),('revive',1,'复起回到默认待机')]
    sheet=Image.new('RGB',(510*3,440*3))
    for i,(name,p,label) in enumerate(poses):
        sample=nearest(name,p).copy()
        if name=='hurt':sample['anger_age']=.7
        sheet.paste(render(sample,label),((i%3)*510,(i//3)*440))
    sheet.save(ROOT/f'preview/contact-sheet-v{VERSION}.png')
    print('Rendered contact sheet.',flush=True)
    if args.sheet_only:return
    sequences=json.loads((ROOT/'work/spine-showcases.json').read_text())
    with ProcessPoolExecutor(max_workers=4) as pool:
        for group,sequence in sequences.items():
            if args.groups and group not in args.groups:continue
            jobs=[];last_hurt=-100;previous='';clip_started=0;hand_position=None;shield_position=None
            for i,sample in enumerate(sequence):
                name=sample['animation']
                if name!=previous:clip_started=i/60;hand_position=None;shield_position=None
                if name.startswith('hurt') and name!=previous:last_hurt=i/60
                if name!=previous and not name.startswith(('hurt','idle_')):last_hurt=-100
                previous=name
                elapsed=i/60-clip_started
                delay=.28 if name=='attack_jab' else .34 if name=='attack' else .36
                effect_duration=.38 if name=='attack' else .32
                if name in ['attack','attack_palm','attack_ranged','attack_jab','attack_cross'] and delay<=elapsed<delay+effect_duration:
                    if hand_position is None:
                        bone_name='ref_hand_front'
                        b=sample['bones'][next(j for j,b in enumerate(DATA['bones']) if b['name']==bone_name)]
                        hand_position=b[4:6]
                    sample['hand_pulse']=[*hand_position,elapsed-delay]
                    sample['painted_pulse']=name=='attack'
                if name.startswith('guard') and .17<=sample['phase']<.81:
                    shield_position=sample['bones'][next(j for j,b in enumerate(DATA['bones']) if b['name']=='ref_hand_front')][4:6]
                    sample['guard_shield']=[*shield_position,sample['phase']]
                if name.startswith(('cast','channel')) and .12<=sample['phase']<.88:
                    palms=[sample['bones'][next(j for j,b in enumerate(DATA['bones']) if b['name']=='ref_hand_'+side)][4:6] for side in ['front','back']]
                    sample['spell_weave']=[*palms,sample['phase'],name.startswith('channel'),name in ['cast_circle','channel','channel_gather','channel_pulse']]
                if i%2 and group not in ['reference_idle','reference_hurt']:continue
                sample['anger_age']=i/60-last_hurt
                label=name
                if group=='reference_guard':
                    label=('防御 · 抬臂护身' if sample['phase']<.26 else '防御 · 水盾格挡' if sample['phase']<.58 else '防御 · 收势') if name=='guard' else '备战待机'
                elif group in ['reference_cast','reference_channel']:
                    label=(('聚能' if name.startswith('channel') else '施法')+(' · 双手蓄力' if sample['phase']<.43 else ' · 引导释放' if sample['phase']<.70 else ' · 收势')) if name.startswith(('cast','channel')) else '备战待机'
                elif group in ['reference_idle','reference_hurt','common_actions','lifecycle','interruptions','entry_victory']:
                    label={'idle_loop':'掌心向上 · 默认待机','idle_angry_loop':'短暂恼火 · 随后恢复','hurt':'短促受击 · 站稳','attack':'收掌推击','guard':'抬手防御','cast':'双手施法','channel_overdrive':'过载聚能','death':'向前倒下 · 趴地','revive':'复起 · 回到默认待机','greeting':'轻轻致意','greeting_wave':'抬手致意','greeting_bow':'点头致意','victory_wave_loop':'庆祝 · 循环首尾回到默认姿势'}.get(name,name)
                jobs.append((sample,label))
            frames=list(pool.map(render_job,jobs,chunksize=6))
            if group in ['reference_idle','reference_hurt']:
                apng_durations=[[17,16,17][i%3] for i in range(len(frames))]
                frames[0].save(ROOT/f'preview/{group}-v{VERSION}.png',save_all=True,append_images=frames[1:],duration=apng_durations,loop=0,disposal=0,blend=0)
                gif_frames=[frames[min(len(frames)-1,round(i*60/50))] for i in range(round(len(frames)*50/60))]
                durations=[20]*len(gif_frames)
            else:
                gif_frames=frames;durations=[[30,40,30][i%3] for i in range(len(frames))]
            gif_frames[0].save(ROOT/f'preview/{group}-v{VERSION}.gif',save_all=True,append_images=gif_frames[1:],duration=durations,loop=0,optimize=False)
            print(f'Rendered {group}: {len(frames)} native poses, native 80ms mixing.',flush=True)
    import hashlib
    manifest={'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest(),
              'native_mixed_poses':True,'gif_fps':30,'reference_idle_gif_fps':50,'reference_idle_apng_fps':60,'reference_hurt_gif_fps':50,'reference_hurt_apng_fps':60,
              'rendered_groups':args.groups or list(sequences),'retained_previews':'Earlier version files are historical examples, not current shared-pose motion',
              'effect_overlay':'software approximation of C# palm, water shield and hand weave effects; not combat tested'}
    (ROOT/f'preview/preview-validation-v{VERSION}.json').write_text(json.dumps(manifest,indent=2))
    print('Software previews use actual native mixed poses; these are not game screenshots or measured game FPS.')

if __name__=='__main__':main()
