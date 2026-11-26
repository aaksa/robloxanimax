#!/usr/bin/env python3
"""The grade for every mood. Same use as cinematicanimation's finish.py (frames dir | still | video -> graded file):

  python3 -I grade.py <frames_dir | still.jpg | plates.mp4> --out film.mp4 --look day [--fps 24] [--grain 3] [--crf 15]

Dark looks (amber, noir, sick, cold, clean) go straight to cinematicanimation finish.py: wide glow round the lamps, lifted black,
heavy vignette, measured from the low-key reference films.
Daylight looks are graded here, because a bright frame breaks that recipe: a wide glow turns a blue sky into milk, and a heavy
vignette reads as dirt on a sunny wall. So: a small glow on the hottest highlights only, a softer film curve that keeps the sky,
a light vignette, finer grain.
  day       midday: clean whites, sky-blue shadows, a touch of warmth in the sun
  morning   fresh: cool shadows, pale warm highlights, a little lower contrast
  golden    late sun: warm mids and highs, rich saturation, deep warm shadows
  overcast  soft grey light: lower saturation, cool neutral, gentle contrast (rain, grief, an ordinary Tuesday)
"""
import sys, os, argparse, subprocess
CS = os.environ.get('CINE_SCRIPTS') or os.path.expanduser('~/.claude/skills/cinematicanimation/scripts')
sys.path.insert(0, CS)
from _probe import src_args

DAY = {  # saturation, contrast, colorbalance (shadows rgb, mids rgb, highs rgb), glow, vignette angle
    'day':      (1.06, 1.03, (-0.03, 0.00, 0.04, 0.01, 0.00, -0.01, 0.03, 0.01, -0.02), .18, 'PI/7'),
    'morning':  (1.00, 0.99, (-0.04, 0.00, 0.05, 0.00, 0.00, 0.01, 0.04, 0.02, -0.01), .22, 'PI/7'),
    'golden':   (1.14, 1.04, (0.03, -0.01, -0.04, 0.05, 0.01, -0.05, 0.05, 0.01, -0.06), .30, 'PI/6'),
    'overcast': (0.90, 0.98, (-0.02, 0.00, 0.03, -0.01, 0.00, 0.01, 0.00, 0.00, 0.01), .10, 'PI/7'),
}
DARK = ('amber', 'noir', 'sick', 'cold', 'clean')
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('--out', required=True); ap.add_argument('--look', default='day', choices=(*DAY, *DARK))
ap.add_argument('--audio'); ap.add_argument('--fps', type=float, default=24); ap.add_argument('--grain', type=int, default=3)
ap.add_argument('--glow', type=float); ap.add_argument('--crf', type=int, default=14)
a = ap.parse_args()
if a.look in DARK:
    cmd = [sys.executable, '-I', f'{CS}/finish.py', a.src, '--out', a.out, '--look', a.look, '--fps', str(a.fps), '--grain', str(a.grain), '--crf', str(a.crf)]
    if a.audio: cmd += ['--audio', a.audio]
    if a.glow is not None: cmd += ['--glow', str(a.glow)]
    raise SystemExit(subprocess.run(cmd).returncode)
sat, con, cb, glow, vig = DAY[a.look]; glow = glow if a.glow is None else a.glow
args, n = src_args(a.src, a.fps)
w = int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width', '-of', 'csv=p=0',
                        *([args[-1]] if n is None else ['-f', 'concat', '-safe', '0', args[-1]])], capture_output=True, text=True).stdout.split()[0])
k = max(1, round(w/1920))
cbs = ':'.join(f'{nm}={v}' for nm, v in zip(('rs', 'gs', 'bs', 'rm', 'gm', 'bm', 'rh', 'gh', 'bh'), cb))
vf = (f"format=gbrp16le,split[a][b];[b]curves=all='0/0 0.82/0 1/1',gblur=sigma={w*0.008:.1f}[g];"     # only the hottest highlights bloom
      f"[a][g]blend=all_mode=screen:all_opacity={glow},"
      f"colorbalance={cbs},eq=saturation={sat}:contrast={con},"
      f"curves=all='0/0.012 0.25/0.245 0.75/0.765 1/0.985',"                                          # gentle shoulder: the sky keeps its blue
      f"gblur=sigma={0.35*k:.2f},vignette=angle={vig},noise=alls={a.grain}:allf=t+u,format=yuv420p")
still = a.out.lower().endswith(('.png', '.jpg', '.jpeg'))
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args] + (['-i', a.audio] if a.audio else []) + ['-vf', vf]
if still: cmd += ['-frames:v', '1', '-update', '1', '-q:v', '2', a.out]
else:
    cmd += ['-r', str(a.fps), '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-colorspace', 'bt709',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart']
    if a.audio: cmd += ['-c:a', 'aac', '-b:a', '256k', '-shortest']
    cmd += [a.out]
subprocess.run(cmd, check=True); print('grade:', a.out, f'(look={a.look})')
