# Directing the cast (anima.Toy)

## The API
```python
k = Toy('cucu', at=(x, y, 0), yaw=0, size=.74, face='hope')    # yaw 0 faces the lens side (-Y); size .74 = a child
k.pose(f, arm_l=(fwd, out, twist), arm_r=(...), head=(nod, turn, tilt), torso=(nod, turn, tilt), leg_l=deg, leg_r=deg, lower=deg,
       tip=(lean_fwd, lean_side), at=(x, y, z), yaw=deg)        # eased key on frame f
k.hit(f, dur=4, head=(-6, 28, 6))     # arrive ON frame f: 3-frame anticipation, snap, 8 % overshoot, settle 4 frames later
k.face(f, 'wide')                     # swap the expression on frame f (no morph: toys switch)
k.look(f, x=-1..1, z=-1..1)           # irises only, 2-frame move: the cheapest acting there is
k.blink(f, ...)                       # life() already blinks every 1.6-3 s; add one on a thought
talk(k, '13', 1)                      # lip-sync line 1 of shot 13 from the timeline (vowels -> a/e/o, b/m/p close)
k.walk(f0, f1, (x0, y0), (x1, y1), stride=8, swing=24, arms=True)   # faces where it walks unless yaw=
k.sit(f)                              # legs 88 deg: raise `at` z to the seat, the body does not drop by itself
r = K.empty('plate_root', (0, -1.8, 1.42), k.waist)  # props ride the waist (carried in front) or k.palm['l'|'r'] (held)
k.life(n, amount=1.0)                 # LAST: joint drift, breathing on the waist, blinks. Never skip it: no still frames
```
`You(at, yaw, pose)` is the user's own avatar (cinematicanimation `K.Avatar`, word-accurate lip sync via `.face.lipsync`).
For the user's films, he is the visitor / the lead unless he says otherwise; ask who plays him if it is not clear.

## Expressions (`anima.EX`)
neutral, smile, hope, soft, grin, happy (eye arcs), wide, ask, sad, stern, worry, strain, call (open shout), relief, sleep (lids shut,
no blinks: someone asleep or at rest). A face = brow height + brow angle + eye openness + one of ten mouths
(smile, small, line, grin, frown, o, a, e, m, teeth). Add your own row to `EX` in the act file if a beat needs it.
Face sizes per character live in `project.json -> cast.<name>.face` (eye / mouth height in studs, eye radius `r`, spacing `dx`,
brow colour, `old` for wrinkles and crow's feet, `lash` for a winged lash, `lips` colour). Set them once on a front still.

## How a beat is acted (Tiga Tradisi, measured from the cut)
- **Hit the word.** `f = word('13', 'bangun')`; the head or arm `hit` lands on f, the face changes on f, the eyes moved 2-4 frames
  earlier. Eyes lead, head follows, body last.
- **One idea per shot**, one big move. Everything else is life(): small, always.
- **Profile hides the face.** A block head shows no face from the side: in two-shots cheat heads 25-35 degrees toward the lens,
  prefer three-quarter singles, and keep a talking face frontal (in Tiga 13 the child's mouth only shows from mid-line).
- **Kids are `size=.74`** of the same body; a guard is `scale 1.12` in prep (taller blocks, same face sizes).
- **A turn is a whip.** Key root rotation over 6-8 frames with an overshoot (Tiga 01: 180 -> 368 -> 358), add a camera `shake`.
- **Hands carry the story.** Half the shots are inserts: a plate set down, a phone, a key. Parent the prop to a palm or the waist
  and pose the arm; the camera finds the hand.
- **Never a static frame.** Camera always moves (push, drift, `hand=.1`); something in the air moves (motes, steam, a lamp sway);
  light stays stable (no flicker, no flashes).

## Camera (`anima.Cam`)
`Cam((f, loc, target, lens, stop, focus), ..., hand=0.12)`. Lenses: 24-28 masters, 32-35 mediums, 45-55 faces, 2.8-4 stops for
faces and inserts (shallow), 5.6-8 masters. `wipe(cam, [(1, 2.2), (n-11, 2.2), (n-1, 0)])` = something dark crossing the lens
at the end of a shot (a door, a post), the next shot starts behind it: an invisible cut. `C.shake(f)` on a slam or a landing.
Place close cameras by size: `K.Cam.distance_for(lens, height)`.
