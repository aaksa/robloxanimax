"""Draft audio/vo_src/phrases.txt from a take's real pauses.

    python3 -I scripts/phrases.py <project> <who> <take file> [--script lines.txt] [--gap 0.22] [--db -38]

Lists every stretch of speech between pauses (ffmpeg silencedetect). With --script (one phrase per line, in the order spoken),
pairs them up when the counts match and appends `<who> <start> <end> <text>` rows to phrases.txt; otherwise prints the stretches
so you can merge or split them by ear. Always listen to the joins once: a breath can read as a pause and a fast join as none.
"""
import os, re, subprocess, sys
a = sys.argv[1:]
if len(a) < 3: raise SystemExit(__doc__)
R, who, take = os.path.abspath(a[0]), a[1], a[2]
opt = lambda k, d: a[a.index(k)+1] if k in a else d
gap, db = float(opt('--gap', .22)), float(opt('--db', -38))
path = take if os.path.isabs(take) else f'{R}/audio/vo_src/{take}'
err = subprocess.run(['ffmpeg', '-nostdin', '-v', 'info', '-i', path, '-af', f'silencedetect=noise={db}dB:d={gap}', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
dur = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', err).groups()[2]) + 60*float(re.search(r'Duration: (\d+):(\d+)', err).group(2)) + 3600*float(re.search(r'Duration: (\d+)', err).group(1))
st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]; en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
edges = sorted([(s, 'S') for s in st]+[(e, 'E') for e in en]); segs = []; cur = 0.0
for t, k in edges:
    if k == 'S':
        if t-cur > .08: segs.append((cur, t))
    else: cur = t
if dur-cur > .08 and (not edges or edges[-1][1] == 'E'): segs.append((cur, dur))
if '--script' in a:
    lines = [l.strip() for l in open(opt('--script', '')) if l.strip()]
    if len(lines) != len(segs):                                   # a comma is often a real pause: try phrases at , ; :
        sub = [p.strip() for l in lines for p in re.findall(r'[^,;:]+[,;:]?', l) if p.strip()]
        if len(sub) == len(segs): lines = sub
    if len(lines) == len(segs):
        with open(f'{R}/audio/vo_src/phrases.txt', 'a') as o:
            for (s, e), t in zip(segs, lines): o.write(f'{who} {s:.2f} {e:.2f} {t}\n')
        print(f'appended {len(lines)} phrases to audio/vo_src/phrases.txt: check each join by ear'); raise SystemExit
    print(f'{len(segs)} speech stretches but {len(lines)} script lines: merge or split by hand (try --gap {gap+.08:.2f} or {max(.1, gap-.06):.2f})')
for i, (s, e) in enumerate(segs): print(f'{i:3d}  {who} {s:.2f} {e:.2f}  ({e-s:.2f} s)')
