# Meshy through MCP: the cast and the props

Everything here goes through the Meshy MCP server (`mcp__meshy__*`). Tools are deferred: load the ones you need in one
`ToolSearch` call, e.g. `select:mcp__meshy__meshy_check_balance,mcp__meshy__meshy_image_to_3d,mcp__meshy__meshy_text_to_image,mcp__meshy__meshy_image_to_image,mcp__meshy__meshy_get_task_status,mcp__meshy__meshy_download_model,mcp__meshy__meshy_list_tasks,mcp__meshy__meshy_text_to_3d,mcp__meshy__meshy_text_to_3d_refine,mcp__meshy__meshy_multi_image_to_3d`.

## Two rules that come before every call
1. **Money first.** Before any call that costs credits: `meshy_check_balance` (free), then tell the user the model pair, the
   price per asset and the total, and wait for a yes. One yes covers the batch you named, not the next one.
2. **Never pay twice.** A create call that times out or errors may still have been created and charged. Check
   `meshy_list_tasks` (that task type) before calling create again. A `meshy_get_task_status` TIMEOUT means "still running":
   call it again with the same id (Meshy allows up to 60 minutes).
Write each task into the ledger the moment it SUCCEEDS: `python3 -I scripts/ledger.py <project> add <name> <task_id> image-to-3d 15 --ai meshy-t2.5 --tex meshy-n1 --file assets/raw/<name>.glb`.

## Characters: block reference -> image-to-3D (15 credits each)
The recipe that made Tiga Tradisi's four characters (64 -> 4 credits; 15,327 and 15,393 faces):

| step | tool | settings | credits |
|---|---|---|---|
| 0. look (optional) | `meshy_text_to_image` | `ai_model: "nano-banana"`, `pose_mode: "a-pose"`, prompt below | 3 |
| 0b. fix the look | `meshy_image_to_image` | `input_task_id` of step 0, prompt = the fixes | 3 |
| 1. the input | `blender/block_ref.py` | the outfit from the approved look, on the block body, **no face** | 0 |
| 2. 3D | `meshy_image_to_3d` | `file_path: <project>/ref/<name>_front.png`, `model_type: "smart-topology"`, `ai_model: "meshy-t2.5"`, `target_polycount: 15000`, `texture_model: "meshy-n1"`, `pose_mode: "a-pose"`, `target_formats: ["glb"]` | 15 |
| 3. wait | `meshy_get_task_status` | `wait: true` (repeat on TIMEOUT) | 0 |
| 4. save | `meshy_download_model` | `format: "glb"`, `save_to: <project>/assets/raw/<name>.glb` | 0 |
| 5. rig | `blender/prep_cast.py` | rigid parts + pivots + face probes -> `cast/<name>.blend` | 0 |

Why these settings:
- **meshy-t2.5 smart topology** returns a clean, part-separated mesh: each block is its own island. `prep_cast.py` sorts the
  islands into head / body / arms / legs by position, so the rig is automatic. A meshy-7.1 mesh is one fused skin and needs the
  slower slice-and-weight route (`cinematicanimation/scripts/rig_block.py`).
- **meshy-n1 texture** paints from the input image itself (front view), so the outfit colours are exactly the reference's.
  It takes no `texture_prompt`, no PBR, 2K only: fine at toy scale.
- **Do not use `meshy_rig`.** Meshy's humanoid skeleton bends a block figure like a person. The film wants rigid toy joints.
- **The faceless front, not the concept.** Meshy builds what it sees: image models draw claw hands (another toy brand's
  minifigure), thin tapered arms with wrists, a neck, a three-quarter turn. The block body has none of that, and no face, because the
  film puts a live face on the clean skin (`anima.Face`): a painted face would show under it and could never blink or talk.
- **Concept pixels can ride along**: `cast.<name>.ref.decals` lays a crop of the approved concept (a woven cloth, a batik) on
  the front of a part, and meshy-n1 carries it into the texture.

Concept prompt (step 0), start every character with:
> Original blocky toy figure, cube head with softly rounded edges, rectangular torso, arms and legs as separate rigid blocks,
> solid square block hands without fingers, head sitting directly on the shoulders with no neck, matte plastic skin, real woven
> fabric detail on the clothing, full body, dead-straight front view, A-pose, plain grey background, no text, no logo.

then the person: age, region, hair, clothing with real names (kebaya, kamen, poleng, songkok, sarong, udeng). The face does not
matter: it is removed in step 1. **Have someone from that culture look at the concept before the 15-credit step**; Tiga Tradisi's
round-1 motifs were the image model's invention, not Torajan.

## Props: three routes, pick by how exact it must be
The full props workflow (list, stand-ins, plan and price, routes, pack, check, cards) is `references/props.md`; this is the summary.
| need | route | credits |
|---|---|---|
| an everyday object (plate, wardrobe, ambulance, stall) | `meshy_text_to_3d` preview (`meshy-6`, 20) then `meshy_text_to_3d_refine` (10); or `model_type: "smart-topology"`, `ai_model: "meshy-t2"` preview (5) + refine | 30 / 15 |
| it must look like ONE specific thing (a badik, a tongkonan) | `meshy_text_to_image` (approve it) -> `meshy_image_to_3d` with `input_task_id` | 3 + 20-30 |
| copy a model you already have (a kit prop, an older asset) | render 2-4 orthographic views, `meshy_multi_image_to_3d` (`meshy-7.1` + `meshy-7`) | 30 |

Prop prompt, start every one with:
> Realistic miniature film prop, worn natural materials, clean silhouette, single object, no people, no text, no logo, no base.

Then `assets/props.json` gets a row (glb, yaw so the front faces -Y, cut, metal) and `blender/prep_props.py` packs it.
Until a model exists its row makes a stand-in box of the right size, so shots can be blocked.

**Culture-specific architecture often comes back wrong.** In Tiga Tradisi the tongkonan came back a gabled barn without the
saddle roof, and the candi bentar came back with a lintel across the opening (a split gate has none). Both were rebuilt in Blender
by hand (`tongkonan`, `candi` in the film's world.py). Look at every Meshy prop next to a real photo before it enters a shot;
"text-to-image designs drift" (a pinisi came out a square-rigged galleon in Sigajang).

## What to say about Meshy afterwards
The ledger (`assets/ASSETS.md`) holds every task id, model, credit and whether it is in the cut. Contest entries (Meshy Z-Axis
Awards) asked for "which assets are Meshy" with screenshots: `blender/studio.py` renders each GLB untouched (textured + wireframe),
`scripts/cast_card.py` makes THE CAST page. Name only the generator that made what is on screen, and say what Blender added:
"Meshy gave body, clothes and texture. Faces, joints, acting and light were added in Blender."
