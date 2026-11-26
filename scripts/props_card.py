"""THE PROPS card (1920x1080 JPEG, ten props a page): every Meshy model in the film, textured on the left, wireframe on the right,
split by a gold diagonal, with its name, where it came from and its face count. The companion of cast_card.py.

    uv run --offline --no-project --with pillow python -I -B scripts/props_card.py <project>

Inputs: out/gallery/assets/<name>_tex.png + _wire.png + faces.txt (blender/studio.py), assets/props.json, assets/meshy.json.
Which props: every row of props.json with a model on disk and "card" not false, in file order. Per row (all optional):
  "title": "Dinner plate"     the name on the card (default: the key, capitalised)
  "source": "Meshy 6"         the line under it (default: the ledger's models, else "Meshy")
Output: out/gallery/props_<n>.jpg. A stand-in (no Meshy task in the ledger) is labelled STAND-IN, never Meshy.
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); CARD = PJ.get('props_card', {})
G = f'{R}/out/gallery'; A = f'{G}/assets'
SPEC = json.load(open(f'{R}/assets/props.json'))
LEDGER = json.load(open(f'{R}/assets/meshy.json')) if os.path.exists(f'{R}/assets/meshy.json') else {}
FACES = dict(l.split() for l in open(f'{A}/faces.txt') if l.strip()) if os.path.exists(f'{A}/faces.txt') else {}
W, H = 1920, 1080; BG = (11, 11, 13); GOLD = (255, 211, 77); WHITE = (244, 244, 244); GREY = (150, 150, 156)


def font(cands, size, index=0):
    for c in cands:
        p = os.path.expanduser(c)
        if c and os.path.exists(p):
            try: return ImageFont.truetype(p, size, index=index)
            except OSError: continue
    return ImageFont.load_default()
HEAD = [PJ.get('title_font', ''), '~/Ngonten/Maxxing/Roblox/sigajang/fonts/Anton-Regular.ttf', '/System/Library/Fonts/Supplemental/Impact.ttf']
BODY = ['/System/Library/Fonts/Avenir Next.ttc', '/System/Library/Fonts/Helvetica.ttc']
TITLE = lambda s: font(HEAD, s); AV = lambda s, i=0: font(BODY, s, i)


def cover(im, w, h, box=None):
    if box: im = im.crop(box)
    s = max(w/im.width, h/im.height); im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    x, y = (im.width-w)//2, (im.height-h)//2; return im.crop((x, y, x+w, y+h))


def source(n, c):
    if c.get('source'): return c['source']
    e = LEDGER.get(n)
    if not e: return 'stand-in, not Meshy'
    return ' + '.join(x for x in (e.get('ai_model'), e.get('texture_model')) if x) or 'Meshy'


names = [n for n, c in SPEC.items() if c.get('card', True) and os.path.exists(f'{A}/{n}_tex.png') and os.path.exists(f'{A}/{n}_wire.png')]
skipped = [n for n, c in SPEC.items() if c.get('card', True) and n not in names]
if skipped: print('no studio render yet (run blender/studio.py):', ', '.join(skipped))
PW, PH, PG = 344, 380, 20
mask = Image.new('L', (PW, PH), 0); ImageDraw.Draw(mask).polygon([(0, 0), (PW*.62, 0), (PW*.38, PH), (0, PH)], fill=255)
for pi in range(0, len(names), 10):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    big = CARD.get('title', 'THE PROPS'); d.text((72, 58), big, font=TITLE(58), fill=GOLD, anchor='ls')
    d.text((72+d.textlength(big, font=TITLE(58))+26, 56), CARD.get('subtitle', 'every Meshy model in the film, textured  /  wireframe'), font=AV(26, 2), fill=GREY, anchor='ls')
    for k, n in enumerate(names[pi:pi+10]):
        c = SPEC[n]; col, row = k % 5, k // 5; x = 72+col*(PW+PG); y = 112+row*(PH+92)
        tex = cover(Image.open(f'{A}/{n}_tex.png').convert('RGB'), PW, PH, (90, 0, 910, 1000))
        wire = cover(Image.open(f'{A}/{n}_wire.png').convert('RGB'), PW, PH, (90, 0, 910, 1000))
        t = wire.copy(); t.paste(tex, (0, 0), mask); im.paste(t, (x, y))
        d.line([(x+PW*.62, y), (x+PW*.38, y+PH)], fill=GOLD, width=2)
        d.text((x, y+PH+34), c.get('title', n.replace('_', ' ')).upper(), font=AV(22, 0), fill=WHITE, anchor='ls')
        f = FACES.get(n); d.text((x, y+PH+62), source(n, c)+(f'  ·  {int(f):,} faces' if f else ''), font=AV(18, 7), fill=GREY, anchor='ls')
    p = f'{G}/props_{pi//10+1}.jpg'; im.save(p, quality=93, subsampling=0); print('wrote', os.path.relpath(p, R))
