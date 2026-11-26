"""The props shopping list: which props still need a model, by which Meshy route, the exact prompt, and what it all costs.
Show its output to the user and wait for a yes before any Meshy call (references/props.md).

    python3 -I scripts/props_plan.py <project> [--all] [--json]

Reads assets/props.json. Per row:
  "route":  text   Meshy text-to-3D: meshy_text_to_3d preview (ai_model meshy-6, 20) -> meshy_text_to_3d_refine (10)      = 30
            draft  the same on meshy-6-lite: preview (5) -> refine (10); cheap, softer detail, for background props      = 15
            image  meshy_text_to_image (nano-banana, 3) -> the user approves it -> meshy_image_to_3d (meshy-7.1 + meshy-7, 30) = 33
                   (for anything that must look like ONE specific thing: a badik, a tongkonan, a boat type)
            multi  2-4 orthographic views you render of a model you already have -> meshy_multi_image_to_3d (meshy-7.1 + meshy-7) = 30
            reuse  a Meshy model from an earlier film (no cost; say where it came from in "source")
            kit    built in Blender by hand (no cost; when Meshy cannot get it right, or it must stay under your control)
  "prompt": what the prop is (the prefix below is added for you)
  "size":   [x, y, z] studs it will be in the film (a figure is 5.2 studs tall), also the stand-in box until the model exists
--all lists every row, not only those still missing a model. --json prints the calls as JSON for a script or a subagent.
"""
import json, os, sys
a = sys.argv[1:]; R = os.path.abspath(a[0]); SPEC = json.load(open(f'{R}/assets/props.json'))
LEDGER = json.load(open(f'{R}/assets/meshy.json')) if os.path.exists(f'{R}/assets/meshy.json') else {}
PREFIX = ('Realistic miniature film prop, worn natural materials, clean silhouette, single object, no people, no text, no logo, '
          'no base, plain background.')
COST = dict(text=30, draft=15, image=33, multi=30, reuse=0, kit=0)
CALLS = dict(
    text='meshy_text_to_3d {ai_model: "meshy-6", prompt, target_formats: ["glb"]} -> wait -> meshy_text_to_3d_refine {preview_task_id} -> wait -> meshy_download_model {format: "glb", save_to}',
    draft='meshy_text_to_3d {ai_model: "meshy-6-lite", prompt, target_formats: ["glb"]} -> wait -> meshy_text_to_3d_refine -> wait -> meshy_download_model',
    image='meshy_text_to_image {ai_model: "nano-banana", prompt, aspect_ratio: "1:1"} -> SHOW the image, wait for OK -> meshy_image_to_3d {input_task_id, ai_model: "meshy-7.1", texture_model: "meshy-7", target_formats: ["glb"]} -> wait -> meshy_download_model',
    multi='render 2-4 ortho views (front first) -> meshy_multi_image_to_3d {file_paths, ai_model: "meshy-7.1", texture_model: "meshy-7", target_formats: ["glb"]} -> wait -> meshy_download_model',
    reuse='copy the GLB into assets/raw/, set "source"', kit='build it in a film/*.py helper; no props.json model')
rows, total = [], 0
for n, c in SPEC.items():
    route = c.get('route', 'text'); glb = os.path.join(R, c.get('glb', f'assets/raw/{n}.glb'))
    have = os.path.exists(glb) or route == 'kit' or bool(c.get('blend'))
    if have and '--all' not in a: continue
    cost = 0 if (have or route in ('reuse', 'kit')) else COST.get(route, 30); total += cost
    st = 'to make' if not have else 'kit' if route == 'kit' else 'done' if (n in LEDGER or route == 'reuse' or c.get('blend')) else 'NO LEDGER'
    rows.append(dict(name=n, route=route, credits=cost, status=st, size=c.get('size'),
                     prompt=(PREFIX+' '+c['prompt']) if c.get('prompt') else None, save_to=glb, calls=CALLS.get(route)))
if '--json' in a: print(json.dumps(dict(total=total, props=rows), indent=1, ensure_ascii=False)); raise SystemExit
print(f'PROPS PLAN  {len(rows)} prop(s), {total} Meshy credits  (check meshy_check_balance; get a yes before the first call)\n')
for r in rows:
    print(f"- {r['name']:14s} {r['route']:6s} {r['credits']:3d} cr  {r['status']:8s} size {r['size']}")
    if r['status'] == 'NO LEDGER': print('    on disk but not in assets/meshy.json: add its task (scripts/ledger.py) or set route "reuse" + "source"')
    if r['status'] == 'to make':
        if r['prompt']: print(f"    prompt: {r['prompt']}")
        print(f"    calls:  {r['calls']}\n    save:   {os.path.relpath(r['save_to'], R)}")
print('\nAfter each SUCCEEDED task: scripts/ledger.py add ...; after all: blender/prep_props.py, then look at each next to a real photo.')
