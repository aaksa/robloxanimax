---
name: robloxanimax
description: >-
  Make a narrated, cinematic Roblox-style animated short (a 9:16 story reel or a 16:9 film) whose whole cast and props are
  generated with Meshy through the Meshy MCP, the way Tiga Tradisi was made: a faceless block-body reference for each character,
  Meshy image-to-3D (meshy-t2.5 smart topology + meshy-n1, 15 credits), automatic rigid rigging from the part-separated mesh, a LIVE
  face added in Blender (eyes, blinks, brows, ten mouths, lip sync to the real voice), a real voice-over that sets every shot length
  on a half-beat grid, one scene per shot acted on the spoken words, moods from bright daylight (day, morning, golden, overcast) to
  lamp-lit night with a matching grade and look gate, EEVEE rendering in two resumable workers, per-world grading,
  a ducked music mix at -14 LUFS, word-by-word gold captions (plus an English cut), a props workflow (plan with prompts and prices,
  text / image / multi-image routes, stand-ins until the model exists), a Meshy ledger, THE CAST and THE PROPS cards. Built on cinematicanimation (cine_kit, finish, look gate). Use whenever the
  user says robloxanimax, wants a Roblox animation / Roblox story film / "In this town / Di kota ini" film with Meshy characters,
  wants to turn a script and a voice-over into an animated Roblox film, asks to use "the Tiga Tradisi workflow", wants Meshy-made
  characters that talk and blink, or needs the Meshy cast card / asset ledger for a Meshy contest entry. For a moody, wordless
  beat-cut film with painted-face figures use cinematicanimation alone; for game assets into Roblox Studio use robloxmaxxing.
---

# robloxanimax

The Tiga Tradisi pipeline as a skill: **script -> board -> faceless block references -> Meshy MCP -> auto-rig + live face ->
voice-locked timeline -> one scene per shot -> preview -> final -> mix, captions, cast card.** Everything that worked on that film
(23 shots, 78.75 s, four Meshy characters, -14 LUFS, clip scan clean) is here as code; everything that cost a round is in
`references/lessons.md`.

`SKILL` = this folder. `B` = `/Applications/Blender.app/Contents/MacOS/Blender` (5.1). `BP` = Blender's Python
(`/Applications/Blender.app/Contents/Resources/5.1/python/bin/python3.13`, has numpy; system python3 has none). `P` = the project.
Needs cinematicanimation installed (`~/.claude/skills/cinematicanimation`, or `CINE_KIT` = its `blender/` folder).

Read before starting: `references/workflow.md` (stages, commands, gates). Before any Meshy call: `references/meshy.md`.
Before planning or generating props: `references/props.md`. Before acting a shot: `references/acting.md`. Before lighting an exterior or any daylight shot: `references/moods.md`.
Once per project: `references/lessons.md`.

## Ground rules (from the user, every film)
- **Money and time are asked for.** Meshy: balance, model pair, price per asset and total, then wait for a yes. Renders: stills,
  then a preview cut, then the user's OK before the full render.
- **Two Blender processes at most** at any moment (renders, stills, checks and subagents together).
- **The cast is new for every film** and the user's own avatar (`You`) plays him when he is in it; ask who plays whom if unclear.
- **Alive, never static; stable light.** A camera move in every shot, `life()` on every actor, no flicker or flashes.
- **Pick the mood from the story, not the habit.** Dark and lamp-lit is the cinematicanimation default; a sunny kampung, a market or
  a happy beat wants `day`, a goodbye `golden`, waiting or grief `overcast`. One film can change mood per world.
- **Culture is checked, not guessed.** Every claim about a real tradition gets a source or a "not verified" line in NOTE.md.
- **Honest reporting.** Say what was only checked from stills and measurements and never watched or heard.

## Pipeline
| stage | do | gate |
|---|---|---|
| 0. script | `inthistownscript` / `scriptmaxxing`; GATE B brief (cinematicanimation) | B: every line is something you can see |
| 1. project | `python3 -I $SKILL/scripts/new_project.py $P`; `board/shots.json` (id, vo, look, caption, action) | S: a move per shot, no two same neighbours |
| 2. cast design | `project.json -> cast.<name>.ref` + `face`; `$B -b --factory-startup -P $SKILL/blender/block_ref.py -- $P --glb` | C: reads by silhouette, culture-checked, user OK |
| 3. block | stand-ins -> `blender/prep_cast.py`, `assets/props.json` -> `blender/prep_props.py`, `film/act_*.py` (a `mood()` per exterior), stills | L: `scripts/grade.py` + `scripts/mood_gate.py --look <mood>` on stills |
| 4. Meshy | cast: `references/meshy.md` (image-to-3D per character); props: `references/props.md` (`scripts/props_plan.py` -> price -> yes -> routes); `scripts/ledger.py`; re-run both preps | M: studio render vs reference / real photo |
| 5. voice | takes in `audio/vo_src/`, `scripts/phrases.py`, `$BP -I $SKILL/scripts/voice.py $P` -> `audio/timeline.json` | V: lengths, licence |
| 6. acting | act on `word()`, `talk()`, `life(n)`; `render.py --stills .1,.5,.9`; `blender/clip_check.py` | X: CLIP clean on every shot |
| 7. preview | `PREVIEW=1 bash $SKILL/scripts/render.sh $P`, `$BP -I $SKILL/scripts/mix.py $P`, `bash $SKILL/scripts/assemble.sh $P` | the user's OK |
| 8. final | `bash $SKILL/scripts/render.sh $P` (background), mix, assemble | F: frames, -14 LUFS, gate L/E, read-back |
| 9. extras | `blender/studio.py`, `scripts/cast_card.py` (THE CAST), `scripts/props_card.py` (THE PROPS), `scripts/pairs.py` (In Meshy / In your work), cover, 16:9 | - |

## A shot
```python
# P/film/act_toraja.py  (frames are LOCAL to the shot: 1..n, n from the timeline)
from anima import *

def s13(n):
    """Kek, bangun. Makan dulu. The child kneels by the coffin with the plate."""
    sky('#05070A', '#05070A', amb_s=.2); lamp((-2.9, 3.4, 7.4), 1600, n)
    light('kid_key', 'SPOT', (-3, -3.5, 6.8), 2300, 2700, target=(.5, -1, 2.6), spot=62, shadow=True)
    plate = asset('plate', (0, -1.2, .1), 0, ('x', 1.9))                 # a Meshy prop from assets/props.blend
    k = Toy('cucu', (.2, -1.5, 0), 20, .74, 'hope')                       # a Meshy character from cast/cucu.blend
    f = word('13', 'bangun'); k.hit(f, torso=(16, 0, 0), head=(10, 4, 0)).face(f, 'call').look(f-3, 0, .2)
    talk(k, '13', 1); k.face(f+18, 'hope'); k.life(n, .8)
    Cam((1, (.2, -6.2, 3.4), (0, -1, 2.6), 35, 4, (.2, -1.6, 3.0)), (n, (.1, -5.4, 3.3), (0, -1, 2.6), 40, 4, (.2, -1.6, 3.0)), hand=.12)
```
`templates/act_01.py` is a complete, tested two-shot scene (the README demo).

## anima in one table (`blender/anima.py`, on top of cine_kit `K`)
| need | call |
|---|---|
| a Meshy character | `Toy(name, at, yaw, size, face)`: `.pose(f, arm_l=(fwd, out, twist), head=(nod, turn, tilt), torso, leg_l, lower, tip, at, yaw)`, `.hit(f, dur, ...)`, `.face(f, expr)`, `.look(f, x, z)`, `.blink(f)`, `.talk(words, rest, off)`, `.walk(f0, f1, a, b)`, `.sit(f)`, `.life(n)`, `.head`, `.waist`, `.palm['l']` |
| the user's avatar | `You(at, yaw, pose, size)` (cinematicanimation `K.Avatar` with its lip-sync face rig) |
| expressions | `EX`: neutral smile hope soft grin happy wide ask sad stern worry strain call relief sleep |
| timeline | `N(id)`, `line(id, k)`, `word(id, 'text')` (local frame a word starts), `talk(actor, id, k)` |
| keys | `key`, `mv`, `rot` (ob, (frame, value), ...), `show(ob, f0, f1)` |
| mood | `mood('day' / 'morning' / 'golden' / 'overcast' / 'dusk' / 'night' / 'dawn', az=35)`: sky, sky light, sun, fill, AgX view and exposure in one call; `clouds(n, f1)`, `sway(ob, f1)` keep a bright frame alive |
| world | `sky(hor, top, amb, amb_s)`, `ground(tint, wet, texture)`, `lamp`, `bulb`, `light(..., shadow=True)`, `motes`, `steam`, `stars`, `mesh`, `beam`, all of `K` (rooms, wood, cloth, haze, neon) |
| props | `asset(name, loc, yaw, size)` from `assets/props.blend`; `dims(name, size)` |
| camera | `Cam((f, loc, target, lens, stop, focus), ..., hand=)`, `.shake(f)`, `wipe(cam, [(f, x), ...])` |

## Files
| file | does |
|---|---|
| `blender/block_ref.py` | faceless front/side/back references on the cast body from `cast.<name>.ref`; `--glb` free stand-ins |
| `blender/prep_cast.py` | Meshy smart-topology GLB -> rigid parts on joints + face probes -> `cast/<name>.blend` (identical output to Tiga's own) |
| `blender/prep_props.py` | `assets/props.json` -> `assets/props.blend` (bottom-centre origin, yaw, cut, metal, size in studs, stand-ins for missing models, .blend objects, kit rows skipped) |
| `blender/anima.py` | the runtime above |
| `blender/render.py` | one scene per shot, lock files, `--stills`, `--preview`, resumable |
| `blender/clip_check.py` | actor vs actor and actor vs solid prop intersections on five frames a shot |
| `blender/studio.py` | each GLB untouched in a dark studio, textured + gold wireframe + face count (`WIDE=1` for 16:9 plates) |
| `scripts/new_project.py` | the project tree and templates |
| `scripts/phrases.py` | real pauses in a take -> draft `phrases.txt` |
| `scripts/voice.py` | takes + board -> `audio/timeline.json` (shots on a half-beat grid, lines, words in frames) + `vo.wav` |
| `scripts/mix.py` | voice + ducked music + holes with room tone + cued effects -> `mix.wav`, `mix_no_vo.wav`, -14 LUFS |
| `scripts/captions.py` | `subs.ass` (gold spoken word), `labels.ass`, `subs_en.ass` |
| `scripts/render.sh` | two workers balanced by frame count, then sweeps; `PREVIEW=1` |
| `scripts/grade.py` | the grade per look: day, morning, golden, overcast here; amber, noir, cold, sick, clean via cinematicanimation `finish.py` |
| `scripts/mood_gate.py` | GATE L for every look (daylight starting bands here, dark looks via cinematicanimation `look_gate.py`) |
| `scripts/assemble.sh` | grade per look run (`grade.py`), black tail, four exports; `captions` = re-burn only |
| `scripts/props_plan.py` | props still to make: route (text, draft, image, multi, reuse, kit), full prompt, MCP calls, credits, total: show it and get a yes |
| `scripts/props_card.py` | THE PROPS pages: ten props a page, textured / wireframe split by a gold diagonal, source and face count |
| `scripts/pairs.py` | In Meshy / In your work pairs at 1920x1080 (contest screenshots, before/after carousels) |
| `scripts/ledger.py` | Meshy tasks, credits, files, used or not -> `assets/ASSETS.md` |
| `scripts/cast_card.py` | THE CAST pages, 1920x1080 (run with `uv run --offline --no-project --with pillow python -I -B`) |

## Project layout
```
P/project.json          name, aspect, width, fps, bpm, engine, cast{scale, legs, face, ref}, voice{takes}, mix{music, sfx}, card
P/board/shots.json      the shots, in order
P/ref/                  <name>_front/side/back.png (the Meshy inputs)
P/assets/raw/           Meshy GLBs (or stand-ins);  props.json -> props.blend;  meshy.json -> ASSETS.md
P/cast/<name>.blend     rigged cast
P/audio/vo_src/         untouched takes + phrases.txt (+ word_starts.json);  timeline.json, vo.wav, mix.wav
P/film/act_*.py         def s<ID>(n)
P/out/                  stills/, frames/, work/, reel.mp4, reel_en.mp4, reel_labels_only.mp4, reel_no_voice.mp4, gallery/
P/NOTE.md               versions, decisions, checks, open questions
```

## Fits with the user's other skills
- Words: `inthistownscript`, `scriptmaxxing`. Hooks: `reel-hook`.
- Look, lamps, materials, grade, gates, painted-face cast (Sigajang's Bugis men), the user's avatar: `cinematicanimation`.
- Music and effects: `~/Ngonten/Maxxing/audio-lib` (CC0). Game-ready versions of the same assets: `robloxmaxxing`.
- The reference project is `~/Ngonten/Maxxing/Roblox/tiga-tradisi` (NOTE.md, film/, tools/): read a shot there when a beat is
  hard; most kinds of shot this skill makes have a worked example in it.
