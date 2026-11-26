"""robloxanimax runtime: the Meshy cast on rigid joints with a LIVE face, the shot scene, world helpers, camera, timeline helpers.

Import it from a project's film/act_*.py through `from anima import *` (blender/render.py puts it on the path and calls
open_project). Frames inside a shot function are LOCAL: 1..n, where n is the shot's length from audio/timeline.json.

Built on cinematicanimation's cine_kit (K): materials, boxes, lamps, Cam, keys, EEVEE setup. Distilled from Tiga Tradisi
(Roblox/tiga-tradisi, Nov 2026): film/actors.py, film/world.py, film/common.py.
"""
import sys, os, json, math, random
sys.dont_write_bytecode = True
_CINE = os.environ.get('CINE_KIT') or os.path.expanduser('~/.claude/skills/cinematicanimation/blender')
if not os.path.exists(os.path.join(_CINE, 'cine_kit.py')):
    raise SystemExit(f'robloxanimax needs cinematicanimation (cine_kit.py not found in {_CINE}). Install it or set CINE_KIT.')
sys.path.insert(0, _CINE)
import bpy, bmesh
from mathutils import Vector, Matrix
import cine_kit as K

D = math.radians
F = K.flat
R = random.Random(11)
ROOT = None          # the project folder
P = {}               # project.json
TL = {}              # shot id -> timeline entry
ACTORS = []          # every actor made in the current shot (clip_check reads it)
KEEP = []            # lights that keep their shadow under EEVEE
_T, _P = {}, {}      # cast / prop caches (per shot)


# ---------------------------------------------------------------- project
def open_project(root):
    """Load project.json and audio/timeline.json. Called once by render.py / clip_check.py."""
    global ROOT, P, TL
    ROOT = os.path.abspath(root)
    P.clear(); P.update(json.load(open(f'{ROOT}/project.json')))
    t = f'{ROOT}/audio/timeline.json'
    TL.clear()
    if os.path.exists(t): TL.update({s['id']: s for s in json.load(open(t))['shots']})
    return P


def new(n, preview=False):
    """A fresh scene for one shot of n frames. preview = a quarter of the size (even pixel sizes), 16 samples, no motion blur."""
    asp = P.get('aspect', '9:16'); w = P.get('width', 1080)
    K.setup(aspect=asp, height=w, fps=P.get('fps', 24), samples=16 if preview else P.get('samples', 24), engine=P.get('engine', 'EEVEE'), preview=False)
    sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, n
    if preview: sc.render.resolution_percentage = 25; sc.render.use_motion_blur = False; sc.eevee.taa_render_samples = 16
    if sc.render.engine.startswith('BLENDER_EEVEE'):
        e = sc.eevee; e.volumetric_tile_size = '8'; e.volumetric_samples = 32; e.volumetric_end = 70
        try: e.ray_tracing_options.resolution_scale = '2'
        except Exception: pass
    _T.clear(); _P.clear(); KEEP.clear(); ACTORS.clear(); R.seed(11); K._ATLAS = None


def finish():
    """After a shot is built: only KEEP lights cast shadows (EEVEE flicker), and big textures are scaled to what the frame shows."""
    if bpy.context.scene.render.engine.startswith('BLENDER_EEVEE'):
        K.eevee_lights(keep=tuple(KEEP), min_power=1e9); bpy.context.scene.eevee.shadow_pool_size = '512'
    for im in bpy.data.images:                                  # 4K maps on 300 px of screen make the GPU swap
        try:
            w, h = im.size[:]
            lim = 2700 if w > 5000 else 2048 if 'face' in im.name.lower() else 1024
            if max(w, h) > lim: im.scale(max(1, round(w*lim/max(w, h))), max(1, round(h*lim/max(w, h))))
        except RuntimeError as e: print('texture kept', im.name, e)


# ---------------------------------------------------------------- timeline helpers (shot-local frames)
def N(i): return TL[i]['n']
def line(i, k=0):
    """First and last local frame of the k-th spoken line of shot i."""
    q = TL[i]['lines'][k]; return q['f0']-TL[i]['f0']+1, q['f1']-TL[i]['f0']+1
def word(i, w, nth=0):
    """Local frame on which a word (substring, lower case) starts. Falls back to the middle of the shot."""
    hits = [x['f'] for q in TL[i]['lines'] for x in q['words'] if w in x['word'].lower()]
    return max(1, hits[nth]-TL[i]['f0']+1) if len(hits) > nth else N(i)//2
def talk(actor, i, k=0, rest='smile'):
    """Lip-sync line k of shot i on this actor."""
    actor.talk(TL[i]['lines'][k]['words'], rest, TL[i]['f0']-1)


# ---------------------------------------------------------------- keys
def key(ob, path, *kv, ease='BEZIER'):
    for f, v in kv: K.key(ob, path, f, v, ease)
    return ob
def mv(ob, *kv, ease='BEZIER'): return key(ob, 'location', *kv, ease=ease)
def rot(ob, *kv, ease='BEZIER'): return key(ob, 'rotation_euler', *[(f, tuple(D(x) for x in v)) for f, v in kv], ease=ease)
def show(ob, f0, f1):
    for o in [ob, *ob.children_recursive]: K.visible(o, [(f0, f1)])
def light(name, kind, loc, power, color=2700, target=None, size=1.0, spot=60, blend=.4, shadow=False, parent=None):
    """K.light, plus shadow=True to keep its shadow under EEVEE. Keep 1-3 shadow lights per shot."""
    o = K.light(name, kind, loc, power, color, target=target, size=size, spot=spot, blend=blend, parent=parent)
    if shadow: KEEP.append(o.name)
    return o


# ---------------------------------------------------------------- face decals
def _ck(ob, path, f, v): K.key(ob, path, f, v, 'CONSTANT')
def _shape(name, pts, m, parent, loc=(0, 0, 0)):
    """A flat face decal in XZ, facing -Y."""
    vs = [(x, 0, z) for x, z in pts]; me = bpy.data.meshes.new(name); me.from_pydata(vs, [], [list(range(len(vs)))]); me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = loc; o.visible_shadow = False; return K._link(o, parent)
def oval(rx, rz, cx=0, cz=0, a0=0, a1=360, n=28):
    return [(cx+rx*math.cos(D(a0+(a1-a0)*i/n)), cz+rz*math.sin(D(a0+(a1-a0)*i/n))) for i in range(n+(a1-a0 < 360))]
def arc(rx, rz, a0, a1, th, cz=0): return oval(rx, rz, 0, cz, a0, a1, 14)+oval(rx-th*.4, rz-th, 0, cz, a0, a1, 14)[::-1]

# expression: (brow raise, brow inner-end lift in degrees, eye openness 0..1.2 (0 = happy arcs), mouth shape)
EX = dict(neutral=(0, 0, 1, 'line'), smile=(.02, 4, 1, 'smile'), hope=(.06, 14, 1.06, 'small'), soft=(.02, 10, .82, 'small'),
          grin=(.06, 4, 0, 'grin'), happy=(.05, 6, 0, 'smile'), wide=(.14, 8, 1.2, 'o'), ask=(.1, 16, 1.1, 'small'), sad=(.03, 20, .85, 'frown'),
          stern=(-.04, -14, .85, 'line'), worry=(.07, 22, 1.08, 'o'), strain=(-.03, -16, .6, 'teeth'), call=(.1, 12, 1.05, 'a'), relief=(.06, 14, .8, 'smile'),
          sleep=(0, 0, 0, 'line'))
MOUTHS = ('smile', 'small', 'line', 'grin', 'frown', 'o', 'a', 'e', 'm', 'teeth')
FACE_DEFAULT = dict(eye=4.38, r=.15, dx=.32, mouth=4.06, brow='#1A100C', lips='#3A170F', iris='#4A2618', nose='#9C5A36', old=0, lash=0, nose_on=1)


class Face:
    """Eyes (white, iris, pupil, highlight), lids for blinks, happy arcs, brows, nose, ten mouth shapes, all flat decals on the head.
    Heights in project.json -> cast.<name>.face are in studs of the 5.2-stud reference body (before the cast's scale)."""
    def __init__(self, who, joint, data, pivot):
        c = dict(FACE_DEFAULT); c.update(P.get('cast', {}).get(who, {}).get('face', {}))
        S = data['scale']; y = data['y_eye']-.015; self.c = c; self.S = S; self.eye_open = [(1, 1)]
        root = self.root = K.empty('face', (0, y, 0), joint); z = lambda v: v*S-pivot[2]
        w, ink, ir, hi = K.flat('#E4DED4', .85), K.flat('#120B08', .7), K.flat(c['iris'], .7), K.emit('#FFFFFF', .9)
        br, red, th, pink = K.flat(c['brow'], .6), K.flat('#54161A', .6), K.flat('#F0EBE0', .4), K.flat('#B9605C', .6)
        lip = K.flat(c['lips'], .5); r = c['r']; self.eyes, self.iris, self.shut, self.arch, self.brows = [], [], [], [], []
        for s in (-1, 1):
            p = (s*c['dx']*S, 0, z(c['eye'])); e = K.empty('eye', p, root); self.eyes.append(e)
            _shape('lash', oval(r*1.12, r*1.06, 0, .012), ink, e); _shape('white', oval(r, r*.92), w, e, (0, -.006, 0))
            i = K.empty('iris', (0, -.012, 0), e); self.iris.append(i)
            _shape('ir', oval(r*.67, r*.78), ir, i); _shape('pu', oval(r*.38, r*.5), ink, i, (0, -.005, 0)); _shape('hi', oval(r*.22, r*.24, -r*.2, r*.3), hi, i, (0, -.01, 0))
            if c['lash']: _shape('wing', [(s*r*.8, r*.5), (s*r*1.5, r*.95), (s*r*1.1, r*.2)][::s], ink, e, (0, -.014, 0))
            q = K.empty('shut', p, root); _shape('sh', arc(r*1.1, r*.5, 200, 340, .05, r*.2), ink, q, (0, -.004, 0)); self.shut.append(q)
            q = K.empty('arch', p, root); _shape('ar', arc(r*1.1, r*.8, 20, 160, .055, -r*.3), ink, q, (0, -.004, 0)); self.arch.append(q)
            b = K.empty('brow', (p[0], -.03, p[2]+r+.085), root); self.brows.append(b)
            _shape('br', [(-r*1.15, -.025), (0, .005), (r*1.15, -.025), (r*1.1, .025), (0, .055), (-r*1.1, .025)], br, b)
            if c['old']:
                for k in (-1, 0, 1): _shape('crow', [(s*r*1.25, .02*k), (s*r*1.85, .075*k+.008), (s*r*1.85, .075*k-.008)], lip, root, (p[0], -.003, p[2]))
        if c['old']:
            for k in (0, 1): _shape('wr', arc(.36-.1*k, .06, 30, 150, .022), K.flat('#7A4530'), root, (0, -.003, z(c['eye']+.36+.06*k)))
            for s in (-1, 1): _shape('lw', [(0, 0), (s*.07, -.17), (s*.05, -.18)][::s], K.flat('#7A4530'), root, (s*.3, -.003, z(c['mouth']+.08)))
        if c['nose_on']:
            n = K.cyl('nose', .085*S, .08*S, (0, -.02, z((c['eye']+c['mouth'])/2+.01)), K.plastic(c['nose']), .03, rot=(90, 0, 0), parent=root); n.visible_shadow = False
        M = self.m = {k: K.empty('m_'+k, (0, -.008, z(c['mouth'])), root) for k in MOUTHS}
        Q = lambda k, pts, m, y=0: _shape('mo', pts, m, M[k], (0, y, 0))
        Q('smile', arc(.22, .13, 200, 340, .045, .07), lip); Q('small', arc(.14, .08, 210, 330, .035, .05), lip); Q('frown', arc(.15, .09, 30, 150, .035, -.05), lip)
        Q('line', [(-.13, -.015), (.13, -.015), (.13, .015), (-.13, .015)], lip); Q('m', [(-.09, -.012), (.09, -.012), (.09, .016), (-.09, .016)], lip)
        Q('grin', oval(.25, .2, 0, .05, 180, 360), red); Q('grin', [(-.24, .05), (-.22, -.01), (.22, -.01), (.24, .05)], th, -.006); Q('grin', oval(.11, .05, 0, -.1), pink, -.005)
        Q('o', oval(.085, .105), red); Q('a', oval(.15, .12, 0, -.02), red); Q('a', oval(.08, .04, 0, -.09), pink, -.005); Q('a', [(-.1, .06), (.1, .06), (.11, .03), (-.11, .03)], th, -.006)
        Q('e', oval(.17, .07), red); Q('e', [(-.13, .035), (.13, .035), (.14, .005), (-.14, .005)], th, -.006); Q('teeth', oval(.19, .075), th)
        for e in M.values(): e.scale = (S, S, S)
        self.mouth(1, 'line'); self.set(1, 'neutral')

    def mouth(self, f, k):
        for n, e in self.m.items(): s = self.S if n == k else 0; _ck(e, 'scale', f, (s, s, s))
    def _eyes(self, f, o, blink=False):
        for e, s, a in zip(self.eyes, self.shut, self.arch):
            show = 0 if blink or o == 0 else o; _ck(e, 'scale', f, (1 if show else 0, 1, show))
            v = 1 if blink else 0; _ck(s, 'scale', f, (v, v, v)); v = 1 if (o == 0 and not blink) else 0; _ck(a, 'scale', f, (v, v, v))
    def _open_at(self, f): return [v for g, v in sorted(self.eye_open, key=lambda p: p[0]) if g <= f][-1]
    def set(self, f, ex):
        dz, rr, o, m = EX[ex]; self.eye_open.append((f, o))
        if ex == 'sleep': self._eyes(f, 1, True)
        else: self._eyes(f, o)
        self.mouth(f, m)
        for i, b in enumerate(self.brows):
            base = self.eyes[i].location.z+self.c['r']+.085
            _ck(b, 'location', f, (b.location.x, -.03, base+dz)); _ck(b, 'rotation_euler', f, (0, D(rr)*(1 if i == 0 else -1)*-1, 0))
    def blink(self, f):
        o = self._open_at(f)
        if o == 0: return
        self._eyes(f, o*.4); self._eyes(f+1, o, True); self._eyes(f+3, o*.55); self._eyes(f+4, self._open_at(f+4))
    def look(self, f, x=0, z=0, dur=2):
        r = self.c['r']
        for i in self.iris:
            K.key(i, 'location', max(1, f-dur), tuple(K.value_at(i, 'location', max(1, f-dur))))
            K.key(i, 'location', f, (x*r*.36, -.012, z*r*.3))


# ---------------------------------------------------------------- the Meshy cast
class Toy:
    """A Meshy character prepared by blender/prep_cast.py (cast/<who>.blend): rigid head, body, arms, legs (or a skirt 'lower')
    on joints, plus a live Face. Channels: arm_l/arm_r=(forward, out, twist), head/torso=(nod, turn, tilt), leg_l/leg_r/lower=deg,
    tip=(lean fwd, lean side), at=(x,y,z), yaw=deg. Frames are local to the shot."""
    REST = dict(arm_l=(0, 7, 0), arm_r=(0, 7, 0), head=(0, 0, 0), torso=(0, 0, 0), leg_l=0, leg_r=0, lower=0, tip=(0, 0))

    def __init__(self, who, at=(0, 0, 0), yaw=0, size=1.0, face='neutral'):
        if who not in _T:
            path = f'{ROOT}/cast/{who}.blend'
            if not os.path.exists(path): raise FileNotFoundError(f'{path}: run blender/prep_cast.py for {who} first')
            with bpy.data.libraries.load(path) as (s, d): d.objects = list(s.objects)
            _T[who] = list(d.objects)
        self.who = who; self.root = K.empty(who, at); self.root.rotation_euler.z = D(yaw); self.size = size; self.root.scale = (size,)*3
        T = {o['part']: o for o in _T[who]}; piv = {k: Vector(o['pivot']) for k, o in T.items()}
        self.S = S = T['head']['scale']; self.tip = K.empty(who+'_tip', parent=self.root); J = self.j = {}
        J['body'] = K.empty(who+'_waist', piv['body'], self.tip)
        for k in ('head', 'arm_l', 'arm_r', 'lower', 'leg_l', 'leg_r'):
            if k not in T: continue
            par = J['body'] if k in ('head', 'arm_l', 'arm_r') else J.get('lower', self.tip) if k.startswith('leg') else self.tip
            off = piv[k]-(piv['body'] if par is J['body'] else piv['lower'] if par is J.get('lower') else Vector())
            J[k] = K.empty(f'{who}_{k}', off, par)
        self.parts = []
        for k, o in T.items():
            c = o.copy(); c.animation_data_clear(); c.location = (0, 0, 0); c.rotation_euler = (0, 0, 0); c.parent = None; K._link(c, J[k]); self.parts.append(c)
        self.palm = {s: K.empty(f'palm_{s}', (0, 0, -2.0*S), J['arm_'+s]) for s in 'lr'}     # parent props here to hold them
        self.head = K.empty(who+'_headmid', (0, 0, .62*S), J['head']); self.waist = J['body']
        self.f = Face(who, J['head'], T['head'], piv['head'])
        self.pose(1, at=at, yaw=yaw, **self.REST); self.face(1, face); ACTORS.append(self)

    def _ch(self, k, v):
        if k == 'at': return self.root, 'location', tuple(v)
        if k == 'yaw': return self.root, 'rotation_euler', (0, 0, D(v))
        if k == 'tip': return self.tip, 'rotation_euler', (D(v[0]), D(v[1]), 0)
        j = self.j.get('body' if k == 'torso' else k)
        if j is None: return None
        if k in ('arm_l', 'arm_r'):
            sx = 1 if k.endswith('l') else -1; f, o, t = v; return j, 'rotation_euler', (D(-f), D(-o*sx), D(t*sx))
        if k in ('leg_l', 'leg_r', 'lower'): return j, 'rotation_euler', (D(-v), 0, 0)
        return j, 'rotation_euler', (D(v[0]), D(v[2]), D(v[1]))
    def pose(self, f, ease='BEZIER', **ch):
        """Key channels on frame f (eased into from the previous key)."""
        for k, v in ch.items():
            q = self._ch(k, v)
            if q: K.key(q[0], q[1], f, q[2], ease)
        return self
    def hit(self, f, dur=4, **ch):
        """Arrive on frame f: anticipation, snap, 8 % overshoot, settle 4 frames later."""
        for k, v in ch.items():
            q = self._ch(k, v)
            if not q: continue
            ob, p, to = q; a = Vector(K.value_at(ob, p, max(1, f-dur))); b = Vector(to); d = b-a
            K.key(ob, p, max(1, f-dur-3), tuple(a))
            if f-dur > 1: K.key(ob, p, f-dur, tuple(a-d*.07))
            K.key(ob, p, max(2, f), tuple(b+d*.08)); K.key(ob, p, max(2, f)+4, tuple(b))
        return self
    def face(self, f, ex): self.f.set(f, ex); return self
    def blink(self, *fs):
        for f in fs: self.f.blink(f)
        return self
    def look(self, f, x=0, z=0): self.f.look(f, x, z); return self
    def talk(self, words, rest='smile', off=0):
        """words = [{'word', 'f', 'e'}] in film frames; off = shot f0-1. Vowels pick the mouth, b/m/p close it."""
        V = dict(a='a', e='e', i='e', o='o', u='o', m='m', b='m', p='m')
        for w in words:
            cs = [c for c in w['word'].lower() if c in V] or ['a']; a, b = w['f']-off, w['e']-off; st = max(2, (b-a)/len(cs))
            for i, c in enumerate(cs):
                f = int(a+i*st)
                if f < b or i == 0: self.f.mouth(max(1, f-1), V[c])
            self.f.mouth(max(2, int(b)), EX[rest][3])
        return self
    def walk(self, f0, f1, a, b, stride=8, swing=24, arms=True, yaw=None, bob=.09, phase=0):
        """Walk from a to b (xy or xyz) between f0 and f1; faces the way it walks unless yaw is given."""
        a, b = Vector(a).to_3d(), Vector(b).to_3d(); d = b-a
        y = math.degrees(math.atan2(d.x, -d.y)) if yaw is None else yaw; f = f0; i = phase; self.pose(f0, 'LINEAR', yaw=y)
        while True:
            e = f >= f1; g = f1 if e else f; u = (g-f0)/max(1, f1-f0); p = a.lerp(b, u); sw = 0 if e else swing*(1 if i % 2 else -1)
            self.pose(g, 'LINEAR', at=p); self.pose(g, leg_l=sw, leg_r=-sw, lower=sw*.12, tip=(0, 0 if e else sw*.12))
            if arms: self.pose(g, arm_l=(-sw*.7, 7, 0), arm_r=(sw*.7, 7, 0))
            if bob and not e and g+stride/2 < f1: self.pose(int(g+stride/2), at=a.lerp(b, (g+stride/2-f0)/(f1-f0))+Vector((0, 0, bob)))
            if e: break
            f += stride; i += 1
        return self
    def sit(self, f=1): return self.pose(f, leg_l=88, leg_r=88, lower=88)
    def life(self, n, amount=1.0, blinks=True):
        """Never a still frame: joint drift, breathing on the waist, blinks every 1.6-3 s. Call last."""
        for k, j in self.j.items():
            if k.startswith('leg'): continue
            K.drift(j, amount=(.03 if k == 'head' else .022)*amount, period=R.uniform(16, 30))
        f, up = 1-R.randint(0, 12), R.random() < .5
        while f < n+18:
            K.key(self.waist, 'scale', f, (1.014, 1.03, 1.02) if up else (1, 1, 1)); up = not up; f += R.randint(15, 19)
        if blinks:
            f = R.randint(9, 34)
            while f < n-5: self.blink(f); f += R.randint(40, 74)
        return self


class You(K.Avatar):
    """The user's own avatar (cinematicanimation K.Avatar, painted face rig) with cloth instead of chrome, plus a walk."""
    def __init__(self, at=(0, 0, 0), yaw=0, pose='relax', size=1.0):
        super().__init__(at=at, yaw=yaw, pose=pose); self.root.scale = (size,)*3
        nt = self.mesh.active_material.node_tree
        for b in [x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED']:
            for l in list(b.inputs['Metallic'].links): nt.links.remove(l)
            for l in list(b.inputs['Roughness'].links): nt.links.remove(l)
            b.inputs['Metallic'].default_value = 0; b.inputs['Roughness'].default_value = .62
        self.pose(1, at=at, yaw=yaw, head=(0, 0, 0), spine=(0, 0, 0), thigh_L=(0, 0, 0), thigh_R=(0, 0, 0)); ACTORS.append(self)
    def walk(self, f0, f1, a, b, stride=8, yaw=None):
        a, b = Vector(a).to_3d(), Vector(b).to_3d(); d = b-a; y = math.degrees(math.atan2(d.x, -d.y)) if yaw is None else yaw
        f, s = f0, 1; self.pose(f0, ease='LINEAR', yaw=y)
        while True:
            e = f >= f1; g = min(f, f1); p = a.lerp(b, (g-f0)/max(1, f1-f0)); w = 0 if e else 26*s
            self.pose(g, ease='LINEAR', at=p); self.pose(g, thigh_L=(w, 0, 0), thigh_R=(-w, 0, 0), spine=(4, 0, w*.06))
            if e: break
            f += stride; s = -s
        return self


# ---------------------------------------------------------------- camera
class Cam:
    """Keys: (frame, loc, target[, lens[, stop[, focus]]]). Give every shot a real move. hand = handheld amount."""
    def __init__(self, *keys, hand=0.0, roll=None):
        f, loc, tgt, *r = keys[0]; lens = r[0] if r else 28; stop = r[1] if len(r) > 1 else 8
        C = self.c = K.Cam('Cam', loc, tgt, lens=lens, stop=stop, focus=r[2] if len(r) > 2 else tgt)
        for f, loc, tgt, *r in keys:
            C.at(f, loc=loc, target=tgt, lens=r[0] if r else None, stop=r[1] if len(r) > 1 else None, focus=r[2] if len(r) > 2 else tgt)
        for f, v in roll or (): C.at(f, roll=v)
        if hand: C.handheld(hand)
        bpy.context.scene.camera = C.ob; C.ob.data.clip_start = .08; C.ob.data.clip_end = 500
    def shake(self, f, amp=.15, dur=10):
        """A hit on frame f (a slam, a landing): decaying shake of the aim point."""
        ob = self.c.target; base = Vector(K.value_at(ob, 'location', f))
        for i in range(0, dur, 2):
            a = amp*(1-i/dur)**2; K.key(ob, 'location', f+i, tuple(base+Vector((a if i % 4 else -a, 0, -a if i % 4 else a))))
        K.key(ob, 'location', f+dur, tuple(Vector(K.value_at(ob, 'location', f+dur))))


def wipe(cam, kv, color='#1A0E08', tilt=8, w=1.9):
    """A dark board crossing the lens, for a hand-over cut: kv = (frame, x) in lens space; x = 0 covers the frame."""
    o = K.box('wipe', (w, 2.6, .03), (3, 0, -.75), K.wood(color, '#3A2014'), rot=(0, 0, tilt), parent=cam.c.ob, bevel=.01); o.visible_shadow = False
    return mv(o, *[(f, (x, 0, -.75)) for f, x in kv])


# ---------------------------------------------------------------- world
def sky(hor, top, amb='#1A1E2A', amb_s=.35, s=1.0):
    """A gradient the camera sees (hor -> top) and a separate, dim ambient colour that lights the scene."""
    w = bpy.context.scene.world; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear(); Nn, L = nt.nodes.new, nt.links.new
    tc, sp, rp = Nn('ShaderNodeTexCoord'), Nn('ShaderNodeSeparateXYZ'), Nn('ShaderNodeValToRGB'); e = rp.color_ramp.elements
    e[0].position = 0; e[0].color = K.col(hor); e[1].position = .5; e[1].color = K.col(top)
    L(tc.outputs['Generated'], sp.inputs[0]); L(sp.outputs['Z'], rp.inputs[0])
    a, b, mx, lp, o = Nn('ShaderNodeBackground'), Nn('ShaderNodeBackground'), Nn('ShaderNodeMixShader'), Nn('ShaderNodeLightPath'), Nn('ShaderNodeOutputWorld')
    a.inputs[0].default_value = K.col(amb); a.inputs[1].default_value = amb_s; L(rp.outputs[0], b.inputs[0]); b.inputs[1].default_value = s
    L(lp.outputs['Is Camera Ray'], mx.inputs[0]); L(a.outputs[0], mx.inputs[1]); L(b.outputs[0], mx.inputs[2]); L(mx.outputs[0], o.inputs[0])


def mesh(name, vs, fs, m, parent=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in vs], [], fs); me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = loc; return K._link(o, parent)
def beam(a, b, r, m, parent=None, r2=None):
    a, b = Vector(a), Vector(b); o = K.cyl('beam', r, (b-a).length, (a+b)/2, m, bevel=0, verts=12, parent=parent, radius2=r2)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler(); return o


def ground(tint='#8A6A50', wet=False, size=240, texture=None):
    """A ground plane. texture = a folder with an ambientCG set (*_Color.jpg, *_NormalGL.jpg); project.json 'ground_texture' is
    the default. Without one, a noise-broken procedural soil."""
    texture = texture or P.get('ground_texture')
    if wet: m = K.asphalt(.5, '#22262C')
    else:
        m = bpy.data.materials.new('ground'); m.use_nodes = True; nt = m.node_tree; Nn, L = nt.nodes.new, nt.links.new
        b = next(x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'); b.inputs['Roughness'].default_value = .9
        tc, mp = Nn('ShaderNodeTexCoord'), Nn('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (size/14, size/14, 1); L(tc.outputs['UV'], mp.inputs[0])
        col = os.path.expanduser(texture) if texture else None
        cf = [x for x in os.listdir(col) if x.endswith('_Color.jpg')] if col and os.path.isdir(col) else []
        if cf:
            t = Nn('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{col}/{cf[0]}', check_existing=True); L(mp.outputs[0], t.inputs[0])
            mix = Nn('ShaderNodeVectorMath'); mix.operation = 'MULTIPLY'; L(t.outputs[0], mix.inputs[0]); mix.inputs[1].default_value = K.col(tint)[:3]; L(mix.outputs[0], b.inputs['Base Color'])
            nf = [x for x in os.listdir(col) if x.endswith('_NormalGL.jpg')]
            if nf:
                n, nm = Nn('ShaderNodeTexImage'), Nn('ShaderNodeNormalMap'); n.image = bpy.data.images.load(f'{col}/{nf[0]}', check_existing=True)
                n.image.colorspace_settings.name = 'Non-Color'; L(mp.outputs[0], n.inputs[0]); L(n.outputs[0], nm.inputs['Color']); L(nm.outputs[0], b.inputs['Normal'])
        else:
            nz = Nn('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 8; L(mp.outputs[0], nz.inputs['Vector'])
            rp = Nn('ShaderNodeValToRGB'); e = rp.color_ramp.elements; c = K.col(tint)
            e[0].color = tuple(v*.55 for v in c[:3])+(1,); e[1].color = c; L(nz.outputs['Fac'], rp.inputs[0]); L(rp.outputs[0], b.inputs['Base Color'])
            bp = Nn('ShaderNodeBump'); bp.inputs['Strength'].default_value = .4; L(nz.outputs['Fac'], bp.inputs['Height']); L(bp.outputs[0], b.inputs['Normal'])
    s = size/2; o = mesh('ground', [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [(0, 1, 2, 3)], m); uv = o.data.uv_layers.new()
    for l, c in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))): l.uv = c
    return o


def stars(n=520, y=95):
    ms = [K.emit('#C8D8FF', s) for s in (2, 5, 12)]
    for i in range(n):
        r = R.uniform(.06, .17); o = K.box('star', (r, r, r), (R.uniform(-70, 70), y, R.uniform(6, 120)), ms[i % 3], bevel=0); o.visible_shadow = False
def bulb(p, power=900, c=2400, r=.28, parent=None, shadow=False, glow=35):
    """A visible bulb + its point light. Every lamp the lens sees is a highlight (GATE L wants a peak over 0.85)."""
    o = K.cyl('bulb', r, r*1.3, p, K.emit(c, glow), bevel=.05, verts=20, parent=parent); o.visible_shadow = False
    return o, (light('bulb_l', 'POINT', p, power, c, size=.4, shadow=shadow, parent=parent) if power else None)
def lamp(loc, power=1500, f1=0, swing=2.5, shadow=True, cord=6):
    """A hanging lamp, bulb at loc. f1 > 0 sways it until frame f1."""
    r = K.empty('lamp', (loc[0], loc[1], loc[2]+cord)); K.cyl('cord', .03, cord, (0, 0, -cord/2), F('#050505'), bevel=0, verts=8, parent=r)
    K.cyl('shade', .85, .5, (0, 0, -cord+.35), F('#14100C', .4, 1), bevel=0, radius2=.2, parent=r)
    bulb((0, 0, -cord), power, 2500, .24, r, shadow)
    if f1:
        f, s = -10, 1
        while f < f1+30: rot(r, (f, (swing*s*.4, swing*s, 0))); f += 28; s = -s
    return r
def motes(lo, hi, n, f1, c='#FFB060', v=(.3, 0, .25), s=.035, glow=4):
    """Dust or embers drifting through a light: the air is alive."""
    m = K.emit(c, glow)
    for i in range(n):
        r = R.uniform(.4, 1.2)*s; p = Vector([R.uniform(a, b) for a, b in zip(lo, hi)])
        o = K.box('mote', (r, r, r), p, m, bevel=0); o.visible_shadow = False
        d = Vector(v)*f1/24*R.uniform(.4, 1.6)+Vector((R.uniform(-.5, .5), R.uniform(-.5, .5), R.uniform(-.2, .3)))
        mv(o, (1, tuple(p)), (f1, tuple(p+d)), ease='LINEAR'); rot(o, (1, (0, 0, 0)), (f1, (180, 90, 200)), ease='LINEAR')
def steam(parent, at, f1, n=13, h=1.7, r=.2):
    """Soft rising puffs (hot food, a kettle, breath in the cold) that loop until f1."""
    m = bpy.data.materials.new('steam'); m.use_nodes = True; nt = m.node_tree; b = next(x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (1, .9, .8, 1); b.inputs['Emission Color'].default_value = (1, .72, .5, 1); b.inputs['Emission Strength'].default_value = .5
    lw, p, mu = nt.nodes.new('ShaderNodeLayerWeight'), nt.nodes.new('ShaderNodeMath'), nt.nodes.new('ShaderNodeMath')
    p.operation = 'POWER'; p.inputs[1].default_value = 1.6; inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
    lw.inputs[0].default_value = .5; nt.links.new(lw.outputs['Facing'], inv.inputs[1]); nt.links.new(inv.outputs[0], p.inputs[0])
    mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = .065; nt.links.new(p.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], b.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=10, radius=1); me = bpy.data.meshes.new('puff'); bm.to_mesh(me); bm.free(); me.materials.append(m)
    for q in me.polygons: q.use_smooth = True
    T = 44; Pp = Vector(at)
    for i in range(n):
        o = bpy.data.objects.new('puff', me); K._link(o, parent); o.visible_shadow = False; f = 1-T*i/n; sx = R.uniform(-.2, .2)
        while f < f1+1:
            for u, q, s in ((0, (0, 0, 0), .01), (.25, (sx*.8, 0, h*.22), r*.55), (.6, (-sx, .05, h*.55), r*.75), (.97, (sx*1.4, .1, h*.8), .01)):
                K.key(o, 'location', int(f+T*u), tuple(Pp+Vector(q)), 'LINEAR'); K.key(o, 'scale', int(f+T*u), (s, s, s*1.7), 'LINEAR')
            f += T


# ---------------------------------------------------------------- moods: one call lights a whole exterior
# sky = (horizon, zenith) the camera sees; amb = (colour, strength) the sky lights the scene with (the shadow colour);
# sun = (colour, strength, elevation deg, softness deg); fill = (colour, strength) a shadowless counter-light from the sky side;
# view = the AgX look (dark moods keep cine_kit's Medium High Contrast), ev = exposure; look = the grade in scripts/grade.py and the
# band in scripts/mood_gate.py. Day moods were tuned on EEVEE stills of templates/act_01.py's yard (pale walls, open sky).
MOODS = {
    'day':      dict(sky=('#D6E8F4', '#3D7EC6'), amb=('#B4CCE6', 1.0), sun=('#FFF1DA', 4.6, 58, 2.5), fill=('#A8C4EA', .8), view='AgX - Punchy', ev=.25, look='day'),
    'morning':  dict(sky=('#F4DCC2', '#6C9AD2'), amb=('#B6C8E2', .75), sun=('#FFDDB0', 3.8, 20, 3), fill=('#A8C2EC', .8), view='AgX - Base Contrast', ev=.3, look='morning'),
    'golden':   dict(sky=('#FFBE80', '#5A7AB4'), amb=('#C4A08A', .8), sun=('#FF9E4E', 4.6, 11, 3), fill=('#8AA0D4', 1.1), view='AgX - Punchy', ev=.35, look='golden'),
    'overcast': dict(sky=('#D8DCE0', '#A8B0BA'), amb=('#C8D0DA', 1.5), sun=('#EEF2F6', 1.1, 60, 35), fill=None, view='AgX - Base Contrast', ev=.2, look='overcast'),
    'dusk':     dict(sky=('#B8542A', '#141428'), amb=('#3A3440', .6), sun=('#FFA868', 2.4, 8, 3), fill=('#6A90D0', .9), look='amber'),
    'night':    dict(sky=('#142B4C', '#03060E'), amb=('#2A4068', .6), sun=('#7898D0', 1.5, 40, 4), fill=None, look='cold'),
    'dawn':     dict(sky=('#5A6E84', '#10151F'), amb=('#3A4A60', .55), sun=('#90B0D8', 1.8, 10, 5), fill=None, look='cold'),
}


def mood(name, az=35, exposure=0.0, sky_s=1.0, sun_mult=1.0):
    """Light an exterior in one call: sky the camera sees, sky light (shadow colour), a shadow-casting sun, a sky fill.
    az = where the sun comes FROM, degrees: 0 behind the camera (flat, frontal), 35-60 a three-quarter key (the default),
    90 from screen right, 150-180 behind the subject (backlight: rim on every edge; best for golden). Returns the sun.
    Dark moods (dusk, night, dawn) are Tiga Tradisi's exterior worlds. Interiors: build the room and use lamps instead."""
    m = MOODS[name]; sky(m['sky'][0], m['sky'][1], m['amb'][0], m['amb'][1], sky_s)
    col, power, el, soft = m['sun']; e, a = D(el), D(az)
    d = Vector((math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e)))
    sun = light('sun', 'SUN', tuple(d*40), power*sun_mult, col, target=(0, 0, 0), size=soft, shadow=True)
    if m['fill']:
        f = Vector((-d.x, -d.y, .6)).normalized()
        light('sky_fill', 'SUN', tuple(f*40), m['fill'][1], m['fill'][0], target=(0, 0, 0), size=20)
    vs = bpy.context.scene.view_settings; vs.exposure = m.get('ev', 0)+exposure
    if m.get('view'):
        try: vs.look = m['view']
        except TypeError: pass
    return sun


def clouds(n=7, f1=240, y=110, z=(28, 60), drift=.04, color='#FFFFFF', glow=3.0):
    """Soft cloud banks far behind the set, drifting slowly (studs per frame): a daylight sky is never a flat card."""
    m = bpy.data.materials.new('cloud'); m.use_nodes = True; nt = m.node_tree; b = next(x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = K.col(color); b.inputs['Emission Color'].default_value = K.col(color)
    b.inputs['Emission Strength'].default_value = glow; b.inputs['Roughness'].default_value = 1
    lw, inv, mu = nt.nodes.new('ShaderNodeLayerWeight'), nt.nodes.new('ShaderNodeMath'), nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; mu.operation = 'POWER'; mu.inputs[1].default_value = 2.2
    lw.inputs[0].default_value = .35; nt.links.new(lw.outputs['Facing'], inv.inputs[1]); nt.links.new(inv.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], b.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1); me = bpy.data.meshes.new('cloud'); bm.to_mesh(me); bm.free(); me.materials.append(m)
    for q in me.polygons: q.use_smooth = True
    for i in range(n):
        r = K.empty('cloud', (R.uniform(-90, 90), y+R.uniform(-10, 20), R.uniform(*z)))
        for j in range(R.randint(3, 6)):
            o = bpy.data.objects.new('puff', me); K._link(o, r); o.visible_shadow = False
            s = R.uniform(6, 13); o.location = (j*R.uniform(5, 8)-12, R.uniform(-2, 2), R.uniform(-1.5, 2)); o.scale = (s*1.5, s*.5, s*.55)
        p = r.location.copy(); mv(r, (1, tuple(p)), (f1, (p.x+drift*f1*R.uniform(.6, 1.4), p.y, p.z)), ease='LINEAR')


def sway(ob, f1, amount=1.5, period=34, axis=(1, .6, 0)):
    """A breeze on a plant, a flag, a hanging cloth, a lantern: a slow, uneven rock about its origin until f1."""
    base = Vector(ob.rotation_euler); f, s = 1-R.randint(0, period), 1
    while f < f1+period:
        a = amount*s*R.uniform(.6, 1.0); rot(ob, (f, tuple(math.degrees(base[k])+a*axis[k] for k in range(3)))); f += int(period*R.uniform(.8, 1.2)); s = -s
    return ob


# ---------------------------------------------------------------- Meshy props (assets/props.blend, from blender/prep_props.py)
def asset(name, loc=(0, 0, 0), yaw=0, size=None, parent=None, solid=True):
    """A prop from assets/props.blend. size = ('x'|'y'|'z', studs) to scale uniformly by one axis, or (x, y, z) studs.
    Origin is bottom centre. solid = clip_check tests actors against it."""
    if name not in _P:
        with bpy.data.libraries.load(f'{ROOT}/assets/props.blend') as (s, d): d.objects = [n for n in s.objects if n == name]
        if not d.objects: raise KeyError(f'{name} is not in assets/props.blend (add it to assets/props.json, run prep_props.py)')
        _P[name] = d.objects[0]
    o = _P[name].copy(); o.animation_data_clear(); o.rotation_mode = 'XYZ'; o.location = loc; o.rotation_euler = (0, 0, D(yaw))
    if size and not isinstance(size[0], str): o.scale = [v/d for v, d in zip(size, _P[name]['dim'])]
    elif size: k = size[1]/_P[name]['dim']['xyz'.index(size[0])]; o.scale = (k, k, k)
    else: o.scale = (1, 1, 1)
    o['solid'] = bool(solid); return K._link(o, parent)
def dims(name, size):
    """World size of asset(name, size=...) before it is placed."""
    d = list(_P[name]['dim']); k = size[1]/d['xyz'.index(size[0])]; return Vector([v*k for v in d])
