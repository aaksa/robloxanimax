"""Shots 01-02: one function per shot, named s<ID>(n). n = the shot's length in frames (from audio/timeline.json);
every frame inside is local, 1..n. Render: Blender -b --factory-startup -P <skill>/blender/render.py -- <project> --stills .1,.5,.9

The pattern of every shot (Tiga Tradisi):
  1. world: sky + ground or a room, 1-3 lights with shadow=True, a visible lamp (the highlight), something alive (motes, steam, sway)
  2. cast: Toy(name, at, yaw, size, face) -> pose / hit on the words -> face / look / blink -> talk -> life(n) LAST
  3. camera: Cam((frame, loc, target, lens, stop, focus), ...) with a real move; wipe() for a hand-over cut
"""
from anima import *


def s01(n):
    sky('#1A1008', '#05070A', '#2A2018', .25)
    K.room(16, 18, 9, floor=K.wood('#24120A', '#6A3C20', planks=.9), wall=K.wood('#1C0E08', '#5A3420', planks=.9))
    lamp((0, 1.5, 6.2), 1400, n)
    light('key', 'SPOT', (-3.5, -4, 7), 2200, 2700, target=(0, 0, 2.5), spot=60, shadow=True)
    light('rim', 'AREA', (3.5, 3, 4.5), 220, '#6A90D0', target=(0, 0, 3), size=2)
    motes((-3, -3, .4), (3, 3, 6), 20, n, s=.022, glow=2)
    k = Toy('anak', (0, 4, 0), 0, .74, 'hope')                         # yaw 0 = facing the lens (-Y)
    k.walk(1, int(n*.7), (0, 4), (0, .2), arms=False)
    k.pose(1, arm_l=(70, -16, 0), arm_r=(70, -16, 0), head=(6, 0, 0))
    r = K.empty('plate_root', (0, -1.8, 1.42), k.waist)
    K.cyl('plate', .7, .08, (0, 0, 0), F('#E8E2D4', .3), .03, parent=r); K.cyl('rice', .45, .25, (0, 0, .12), F('#F4F0E6', .8), .12, parent=r)
    steam(r, (0, 0, .3), n, r=.16, h=.9)
    k.face(int(n*.72), 'smile').look(int(n*.75), 0, .3); k.life(n, .8)
    Cam((1, (.4, -7.5, 3.0), (0, 1, 2.6), 32, 4, (0, 2, 2.8)), (n, (.2, -6.2, 3.1), (0, 0, 2.6), 35, 4, (0, .4, 2.8)), hand=.12)


def s02(n):
    sky('#1A1008', '#05070A', '#2A2018', .25)
    K.room(16, 18, 9, floor=K.wood('#24120A', '#6A3C20', planks=.9), wall=K.wood('#1C0E08', '#5A3420', planks=.9))
    lamp((-.8, 1, 6.2), 1400, n)
    light('key', 'SPOT', (3.5, -4, 7), 2000, 2700, target=(0, 1, 3), spot=55, shadow=True)
    K.box('table', (4.5, 2.4, .2), (0, -.6, 2.6), K.wood('#2A1408', '#7A4A24'))
    K.cyl('plate', .7, .08, (.2, -.9, 2.74), F('#E8E2D4', .3), .03)
    g = Toy('nenek', (0, 1, 0), 0, 1.0, 'neutral')
    g.pose(1, head=(14, 0, 0), arm_l=(38, 5, 0), arm_r=(38, 5, 0))
    g.hit(int(n*.35), 5, head=(-4, 0, 6)).face(int(n*.35), 'ask').look(int(n*.35), 0, .4)
    g.face(int(n*.6), 'happy').hit(int(n*.6), 4, torso=(-4, 0, 3)); g.life(n)
    Cam((1, (.5, -6.6, 4.3), (0, 1, 3.9), 45, 3.5, (0, .4, 4.4)), (n, (.3, -5.7, 4.35), (0, 1, 4.0), 50, 3.5, (0, .4, 4.4)), hand=.1)


def yard(n, m='day', az=35):
    """A village yard in any mood. Daylight wants PALE surfaces and OPEN SKY in frame: a dark wall filling the frame reads as dusk
    whatever the sun does. House on the right, sky and far hills on the left, the two of them at the bench."""
    mood(m, az=az); ground('#C4AC84')
    plaster, paint, roofm = F('#E6DCC6', .9), K.wood('#2E5E52', '#4A8A78', planks=.0), F('#B0502E', .7)
    K.box('house', (10, 1, 5.6), (5, 7, 2.8), plaster); K.box('trim', (10.2, 1.1, .35), (5, 7, 5.6), paint)
    K.box('door', (2.2, .2, 4.2), (2.4, 6.45, 2.1), paint); K.box('window', (2.4, .2, 1.9), (6.6, 6.45, 3.2), F('#22303A', .15))
    K.box('roof', (11.5, 4.2, .45), (5, 6.2, 6.6), roofm, rot=(-16, 0, 0))
    for i, (x, y, r) in enumerate(((-30, 60, 16), (-8, 75, 22), (22, 70, 18), (45, 62, 14))):       # far hills: depth and green
        K.cyl('hill', r, 2, (x, y, -r*.55), F(('#5E8A4A', '#6E9656', '#557E44', '#6A9050')[i], .9), 0, verts=48, rot=(90, 0, 0))
    trim = K.wood('#3A2414', '#8A5A34')
    K.box('bench', (5, 1.4, .3), (1.6, 3.4, 1.7), trim)
    for x in (-.6, 3.8): K.box('leg', (.3, 1.2, 1.6), (x, 3.4, .8), trim)
    for x, h in ((-4.5, 2.4), (8.2, 3.0)):
        K.cyl('pot', .7, 1.0, (x, 4.5, .5), F('#B45A34', .8), .05, radius2=.5)
        r = K.empty('plant', (x, 4.5, 1.0))
        for i in range(6): K.box('leaf', (.35, .08, h), (0, 0, h/2), F('#3F8A34', .6), rot=(R.uniform(-30, 30), R.uniform(-30, 30), i*60), parent=r)
        sway(r, n, 2.5)
    clouds(6, n); motes((-4, -2, .5), (4, 4, 5), 14, n, '#FFF4D0', s=.02, glow=1.5)
    g = Toy('nenek', (1.6, 3.4, .45), 0, 1.0, 'smile'); g.sit(1); g.pose(1, arm_l=(30, 5, 0), arm_r=(30, 5, 0))
    k = Toy('anak', (-2.6, 1.0, 0), 60, .74, 'hope'); k.pose(1, arm_l=(60, -10, 0), arm_r=(60, -10, 0))
    r = K.empty('plate_root', (0, -1.8, 1.42), k.waist); K.cyl('plate', .7, .08, (0, 0, 0), F('#F2EEE4', .3), .03, parent=r)
    k.walk(1, int(n*.6), (-2.6, 1.0), (-1.1, 2.0), arms=False); k.pose(int(n*.6)+4, yaw=50)
    g.hit(int(n*.55), 5, head=(-6, -18, 4)).face(int(n*.55), 'happy'); k.face(int(n*.65), 'smile')
    g.life(n); k.life(n, .8)
    Cam((1, (-3.0, -10.5, 2.2), (.6, 2.6, 3.4), 28, 5.6, (0, 2.4, 2.8)), (n, (-2.2, -9.4, 2.3), (.8, 2.6, 3.4), 30, 5.6, (.2, 2.6, 2.8)), hand=.1)


def s03(n):
    """Daylight: the same two, outside, at midday."""
    yard(n, 'day')
