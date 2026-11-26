"""The voice decides the cut: real takes + the board -> audio/timeline.json (every shot, line and word in frames) + audio/vo.wav.

    $BP -I scripts/voice.py <project>          (BP = Blender's Python: it has numpy)

Inputs
  board/shots.json   shots in order: {"id", "look", "caption", "vo"} (+ optional "lines": [[who, text, gap_s], ...] when a shot
                     has more than one speaker or line, "beats": N for a shot with no voice, "pad": [lead_s, tail_s]).
  audio/vo_src/phrases.txt   one phrase per row, in take order:  <who> <start_s> <end_s> <text>
                     Phrases end at REAL pauses. Write them from the waveform (scripts/phrases.py lists the pauses); do not trust
                     whisper word times at pauses (up to 0.3 s off in Tiga Tradisi).
  project.json -> voice.takes: {"n": {"file": "narrator.mp3", "filter": "highpass=f=70", "denoise": [[1.36, 1.66]]}}
                     denoise = quiet stretches of that take used as its noise print (a noisy take only).
Rules (from Tiga Tradisi): cuts sit in the pauses; no change of speed or pitch; every shot = lead + its lines + tail, rounded UP to a
half beat of project.bpm; a phrase may not cross a shot; 0.75 s of black at the end. Words inside a phrase are spread by syllables.
"""
import json, os, re, sys, math, subprocess, wave
import numpy as np
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); V = PJ.get('voice', {})
FPS = PJ.get('fps', 24); BPM = PJ.get('bpm', 120); HB = 30/BPM          # half a beat in seconds
SRC, L, SR = f'{R}/audio/vo_src', f'{R}/audio/lines', 48000
TAKES = V.get('takes', {}); DPAD = V.get('pad', [.02, .05]); BLACK = V.get('black_tail', .75)
board = json.load(open(f'{R}/board/shots.json'))['shots']
norm = lambda w: re.sub(r'[^a-z0-9-]', '', w.lower())
def run(*a): return subprocess.run(a, check=True, capture_output=True).stdout

A = {w: dict(p=[], w=[], i=0) for w in TAKES}
if TAKES:
    for ln in open(f'{SRC}/phrases.txt'):
        if ln.startswith('#') or not ln.strip(): continue
        who, a, b, text = ln.strip().split(' ', 3); a, b = float(a), float(b); d = A[who]; ws = text.split()
        wt = [len(re.findall('[aeiou]', norm(w)))+.12*len(norm(w))+.25 for w in ws]; c = a
        for w, g in zip(ws, wt): d['w'].append(dict(word=w, start=c, end=c+(b-a)*g/sum(wt), phrase=len(d['p']))); c = d['w'][-1]['end']
        d['p'].append((a, b))


def denoise(x, quiet, floor=.16):
    """Wiener gain from the room tone between words, smoothed in time and frequency so it does not chirp."""
    n, h = 2048, 256; win = np.hanning(n); p = np.pad(x, n); ids = range(0, len(p)-n, h); X = np.array([np.fft.rfft(p[i:i+n]*win) for i in ids])
    t = np.array([(i-n/2)/SR for i in ids]); Pw = abs(X)**2; Nz = np.mean(Pw[np.any([(t > a) & (t < b) for a, b in quiet], axis=0)], 0)
    k = np.ones(5)/5; Pw = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), 0, Pw); Pw = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), 1, Pw)
    G = np.maximum(floor, 1-1.4*Nz/np.maximum(Pw, 1e-12)); o, w = np.zeros(len(p)), np.zeros(len(p))
    for i, Fq, g in zip(ids, X, G): o[i:i+n] += np.fft.irfft(Fq*g, n)*win; w[i:i+n] += win**2
    return (o/np.maximum(w, 1e-3))[n:n+len(x)]


for who, t in TAKES.items():
    af = (t.get('filter', 'highpass=f=70')+',') if t.get('filter', 'highpass=f=70') else ''
    x = np.frombuffer(run('ffmpeg', '-nostdin', '-v', 'error', '-i', f'{SRC}/{t["file"]}', '-af', f'{af}aresample={SR},alimiter=limit=0.93:level=0:latency=1',
                          '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'), '<f4').astype(float)
    if t.get('denoise'): x = denoise(x, t['denoise'])
    h = 240; A[who].update(x=x, noisy=bool(t.get('denoise')), h=h/SR, db=20*np.log10(np.maximum(np.sqrt(np.convolve(x**2, np.ones(960)/960, 'same'))[::h], 1e-6)))

segs = []
first = next(iter(TAKES), None)
for s in board:
    rows = s.get('lines') or ([[first, s['vo'], 0]] if s.get('vo') and first else [])
    for who, text, gap in rows:
        d = A[who]; n = len(text.split()); got = d['w'][d['i']:d['i']+n]; d['i'] += n
        assert [norm(w) for w in text.split()] == [norm(w['word']) for w in got], f"{s['id']}: {text!r} != {[w['word'] for w in got]} (phrases.txt out of step)"
        p0, p1 = got[0]['phrase'], got[-1]['phrase']; a, b = d['p'][p0][0], d['p'][p1][1]
        assert abs(got[0]['start']-a) < 1e-6 and abs(got[-1]['end']-b) < 1e-6, f"{s['id']}: a phrase crosses the shot boundary"
        lo = (d['p'][p0-1][1]+a)/2 if p0 else 0; hi = (d['p'][p1+1][0]+b)/2 if p1+1 < len(d['p']) else len(d['x'])/SR
        if d['noisy']: y, z = max(lo, a-.07), min(hi, b+.14)
        else:                                                   # keep soft onsets and breath-free tails: out to -52 dB
            y, z = a, b; at = lambda q: d['db'][min(len(d['db'])-1, int(q/d['h']))]
            while y > lo and at(y) > -52: y -= d['h']
            while z < hi and at(z) > -52: z += d['h']
            y, z = max(lo, y-.015), min(hi, z+.02)
        segs.append(dict(id=s['id'], who=who, text=text, gap=gap, src=got, a=y, b=z))
for who, d in A.items(): assert d['i'] == len(d['w']), f'{who}: {len(d["w"])-d["i"]} words in phrases.txt are not in the board'

os.makedirs(L, exist_ok=True); shots, f = [], 1
for s in board:
    i = s['id']; lead, tail = s.get('pad', DPAD); t = lead; lines = []; mine = [q for q in segs if q['id'] == i]
    for k, q in enumerate(mine):
        x = A[q['who']]['x'][int(q['a']*SR):int(q['b']*SR)].copy(); r = min(384, len(x)//4)
        rms = np.sqrt([np.mean(x[j:j+480]**2) for j in range(0, len(x)-480, 480)]); lvl = 20*np.log10(np.sqrt(np.mean(rms[rms > rms.max()*.08]**2)))
        x *= 10**((-18.8-lvl)*.75/20); x = np.tanh(x/.95)*.95 if abs(x).max() > .95 else x     # even the take out, line by line
        x[:r] *= np.linspace(0, 1, r); x[-r:] *= np.linspace(1, 0, r); p = f'{L}/{i}_{k}.wav'
        o = wave.open(p, 'w'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x, -1, 1)*32767).astype('<i2').tobytes()); o.close()
        dur = len(x)/SR; f0 = f+round(t*FPS); ws = []
        for wd, src in zip(q['text'].split(), q['src']):
            a = f0+round(max(0, src['start']-q['a'])*FPS); b = f0+round(min(dur, src['end']-q['a'])*FPS); ws.append(dict(word=wd, f=a, e=max(a+2, b), p=src['phrase']))
        lines.append(dict(who=q['who'], text=q['text'], t=t, dur=dur, wav=p, src=[q['a'], q['b']], f0=f0, f1=f+round((t+dur)*FPS), words=ws))
        t += dur+q['gap']*(k < len(mine)-1)
    sec = s['beats']*HB*2 if 'beats' in s and not mine else math.ceil((t+tail)/HB-.02)*HB
    n = max(6, round(sec*FPS))
    shots.append(dict(id=i, f0=f, f1=f+n-1, n=n, beats=round(sec/HB/2, 2), look=s.get('look', 'amber'), vo=s.get('vo', ''), caption=s.get('caption', ''), lines=lines)); f += n
total = f-1+round(BLACK*FPS); N = round(total/FPS*SR); mix = np.zeros(N)
for s in shots:
    for q in s['lines']:
        w = wave.open(q['wav']); x = np.frombuffer(w.readframes(w.getnframes()), '<i2')/32768; a = round((q['f0']-1)/FPS*SR); x = x[:N-a]; mix[a:a+len(x)] += x
o = wave.open(f'{R}/audio/vo.wav', 'w'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(mix, -1, 1)*32767).astype('<i2').tobytes()); o.close()
json.dump(dict(fps=FPS, bpm=BPM, total=total, black=round(BLACK*FPS), shots=shots), open(f'{R}/audio/timeline.json', 'w'), indent=1, ensure_ascii=False)
print(f'TOTAL {total} frames, {total/FPS:.2f} s, {len(shots)} shots')
for s in shots: print(f"{s['id']:>4} {s['n']:4d} f {s['beats']:5.1f} beats | " + ' | '.join(q['text'][:40] for q in s['lines']))
