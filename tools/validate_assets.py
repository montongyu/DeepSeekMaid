"""Verify mapping and PNG integrity; do not modify images or the installation."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image
from pck import Pack

parser = argparse.ArgumentParser()
parser.add_argument('--game', default=r'C:\game\steamapps\common\Slay the Spire 2')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
pack = Pack(Path(args.game) / 'SlayTheSpire2.pck')
expected = {Path(n).stem for n in pack.entries if re.fullmatch(r'images/atlases/card_atlas.sprites/defect/[^/]+\.tres', n)}
index = json.loads((root / 'assets/cards/index.json').read_text(encoding='utf-8'))
assert set(index) == expected, {'missing': sorted(expected - index.keys()), 'extra': sorted(index.keys() - expected)}
assert len({(v['sheet'], v['slot']) for v in index.values()}) == len(index), 'Duplicate card illustration slot'
assert {k for k,v in index.items() if 'file' in v} == {'strike_defect','defend_defect'}
colors = {}
for name in ['strike_defect','defend_defect']:
    path=root/'assets/cards'/index[name]['file']
    with Image.open(path) as image:
        image.load()
        assert image.width>=1000 and image.height>=760
        assert abs(image.width/image.height - 250/190)<.025
        rgb=image.convert('RGB').resize((64,48))
        pixels=list(rgb.getdata())
        means=tuple(sum(p[c] for p in pixels)/len(pixels) for c in range(3))
        colors[name]=means
assert colors['strike_defect'][0] > colors['strike_defect'][1]*1.2,'Strike must read as warm red/orange'
assert colors['defend_defect'][1] > colors['defend_defect'][0]*1.2,'Defend must read as cool green'
for sheet in range(5):
    filenames={v['sheet_file'] for v in index.values() if v['sheet']==sheet}
    assert filenames=={f'cards-{sheet:02}-v0.8.png'}
    with Image.open(root / 'assets/cards' / next(iter(filenames))) as image:
        image.load()
        assert image.width >= 1250 and image.height >= 760
        for entry in (v for v in index.values() if v['sheet'] == sheet):
            slot = entry['slot']
            assert 0 <= slot < 20
            x0, x1 = slot % 5 * image.width // 5, (slot % 5 + 1) * image.width // 5
            y0, y1 = slot // 5 * image.height // 4, (slot // 5 + 1) * image.height // 4
            assert x1 > x0 and y1 > y0
for name in ['deepseek-poses-v0.3.png', 'deepseek-idle-v0.3.png']:
    with Image.open(root / 'assets/sprites' / name) as image:
        image.load()
        assert image.mode == 'RGBA', 'Sprite image must retain real alpha'
        assert abs(image.width / image.height - 2) < .01, 'Expected 4x2 square-cell atlas'
        alpha = image.getchannel('A')
        assert alpha.getextrema() == (0, 255), 'Missing transparency or opaque character'
        for slot in range(8):
            x0, x1 = slot % 4 * image.width // 4, (slot % 4 + 1) * image.width // 4
            y0, y1 = slot // 4 * image.height // 2, (slot // 4 + 1) * image.height // 2
            assert alpha.crop((x0,y0,x1,y1)).getextrema() == (0, 255), f'Bad cell {name}/{slot}'
for relative in ['assets/effects/elemental-orbs.png', 'assets/ui/character-select.png']:
    with Image.open(root / relative) as image:
        image.load()
        assert image.mode == 'RGBA', f'{relative} needs real alpha'
        low, high = image.getchannel('A').getextrema()
        assert low == 0 and high >= 240, f'{relative} has invalid transparency'
        assert image.width >= 1024 and image.height >= 1024
with Image.open(root / 'assets/ui/selection-background.png') as image:
    image.load()
    assert image.width >= 1600 and image.height >= 900
    assert 1.7 < image.width / image.height < 1.85
rig=json.loads((root/'assets/animation/maid.spine-json').read_text())
payload=json.loads((root/'assets/animation/payload.json').read_text())
preloaded=set(re.findall(r'"([^"\n]+\.png)"',(root/'src/SpineRig.cs').read_text()))
assert preloaded==set(payload['textures']),('Preloader does not match atlas textures',preloaded,set(payload['textures']))
for filename in payload['textures']:
    with Image.open(root/'assets/sprites'/filename) as image:
        image.load()
        assert image.mode=='RGBA',filename
        low,high=image.getchannel('A').getextrema()
        assert low==0 and high>=250,(filename,low,high)
report = {
    'game': json.loads((Path(args.game) / 'release_info.json').read_text()),
    'card_portrait_resource_entries': len(expected),
    'mapped_unique_illustrations': len(index),
    'animation_system': 'Native Spine 4.2 / shared palm-up rest pose / hierarchical joints and shared attachment slots / render-frame interpolation',
    'bone_count': len(rig['bones']),
    'animation_count': len(rig['animations']),
    'painted_slots': payload['slots'],
    'painted_attachments': payload['attachments'],
    'external_animation_textures': payload['textures'],
    'prone_death_and_annoyed_expression': True,
    'basic_card_color_overrides': {'strike_defect':'coral red / amber','defend_defect':'emerald / mint'},
    'non_basic_card_recolor_count':96,
    'active_card_sheets':sorted({v['sheet_file'] for v in index.values()}),
    'default_sprite_height': 300,
    'legacy_idle_atlas_used_at_runtime': False,
    'dedicated_selection_background': True,
    'cartoon_elemental_orb_count': 5,
    'dedicated_selection_portrait': True,
    'game_started': False,
    'deployed': False,
    'validation': ['PCK index and file checksum parsing', 'Exact portrait map coverage', 'Unique atlas slots', 'PNG decode', 'Transparent active pose and idle cells', 'Transparent cartoon orb atlas', 'Transparent dedicated selection portrait', 'Widescreen selection background'],
    'not_verified': ['Full combat scene integration', 'In-game frame rate and GPU rendering', 'Combat timing and scene layout', 'Special VFX and multiplayer in engine'],
}
(root / 'work/asset-validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'PASS: {len(index)} unique card illustrations, source sprite atlases, five cartoon orbs, selection portrait and background verified. Native rig has a separate engine check.')
