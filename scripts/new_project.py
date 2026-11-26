"""Start a film: the folder tree, project.json, board/shots.json, film/act_01.py and the empty ledgers.

    python3 -I scripts/new_project.py <folder> [--name title] [--aspect 9:16|16:9] [--bpm 120]

Refuses to touch a folder that already has a project.json. The templates carry a working two-shot scene with two characters
(anak, nenek); run the demo chain on it once (README "Try it") to see every stage before replacing them with your own.
"""
import json, os, shutil, sys
a = sys.argv[1:]
if not a: raise SystemExit(__doc__)
R = os.path.abspath(a[0]); H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = f'{H}/templates'
opt = lambda k, d=None: a[a.index(k)+1] if k in a else d
if os.path.exists(f'{R}/project.json'): raise SystemExit(f'{R}/project.json exists: not touching it')
for d in ('board', 'ref', 'cast', 'assets/raw', 'audio/vo_src', 'film', 'out', 'logs'): os.makedirs(f'{R}/{d}', exist_ok=True)
pj = json.load(open(f'{T}/project.json')); pj['name'] = opt('--name', os.path.basename(R)); pj['aspect'] = opt('--aspect', '9:16'); pj['bpm'] = float(opt('--bpm', 120))
json.dump(pj, open(f'{R}/project.json', 'w'), indent=1, ensure_ascii=False)
shutil.copy(f'{T}/shots.json', f'{R}/board/shots.json'); shutil.copy(f'{T}/act_01.py', f'{R}/film/act_01.py')
shutil.copy(f'{T}/props.json', f'{R}/assets/props.json')
open(f'{R}/audio/vo_src/phrases.txt', 'w').write('# <who> <start_s> <end_s> <text>   one phrase per row, in take order, ending at real pauses\n')
open(f'{R}/NOTE.md', 'w').write(f"# {pj['name']}\n\nState, decisions, what is checked and what is not. Write it as you go (Tiga Tradisi's NOTE.md is the model).\n")
print('project ready:', R)
