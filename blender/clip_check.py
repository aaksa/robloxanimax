"""Find actors passing through each other or through solid props, on five frames of every shot. No render.

    Blender -b --factory-startup -P blender/clip_check.py -- <project> [--ids 01,02]

Tests every actor (anima.ACTORS) against every other actor and against every object marked solid (asset(..., solid=True), the
default, or any object you give a custom prop o['solid'] = True). Prints `CLIP <id> clean` or the worst pairs with the number of
overlapping triangles. Face decals, steam and held props (anything parented to a palm) are skipped.
Tiga Tradisi: a plate sat inside an avatar's legs in shot 07; only this scan saw it.
"""
import sys, os, glob, importlib
sys.dont_write_bytecode = True
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
a = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ROOT = os.path.abspath(a[0]); sys.path.insert(0, f'{ROOT}/film')
import anima
anima.open_project(ROOT)
import bpy
from mathutils.bvhtree import BVHTree
mods = [importlib.import_module(os.path.basename(p)[:-3]) for p in sorted(glob.glob(f'{ROOT}/film/act_*.py'))]
IDS = a[a.index('--ids')+1].split(',') if '--ids' in a else list(anima.TL)
SKIP = ('puff', 'mo', 'br', 'lash', 'white', 'ir', 'pu', 'hi', 'sh', 'ar', 'wing', 'crow', 'wr', 'lw', 'nose')


def held(o):
    p = o.parent
    while p:
        if p.name.startswith('palm_'): return True
        p = p.parent
    return False


for i in IDS:
    fn = next((getattr(m, 's'+i) for m in mods if hasattr(m, 's'+i)), None)
    if not fn: continue
    n = anima.TL[i]['n']; anima.new(n, True); fn(n); res = {}
    for f in sorted({1, n//4, n//2, 3*n//4, max(1, n-1)}):
        bpy.context.scene.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); groups = []
        def tree(obs):
            vs, fs = [], []
            for o in obs:
                e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world; b = len(vs)
                vs += [M @ v.co for v in me.vertices]; fs += [[b+v for v in p.vertices] for p in me.polygons]; e.to_mesh_clear()
            return BVHTree.FromPolygons(vs, fs) if fs else None
        for k, act in enumerate(anima.ACTORS):
            if isinstance(act, anima.Toy): obs = list(act.parts)
            else: obs = [getattr(act, 'mesh', None)]
            obs = [o for o in obs if o is not None]
            groups.append((f'{getattr(act, "who", type(act).__name__)}#{k}', tree(obs), True))
        for o in bpy.context.scene.objects:
            if o.type == 'MESH' and o.get('solid') and not held(o) and not o.name.split('.')[0] in SKIP: groups.append((o.name, tree([o]), False))
        for x in range(len(groups)):
            for y in range(x+1, len(groups)):
                A, B = groups[x], groups[y]
                if not (A[2] or B[2]) or not A[1] or not B[1]: continue
                c = len(A[1].overlap(B[1]))
                if c: res[(A[0], B[0])] = max(c, res.get((A[0], B[0]), 0))
    print('CLIP', i, 'clean' if not res else ', '.join(f'{p} x {q}={c}' for (p, q), c in sorted(res.items(), key=lambda t: -t[1])[:7]), flush=True)
