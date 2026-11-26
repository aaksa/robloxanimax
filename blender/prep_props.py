"""Meshy props -> assets/props.blend: one joined mesh per prop, origin at bottom centre, its size in studs as custom prop 'dim'.

    Blender -b --factory-startup -P blender/prep_props.py -- <project>

Reads assets/props.json:
  {"plate": {"glb": "assets/raw/plate.glb", "size": [2, 2, .25], "yaw": 0, "cut": null, "metal": false}, ...}
  glb    the Meshy download (any path, relative to the project). Missing file = a plain brown stand-in box of `size`, so the
         cut can be blocked before the model exists. Replace it later and re-run: shots keep working.
  yaw    degrees to turn it so its front faces -Y (the camera side of every set).
  cut    0..1: slice off that fraction from the bottom (a house whose stilts the shot hides).
  metal  keep Meshy's metallic maps (cars, planes). Everything else is made non-metallic: Meshy often bakes chrome into cloth and wood.
  blend + object   take a ready object from a .blend instead of a GLB (trees, a set piece from an earlier film), kept as it is.
  One GLB can feed two rows: Tiga Tradisi had "rumah" (the whole stilt house) and "rumah_top" (cut .262, carried by the neighbours).
  The other keys (prompt, route, title, source, card, film) are for scripts/props_plan.py, props_card.py and pairs.py.
In a shot: asset('plate', (x, y, z), yaw, ('x', 1.9)) = scale so its x is 1.9 studs.
"""
import bpy, bmesh, os, sys, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if not argv: raise SystemExit('usage: Blender -b --factory-startup -P prep_props.py -- <project>')
ROOT = os.path.abspath(argv[0]); SPEC = json.load(open(f'{ROOT}/assets/props.json'))
bpy.ops.wm.read_factory_settings(use_empty=True); out = set()


def norm(name, obs, c):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True); m = o.matrix_world.copy(); o.parent = None; o.matrix_world = m
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; me = o.data; me.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    me.transform(Matrix.Rotation(math.radians(c.get('yaw', 0)), 4, 'Z'))
    ps = [v.co for v in me.vertices]; lo = Vector([min(p[k] for p in ps) for k in range(3)]); hi = Vector([max(p[k] for p in ps) for k in range(3)])
    me.transform(Matrix.Translation((-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z))); d = hi-lo
    cut = c.get('cut')
    if cut:
        b = bmesh.new(); b.from_mesh(me); bmesh.ops.bisect_plane(b, geom=b.verts[:]+b.edges[:]+b.faces[:], plane_co=(0, 0, cut*d.z), plane_no=(0, 0, 1), clear_inner=True)
        bmesh.ops.translate(b, verts=b.verts, vec=(0, 0, -cut*d.z)); b.to_mesh(me); b.free(); d.z *= 1-cut
    if not c.get('metal'):
        for m in me.materials:
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        for l in list(n.inputs['Metallic'].links): m.node_tree.links.remove(l)
                        n.inputs['Metallic'].default_value = 0
    for e in [x for x in bpy.data.objects if x.type == 'EMPTY']: bpy.data.objects.remove(e)
    o.name = name; o['dim'] = list(d); out.add(o); return d


for name, c in SPEC.items():
    p = os.path.join(ROOT, c['glb']) if c.get('glb') else ''
    if c.get('route') == 'kit': print('KIT (built in a film helper, skipped)', name); continue
    if c.get('blend'):
        with bpy.data.libraries.load(os.path.expanduser(c['blend'])) as (s, d_): d_.objects = [c.get('object', name)]
        o = d_.objects[0]; bpy.context.collection.objects.link(o); o.name = name; o['dim'] = list(o.dimensions); out.add(o); print('BLEND', name, flush=True)
    elif p and os.path.exists(p):
        b = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=p)
        print('MESHY', name, [round(v, 3) for v in norm(name, [o for o in bpy.data.objects if o not in b and o.type == 'MESH'], c)], flush=True)
    else:
        d = c.get('size', (1, 1, 1)); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts: v.co = Vector(a*k for a, k in zip(v.co, d))
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        m = bpy.data.materials.new(name); m.use_nodes = True; next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.35, .28, .22, 1)
        me.materials.append(m); o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); norm(name, [o], {}); print('STAND-IN', name, flush=True)
bpy.ops.file.pack_all()
bpy.data.libraries.write(f'{ROOT}/assets/props.blend', out, fake_user=True, compress=True); print('PROPS OK', len(out))
