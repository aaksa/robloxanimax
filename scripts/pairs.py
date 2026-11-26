"""'In Meshy / In your work' pairs: for every Meshy model, the untouched GLB in the studio next to a frame of the film where it
plays. Contest forms (Meshy Z-Axis Awards "Screenshots") ask for exactly this; it also makes a clean before/after carousel.

    WIDE=1 Blender -b --factory-startup -P blender/studio.py -- <project>      (once: 1920x1080 studio plates, <name>_wide.png)
    uv run --offline --no-project --with pillow python -I -B scripts/pairs.py <project>

Which frame: "film": "out/stills/20_0040.jpg" (+ optional "pair_box": [x0, y0, x1, y1] crop) on the prop's row in assets/props.json, or
on the character's row in project.json -> card.cast. Pick frames by LOOKING at candidates: Tiga Tradisi found that frames chosen
by the prop's projected box alone showed it behind a character or mid whip-pan.
Output: out/gallery/pairs/pairNN_<name>_a_meshy.jpg and _b_film.jpg, 1920x1080 each (a vertical frame sits centred on dark).
"""
import os, sys, json
from PIL import Image, ImageFilter
R = os.path.abspath(sys.argv[1]); PJ = json.load(open(f'{R}/project.json')); G = f'{R}/out/gallery'; OUT = f'{G}/pairs'
os.makedirs(OUT, exist_ok=True); W, H = 1920, 1080
rows = [(n, c) for n, c in PJ.get('card', {}).get('cast', {}).items() if c.get('film')]
if os.path.exists(f'{R}/assets/props.json'): rows += [(n, c) for n, c in json.load(open(f'{R}/assets/props.json')).items() if c.get('film')]


def fit(im):
    """Fill 16:9 when the frame is landscape; a vertical frame goes in the middle over a blurred, darkened copy of itself."""
    if im.width/im.height > 1.3:
        s = max(W/im.width, H/im.height); im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
        x, y = (im.width-W)//2, (im.height-H)//2; return im.crop((x, y, x+W, y+H))
    bg = im.resize((W, round(W*im.height/im.width)), Image.LANCZOS); y = (bg.height-H)//2
    bg = bg.crop((0, y, W, y+H)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v*.35))
    fg = im.resize((round(H*im.width/im.height), H), Image.LANCZOS); bg.paste(fg, ((W-fg.width)//2, 0)); return bg


i = 0
for n, c in rows:
    a = f'{G}/assets/{n}_wide.png'; b = os.path.join(R, c['film'])
    if not os.path.exists(a) or not os.path.exists(b): print('skip', n, '(missing', a if not os.path.exists(a) else b, ')'); continue
    i += 1
    Image.open(a).convert('RGB').resize((W, H), Image.LANCZOS).save(f'{OUT}/pair{i:02d}_{n}_a_meshy.jpg', quality=93, subsampling=0)
    f = Image.open(b).convert('RGB')
    if c.get('pair_box'): f = f.crop(tuple(c['pair_box']))
    fit(f).save(f'{OUT}/pair{i:02d}_{n}_b_film.jpg', quality=93, subsampling=0); print('pair', i, n)
