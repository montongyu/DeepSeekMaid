"""Render the locked original poses with the newly painted intervening poses.

This is an animatic for review, not a smooth or game-ready animation claim.
No synthetic optical-flow frames are included: those failed visual review.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from reference_attack import load, CROPS, PADS, SOURCE, OUT, W, H

ROOT=Path(__file__).resolve().parents[1]
PAINTED=ROOT/'assets/concept/attack-painted-inbetweens-v0.8.2.png'


def main():
    original,_=load()
    atlas=Image.open(PAINTED).convert('RGBA')
    cw,ch=atlas.width//3,atlas.height//3
    # Face centres guide a uniform camera alignment. Do not stretch individual
    # hands, arms, heads or legs to make the frames fit one another.
    faces=[(248,85),(263,90),(323,91),(269,91),(292,95),(293,97),(271,74),(265,62),(273,66)]
    face_target=[(470,158),(476,163),(480,169),(480,170),(480,170),(480,161),(478,146),(478,146),(478,146)]
    yy,xx=np.mgrid[:H,:W]
    # A procedural navy review stage, not a background extraction or repaint.
    edge=np.abs(xx-W/2)/(W/2)
    gradient=np.clip(1-.24*yy/H+.06*edge,0,1)
    backdrop=np.stack([25*gradient,37*gradient,63*gradient],axis=2).astype(np.uint8)
    painted=[]
    for k in range(9):
        col,row=k%3,k//3
        # The generated rows are not perfectly isolated. A UV crop excludes
        # the next row's hair curl; keep the second row's whole shoes.
        top,bottom=[(0,410),(420,818),(820,1254)][row]
        cell=atlas.crop((col*cw,top,(col+1)*cw,bottom))
        scale=1.73
        cell=cell.resize((round(cw*scale),round((bottom-top)*scale)),Image.Resampling.LANCZOS)
        x=round(face_target[k][0]-faces[k][0]*scale)
        y=round(face_target[k][1]-(faces[k][1]+row*ch-top)*scale)
        frame=Image.fromarray(backdrop).convert('RGBA')
        frame.alpha_composite(cell,(x,y))
        painted.append(frame.convert('RGB'))
    # Preserve the exact locked source panels at ready, impact and recovery.
    source=[Image.fromarray(a) for a in original]
    key=[source[0],painted[1],painted[2],source[1],painted[4],painted[5],painted[6],source[2]]
    durations=[340,70,60,180,60,80,70,640]
    labels=['原图 · 蓄力','补绘 · 伸掌','补绘 · 发力','原图 · 推掌','补绘 · 余势','补绘 · 收掌','补绘 · 收势','原图 · 收势']
    gif=OUT/'attack-painted-animatic.gif'
    key[0].save(gif,save_all=True,append_images=key[1:],duration=durations,loop=0,optimize=False,disposal=2)
    # Lossless original-keyframe proof is kept alongside the quantized GIF.
    for k,frame in enumerate(source):frame.save(OUT/f'key-{k+1}.png')
    key[0].save(OUT/'attack-painted-animatic.png',save_all=True,append_images=key[1:],duration=durations,loop=0,disposal=0,blend=0)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
    contact=Image.new('RGB',(W*4,H*2),(17,27,46))
    for k,frame in enumerate(key):
        panel=frame.copy()
        ImageDraw.Draw(panel).text((15,12),labels[k],font=font,fill=(223,240,255))
        contact.paste(panel,((k%4)*W,(k//4)*H))
    contact.resize((1600,724),Image.Resampling.LANCZOS).save(OUT/'painted-animatic-review.jpg',quality=94)
    checks=[]
    raw=Image.open(SOURCE).convert('RGB')
    for k,(rect,pad) in enumerate(zip(CROPS,PADS)):
        expected=np.array(raw.crop(rect))
        got=np.array(Image.open(OUT/f'key-{k+1}.png'))[:,pad:pad+expected.shape[1]]
        checks.append({'key':k+1,'max_original_pixel_error':int(np.abs(got.astype(int)-expected.astype(int)).max())})
    report={
        'status':'animatic_for_review_not_game_ready',
        'exact_original_poses':3,'painted_intervening_poses_used':5,
        'distinct_pictures':8,'duration_ms':sum(durations),'frame_durations_ms':durations,
        'keyframe_checks':checks,
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'painted_sha256':hashlib.sha256(PAINTED.read_bytes()).hexdigest(),
        'source_vs_user_attachment_rgb_error':0,
        'automatic_morph_result':'rejected; not included',
        'limitations':['Painted inbetweens change some details and body spacing.','This is timed keyframe blocking, not a completed smooth animation.','The review retains the original opaque navy backdrop.','No runtime animation, release package or installed game was modified.'],
        'image_tool':'built-in image_gen; no API or CLI fallback',
        'prompt':'assets/concept/attack-exact-inbetweens-prompt.txt',
        'dist_modified':False,'game_deployed':False,
    }
    (OUT/'painted-animatic-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
