"""Run the bundled engine on an isolated, temporary GDScript project, never the game project."""
import hashlib
import json
import struct
import subprocess
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
GAME=Path(r'C:\game\steamapps\common\Slay the Spire 2')
WORK=ROOT/'work/spine-check'
WORK.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser()
parser.add_argument('--inspect-hunter',action='store_true')
args=parser.parse_args()

def make_pack(path,files):
    records=[]
    directory_size=100
    for name,data in files.items():
        raw=name.encode()+b'\0';raw+=b'\0'*((-len(raw))%4)
        directory_size+=4+len(raw)+8+8+16+4
        records.append((raw,data))
    offset=(directory_size+31)//32*32
    with path.open('wb') as f:
        f.write(struct.pack('<6IQ',0x43504447,2,4,5,1,0,0)+b'\0'*64)
        f.write(struct.pack('<I',len(records)))
        locations=[]
        for raw,data in records:
            f.write(struct.pack('<I',len(raw))+raw+struct.pack('<QQ',offset,len(data))+hashlib.md5(data).digest()+struct.pack('<I',0))
            locations.append(offset);offset=(offset+len(data)+31)//32*32
        for (_,data),location in zip(records,locations):
            f.write(b'\0'*(location-f.tell()));f.write(data)

config='''config_version=5
[application]
config/name="DeepSeekMaid isolated Spine verification"
[debug]
file_logging/enable_file_logging=false
[rendering]
renderer/rendering_method="gl_compatibility"
'''
extension='''[configuration]
entry_symbol="spine_godot_library_init"
compatibility_minimum="4.1"
[libraries]
windows.x86_64="'''+(GAME/'libspine_godot.windows.template_release.x86_64.dll').as_posix()+'''"
'''
files={
    'project.godot':config.encode(),
    '.godot/extension_list.cfg':b'res://spine.gdextension\n',
    '.godot/global_script_class_cache.cfg':b'list=[]\n',
    'spine.gdextension':extension.encode(),
    'main.gd':(ROOT/'tools'/('hunter_check.gd' if args.inspect_hunter else 'common_check.gd')).read_bytes(),
}
pack=WORK/'check.pck'
make_pack(pack,files)
command=[str(GAME/'SlayTheSpire2.exe'),'--headless','--main-pack',str(pack),'--path',str(WORK),'--log-file',str(WORK/'engine.log'),'--script','res://main.gd','--',str(ROOT)]
result=subprocess.run(command,cwd=WORK,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
(WORK/'output.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
print(result.stdout)
if result.stderr: print(result.stderr)
marker='PASS: hunter inspection' if args.inspect_hunter else 'PASS: native Spine'
if result.returncode or marker not in result.stdout:
    raise SystemExit('Native Spine check did not pass. See work/spine-check/output.log.')
