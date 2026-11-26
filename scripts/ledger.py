"""The Meshy ledger: every task, what it cost, where its file went, whether it made the cut. -> assets/ASSETS.md

    python3 -I scripts/ledger.py <project> add <name> <task_id> <kind> <credits> [--ai meshy-t2.5] [--tex meshy-n1] [--file assets/raw/x.glb] [--note ...]
    python3 -I scripts/ledger.py <project> set <name> used yes|no [reason]
    python3 -I scripts/ledger.py <project>                     (rewrite assets/ASSETS.md and print the total)

kind = image | image-to-3d | multi-image-to-3d | text-to-3d | refine | remesh | retexture.
Why: a contest entry or a sponsor asks "which assets are Meshy?", and Tiga Tradisi needed task ids, models and credits per asset
weeks later. Write the row the moment a task SUCCEEDS (and after a failed call, check meshy_list_tasks before paying twice).
"""
import json, os, sys
a = sys.argv[1:]; R = os.path.abspath(a[0]); P = f'{R}/assets/meshy.json'; os.makedirs(f'{R}/assets', exist_ok=True)
L = json.load(open(P)) if os.path.exists(P) else {}
opt = lambda k: a[a.index(k)+1] if k in a else None
if len(a) > 1 and a[1] == 'add':
    name, tid, kind, cr = a[2], a[3], a[4], float(a[5])
    e = L.setdefault(name, {'tasks': []}); e['tasks'].append(dict(id=tid, kind=kind, credits=cr))
    for k, f in (('ai_model', '--ai'), ('texture_model', '--tex'), ('file', '--file'), ('note', '--note')):
        if opt(f): e[k] = opt(f)
elif len(a) > 1 and a[1] == 'set':
    e = L.setdefault(a[2], {'tasks': []}); e[a[3]] = a[4]
    if len(a) > 5: e['why'] = ' '.join(a[5:])
json.dump(L, open(P, 'w'), indent=1, ensure_ascii=False)
tot = sum(t['credits'] for e in L.values() for t in e['tasks'])
rows = ['# Meshy assets', '', f'{len(L)} assets, {tot:g} credits in total. Kept by `scripts/ledger.py`; do not edit by hand.', '',
        '| asset | models | tasks (kind: id) | credits | file | in the film |', '|---|---|---|---|---|---|']
for n, e in L.items():
    m = ' + '.join(x for x in (e.get('ai_model'), e.get('texture_model')) if x)
    ts = '<br>'.join(f"{t['kind']}: `{t['id']}`" for t in e['tasks'])
    used = e.get('used', '?') + (f" ({e['why']})" if e.get('why') else '')
    rows.append(f"| {n} | {m} | {ts} | {sum(t['credits'] for t in e['tasks']):g} | {e.get('file', '')} | {used} |")
open(f'{R}/assets/ASSETS.md', 'w').write('\n'.join(rows)+'\n'); print(f'{len(L)} assets, {tot:g} credits -> assets/ASSETS.md')
