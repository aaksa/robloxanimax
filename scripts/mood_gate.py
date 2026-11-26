#!/usr/bin/env python3
"""GATE L for every mood: is this picture as bright, as deep and as coloured as its mood should be?

  python3 -I mood_gate.py <still | frames_dir | film.mp4> --look day|morning|golden|overcast|amber|noir|cold|sick [--fps 24]

Dark looks go to cinematicanimation look_gate.py (bands measured on two low-key reference films).
Daylight bands below are STARTING bands, not measurements of reference films: they were set from what reads as a clean, sunny
toy-world frame on a phone and checked against this skill's own day stills (see references/moods.md). When the user approves a
day film, measure it (`mood_gate.py film.mp4 --look day`) and move the bands to it.
Exit code 1 on a FAIL. A FAIL is fixed in the light (sun strength, sky light, exposure), not in the grade.
"""
import sys, os, argparse, subprocess
CS = os.environ.get('CINE_SCRIPTS') or os.path.expanduser('~/.claude/skills/cinematicanimation/scripts')
sys.path.insert(0, CS)
from _probe import probe, cuts, pct

DARK = {'amber': 'amber', 'noir': 'noir', 'cold': 'any', 'sick': 'any', 'clean': 'any'}
# name: median, shadow p10, bright p90, peak, black floor, saturation   (pass ranges; warn = 30 % wider)
BANDS = {
    'day':      dict(med=(.36, .62), lo=(.08, .30), hi=(.55, .92), mx=(.88, 1), mn=(0, .10), sat=(.14, .42)),
    'morning':  dict(med=(.30, .58), lo=(.07, .30), hi=(.55, .90), mx=(.85, 1), mn=(0, .10), sat=(.10, .38)),
    'golden':   dict(med=(.24, .52), lo=(.04, .22), hi=(.45, .88), mx=(.85, 1), mn=(0, .08), sat=(.14, .45)),
    'overcast': dict(med=(.32, .58), lo=(.12, .34), hi=(.52, .84), mx=(.72, 1), mn=(0, .14), sat=(.06, .28)),
}
TIP = dict(med='too dark: raise sun_mult or exposure +0.3 / too bright: lower exposure, darker ground',
           lo='shadows: grey and flat = less sky light (amb); crushed = more sky light or a fill',
           hi='the lit area: too small = turn the sun toward the lens side (az 20-50); blown = lower the sun',
           mx='no true white: a white shirt, a glint, a sunlit wall, a cloud in frame', mn='blacks lifted: something dark in frame (a doorway, hair, a shadow)',
           sat='too grey: warmer sun, coloured props / too loud: fewer saturated props, lower the grade')
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('--look', default='day'); ap.add_argument('--fps', type=float, default=24)
a = ap.parse_args()
if a.look in DARK:
    raise SystemExit(subprocess.run([sys.executable, '-I', f'{CS}/look_gate.py', a.src, '--look', DARK[a.look], '--fps', str(a.fps)]).returncode)
B = BANDS[a.look]; fr = probe(a.src, a.fps); fr = [f for f in fr if f['mx'] > .06] or fr
val = dict(med=pct([f['Y'] for f in fr], .5), lo=pct([f['lo'] for f in fr], .5), hi=pct([f['hi'] for f in fr], .5),
           mx=pct([f['mx'] for f in fr], .5), mn=pct([f['mn'] for f in fr], .5), sat=pct([f['sat'] for f in fr], .5))
NAME = dict(med='median brightness', lo='shadow level (10th pct pixel)', hi='bright level (90th pct pixel)', mx='peak (brightest pixel)',
            mn='black floor (darkest pixel)', sat='saturation')
bad = 0; print(f"GATE L  {a.src}  ({len(fr)} frame{'s'*(len(fr) != 1)}, look={a.look}, daylight starting bands)")
for k, (p0, p1) in B.items():
    v = val[k]; w = (p1-p0)*.3; st = 'ok  ' if p0 <= v <= p1 else 'WARN' if p0-w <= v <= p1+w else 'FAIL'; bad += st == 'FAIL'
    print(f"  [{st}] {NAME[k]:32s} {v:5.2f}   target {p0:.2f}-{p1:.2f}" + ('' if st == 'ok  ' else f'   -> {TIP[k]}'))
if len(fr) > 2:
    c = cuts(fr); ct = set(round(x, 3) for x in c)
    j = [f['t'] for i, f in enumerate(fr[1:], 1) if abs(f['Y']-fr[i-1]['Y']) > .06 and round(f['t'], 3) not in ct]
    print(f"  [{'ok  ' if not j else 'WARN'}] brightness jumps inside a shot    {len(j):3d}" + ('' if not j else f"   -> near {', '.join(f'{t:.2f}s' for t in j[:8])}"))
sys.exit(1 if bad else 0)
