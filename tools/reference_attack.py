"""Animate the approved painted attack poses without redrawing their keyframes.

This is a reference-animation review, separate from the shipped Spine rig.
The original painting remains the texture source. Piecewise affine body
correspondences and local optical flow render the intervening frames.
"""
from pathlib import Path
import argparse
import hashlib
import json
import cv2
import numpy as np
from scipy.spatial import Delaunay
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/concept/attack-right-v0.8-review.png'
OUT = ROOT / 'preview/exact-reference-attack'
W, H = 800, 724
# The painted dividers are at x=723 and x=1525; the panels are NOT equal thirds.
CROPS = [(0, 0, 722, 724), (727, 0, 1523, 724), (1528, 0, 2172, 724)]
PADS = [39, 2, 78]

# Coordinates in each original panel, before the padding above. Landmarks
# describe the same anatomical or costume point in all three painted poses.
LANDMARKS = {
    'hair_top': [(415,24),(459,30),(402,18)],
    'head_top': [(416,66),(465,76),(407,56)],
    'head_left': [(375,111),(425,120),(367,104)],
    'head_right': [(474,111),(521,123),(462,100)],
    'eye_l': [(415,147),(462,160),(410,132)],
    'eye_r': [(454,145),(499,158),(443,133)],
    'nose': [(444,169),(490,179),(440,154)],
    'chin': [(431,188),(480,199),(430,173)],
    'ear_l': [(342,136),(365,145),(328,108)],
    'neck': [(421,209),(460,214),(416,194)],
    'shoulder_l': [(347,237),(416,224),(364,210)],
    'shoulder_r': [(479,232),(489,223),(456,211)],
    'bust_l': [(362,267),(421,272),(404,244)],
    'bust_r': [(445,267),(493,274),(479,244)],
    'belt_l': [(350,290),(427,300),(425,285)],
    'belt_r': [(436,292),(485,311),(476,289)],
    'belt_c': [(393,295),(457,306),(449,286)],
    'apron_l': [(336,361),(412,376),(401,361)],
    'apron_r': [(450,366),(526,387),(509,363)],
    'apron_logo': [(396,383),(492,400),(461,383)],
    'apron_bottom': [(400,425),(484,438),(470,428)],
    'front_elbow': [(514,287),(555,243),(402,284)],
    'front_wrist': [(480,311),(627,249),(468,257)],
    'front_palm': [(454,287),(663,231),(484,226)],
    'front_fingers': [(449,256),(680,185),(510,208)],
    'rear_elbow': [(285,266),(359,275),(492,298)],
    'rear_wrist': [(296,290),(312,285),(509,291)],
    'rear_hand': [(313,283),(291,290),(517,276)],
    'skirt_l': [(237,403),(234,398),(268,401)],
    'skirt_r': [(592,383),(593,422),(578,401)],
    'skirt_bow_l': [(328,410),(350,401),(360,404)],
    'skirt_bow_r': [(493,411),(562,435),(554,411)],
    'skirt_bottom_l': [(257,488),(263,482),(294,485)],
    'skirt_bottom_c': [(409,532),(442,533),(420,538)],
    'skirt_bottom_r': [(575,491),(579,500),(564,494)],
    'thigh_l': [(331,488),(329,484),(352,491)],
    'thigh_r': [(477,485),(547,485),(457,489)],
    'knee_l': [(263,551),(232,543),(299,558)],
    'knee_r': [(541,549),(558,551),(477,555)],
    'ankle_l': [(205,619),(132,616),(246,624)],
    'ankle_r': [(590,629),(570,627),(483,626)],
    'shoe_l': [(199,663),(126,660),(244,663)],
    'shoe_r': [(613,665),(597,668),(506,666)],
    'toe_l': [(215,694),(153,695),(280,697)],
    'toe_r': [(652,692),(642,695),(543,695)],
    'tail_top': [(86,320),(82,302),(110,324)],
    'tail_tip_l': [(25,397),(17,407),(37,421)],
    'tail_bottom': [(148,435),(144,425),(168,464)],
    'tail_base': [(259,492),(260,486),(272,514)],
    'hair_l_1': [(151,113),(152,93),(149,122)],
    'hair_l_2': [(84,214),(73,206),(77,228)],
    'hair_l_3': [(186,298),(197,301),(207,320)],
    'hair_l_4': [(292,330),(302,306),(309,349)],
    'hair_r': [(491,192),(537,210),(472,186)],
}


def load():
    atlas = np.array(Image.open(SOURCE).convert('RGB'))
    frames = []
    for (x0,y0,x1,y1), pad in zip(CROPS, PADS):
        panel = atlas[y0:y1,x0:x1].copy()
        # Extend only outside the original panel, retaining every source pixel.
        frames.append(cv2.copyMakeBorder(panel, 0, 0, pad, W-pad-panel.shape[1], cv2.BORDER_REPLICATE))
    points = np.array([[np.array(p[k])+[PADS[k],0] for p in LANDMARKS.values()] for k in range(3)], np.float32)
    anchors = np.array([(x,y) for x,y in [(0,0),(200,0),(400,0),(600,0),(799,0),(799,180),(799,360),(799,540),(799,723),(600,723),(400,723),(200,723),(0,723),(0,540),(0,360),(0,180)]],np.float32)
    points = np.concatenate([points, np.repeat(anchors[None],3,axis=0)],axis=1)
    return frames, points


YY, XX = np.mgrid[:H,:W].astype(np.float32)


def inverse_mesh(source, target):
    """A continuous inverse texture-coordinate map on the current pose mesh."""
    triangles = Delaunay(target)
    queries = np.column_stack([XX.ravel(), YY.ravel()])
    ids = triangles.find_simplex(queries)
    ids = np.maximum(ids,0)
    t = triangles.transform[ids]
    bary = np.einsum('nij,nj->ni',t[:,:2],queries-t[:,2])
    bary = np.column_stack([bary,1-bary.sum(axis=1)])
    uv = np.einsum('ni,nij->nj',bary,source[triangles.simplices[ids]])
    return uv[:,0].reshape(H,W).astype(np.float32),uv[:,1].reshape(H,W).astype(np.float32)


def remap(im, x, y):
    return cv2.remap(im,x,y,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)


def interpolate(a,b,pa,pb,u,refine=True):
    if u <= 0: return a.copy()
    if u >= 1: return b.copy()
    target = pa*(1-u)+pb*u
    ma = inverse_mesh(pa,target)
    mb = inverse_mesh(pb,target)
    wa = remap(a,*ma)
    wb = remap(b,*mb)
    if refine:
        # Align local painted details after the anatomy has been registered.
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        dis.setUseSpatialPropagation(True)
        ga = cv2.cvtColor(wa,cv2.COLOR_RGB2GRAY)
        gb = cv2.cvtColor(wb,cv2.COLOR_RGB2GRAY)
        fab = dis.calc(ga,gb,None)
        fba = dis.calc(gb,ga,None)
        # Limit this pass to texture alignment; do not undo anatomical motion.
        for flow in (fab,fba):
            length = np.linalg.norm(flow,axis=2)
            flow *= np.minimum(1,18/np.maximum(length,1e-4))[...,None]
        wa = remap(wa,XX-u*fab[:,:,0],YY-u*fab[:,:,1])
        wb = remap(wb,XX-(1-u)*fba[:,:,0],YY-(1-u)*fba[:,:,1])
    return cv2.addWeighted(wa,1-u,wb,u,0)


def pair_flow(a,b,pa,pb):
    ax,ay=inverse_mesh(pb,pa)
    bx,by=inverse_mesh(pa,pb)
    init_a=np.stack([ax-XX,ay-YY],axis=2)
    init_b=np.stack([bx-XX,by-YY],axis=2)
    ga=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    gb=cv2.cvtColor(b,cv2.COLOR_RGB2GRAY)
    dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    dis.setFinestScale(0)
    dis.setGradientDescentIterations(40)
    dis.setVariationalRefinementIterations(15)
    return dis.calc(ga,gb,init_a),dis.calc(gb,ga,init_b)


def flow_interpolate(a,b,fa,fb,u):
    if u<=0:return a.copy()
    if u>=1:return b.copy()
    def warp(im,flow,factor):
        mx,my=XX.copy(),YY.copy()
        for _ in range(8):
            fx=remap(flow[:,:,0],mx,my)
            fy=remap(flow[:,:,1],mx,my)
            mx=XX-factor*fx;my=YY-factor*fy
        return remap(im,mx,my)
    wa=warp(a,fa,u);wb=warp(b,fb,1-u)
    return cv2.addWeighted(wa,1-u,wb,u,0)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--draft',action='store_true')
    parser.add_argument('--experimental-morph',action='store_true',help='Rejected morph diagnostic only; not a deliverable')
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    frames,points = load()
    for i,f in enumerate(frames):
        Image.fromarray(f).save(OUT/f'key-{i+1}.png')
    if not args.draft and not args.experimental_morph:
        print('Exported three locked original poses. Use render_reference_animatic.py for the painted review.')
        return
    # First review anatomical interpolation at several phases before encoding.
    if args.draft:
        contact=Image.new('RGB',(W*4,H*2))
        for pair in range(2):
            fa,fb=pair_flow(frames[pair],frames[pair+1],points[pair],points[pair+1])
            for n,u in enumerate([0,.33,.67,1]):
                im=Image.fromarray(flow_interpolate(frames[pair],frames[pair+1],fa,fb,u))
                ImageDraw.Draw(im).text((12,10),f'{pair+1} -> {pair+2} / {u:.2f}',fill='white')
                contact.paste(im,(n*W,pair*H))
        contact.resize((1600,724)).save(OUT/'transition-review.jpg',quality=94)
        return
    fps=50
    # A short, readable strike: anticipation, fast extension, impact, recovery.
    sequence=[(0,0,.30),(0,1,.22),(1,1,.12),(1,2,.34),(2,2,.30),(2,0,.40),(0,0,.30)]
    rendered=[]
    anchor_indices=[]
    for first,last,duration in sequence:
        count=round(duration*fps)
        for n in range(count):
            u=n/max(count-1,1)
            # C1 easing keeps velocity continuous where the reference holds.
            u=u*u*(3-2*u)
            if first==last:
                f=frames[first].copy()
                if n==0:anchor_indices.append([len(rendered),first])
            else:
                f=interpolate(frames[first],frames[last],points[first],points[last],u)
            rendered.append(Image.fromarray(f))
        print(f'Rendered {first+1} -> {last+1}',flush=True)
    out=OUT/'attack-original-poses.gif'
    rendered[0].save(out,save_all=True,append_images=rendered[1:],duration=20,loop=0,optimize=False,disposal=2)
    apng=OUT/'attack-original-poses.png'
    rendered[0].save(apng,save_all=True,append_images=rendered[1:],duration=20,loop=0,disposal=0,blend=0)
    original=np.array(Image.open(SOURCE).convert('RGB'))
    checks=[]
    for k,((x0,y0,x1,y1),pad) in enumerate(zip(CROPS,PADS)):
        diff=np.abs(frames[k][:,pad:pad+x1-x0].astype(int)-original[y0:y1,x0:x1].astype(int))
        checks.append({'pose':k+1,'source_rect':[x0,y0,x1,y1],'pad_left':pad,'max_source_pixel_error':int(diff.max())})
    report={
        'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'kind':'painted-reference-animation-review','keyframe_checks':checks,
        'frames':len(rendered),'fps':fps,'duration_seconds':len(rendered)/fps,
        'anchors':anchor_indices,'transition_method':'anatomical mesh registration + bounded bidirectional DIS texture alignment',
        'limitations':['Inbetweens are interpolated, not painted reference frames.','Occlusion and changing artwork can cause blended details during transitions.','Opaque review background; not a game sprite or packaged Spine animation.'],
        'game_deployed':False,'dist_modified':False,
    }
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
