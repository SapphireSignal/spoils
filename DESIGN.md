# SPOILS — Design & Workflow Doc

> Handoff brief. A fresh Claude session should be able to read this and start building
> with zero questions about setup, tooling, or intent.
> Project dir: `D:\Games\Spoils`. The name **SPOILS** was chosen and availability-vetted
> 2026-07-31 (only collision: an out-of-print 2016 card game) — it's the loot you carry
> out, and what greed does to you.

## 1. What this is

A **2D isometric extraction shooter with pixel art**, built in **Godot 4.7**, for Windows.
Solo-with-AI first (a real, shippable single-player game), designed so a true PvPvE
multiplayer version remains possible later without a rewrite.

Inspirations and what to take from each:

- **ARC Raiders** — the *world and threat*: a hostile **machine faction** as the headline
  PvE enemy (patrolling mechs/drones that hunt noise and light), topside ruins, the feeling
  of scavenging under something bigger than you.
- **Escape from Tarkov** — the *stakes and meta*: raid-based loop, **you lose what you
  carry when you die**, persistent stash between raids, gear choice = risk choice,
  extraction points, raid timer, tension over action.
- **Destiny** — the *feel and reward*: punchy, juicy gunplay (screen shake, muzzle flash,
  meaty sounds, satisfying reloads) and **color-coded loot rarity** with dopamine on pickup.
  Guns should feel great even when the fantasy is grim.

One-line pitch: *Tarkov's raid loop + ARC Raiders' machine-haunted world + Destiny's
gun-feel, at 32 pixels tall.*

## 2. The workflow contract (important)

**Claude does everything. The user does not want to perform any tasks.**

- Claude writes all code, generates all art, synthesizes all audio, authors all maps,
  tests its own work, and proves it with screenshots.
- The user's entire role: read updates, look at screenshots, **playtest builds, and react**.
  Their reactions steer design. Nothing in the plan may depend on the user editing a file,
  drawing a sprite, recording a sound, or installing anything.
- Never ask the user to install tools. The machine is already fully equipped (section 6).
  Previous sessions installed Aseprite, Tiled, and Audacity and then **deliberately removed
  all three** as unnecessary — do not suggest reinstalling them.
- **Conversation etiquette (user has explicitly corrected this):**
  - When the user interrupts with a question, answer it and **stop working**. Resume only on
    an explicit "go" / "keep going".
  - Give ideas the same weight the user gives them — don't inflate side details into
    headline plan items.
  - Keep summaries short and plain; the user is not deeply technical about tooling.
- Work in milestones. Every milestone ends with something runnable plus a screenshot sent
  to the user. Keep a "Play" shortcut (double-click .bat) working at all times.

## 3. Game design

### Core loop
1. **Stash screen** — pick loadout from persistent stash (gun, armor, meds, backpack size).
2. **Deploy** into the map at a spawn point. Raid timer starts.
3. **Loot** containers/corpses, **fight or avoid** AI, manage noise and light.
4. **Extract** at one of several extraction points (some conditional) before the timer ends
   — or die and **lose everything you carried**.
5. Stash grows, buy/sell at a simple trader, deploy again. Meta progression = stash value +
   trader unlocks. Persist to a local config file.

### v1 scope (defaults — adjustable by the user, not by Claude)
- **1 map**: "transit" — a 320×320 ruined industrial/urban district with interiors,
  chokepoints, 3–4 extraction points. A fresh layout is generated per deploy from a seed
  (pinnable for testing); the road grid / forest / building DNA stays recognizable.
- **6–10 guns** across classes (pistol / SMG / shotgun / rifle / DMR) with rarity tiers
  (white→green→blue→purple→gold, Destiny-style colors within the palette).
- **AI factions:**
  - **Machines** (ARC-style): patrol routes, react to sound/light, telegraphed attacks,
    tanky, drop rare components. Not farmable loot piñatas — a hazard to route around.
  - **Scavs** (human raiders): squads with basic tactics (flank, suppress, retreat), varied
    gear, fight machines too. Three-way fights are a feature.
  - **"Fake players"** (elite scav variant): human-like callsigns, randomized player-tier
    loadouts, and player-like behavior — they loot containers, pick their fights, and
    **path to an extraction zone to leave the raid with their haul** (if one extracts with
    loot you wanted, it's gone). Design details are at Claude's discretion — user greenlit
    this and specifically likes the extract-seeking behavior.
- **Systems:** hitscan-with-tracer gunplay, armor/HP, simple healing, loot tables, containers,
  raid timer, extraction, stash persistence, trader, death = loss.
- **Explicitly out of v1:** multiplayer/netcode, attachments/modding, quests, hideout
  upgrades, limb damage, insurance.

### World rules (shipped in v0.6.3 — keep true)
- The map is walkable to its true diamond edge; there is no visible void, ever.
- The last stretch before the edge is **sniper country**: a centered warning
  ("turn back or you will get sniped"), a 3 s grace period, then off-screen rounds.
  Three hits kill; death currently respawns at the spawn crossroads (M4 turns this
  into real raid loss).
- Building doors are **closed and interactive** (F opens/closes, swing animation,
  collision while shut). Entrances — inside pocket and outside approach — always
  spawn clear of props.
- Nights are dark for real; the flashlight (E) and the surviving minority of
  flickering street lamps are the light sources until M5 lighting.
- Weather is world-anchored: raindrops fall to real ground points and splash where
  they land, in the puddles' blue.

### Multiplayer future (build-for, don't build-yet)
The long-term goal is real PvPvE. **Architecture rule from day one:** gameplay state changes
flow through clear authoritative functions (spawn, damage, loot roll, pickup, extract) rather
than being scattered through UI/input code — so a server can own them later. No netcode now.

## 4. Art direction

- **Style:** pixel art, **Apollo palette (46 colors)** — file at `art/palettes/apollo.gpl`
  (Endesga-32 also saved as fallback; palettes must never be mixed in one asset).
- **Scale:** ~32px tall characters, **64×32 isometric floor tiles**, props sized to match.
- **Mood:** grim, overcast, readable. Dithering for grime/texture. Godot 2D dynamic lighting
  does the heavy lifting: dark interiors, muzzle flashes as brief PointLight2D pops,
  flashlight cones, machine eye-glow. Rarity colors are the deliberate saturation pops.
- **Pipeline:** ALL art is generated by a Python script (`tools/gen_art.py`, Pillow,
  deterministic seed, palette loaded from the .gpl). Regenerating is always safe.
  No hand-drawn files, no external art. If an asset looks bad, fix the generator.
- **Rendering:** low-res viewport (**640×360**) integer-scaled to window; nearest-neighbor
  filtering everywhere (`rendering/textures/canvas_textures/default_texture_filter=0`);
  Y-sorted isometric TileMapLayer. Do NOT enable `rendering/viewport/hdr_2d` — it crushes
  2D colors; do glow with additive-blend sprites + lights instead.

## 5. Audio direction

- **Fully synthesized in GDScript at runtime** (AudioStreamGenerator or precomputed
  AudioStreamWAV buffers at startup). **No audio files in the repo.**
- Gunshots = shaped noise bursts with per-class character (bass thump for shotgun, crack
  for DMR); impacts, footsteps (surface-aware later), UI ticks, extraction siren.
- Sparse ambient dread over music: low wind/rumble loop, distant machine sounds as a
  *gameplay tell*. No melodies needed for v1.

## 6. Machine & toolchain facts (verified 2026-07-31)

- **OS:** Windows 11. Shell: PowerShell 5.1. Beefy CPU (i9-14900KF, 32 threads).
- **Display: 240 Hz monitor, desktop at 1680x1080 (a stretched/non-native mode).**
  Consequences (learned from user playtest complaints): ALL motion must update at
  render rate (`_process`), never at the 60 Hz physics tick — 60 Hz stepping reads
  as "20 fps" at 240 Hz. Camera must sit on whole pixels every frame. Game runs
  fullscreen (integer 2x letterboxed at this desktop res; native 1080p would be
  a perfect 3x).
- **Engine:** `D:\Godot\Godot_v4.7.1-stable_win64_console.exe` (console build — use for all
  CLI/headless work; there is also a windowed exe without `_console` for Play shortcuts).
- **Python 3.14 + Pillow 12.3** on PATH — the art pipeline.
- **Git** installed. No repo in `D:\Games\Spoils` yet — `git init` on first build.
  Commit at milestones.
- **Godot 4.7.1 Windows export templates already installed** (`%APPDATA%\Godot\export_templates\4.7.1.stable\`)
  — shipping a standalone .exe needs no downloads.
- **Deliberately absent:** Aseprite, Tiled, Audacity (removed at user request — do not reinstall).
- Current project state: **v0.6.2** — Milestone 1 plus many user-feedback and
  content passes (160×160 living district, weather/day-night, menus, keybinds,
  crouch; see CHANGELOG.md and **CLAUDE.md — the session handoff file with all
  operational conventions**). Next: Milestone 2 (gunplay) as v0.7.0.
  GitHub repo (private): https://github.com/SapphireSignal/spoils. Established
  conventions that must not regress (fuller list in CLAUDE.md):
  - Camera locked to whole pixels; ALL motion updates in `_process` (see Display note).
  - UI text uses the generated bitmap font (`tools/gen_font.py`) via `UITheme` —
    never Godot's default vector font (blurry at 1x).
  - Prop sprites, origins, collision shapes and variant families come from
    `art/gen/manifest.json`; the game hardcodes none of it. Props vary per
    instance (parameterized generators, incl. fallen/toppled poses).
  - Buildings: THIN edge-wall segments (not full-tile blocks) + corner/door
    posts, varied windows, tar roofs. RoofReveal fades the roof to zero AND
    the camera-facing walls to 30% while the player is inside.
  - Font: lowercase-only proportional bitmap font; uppercase codepoints map to
    lowercase glyphs (user wants no capitals anywhere). If the .fnt ever fails
    to import, delete its .import + .godot/imported cache and reimport —
    Godot caches import failures for unchanged files (cost us a whole "blurry
    text" investigation).
  - Boot scene is the main menu (`scenes/menu.tscn`): four generated backdrop
    scenes rotate with crossfades (hoard / neon scrapyard / safehouse /
    overlook), each with an animated layer. Harness: `--scene=menu` stays on
    the menu, `--backdrop=N` picks a scene, `--at=X,Y` teleports the player.

## 7. Self-verification requirements (non-negotiable)

Claude must prove its own work without the user:

- **Smoke harness:** `godot_console --headless --path . -- --smoke` runs scripted checks
  (scene builds, player spawns/moves, a raid can start/extract) and must end by printing
  `SMOKE PASS`. Run it before claiming anything works.
- **Screenshot harness:** `godot_console --path . -- --shot=<name>` boots the game,
  captures to `shots/<name>.png`, quits. Claude reads the PNG itself, judges it visually,
  iterates, and sends the user the good one.
- After adding any new `class_name` script or new art files, run
  `godot_console --headless --path . --import` (skipping this causes phantom
  "Identifier not declared" parse errors).
- Smoke runs pollute the persisted stash file under `%APPDATA%\Godot\app_userdata\` —
  use a separate test profile or clean up after test batches.
- GDScript 4.7 gotcha: `var x := dict.key` fails to infer (Variant) — always type-annotate
  when reading from Dictionary/Array.

## 8. First milestones (each ends with a screenshot to the user)

1. **Walkable world:** project scaffold, generated iso tileset + 8-dir character,
   Y-sorted map with props, camera, WASD movement, Play.bat. *(DONE 2026-07-31,
   plus a feedback pass: smooth ground, brick buildings, distinct props,
   6-frame walk, pixel-snapped camera.)*
2. **Gunplay:** aim at mouse, shoot with tracers/flash/shake/sound, destructible props.
3. **Enemies:** scav AI (patrol→chase→shoot), health/death, loot drops.
4. **The loop:** containers, inventory, extraction point, raid timer, death = loss, stash
   persistence. First real "raid".
5. **Machines, fake-player bots, lighting pass, trader** — then iterate on user playtests.
