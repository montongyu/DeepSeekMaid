"""Validate every visible attachment using actual native bone/slot samples."""
import hashlib
import json
import numpy as np
from puppet_geometry import ROOT,DATA,REGIONS,MESHES,points,areas

payload=json.loads((ROOT/'assets/animation/payload.json').read_text())
for name in ['maid.atlas','maid.spine-json']:
    assert (ROOT/'assets/animation'/name).read_bytes()==(ROOT/'dist/DeepSeekMaid/animation'/name).read_bytes()
for name in payload['textures']:
    assert (ROOT/'assets/sprites'/name).read_bytes()==(ROOT/'dist/DeepSeekMaid/animation'/name).read_bytes()
samples=json.loads((ROOT/'work/spine-mesh-samples.json').read_text())
single_count=len(samples)
mixed=json.loads((ROOT/'work/spine-showcases.json').read_text())
for sequence in mixed.values():samples.extend(sequence)
minimum=float('inf');tested=0;seen=set();bounds={};prone_min_y=None;prone_height=None
reference={}
reference_palm=json.loads((ROOT/'assets/animation/reference-palm.json').read_text())
reference_guard=json.loads((ROOT/'assets/animation/reference-guard.json').read_text())
reference_spell=json.loads((ROOT/'assets/animation/reference-spell.json').read_text())
reference_key_error=0
bind_error=0
for key,m in MESHES.items():
    if key[0].startswith(('ref_','guard_','spell_')):
        author=reference_spell if key[0].startswith('spell_') else reference_guard if key[0].startswith('guard_') else reference_palm
        meta=author['meshes'][key[0]]
        sample=min((s for s in samples[:single_count] if s['animation']==('cast' if key[0].startswith('spell_') else 'guard' if key[0].startswith('guard_') else 'attack')),key=lambda s:abs(s['phase']*author['duration']-meta['key_time']))
        p=points(m,sample)
        expected=np.array(meta['source_geometry']);expected[:,1]*=-1
        reference_key_error=max(reference_key_error,float(np.abs(expected-p).max()))
        reference[key]=areas(expected,m['tri'])
        continue
    # Compare each mesh to its bind geometry; mirrored UVs do not change geometry winding.
    p=(m['local']*m['weights'][:,:,None]).sum(axis=1)
    bind=np.zeros((len(DATA['bones']),2))
    for i,b in enumerate(DATA['bones']):
        parent=next((j for j,p in enumerate(DATA['bones']) if p['name']==b.get('parent')),-1)
        bind[i]=[b.get('x',0),b.get('y',0)]+(bind[parent] if parent>=0 else np.zeros(2))
    p+=(bind[m['indices']]*m['weights'][:,:,None]).sum(axis=1);p[:,1]*=-1
    if key[0]!='prone':
        source=np.array([1024,1536])*m['uv']
        transform=REGIONS[m['path']].get('source_to_model')
        if transform:source=source*transform[0]+transform[1:]
        expected=(source-[600,1518])*(443/1518)
        bind_error=max(bind_error,float(np.abs(expected-p).max()))
    reference[key]=areas(p,m['tri'])
assert bind_error<.00003,('Upright parts changed original proportions',bind_error)
assert reference_key_error<.0002,('Reference key pose did not reconstruct its registered source geometry',reference_key_error)
for sample in samples:
    visible=[]
    for slot,(attachment,alpha) in sample['slots'].items():
        if not attachment or alpha<.001:continue
        key=slot,attachment;seen.add(key);m=MESHES[key];p=points(m,sample)
        assert np.isfinite(p).all() and np.abs(p).max()<900,(sample['animation'],slot)
        ratios=areas(p,m['tri'])/reference[key]
        assert (ratios>0).all(),f"Folded {slot} in {sample['animation']} at {sample['phase']}"
        minimum=min(minimum,float(ratios.min()));tested+=len(ratios);visible.append(p)
        if sample['animation']=='death' and sample['phase']==1 and slot=='prone':
            prone_min_y=float(-p[:,1].max());prone_height=float(np.ptp(p[:,1]))
    if visible:
        p=np.concatenate(visible);bounds.setdefault(sample['animation'],[]).append([float(p[:,0].min()),float(p[:,1].min()),float(p[:,0].max()),float(p[:,1].max())])
assert len(seen)==len(MESHES),{'unused_attachments':set(MESHES)-seen}
assert abs(prone_min_y)<2 and abs(prone_height-payload['prone_height'])<.02,(prone_min_y,prone_height)
report=json.loads((ROOT/'work/spine-validation.json').read_text())
report.update({'mesh_pose_samples':len(samples),'layered_attachments_checked':len(seen),'triangle_evaluations':tested,
               'standalone_pose_samples':single_count,'native_mixed_pose_samples':len(samples)-single_count,
               'maximum_original_coordinate_bind_error':bind_error,
               'maximum_reference_source_key_geometry_error':reference_key_error,
               'all_sampled_triangles_preserve_winding':True,'minimum_triangle_area_ratio':minimum,
               'prone_bottom_from_floor_source_pixels':prone_min_y,'prone_height_source_pixels':prone_height,
               'external_rig_files_match_source':True,'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest()})
(ROOT/'work/spine-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'PASS: {len(samples)} native poses, {len(seen)} separate attachments, {tested:,} triangle evaluations; no foldovers. Prone pose rests at ground level.')
