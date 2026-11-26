"""Untouched Meshy GLBs in a dark studio: <name>_tex.png (textured) and <name>_wire.png (gold wireframe on clay), plus faces.txt.
The material for the cast card and the "In Meshy / In your work" pairs. Nothing in the film is touched.

    Blender -b --factory-startup -P blender/studio.py -- <project> [name ...]      (names from cast + props; default all)
    WIDE=1 ... = 1920x1080 textured only (<name>_wide.png), for side-by-side pairs.
Output: out/gallery/assets/. Cycles, 96 samples, about 20 s a model on an M4.
"""
import bpy, os, sys, math, json
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ROOT = os.path.abspath(argv[0]); PJ = json.load(open(f'{ROOT}/project.json'))
SRC = {n: os.path.join(ROOT, c.get('glb', f'assets/raw/{n}.glb')) for n, c in PJ.get('cast', {}).items()}
if os.path.exists(f'{ROOT}/assets/props.json'):
    SRC.update({n: os.path.join(ROOT, c['glb']) for n, c in json.load(open(f'{ROOT}/assets/props.json')).items() if c.get('glb')})
PROPS = json.load(open(f'{ROOT}/assets/props.json')) if os.path.exists(f'{ROOT}/assets/props.json') else {}
SRC = {n: p for n, p in SRC.items() if os.path.exists(p)}
NAMES = argv[1:] or list(SRC); OUT = f'{ROOT}/out/gallery/assets'; os.makedirs(OUT, exist_ok=True)
WIDE = os.environ.get('WIDE') == '1'; RES = 1000


def studio():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 96; sc.cycles.use_denoising = True
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'METAL'; pr.get_devices(); sc.cycles.device = 'GPU'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = (1920, 1080) if WIDE else (RES, RES)
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (.010, .011, .014, 1)
    prof = [(-12+14*i/10, 0) for i in range(11)]                                     # a curved sweep: floor, quarter circle, wall
    prof += [(2+4*math.sin(i/12*math.pi/2), 4-4*math.cos(i/12*math.pi/2)) for i in range(1, 13)]+[(6, 14)]
    verts = [v for y, z in prof for v in ((-14, y, z), (14, y, z))]
    me = bpy.data.meshes.new('bd'); me.from_pydata(verts, [], [(2*i, 2*i+1, 2*i+3, 2*i+2) for i in range(len(prof)-1)]); me.update()
    bd = bpy.data.objects.new('Backdrop', me); sc.collection.objects.link(bd)
    for p in me.polygons: p.use_smooth = True
    m = bpy.data.materials.new('bd'); m.use_nodes = True; bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (.018, .018, .02, 1); bs.inputs['Roughness'].default_value = .45; me.materials.append(m)
    def area(name, loc, power, size, color, target=(0, 0, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(target)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area('Key', (-4.5, -5, 6), 900, 4, (1, .86, .70)); area('Rim', (4.5, 4, 5), 900, 3, (.62, .78, 1)); area('Fill', (5, -6, 1.5), 90, 6, (1, .95, .9))
    d = bpy.data.lights.new('Pool', 'SPOT'); d.energy = 1500; d.spot_size = math.radians(60); d.spot_blend = .9; d.shadow_soft_size = 1.5
    o = bpy.data.objects.new('Pool', d); sc.collection.objects.link(o); o.location = (0, 0, 9)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 70; cam.data.sensor_fit = 'VERTICAL' if WIDE else 'AUTO'; cam.data.sensor_height = 24
    return sc, cam


def load(name):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=SRC[name])
    obs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs: m = o.matrix_world.copy(); o.parent = None; o.matrix_world = m; o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; me = o.data; me.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    for e in [x for x in bpy.data.objects if x not in before and x != o]: bpy.data.objects.remove(e)
    ps = [v.co for v in me.vertices]; lo = Vector([min(p[k] for p in ps) for k in range(3)]); hi = Vector([max(p[k] for p in ps) for k in range(3)])
    me.transform(Matrix.Translation((-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z)))
    if name in PJ.get('cast', {}): yaw = PJ['cast'][name].get('studio_yaw', 0)                    # characters face the lens
    else: c = PROPS.get(name, {}); yaw = c.get('studio_yaw', c.get('yaw', 0)+35)                  # props: front to -Y, then three-quarter
    me.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z')); me.transform(Matrix.Scale(3.2/max(hi-lo), 4))
    for p in me.polygons: p.use_smooth = True
    return o, len(me.polygons)


def frame(cam, o):
    ps = [v.co for v in o.data.vertices]; lo = Vector([min(p[k] for p in ps) for k in range(3)]); hi = Vector([max(p[k] for p in ps) for k in range(3)])
    c = (lo+hi)/2; r = (hi-lo).length/2; dist = r/((12 if WIDE else 18)/cam.data.lens)*(.86 if WIDE else 1.05)
    cam.location = c+Vector((0, -1, .32)).normalized()*dist; cam.rotation_euler = (c-cam.location).to_track_quat('-Z', 'Y').to_euler()


def wire_material():
    m = bpy.data.materials.new('wire'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); wf = nt.nodes.new('ShaderNodeWireframe'); wf.use_pixel_size = True; wf.inputs[0].default_value = .9
    clay = nt.nodes.new('ShaderNodeBsdfPrincipled'); clay.inputs['Base Color'].default_value = (.16, .16, .17, 1); clay.inputs['Roughness'].default_value = .6
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1, .78, .30, 1); em.inputs['Strength'].default_value = 1.6
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(wf.outputs[0], mix.inputs[0]); nt.links.new(clay.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    return m


sc, cam = studio(); wire = wire_material(); info = {}
fp = f'{OUT}/faces.txt'
if os.path.exists(fp): info = dict(l.split() for l in open(fp) if l.strip())
for name in NAMES:
    if name not in SRC: print('NO GLB', name); continue
    o, nf = load(name); frame(cam, o)
    sc.render.filepath = f'{OUT}/{name}_{"wide" if WIDE else "tex"}.png'; bpy.ops.render.render(write_still=True)
    if not WIDE:
        o.data.materials.clear(); o.data.materials.append(wire)
        sc.render.filepath = f'{OUT}/{name}_wire.png'; bpy.ops.render.render(write_still=True)
    info[name] = str(nf); print('DONE', name, nf, flush=True)
    me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
open(fp, 'w').write(''.join(f'{k} {v}\n' for k, v in info.items()))
