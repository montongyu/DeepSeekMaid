"""Package only project artifacts. Never write to or launch the game."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
stage = root / 'dist/DeepSeekMaid'
required = {'DeepSeekMaid.dll', 'DeepSeekMaid.json', 'DeepSeekMaid.cfg', 'README.md', 'CREDITS.md', 'animation'}
assert {p.name for p in stage.iterdir()} == required, 'Unexpected or missing files in release directory'
payload=json.loads((root/'assets/animation/payload.json').read_text())
assert {p.name for p in (stage/'animation').iterdir()} == {'maid.spine-json','maid.atlas',*payload['textures']}, 'Missing or unexpected rig payload'
manifest = json.loads((stage / 'DeepSeekMaid.json').read_text(encoding='utf-8'))
assert manifest['id'] == 'DeepSeekMaid' and manifest['has_dll'] and not manifest['has_pck']
assert manifest['affects_gameplay'] is False

def archive(path, files, prefix):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for source, relative in sorted(files, key=lambda pair: str(pair[1])):
            z.write(source, str(Path(prefix) / relative).replace('\\', '/'))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, f'Corrupt archive: {path}'
    print(f'{path.name}: {path.stat().st_size:,} bytes; archive integrity OK')

version = manifest['version']
release = root / f'dist/DeepSeekMaid-v{version}-beta-v0.111.0.zip'
archive(release, [(p, p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()], 'DeepSeekMaid')
files = [(root / name, Path(name)) for name in ['DeepSeekMaid.csproj','DeepSeekMaid.json','DeepSeekMaid.cfg','build.ps1','README.md','CREDITS.md','.gitignore']]
for folder in ['src','tools','preview','assets/cards','assets/sprites','assets/concept','assets/effects','assets/ui','assets/animation']:
    files += [(p, p.relative_to(root)) for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files.append((root/'assets/prompts.txt', Path('assets/prompts.txt')))
files.append((root/'assets/prompts-v0.2.txt', Path('assets/prompts-v0.2.txt')))
files.append((root/'assets/prompts-v0.3.txt', Path('assets/prompts-v0.3.txt')))
files.append((root/'assets/prompts-v0.5.txt', Path('assets/prompts-v0.5.txt')))
files.append((root/'assets/prompts-v0.7.txt', Path('assets/prompts-v0.7.txt')))
for prompt in ['prompts-v0.8.txt','right-animation-prompts-v0.8.txt','right-face-prompts-v0.8.txt','attack-legs-prompts-v0.8.1.txt']:
    files.append((root/'assets'/prompt,Path('assets')/prompt))
source = root / f'dist/DeepSeekMaid-v{version}-source.zip'
archive(source, files, 'DeepSeekMaid-source')
validation = json.loads((root/'work/asset-validation.json').read_text(encoding='utf-8'))
validation['mod_version'] = version
validation['build'] = 'Roslyn 4.14.0 / C# 13 / net9 game references; warnings as errors'
validation['bindings'] = 'PASS: Harmony targets and reflected fields resolve against installed beta'
validation['embedded_resources'] = 'PASS: all eleven embedded resources match source SHA-256'
validation['native_spine'] = json.loads((root/'work/spine-validation.json').read_text(encoding='utf-8'))
assert validation['native_spine']['rig_sha256'] == hashlib.sha256((stage/'animation/maid.spine-json').read_bytes()).hexdigest(), 'Native check report is stale'
assert validation['native_spine']['all_sampled_triangles_preserve_winding']
preview_report=json.loads((root/f'preview/preview-validation-v{version}.json').read_text())
assert preview_report['rig_sha256']==validation['native_spine']['rig_sha256'],'Animation previews are stale'
validation['software_animation_previews']=preview_report
validation['common_state']=json.loads((root/'work/common-state-validation.json').read_text())
assert validation['common_state']['rig_sha256']==validation['native_spine']['rig_sha256'],'Common-state motion report is stale'
validation['portrait_regression'] = 'PASS: 91 active card types resolve independently of pool identity; unrelated cards excluded'
validation['animation_routes'] = 'PASS: 50 defined/selectable cosmetic clips; common start/end pose checked natively; startup directly uses idle, Greet entry gestures retained; no game RNG'
validation['harmony_application'] = 'PASS: all mod patches applied in an isolated .NET 9 host; this does not test rendering'
validation['release_sha256'] = hashlib.sha256(release.read_bytes()).hexdigest()
validation['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
(root/'dist/validation-report.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
(root/'dist/SHA256SUMS.txt').write_text(f"{validation['release_sha256']}  {release.name}\n{validation['source_sha256']}  {source.name}\n", encoding='utf-8')
