"""Meshy smart-topology characters -> rigid parts on joints, one cast/<name>.blend each.

    Blender -b --factory-startup -P blender/prep_cast.py -- <project> [name ...]

Reads project.json -> cast.<name>: {"glb": "assets/raw/<name>.glb", "scale": 1.0, "legs": true}
  scale  height multiplier on the 5.2-stud reference body (a guard 1.12, a child 0.74 is better done with Toy(size=)).
  legs   true = trousers / shorts: the body is cut into two legs at the hip.
         false = skirt / sarong / kain: the lower body stays one block ('lower') that swings as one; feet are 'leg_l'/'leg_r'.

Why this works: meshy-t2.5 smart topology returns a part-separated mesh (each block is its own island), so every island can be
sorted into head / body / arms by where it sits. The input image must be the block body of blender/block_ref.py (2-stud torso,
1-stud arms, head on the shoulders, no neck, no face): these thresholds are measured on that body.
Writes custom props the runtime reads: part, pivot, scale, legs, y_eye / y_mouth / y_brow (the face front, probed by rays).
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if not argv: raise SystemExit('usage: Blender -b --factory-startup -P prep_cast.py -- <project> [name ...]')
ROOT = os.path.abspath(argv[0]); PJ = json.load(open(f'{ROOT}/project.json')); CAST = PJ.get('cast', {})
NAMES = argv[1:] or list(CAST)
os.makedirs(f'{ROOT}/cast', exist_ok=True)

for n in NAMES:
    c = dict(scale=1.0, legs=True); c.update(CAST.get(n, {})); S = c['scale']
    src = os.path.join(ROOT, c.get('glb', f'assets/raw/{n}.glb'))
    if not os.path.exists(src): print('MISSING', n, src); continue
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
    obs = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in obs: o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    if len(obs) > 1:
        for o in obs: o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]; bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active or obs[0]; me = o.data
    lo = Vector([min(v.co[k] for v in me.vertices) for k in range(3)]); hi = Vector([max(v.co[k] for v in me.vertices) for k in range(3)])
    s = 5.2/(hi.z-lo.z)*S
    cx = (lo.x+hi.x)/2; mid = [v.co.y for v in me.vertices if abs(v.co.x-cx) > (hi.x-lo.x)*.34]     # the arms give the depth centre
    cy = (min(mid)+max(mid))/2 if mid else (lo.y+hi.y)/2
    me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -lo.z)))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=5e-5)
    long = [f for f in bm.faces if max(v.co.z for v in f.verts)-min(v.co.z for v in f.verts) > 2.4]   # stray slivers across the body
    bmesh.ops.delete(bm, geom=long, context='FACES'); bm.faces.ensure_lookup_table()
    hip = 2.02*S
    isl, seen = [], set()
    for f in bm.faces:
        if f in seen: continue
        st, g = [f], []; seen.add(f)
        while st:
            a = st.pop(); g.append(a)
            for e in a.edges:
                for b in e.link_faces:
                    if b not in seen: seen.add(b); st.append(b)
        isl.append(g)
    part = {}
    for g in isl:
        co = [v.co for f in g for v in f.verts]; L = [min(p[k] for p in co) for k in range(3)]; H = [max(p[k] for p in co) for k in range(3)]
        mx, mz = (L[0]+H[0])/2, (L[2]+H[2])/2
        if abs(mx) > 1.2*S: k = 'arm_l' if mx > 0 else 'arm_r'
        elif H[2]-L[2] > 3.0*S and H[2] > 4.2*S: k = None                   # one island spanning head and body: split per face
        elif mz > 3.85*S: k = 'head'
        elif not c['legs'] and H[2] < .62*S: k = 'leg_l' if mx > 0 else 'leg_r'
        else: k = 'body'
        for f in g: part[f.index] = k or ('head' if f.calc_center_median().z > 3.86*S else 'body')
    bm.to_mesh(me); bm.free()

    def sub(names):
        b = bmesh.new(); b.from_mesh(me); b.faces.ensure_lookup_table()
        bmesh.ops.delete(b, geom=[f for f in b.faces if part[f.index] not in names], context='FACES'); return b
    Pp = {k: sub((k,)) for k in ('head', 'body', 'arm_l', 'arm_r')}
    cap = bpy.data.materials.new(n+'_cap'); cap.use_nodes = True
    next(x for x in cap.node_tree.nodes if x.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.12, .035, .025, 1)
    me.materials.append(cap); ci = len(me.materials)-1

    def cut(b, co, no):
        """Cut away one side of a plane and cap the hole (the cap is dark: it only shows inside a bent joint)."""
        r = bmesh.ops.bisect_plane(b, geom=b.verts[:]+b.edges[:]+b.faces[:], plane_co=co, plane_no=no, clear_inner=True)
        e = [x for x in r['geom_cut'] if isinstance(x, bmesh.types.BMEdge) and x.is_boundary]
        if e:
            for f in bmesh.ops.triangle_fill(b, edges=e, use_beauty=True)['geom']:
                if isinstance(f, bmesh.types.BMFace): f.material_index = ci
    if c['legs']:
        for side, sx in (('leg_l', 1), ('leg_r', -1)):
            b = Pp['body'].copy(); cut(b, (0, 0, hip), (0, 0, -1)); cut(b, (sx*.004, 0, 0), (sx, 0, 0)); Pp[side] = b
        cut(Pp['body'], (0, 0, hip-.03), (0, 0, 1))
    else:
        Pp['lower'] = Pp['body'].copy(); cut(Pp['lower'], (0, 0, hip+.04), (0, 0, -1)); cut(Pp['body'], (0, 0, hip-.03), (0, 0, 1))
        for k in ('leg_l', 'leg_r'):
            b = sub((k,))
            if len(b.faces): Pp[k] = b
            else: b.free()
    J = dict(body=(0, 0, hip), head=(0, 0, 3.86*S), arm_l=(1.48*S, 0, 3.68*S), arm_r=(-1.48*S, 0, 3.68*S),
             leg_l=(.5*S, 0, hip), leg_r=(-.5*S, 0, hip), lower=(0, 0, hip))
    if not c['legs']: J['leg_l'] = (.45, 0, .62); J['leg_r'] = (-.45, 0, .62)

    bv = BVHTree.FromBMesh(Pp['head']); fy = {}
    for key, z in (('eye', 4.38), ('mouth', 4.07), ('brow', 4.6)):          # where the front of the face is, at three heights
        hits = [bv.ray_cast(Vector((x*S, -4, z*S)), Vector((0, 1, 0)))[0] for x in (-.3, -.15, 0, .15, .3)]
        ys = sorted(h.y for h in hits if h); fy[key] = ys[len(ys)//2] if ys else -.6
    out = []
    for k, b in Pp.items():
        piv = Vector(J[k]); bmesh.ops.translate(b, verts=b.verts, vec=-piv)
        if k.startswith('arm'):                                              # A-pose arms down toward the side
            bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(14 if k == 'arm_l' else -14), 3, 'Y'))
        m = bpy.data.meshes.new(f'{n}.{k}'); b.to_mesh(m); b.free()
        for mt in me.materials: m.materials.append(mt)
        ob = bpy.data.objects.new(f'{n}.{k}', m); bpy.context.collection.objects.link(ob)
        ob['pivot'] = list(piv); ob['part'] = k; out.append(ob)
        if k == 'head':
            ob['scale'] = S; ob['legs'] = c['legs']
            for q, v in fy.items(): ob['y_'+q] = v
    for mt in me.materials:                                                  # Meshy textures often arrive metallic: make it cloth and skin
        if mt and mt.use_nodes:
            for x in mt.node_tree.nodes:
                if x.type == 'BSDF_PRINCIPLED':
                    for sock in ('Metallic', 'Roughness'):
                        for l in list(x.inputs[sock].links): mt.node_tree.links.remove(l)
                    x.inputs['Metallic'].default_value = 0; x.inputs['Roughness'].default_value = .5; x.inputs['Subsurface Weight'].default_value = .06
    bpy.ops.file.pack_all()
    bpy.data.libraries.write(f'{ROOT}/cast/{n}.blend', set(out), fake_user=True, compress=True)
    print('PREP', n, {o['part']: len(o.data.polygons) for o in out}, {k: round(v, 3) for k, v in fy.items()}, 'slivers removed', len(long), flush=True)
