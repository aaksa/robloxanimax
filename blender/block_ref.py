"""The Meshy input image: a character's outfit on the cast's block body, FACELESS, front / side / back.

    Blender -b --factory-startup -P blender/block_ref.py -- <project> [name ...] [--glb] [--force]

Reads project.json -> cast.<name>.ref (see templates/project.json). Writes ref/<name>_front.png, _side.png, _back.png
(900x1200, orthographic, flat grey studio) and ref/lineup.png is left to the caller.
--glb also writes assets/raw/<name>.glb (only if it is missing, or with --force): a free stand-in with the same proportions, so
the whole film can be blocked, timed and lit before a single Meshy credit is spent. Swap in the Meshy GLB later; nothing else changes.

Why a block body and not the concept image straight to Meshy:
- Meshy follows the picture. Image models draw claw hands, thin arms, a neck, a turned pose; Meshy then builds exactly that.
  This body is 2 studs of torso, 1-stud arms, solid block hands, head sitting on the shoulders: what prep_cast.py can cut.
- No face. The film adds a live face (eyes, lids, brows, ten mouths). A painted face would show through it and cannot blink.
- Concept pixels (a woven cloth, a batik) can be laid on the front of a part with "decals" so the Meshy texture keeps them.
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
flags = {a for a in argv if a.startswith('--')}; argv = [a for a in argv if not a.startswith('--')]
if not argv: raise SystemExit('usage: Blender -b --factory-startup -P block_ref.py -- <project> [name ...] [--glb] [--force]')
ROOT = os.path.abspath(argv[0]); PJ = json.load(open(f'{ROOT}/project.json')); CAST = PJ.get('cast', {})
NAMES = argv[1:] or [n for n in CAST if 'ref' in CAST[n]]
M = {}


def lin(h):
    c = [int(h[i:i+2], 16)/255 for i in (1, 3, 5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)


def mat(c, rough=.75, weave=False):
    k = (c, rough, weave)
    if k in M: return M[k]
    m = bpy.data.materials.new(c); m.use_nodes = True; nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = lin(c); b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = .25
    if weave:                                                   # a fine cloth bump, so Meshy reads fabric, not plastic
        tc, n, bp = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeTexChecker'), nt.nodes.new('ShaderNodeBump')
        n.inputs['Scale'].default_value = 34; bp.inputs['Strength'].default_value = .25; bp.inputs['Distance'].default_value = .01
        nt.links.new(tc.outputs['Object'], n.inputs['Vector']); nt.links.new(n.outputs[1], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    M[k] = m; return m


def photo(path):
    k = ('photo', path)
    if k in M: return M[k]
    m = bpy.data.materials.new('photo'); m.use_nodes = True; nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True); t.extension = 'EXTEND'
    nt.links.new(t.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .8; M[k] = m; return m


def part(size, at, base, bevel=.1, parent=None, ry=0, decal=None, name='part'):
    """A bevelled box. decal = {"image", "crop": [x0, y0, x1, y1]} puts those pixels on the faces that look at the camera."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts: v.co = Vector(a*b for a, b in zip(v.co, size))
    bv = min(bevel, min(size)*.45)
    if bv: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bv, segments=4, profile=.5, affect='EDGES')
    me = bpy.data.meshes.new(name); me.materials.append(base)
    if decal:
        path = os.path.join(ROOT, decal['image']); img = bpy.data.images.load(path, check_existing=True); W, H = img.size
        uv = bm.loops.layers.uv.new(); me.materials.append(photo(path)); x0, y0, x1, y1 = decal['crop']
        for f in bm.faces:
            f.normal_update(); f.material_index = 1 if f.normal.y < -.5 else 0
            for l in f.loops: l[uv].uv = ((x0+(l.vert.co.x/size[0]+.5)*(x1-x0))/W, 1-(y1-(l.vert.co.z/size[2]+.5)*(y1-y0))/H)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler.y = math.radians(ry); o.parent = parent; return o


def build(spec):
    """The cast body in studs: feet at 0, torso 2-4, head 3.98-5.38, shoulders at x +-1.02. Front is -Y."""
    sk = mat(spec.get('skin', '#9C5A32'), .45); dec = spec.get('decals', {})
    top = spec.get('top', {}); tc = mat(top.get('color', '#651A25'), weave=top.get('weave', True))
    low = spec.get('lower', {}); kind = low.get('kind', 'shorts'); lc = mat(low.get('color', '#2A2A2C'), weave=low.get('weave', True))
    shoe = mat(spec.get('shoes', '#3A2118'))
    # legs and feet
    leg_h = .6 if kind == 'skirt' else 2.0
    for s in (-1, 1):
        part((.94, .94, leg_h), (s*.5, 0, leg_h/2), lc if kind == 'trousers' else sk, name='leg')
        part((.98, 1.12, .16), (s*.5, -.06, .08), shoe, bevel=.05, name='shoe')
    if kind == 'shorts':
        for s, k in ((-1, 'lower_r'), (1, 'lower_l')):
            part((1, 1.02, 1.3), (s*.5, 0, 1.5), lc, .08, decal=dec.get(k), name='shorts')
            if low.get('bands'):
                for i in range(3): part((1.01, 1.04, .055), (s*.5, 0, 1.02+.14*i), mat(low['bands'], weave=True), bevel=.015, name='band')
    elif kind == 'skirt':
        part((2, 1.04, 1.8), (0, 0, 1.22), lc, .1, decal=dec.get('lower'), name='skirt')
        if low.get('bands'):
            for i in range(7):
                for y in (-.53, .53): part((.05, .03, 1.7), (-.84+.28*i, y, 1.22), mat(low['bands'], weave=True), bevel=.01, name='stripe')
    # torso, belly, sash
    part((2, 1, 2), (0, 0, 3), tc, .12, decal=dec.get('torso'), name='torso')
    if spec.get('belly'):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1); me = bpy.data.meshes.new('belly'); bm.to_mesh(me); bm.free()
        me.materials.append(tc)
        for f in me.polygons: f.use_smooth = True
        o = bpy.data.objects.new('belly', me); bpy.context.collection.objects.link(o); o.location = (0, -.42, 2.65); o.scale = (.82, .62, .76)
    if spec.get('sash'):
        sc = mat(spec['sash'], weave=True); part((2.06, 1.1, .3), (0, 0, 2.2), sc, .05, name='sash')
        part((.34, .14, .34), (.35, -.56, 2.2), sc, .07, name='knot'); part((.26, .1, .6), (.42, -.57, 1.9), sc, .05, ry=-8, name='tail')
    if spec.get('collar'): part((.7, .1, .22), (0, -.49, 3.94), sk, .1, name='collar')
    # arms: a sleeve block and a skin block, hung from the shoulder 18 degrees out (A-pose)
    sl = min(1.7, top.get('sleeve', 1.0))                     # leave at least 0.4 stud of hand
    for s in (-1, 1):
        e = bpy.data.objects.new('shoulder', None); bpy.context.collection.objects.link(e); e.location = (s*1.02, 0, 3.98); e.rotation_euler.y = math.radians(-18*s)
        part((1, 1, sl), (s*.5, 0, -sl/2), tc, .12, parent=e, name='sleeve')
        part((.97, .97, 2.12-sl), (s*.5, 0, -sl-(2.12-sl)/2+.04), sk, .18, parent=e, name='hand')
        if top.get('cuff'): part((1.03, 1.03, .09), (s*.5, 0, -sl+.02), mat(top['cuff'], weave=True), .03, parent=e, name='cuff')
    # head: blank skin, no face
    part((1.5, 1.32, 1.4), (0, 0, 4.68), sk, .22, name='head')
    hair = spec.get('hair', {}); hs = hair.get('style', 'short'); h = mat(hair.get('color', '#17120F'), .4)
    if hs == 'short':
        part((1.56, 1.40, .36), (0, .02, 5.28), h, .16); part((1.5, .1, .16), (0, -.66, 5.13), h, .04); part((1.56, .5, 1.05), (0, .46, 4.88), h, .18)
    elif hs == 'bun':
        part((1.54, .6, 1.3), (0, .42, 4.76), h, .2); part((1.56, 1.4, .26), (0, 0, 5.33), h, .12); part((.8, .6, .6), (0, .8, 5.2), h, .25)
    elif hs == 'long':
        part((1.56, .6, 1.3), (0, .42, 4.8), h, .2); part((1.56, 1.4, .36), (0, .02, 5.3), h, .16); part((.7, .6, .65), (0, .85, 4.75), h, .25)
        for s in (-1, 1): part((.2, .5, 1.22), (s*.76, -.36, 4.7), h, .09)
    hw = spec.get('headwear')
    if hw:
        c = mat(hw.get('color', '#E6E2D8'), weave=True); k = hw.get('kind', 'cap')
        if k == 'udeng':                                        # a tied headcloth with a front fold
            part((1.64, 1.44, .42), (0, 0, 5.32), c, .12); part((1.3, .5, .22), (0, .35, 5.56), c, .1); part((.28, .16, .3), (0, -.74, 5.38), c, .08)
        elif k == 'peci':
            part((1.6, 1.42, .55), (0, 0, 5.5), c, .08)
        elif k == 'hijab':                                      # covers the head and the sides, the face stays open
            part((1.66, 1.5, .4), (0, .02, 5.38), c, .18); part((1.66, .5, 1.4), (0, .52, 4.7), c, .18)
            for s in (-1, 1): part((.14, 1.2, 1.3), (s*.82, -.04, 4.62), c, .06)
            part((2.1, 1.1, .5), (0, 0, 3.86), c, .2)
        else:
            part((1.62, 1.46, .4), (0, 0, 5.36), c, .14); part((1.5, .7, .1), (0, -.9, 5.2), c, .04)
    for x in spec.get('extras', []):                            # free boxes: a vest, a strap, a badge (studs)
        part(x['size'], x['at'], mat(x.get('color', '#777777'), x.get('rough', .7), x.get('weave', False)), x.get('bevel', .05), ry=x.get('ry', 0))


def studio():
    sc = bpy.context.scene; w = bpy.data.worlds.new('w'); w.use_nodes = True; nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    a = nt.nodes.new('ShaderNodeBackground'); mx = nt.nodes.new('ShaderNodeMixShader'); lp = nt.nodes.new('ShaderNodeLightPath')
    bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = .78; a.inputs[0].default_value = lin('#C8C8C8')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(a.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD').inputs['Surface']); sc.world = w
    piv = bpy.data.objects.new('pivot', None); sc.collection.objects.link(piv)
    l = bpy.data.lights.new('sun', 'SUN'); l.energy = 1.3; l.angle = .35
    o = bpy.data.objects.new('sun', l); sc.collection.objects.link(o); o.parent = piv; o.rotation_euler = (math.radians(55), 0, math.radians(-22))
    c = bpy.data.cameras.new('c'); c.type = 'ORTHO'; c.ortho_scale = 6.9
    o = bpy.data.objects.new('c', c); sc.collection.objects.link(o); o.parent = piv; o.location = (0, -14, 2.93); o.rotation_euler.x = math.pi/2; sc.camera = o
    try: sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError: sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_render_samples = 48; sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = 900; sc.render.resolution_y = 1200
    return sc, piv


os.makedirs(f'{ROOT}/ref', exist_ok=True)
for name in NAMES:
    spec = CAST.get(name, {}).get('ref')
    if not spec: print('NO REF SPEC', name); continue
    bpy.ops.wm.read_factory_settings(use_empty=True); M.clear(); build(spec); sc, piv = studio()
    for view, deg in (('front', 0), ('side', 90), ('back', 180)):
        piv.rotation_euler.z = math.radians(deg); sc.render.filepath = f'{ROOT}/ref/{name}_{view}.png'; bpy.ops.render.render(write_still=True)
    if '--glb' in flags:
        g = f'{ROOT}/assets/raw/{name}.glb'
        if os.path.exists(g) and '--force' not in flags: print('GLB KEPT (exists)', g)
        else:
            os.makedirs(os.path.dirname(g), exist_ok=True)
            for o in [o for o in bpy.data.objects if o.type != 'MESH']: bpy.data.objects.remove(o) if o.type in ('LIGHT', 'CAMERA') else None
            bpy.ops.object.select_all(action='DESELECT')
            for o in bpy.data.objects:
                if o.type == 'MESH': o.select_set(True)
            bpy.ops.export_scene.gltf(filepath=g, use_selection=True, export_apply=True)
            print('STAND-IN GLB', g)
    print('REF', name, flush=True)
