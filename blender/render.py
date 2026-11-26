"""Render a project's shots. Every shot is its own scene, built by a function s<ID>(n) in film/act_*.py.

    Blender -b --factory-startup -P blender/render.py -- <project> [--ids 01,02] [--preview] [--step N] [--out DIR] [--stills .1,.5,.9]

--stills  fractions of each shot -> <out>/<id>_<frame>.jpg (default out dir out/stills). The cheap check before any long render.
--preview a quarter of the size, 16 samples, no motion blur.
Frames go to out/frames/f_<film frame>.jpg. Existing frames are skipped and every frame is claimed with a lock file, so two
workers can walk the same list (scripts/render.sh does that) and a stopped render resumes.
"""
import sys, os, time, traceback, importlib, glob
sys.dont_write_bytecode = True
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
a = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if not a: raise SystemExit('usage: Blender -b --factory-startup -P render.py -- <project> [--ids ..] [--preview] [--stills ..]')
ROOT = os.path.abspath(a[0]); sys.path.insert(0, f'{ROOT}/film')
import anima
anima.open_project(ROOT)
import bpy
opt = lambda k, d=None: a[a.index(k)+1] if k in a else d
frac = opt('--stills'); prev = '--preview' in a; step = int(opt('--step', 1))
out = os.path.abspath(opt('--out', f'{ROOT}/out/stills' if frac else f'{ROOT}/out/frames')); os.makedirs(out, exist_ok=True)
if not anima.TL: raise SystemExit('audio/timeline.json is missing: run scripts/voice.py first')
mods = [importlib.import_module(os.path.basename(p)[:-3]) for p in sorted(glob.glob(f'{ROOT}/film/act_*.py'))]
ids = opt('--ids', ','.join(anima.TL)).split(',')
for i in ids:
    fn = next((getattr(m, 's'+i) for m in mods if hasattr(m, 's'+i)), None)
    if not fn: print('NO SHOT FUNCTION', 's'+i, flush=True); continue
    s = anima.TL[i]; n = s['n']
    want = sorted({max(1, min(n, round(float(x)*n))) for x in frac.split(',')}) if frac else list(range(1, n+1, step))
    nm = lambda f: f'{out}/{i}_{f:04d}.jpg' if frac else f'{out}/f_{s["f0"]+f-1:05d}.jpg'
    if all(os.path.exists(nm(f)) for f in want) and not frac: continue
    try:
        anima.new(n, prev); fn(n); anima.finish(); sc = bpy.context.scene
        sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 92 if frac else 97
        t0 = time.time(); c = 0
        for f in want:
            p = nm(f); lock = p+'.lock'
            if os.path.exists(p) and not frac: continue
            try: os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            except FileExistsError: continue
            try:
                sc.frame_set(f); sc.render.filepath = p[:-4]+'.part.jpg'
                bpy.ops.render.render(write_still=True); os.replace(sc.render.filepath, p); c += 1
            finally: os.remove(lock)
        print(f'SHOT {i} {c} frames {(time.time()-t0)/max(c, 1):.2f} s/frame', flush=True)
    except Exception:
        print('SHOT FAILED', i, flush=True); traceback.print_exc()
