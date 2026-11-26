"""Voice + music + effects -> audio/mix.wav and audio/mix_no_vo.wav (48 kHz stereo, -14 LUFS, true peak under -1.5 dBFS).

    $BP -I scripts/mix.py <project>          (BP = Blender's Python: numpy)    REPORT=1 also prints voice-over-music levels

project.json -> mix:
  music        a track (any format ffmpeg reads). Leave out for voice + effects only.
  music_in     where in the track to start (s);  at = where in the film it starts (s);  gain_db (default -15)
  duck_db      how far the music dips under speech (default 7; Tiga Tradisi's bed sat 9-11 dB under the voice)
  holes        [[from_s, to_s], ...] the music is OUT (the turn: 3-8 s of room tone). Fades 0.4 s each side.
  fade_out     seconds of fade at the end (default 3)
  room         room-tone level in dB under the holes (default -48; null = true silence)
  sfx          [{"file": path, "at": CUE, "gain_db": -6, "pan": 0}]   CUE = seconds | "shot:ID" | "shot:ID+0.4" | "word:ID:text"
Effects come from ~/Ngonten/Maxxing/audio-lib (CC0: Kenney, Earshot bank). Put one on every hit you can see: a slam, a step,
a plate set down, a light switch. The picture never moves without a sound and the sound never plays without a picture.
"""
import json, os, sys, subprocess, re, tempfile
import numpy as np
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); MX = PJ.get('mix', {})
T = json.load(open(f'{R}/audio/timeline.json')); FPS = T['fps']; SR = 48000; N = int(T['total']/FPS*SR)
S = {s['id']: s for s in T['shots']}
P = lambda p: p if os.path.isabs(os.path.expanduser(p)) else os.path.join(R, p)


def load(path, ch=2):
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', os.path.expanduser(P(path)), '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, '<f4').astype(float).reshape(-1, ch).T


def cue(c):
    if isinstance(c, (int, float)): return float(c)
    kind, rest = c.split(':', 1)
    if kind == 'shot':
        sid, _, off = rest.partition('+'); return (S[sid]['f0']-1)/FPS+float(off or 0)
    if kind == 'word':
        sid, w = rest.split(':', 1)
        hits = [x['f'] for q in S[sid]['lines'] for x in q['words'] if w.lower() in x['word'].lower()]
        if not hits: raise SystemExit(f'cue {c}: no such word in shot {sid}')
        return (hits[0]-1)/FPS
    raise SystemExit(f'unknown cue {c}')


def ramp(env, a, b, lo, f=.4):
    """Multiply env down to lo between a and b seconds, with f-second ramps."""
    t = np.arange(len(env))/SR
    m =np.clip(np.minimum((t-(a-f))/f, ((b+f)-t)/f), 0, 1); return env*(1-m*(1-lo))


vo = load(f'{R}/audio/vo.wav', 1)[0][:N]; vo = np.pad(vo, (0, N-len(vo)))
mus, fx = np.zeros((2, N)), np.zeros((2, N))
if MX.get('music'):
    x = load(MX['music']); a = int(MX.get('music_in', 0)*SR); x = x[:, a:]; at = int(MX.get('at', 0)*SR); x = x[:, :max(0, N-at)]
    mus[:, at:at+x.shape[1]] += x*10**(MX.get('gain_db', -15)/20)
    env = np.ones(N)
    for h in MX.get('holes', []): env = ramp(env, h[0], h[1], 0.0)
    sp = np.convolve(np.abs(vo) > .02, np.ones(int(.25*SR))/(.25*SR), 'same') > .05     # speech present (250 ms window)
    duck = np.where(sp, 10**(-MX.get('duck_db', 7)/20), 1.0)
    k = int(.12*SR); duck = np.convolve(np.pad(duck, k, mode='edge'), np.ones(k)/k, 'same')[k:-k][:N]
    fo = int(MX.get('fade_out', 3)*SR); env[-fo:] *= np.linspace(1, 0, fo)
    mus *= env*duck
    if MX.get('room', -48) is not None:
        rng = np.random.default_rng(5); X = np.fft.rfft(rng.standard_normal(N)); f = np.fft.rfftfreq(N, 1/SR)
        X /= np.maximum(f, 20)**.5; X[f > 4000] *= .2; rt = np.fft.irfft(X, N); rt /= np.abs(rt).max()
        mus += np.vstack([rt, np.roll(rt, 4800)])*(1-env)*10**(MX.get('room', -48)/20)
for e in MX.get('sfx', []):
    if not os.path.exists(os.path.expanduser(P(e['file']))): print('effect missing, skipped:', e['file']); continue
    x = load(e['file']); a = int(cue(e['at'])*SR); x = x[:, :max(0, N-a)]; g = 10**(e.get('gain_db', -6)/20); p = e.get('pan', 0)
    fx[0, a:a+x.shape[1]] += x[0]*g*np.sqrt((1-p)/2)*1.414; fx[1, a:a+x.shape[1]] += x[1]*g*np.sqrt((1+p)/2)*1.414


def write(path, y):
    tmp = tempfile.mktemp(suffix='.f32'); (np.clip(y.T, -4, 4).astype('<f4')).tofile(tmp)
    base = ['ffmpeg', '-nostdin', '-v', 'info', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', tmp]
    m = subprocess.run(base+['-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    j = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', m)[-1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample={SR}")
    subprocess.run(base+['-af', af, '-c:a', 'pcm_s24le', '-y', path], check=True, capture_output=True); os.remove(tmp)
    print('wrote', os.path.relpath(path, R), f"(input {j['input_i']} LUFS)")


write(f'{R}/audio/mix.wav', mus+fx+np.vstack([vo, vo]))
write(f'{R}/audio/mix_no_vo.wav', mus+fx)
if os.environ.get('REPORT') and MX.get('music'):
    sp = np.abs(vo) > .02; db = lambda v: 20*np.log10(np.sqrt(np.mean(v**2))+1e-9)
    print(f'voice over music while talking: {db(vo[sp])-db(mus[0][sp]):.1f} dB (aim 9-17)')
