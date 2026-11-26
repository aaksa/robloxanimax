"""THE CAST card (1920x1080 JPEG, two characters a page): concept > Meshy image-to-3D > wireframe > in the film.
The behind-the-scenes image Tiga Tradisi used for its Meshy Z-Axis entry; also a cover for a "how I made it" reel.

    uv run --offline --no-project --with pillow python -I -B scripts/cast_card.py <project>

Inputs:  ref/<name>_front.png (the faceless block reference), out/gallery/assets/<name>_tex.png + _wire.png + faces.txt
         (blender/studio.py), a graded film frame per character, assets/meshy.json (which models made it).
project.json -> card:
  {"pages": [["cucu", "nenek"]],
   "cast": {"cucu": {"title": "CUCU", "role": "the grandchild, Toraja", "film": "out/stills/01_0030.jpg", "box": [20, 500, 920, 1700]}},
   "footer": "Meshy gave body, clothes and texture. Faces, joints, acting and light were added in Blender."}
  box = the crop of the film frame (pixels) that shows the character; the tile is 3:4.
Output: out/gallery/cast_<n>.jpg
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); CARD = PJ.get('card', {})
G = f'{R}/out/gallery'; A = f'{G}/assets'; os.makedirs(G, exist_ok=True)
W, H = 1920, 1080; BG = (11, 11, 13); GOLD = (255, 211, 77); WHITE = (244, 244, 244); GREY = (150, 150, 156)


def font(cands, size, index=0):
    for c in cands:
        p = os.path.expanduser(c)
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size, index=index)
            except OSError: continue
    return ImageFont.load_default()
HEAD = [PJ.get('title_font', ''), '~/Ngonten/Maxxing/Roblox/sigajang/fonts/Anton-Regular.ttf', '/System/Library/Fonts/Supplemental/Impact.ttf',
        '/System/Library/Fonts/Supplemental/Arial Black.ttf']
BODY = ['/System/Library/Fonts/Avenir Next.ttc', '/System/Library/Fonts/Helvetica.ttc']
TITLE = lambda s: font(HEAD, s); AV = lambda s, i=0: font(BODY, s, i)     # Avenir Next: 0 Bold, 2 Demi Bold, 7 Regular
FACES = dict(l.split() for l in open(f'{A}/faces.txt') if l.strip()) if os.path.exists(f'{A}/faces.txt') else {}
LEDGER = json.load(open(f'{R}/assets/meshy.json')) if os.path.exists(f'{R}/assets/meshy.json') else {}


def cover(im, w, h, box=None):
    if box: im = im.crop(box)
    s = max(w/im.width, h/im.height); im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    x, y = (im.width-w)//2, (im.height-h)//2; return im.crop((x, y, x+w, y+h))


def tile(path, w, h, box=None):
    p = path if os.path.isabs(path) else os.path.join(R, path)
    if os.path.exists(p): return cover(Image.open(p).convert('RGB'), w, h, box)
    im = Image.new('RGB', (w, h), (26, 26, 30)); ImageDraw.Draw(im).text((w//2, h//2), 'missing', font=AV(20), fill=GREY, anchor='mm'); print('missing', p); return im


def models(n):
    e = LEDGER.get(n, {}); g = e.get('ai_model'); t = e.get('texture_model')
    return ' + '.join(x for x in (g, t) if x) or e.get('note', '')


TW, TH, GAP, LEFT = 300, 400, 26, 430
pages = CARD.get('pages') or [list(CARD.get('cast', PJ.get('cast', {})))[i:i+2] for i in range(0, len(CARD.get('cast', PJ.get('cast', {}))), 2)]
for pi, who in enumerate(pages, 1):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    big = CARD.get('title', 'THE CAST'); d.text((72, 58), big, font=TITLE(58), fill=GOLD, anchor='ls')
    d.text((72+d.textlength(big, font=TITLE(58))+26, 56), CARD.get('subtitle', 'concept  >  Meshy image-to-3D  >  wireframe  >  in the film'), font=AV(26, 2), fill=GREY, anchor='ls')
    for r, n in enumerate(who):
        c = CARD.get('cast', {}).get(n, {}); y = 112+r*(TH+76)
        d.text((72, y+170), c.get('title', n.upper().replace('_', ' ')), font=TITLE(64), fill=WHITE, anchor='ls')
        d.text((74, y+212), c.get('role', ''), font=AV(27, 2), fill=GREY, anchor='ls')
        d.text((74, y+256), models(n) if n in LEDGER else 'block stand-in, no Meshy task yet', font=AV(22, 7), fill=GREY, anchor='ls')
        nf = FACES.get(n); tiles = [(tile(f'ref/{n}_front.png', TW, TH), 'CONCEPT'), (tile(f'{A}/{n}_tex.png', TW, TH), 'MESHY MODEL' if n in LEDGER else 'STAND-IN (NOT MESHY YET)'),
                                    (tile(f'{A}/{n}_wire.png', TW, TH), f'WIREFRAME  {int(nf):,} FACES' if nf else 'WIREFRAME'),
                                    (tile(c.get('film', ''), TW, TH, tuple(c['box']) if c.get('box') else None), 'IN THE FILM')]
        for i, (t, lab) in enumerate(tiles):
            x = LEFT+80+i*(TW+GAP); im.paste(t, (x, y))
            if i == 3: d.rectangle((x-2, y-2, x+TW+1, y+TH+1), outline=GOLD, width=2)
            d.text((x, y+TH+30), lab, font=AV(19, 2), fill=GOLD if i == 3 else GREY, anchor='ls')
            if i: d.text((x-GAP//2, y+TH//2), '>', font=AV(26, 0), fill=GREY, anchor='mm')
    d.text((W-72, H-30), CARD.get('footer', 'Meshy gave body, clothes and texture. Faces, joints, acting and light were added in Blender.'), font=AV(21, 7), fill=GREY, anchor='rs')
    p = f'{G}/cast_{pi}.jpg'; im.save(p, quality=93, subsampling=0); print('wrote', os.path.relpath(p, R))
