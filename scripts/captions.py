"""Burned-in text: out/subs.ass (phrase subtitles, the word being spoken in gold, + labels), out/labels.ass (labels only),
out/subs_en.ass (Indonesian above, English below) when board/shots.json has "en" per line.

    python3 -I scripts/captions.py <project>

Labels: a shot's "caption" in board/shots.json (a place name, a term with its meaning: small, yellow, top). Leave it empty for none.
Word timing: the timeline's syllable estimate inside each phrase; audio/vo_src/word_starts.json ({"who": [[word, take_s], ...]},
from a forced alignment, +0.11 s lag) overrides it when present.
Layout is measured from Tiga Tradisi / Sigajang at 1080x1920: subtitles bottom-centre at 400 px margin, gold &H4DD3FF&, cues are
spoken phrases (a lone short word is merged into its neighbour, a long phrase is split near its middle, 32 characters max).
For 16:9 set project.json width/aspect; the sizes scale with the frame.
"""
import json, os, sys
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); T = json.load(open(f'{R}/audio/timeline.json'))
FPS = T['fps']; board = {s['id']: s for s in json.load(open(f'{R}/board/shots.json'))['shots']}
asp = PJ.get('aspect', '9:16'); W = PJ.get('width', 1080)
if asp == '9:16': PX, PY = W, round(W*16/9)
else: PX, PY = round(W*16/9), W
k = PX/1080 if asp == '9:16' else PY/1080
font = PJ.get('caption_font', 'Helvetica Neue')
HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PX}
PlayResY: {PY}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: L,{font},{round(56*k)},&H0040D8FF,&H0040D8FF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,8,90,90,{round(300*k)},1
Style: S,{font},{round(54*k)},&H00F4F4F4,&H00F4F4F4,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,3.5,0,2,110,150,{round(400*k)},1
Style: E,Avenir Next Demi Bold,{round(46*k)},&H00F4F4F4,&H00F4F4F4,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,8,110,150,{round(1412*k) if asp == '9:16' else round(900*k)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
GOLD, WHITE = '&H4DD3FF&', '&HF4F4F4&'
def ts(f): s = max(0, (f-1)/FPS); return f'{int(s//3600)}:{int(s//60 % 60):02d}:{s % 60:05.2f}'

ws_path = f'{R}/audio/vo_src/word_starts.json'
if os.path.exists(ws_path):
    WS = json.load(open(ws_path)); n_ = {x: 0 for x in WS}
    for q in [q for s in T['shots'] for q in s['lines']]:
        for w in q['words']:
            word, t = WS[q['who']][n_[q['who']]]; n_[q['who']] += 1
            assert word.lower().strip('.,!?') == w['word'].lower().strip('.,!?'), f'word_starts.json out of step: {word!r} / {w["word"]!r}'
            w['hl'] = q['f0']+round((t-q['src'][0])*FPS)
L, C, E = [], [], []
for s in T['shots']:
    cap = (s.get('caption') or '').strip()
    if cap:
        f0 = s['f0']+(0 if s['f0'] == 1 else 6); f1 = min(s['f1'], f0+56)
        L.append(f"Dialogue: 1,{ts(f0)},{ts(f1)},L,,0,0,0,,{{\\fad({0 if s['f0'] == 1 else 150},150)}}{cap}")
    en_lines = board.get(s['id'], {}).get('en') or []
    if isinstance(en_lines, str): en_lines = [en_lines]
    for qi, q in enumerate(s['lines']):
        if qi < len(en_lines) and en_lines[qi]: E.append((q['f0'], q['f1'], en_lines[qi]))
        ph = []
        for w in q['words']:
            if ph and ph[-1][-1]['p'] == w['p']: ph[-1].append(w)
            else: ph.append([w])
        size = lambda g: len(' '.join(x['word'] for x in g))
        short = lambda g: size(g) < 10 or g[-1]['e']-g[0]['f'] < 9; stop = lambda g: g[-1]['word'][-1] in '.?!'
        i = 0
        while i < len(ph):
            if short(ph[i]) and i and not stop(ph[i-1]) and size(ph[i-1]+ph[i]) <= 32: ph[i-1:i+1] = [ph[i-1]+ph[i]]; i -= 1
            elif short(ph[i]) and i+1 < len(ph) and not stop(ph[i]) and size(ph[i]+ph[i+1]) <= 32: ph[i:i+2] = [ph[i]+ph[i+1]]
            else: i += 1
        for g in ph:
            if size(g) > 32: m = min(range(1, len(g)), key=lambda j: abs(size(g[:j])-size(g[j:]))); C.extend((g[:m], g[m:]))
            else: C.append(g)
S = []
for ci, g in enumerate(C):
    a = g[0].get('hl', g[0]['f']); b = g[-1]['e']+4
    nxt = C[ci+1][0].get('hl', C[ci+1][0]['f']) if ci+1 < len(C) else None
    if nxt and nxt-b < 8: b = nxt                                       # no flicker between close cues
    hs = [w.get('hl', w['f']) for w in g]
    for j, w in enumerate(g):                                            # one event per word: the spoken word is gold
        f0 = a if j == 0 else hs[j]; f1 = hs[j+1] if j+1 < len(g) else b
        if f1 <= f0: continue
        txt = ' '.join((f'{{\\c{GOLD}}}{x["word"]}{{\\c{WHITE}}}' if x is w else x['word']) for x in g)
        S.append(f'Dialogue: 0,{ts(f0)},{ts(f1)},S,,0,0,0,,{txt}')
os.makedirs(f'{R}/out', exist_ok=True)
open(f'{R}/out/labels.ass', 'w').write(HEAD+'\n'.join(L)+'\n')
open(f'{R}/out/subs.ass', 'w').write(HEAD+'\n'.join(L+S)+'\n')
if E: open(f'{R}/out/subs_en.ass', 'w').write(HEAD+'\n'.join(L+S+[f'Dialogue: 0,{ts(a)},{ts(b+4)},E,,0,0,0,,{t}' for a, b, t in E])+'\n')
print(f'labels {len(L)}, cues {len(C)}, word events {len(S)}, english {len(E)}')
