# Lessons that cost a round (Tiga Tradisi, Sigajang, Negara Angin; Nov 2026)

## Cast
- **Faceless input, live face.** A painted Meshy face cannot blink or talk and shows through decals. The block reference has no
  face; `anima.Face` puts eyes, lids, brows, a nose and ten mouths on the clean skin. In Tiga this is what made the cast act.
- **Smart topology is what makes auto-rigging possible.** meshy-t2.5 keeps blocks as separate islands; prep_cast sorts them.
  A fused mesh (meshy-7.1, Meshy Agent exports) goes through cinematicanimation `rig_block.py` + `neck_blend.py` instead, and its
  face is painted (expression atlas, no live face).
- **The block body's numbers are the contract.** 5.2 studs, hip 2.02, head from 3.86, arms out past x 1.2, shoulders 1.48/3.68.
  Change block_ref and prep_cast together or not at all.
- **Sarong / skirt = `legs: false`.** The lower body swings as one block; feet are separate. Cutting a sarong into two legs tears it.
- **Chin seam on fused meshes.** A rig cut through the chin left thousands of folded faces and a trench round the face plate
  (Tiga v3 fixed raka and daeng with `tools/fix_neck.py`: strip removed, rims welded, chin on the head bone, a gradient in the collar).
  Smart-topology cast does not have it: the head is its own island.
- **Profile hides a block face.** Cheat heads 25-35 degrees toward the lens.

## Meshy
- Image models invent: claw hands, thin arms, necks, a turned pose, "Torajan" motifs that are not. Fix the look with
  image-to-image (3 credits), then rebuild it on the block body; never send the concept itself to 3D.
- Culture-specific buildings came back wrong twice in one film (tongkonan without the saddle roof, candi bentar with a lintel).
  Build those in Blender when the Meshy result is wrong; say so in the ledger.
- A failed create call may have charged: check `meshy_list_tasks` before trying again.
- Keep every task id in the ledger the same day. Weeks later a contest asked which assets were Meshy, with screenshots.

## Voice and timing
- The voice cuts the film. Shot length = lead + lines + tail, rounded UP to a half beat.
- Whisper word times are up to 0.3 s off at pauses. Phrases come from the waveform; whisper (forced alignment, +0.11 s lag) only for
  word onsets inside phrases (`word_starts.json`), checked on a spectrogram.
- No speed or pitch change on a real take. Level line by line (they arrive 10+ dB apart); denoise only a noisy take, with its own
  room tone as the print.
- A second speaker recorded somewhere else (Tiga's child, -31 LUFS with room noise): +14.5 dB, denoised, then levelled.

## Picture
- **Never a static frame.** Camera move in every shot, life() on every actor, something in the air (motes, steam, a lamp sway).
- **Stable light.** No flicker, no police flashes, no lightning. Under EEVEE keep 1-3 shadow lights per shot (`light(..., shadow=True)`);
  many shadow lights overflow the pool and flicker frame to frame.
- **Big textures swap the GPU.** `anima.finish()` scales images to what the frame shows (1024, 2048 for faces).
- **One scene per shot.** Load only that shot's set: every loaded thing is evaluated every frame.
- **A wipe hides a cut**: something dark crossing the lens ends one shot, the next starts behind it.
- **Look at what touches what.** clip_check found a plate inside an avatar's legs that no still showed.

## Sound
- One music track from the first frame to the last, ducked 7 dB under speech, 9-11 dB below the voice overall; the designed silence
  is a dip with room tone, not a cut to digital zero. Effects on every visible hit.
- The user rejected a separately designed score + foley for Tiga ("revert it, don't use it"): keep the film's own mix, and do not
  re-propose a replacement sound design unless asked.
- Know the licence of every track before posting (Tiga: Roblox.mp3's source was unknown; NOTE.md said so).

## Process
- **Stills before frames, preview before final, the user's OK before anything long.** A full render is hours.
- **Two Blender processes at most**, counting background renders, stills and subagents.
- **NOTE.md as you go**: versions (v1 bed -> v2 coffin -> v3 neck -> v4 real voice), what each changed, where the old one is kept,
  what is checked, what is not, what waits on the user. Keep each superseded version in `out/vN_*/` until the user lets it go.
- Say what was never watched in motion or listened to. "Reviewed from stills and measurements only" is a valid, honest state.
