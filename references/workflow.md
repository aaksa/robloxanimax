# The workflow, stage by stage

The pipeline Tiga Tradisi ("In This Town: Nggak Ada yang Sendiri", Nov 2026: 23 shots, 78.75 s, 9:16, EEVEE, four Meshy
characters, Meshy props, a real ElevenLabs voice) went through, in the order that wasted the least. Every stage ends on a thing
the user can look at, and nothing long starts without their OK.

`SKILL` = this folder. `B` = `/Applications/Blender.app/Contents/MacOS/Blender`. `BP` = Blender's Python
(`/Applications/Blender.app/Contents/Resources/5.1/python/bin/python3.13`, has numpy). `P` = the project folder.

| # | stage | command / tool | the user sees | gate |
|---|---|---|---|---|
| 0 | script + brief | `inthistownscript` or `scriptmaxxing`, then GATE B (cinematicanimation) | the script, the brief | B |
| 1 | project + board | `python3 -I $SKILL/scripts/new_project.py $P`, write `board/shots.json` | the shot table | S |
| 2 | cast design | `cast.<name>.ref` in project.json -> `$B -b --factory-startup -P $SKILL/blender/block_ref.py -- $P --glb` | `ref/*_front.png` lineup | C |
| 3 | block the film | stand-in GLBs -> `prep_cast.py`, props.json stand-ins -> `prep_props.py`, act files, stills | contact sheet of stills | L |
| 4 | Meshy | cast: `references/meshy.md`; props: `references/props.md` (`props_plan.py`, price, OK, routes); ledger; `prep_cast.py` / `prep_props.py` | studio renders of each model | M |
| 5 | voice | takes in `audio/vo_src/`, `scripts/phrases.py`, `$BP -I $SKILL/scripts/voice.py $P` | shot lengths in beats | V |
| 6 | performance | act files on the words; `render.py --stills .1,.5,.9`; `clip_check.py` | stills + clip report | L, X |
| 7 | preview | `PREVIEW=1 bash $SKILL/scripts/render.sh $P` + mix + `assemble.sh` | a 270x480 cut with sound | the user's OK |
| 8 | final | `bash $SKILL/scripts/render.sh $P` (background), `mix.py`, `assemble.sh` | `out/reel*.mp4` | F |
| 9 | extras | `studio.py`, `cast_card.py`, `props_card.py`, `pairs.py`, cover, 16:9 | THE CAST and THE PROPS pages, pairs | - |

## 0. Script and brief
- Indonesian story reels: `inthistownscript` (the "Di kota ini..." format) or `scriptmaxxing` (Aksa's voice). Write the words first;
  the voice decides every shot length later.
- GATE B (cinematicanimation SKILL.md): logline with a want and a price, shape (a chain: every shot ends on the object that starts
  the next), the stake object (Tiga: the plate, planted in 01 and 07, paid off in 20), a palette per world (Bugis ember orange,
  deep green, gold; Bali starlight blue, black, one white beam; Toraja lamp amber, maroon, one blue window) and the mood of each
  world (`references/moods.md`: day, morning, golden, overcast, dusk, night, lamp-lit), sound (where the
  music drops, the 3-8 s where it stops), the ending image, exclusions (no visible decay, no villain made of a real role, no logos).
- Culture: write down every claim the film makes about a real tradition and where it comes from. Unverified claims go in NOTE.md
  as "ask a Torajan" (Tiga: the coffin carving) and the user decides.

## 1. Board (GATE S)
`board/shots.json`, one row per shot: id, vo (word for word what is said over it), look, caption, size, move, action, sound.
Rules that held: a real camera move in every shot; no two neighbours with the same size and angle (one deliberate match-cut is
fine); cuts on half beats; an insert (hands, an object) at least every third shot; labels small and yellow, never a headline.
A proxy storyboard (blocks in cine_kit, rendered stills -> panels) is worth it for more than ~10 shots: Tiga's board PDF and
`shots.json` came from it and the cameras survived into the film almost unchanged.

## 2. Cast design (GATE C)
For each character write `cast.<name>` in project.json: `scale`, `legs` (false for sarong / skirt / kain), `ref` (skin, hair style
and colour, top colour and sleeve length, lower kind and colour, sash, headwear, extras, decals), `face` (eye / mouth heights,
eye size, brow colour, `old`). `block_ref.py` renders front / side / back. Show the lineup. **GATE C:** every character reads at
thumbnail size by silhouette and one colour; nobody reuses a character from another reel (ask who plays the user); the outfit is
right for the place and the moment (Tiga: a pregnant Balinese woman at home on Nyepi wears a plain blouse and kamen, not a festival
kebaya); someone from that culture has seen it, or NOTE.md says they have not.
`--glb` writes free stand-ins with the same proportions: stage 3 runs on them.

## 3. Block the film on stand-ins (GATE L)
`prep_cast.py`, `prep_props.py` (missing GLBs become boxes of the right size), one `film/act_*.py` per world with `s<ID>(n)`.
Until the voice exists give each shot `"beats": N` in the board and run `voice.py` (it makes a timeline with no lines).
`$B -b --factory-startup -P $SKILL/blender/render.py -- $P --stills .1,.5,.9` -> `out/stills/`, about 2 s a still at full size.
Grade a few with `scripts/grade.py --look <its look>` and run `scripts/mood_gate.py --look <its look>` on them. **GATE L** on every
shot against its mood's band (low-key: median 0.10-0.26, a real highlight over 0.85, black floor under 0.05; daylight bands in
`references/moods.md`). Fix light in the scene (sun, sky light, exposure, pale surfaces), never in the grade.

## 4. Meshy (GATE M)
`references/meshy.md`. Ask once for the whole batch with the price (Tiga: 4 characters x 15 = 60 credits). Download to
`assets/raw/<name>.glb` (the stand-in is overwritten: that is the point), ledger, `prep_cast.py`, re-render the same stills: shots
do not change. **GATE M:** each model in `studio.py`'s studio next to its reference: outfit colours right, no claw hands, no extra
neck, no face painted on (if Meshy painted one anyway, the face decals cover it only from the front: regenerate). Props: the
culture-specific ones next to a photo.

## 5. Voice (GATE V)
Takes go in `audio/vo_src/` untouched. `phrases.txt` = one row per phrase between REAL pauses (`phrases.py` lists them; commas are
often pauses). `voice.py` cuts each line out of its take (soft onsets kept, tails out to -52 dB), levels them line by line, lays
them shot by shot and rounds every shot up to a half beat. It refuses a phrase that crosses a shot and words that do not match the
board. **GATE V:** total length (Tiga 78.75 s), no shot under ~1.5 s unless it is a designed hit, the music's BPM in project.json.
A new take = new phrases.txt, voice.py, and every frame renders again (shot lengths moved): move `out/frames` aside first.
Licences: macOS System Voices are personal-use only (guide voice, never posted); ElevenLabs paid plan = commercial.

## 6. Performance (GATE X)
`references/acting.md`. Act on the words (`word()`), lip-sync with `talk()`, `life(n)` last. Stills at .1/.5/.9 of each shot,
contact sheet, describe each still in one sentence: if the sentence is not the board's action, the shot is not done.
`$B -b --factory-startup -P $SKILL/blender/clip_check.py -- $P` -> **GATE X:** `CLIP <id> clean` on every shot.

## 7. Preview, then ask
`PREVIEW=1 bash $SKILL/scripts/render.sh $P` (a quarter size, 16 samples: Tiga-size films in well under an hour), `$BP -I
$SKILL/scripts/mix.py $P`, `bash $SKILL/scripts/assemble.sh $P`. Send the user `out/reel.mp4` and the contact sheet, and wait.
A full render costs hours; a fix found here costs minutes.

## 8. Final (GATE F)
Move preview frames aside (`out/frames` -> `out/frames_preview`). `bash $SKILL/scripts/render.sh $P` in the background (two Blender
workers, never more; Tiga: ~1.5-3 s a frame each). Re-render a few shots: delete their frames, `render.sh $P 07,13`.
`mix.py`, `assemble.sh` (graded per look, captions burned, four exports). **GATE F:**
- frame count = timeline total; every export decodes; -14 LUFS (+-0.5), true peak under -1 dBFS;
- GATE L per world with `mood_gate.py` (WARN allowed on a designed transition), GATE E with `shotlist.py --bpm`;
- a whisper read-back of the mix returns every line; the gold word sits on the spoken word (spot-check 5);
- clip scan clean; say plainly what was only checked from stills and never watched in motion or listened to.

## 9. Extras
- `studio.py` (square textured + wireframe renders) + `cast_card.py` -> THE CAST pages (concept > Meshy > wireframe > in the film),
  + `props_card.py` -> THE PROPS pages (textured / wireframe on a gold diagonal).
- `WIDE=1 ... studio.py` -> 1920x1080 "In Meshy" plates, `pairs.py` -> "In Meshy / In your work" pairs.
- Covers: stage a key-art scene in Blender from the film's own sets and cast (the user rejected composited frame collages).
- 16:9: a `wide/` folder that imports `film/` unchanged and swaps frame size, cameras and captions in memory (Tiga's wide/build.py).
