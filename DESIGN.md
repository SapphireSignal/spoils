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

- **ARC Raiders** — the *world*: a dead, overrun topside, the feeling of scavenging
  a place that ended without you. (User call 2026-08-01: NO machine faction —
  every enemy in SPOILS is human AI with guns.)
- **Escape from Tarkov** — the *stakes, meta, and loot*: raid-based loop, **you lose
  what you carry when you die**, persistent stash between raids, gear choice = risk
  choice, extraction points, raid timer, tension over action. Loot is Tarkov-style:
  grid inventory, item footprints, containers you search, a character doll with gear
  slots — item VALUE over rarity colors (user call 2026-08-01: no color-coded tiers).
- **Destiny** — the *gun feel only*: punchy, juicy gunplay (screen shake, muzzle
  flash, meaty sounds, satisfying reloads). Guns should feel great even when the
  fantasy is grim.

One-line pitch: *Tarkov's raid loop and loot in a sealed, picked-over district,
with guns that feel like Destiny, at 32 pixels tall.* (Nothing "overran" this
city — it was evacuated, walled in, and left to the people who stayed. Every
threat is human; see LORE.md hard rule 1.)

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
  chokepoints, 3–4 extraction points. The layout is **FIXED** (user call 2026-08-01:
  no procedural rerolls, ever — quests will point at real addresses and players must
  be able to learn the district). The deterministic generator plus the pinned
  `DISTRICT_SEED` in world_builder.gd ARE the map file; changing that seed is a
  deliberate map revision, never a roll. Per-raid variety comes from weather, time
  of day, and (later) loot/AI — never from layout.
- **6–10 guns** across classes (pistol / SMG / shotgun / rifle / DMR), told apart by
  stats, feel, and condition — NOT rarity colors (user call: Tarkov has none).
- **AI factions — all human, all armed** (user call: no machines):
  - **Scavs** (human raiders): squads with basic tactics (flank, suppress, retreat), varied
    gear. Rival squads fight each other too — three-way fights are a feature.
  - **"Fake players"** (elite scav variant): human-like callsigns, randomized player-tier
    loadouts, and player-like behavior — they loot containers, pick their fights, and
    **path to an extraction zone to leave the raid with their haul** (if one extracts with
    loot you wanted, it's gone). Design details are at Claude's discretion — user greenlit
    this and specifically likes the extract-seeking behavior.
- **Systems:** hitscan-with-tracer gunplay, armor/HP, simple healing, Tarkov-style loot
  (grid inventory with item footprints, searchable containers, character doll gear
  slots: helmet/armor/rig/backpack/weapons), loot tables, raid timer, extraction,
  stash persistence, trader, death = loss.
- **Post-1.0, already committed (user call 2026-08-01):** quests (trader tasks), a
  second map. **Explicitly out of v1:** multiplayer/netcode, attachments/modding,
  hideout upgrades, limb damage, insurance.

### World rules (v0.6.3–v0.6.5 — keep true)
- **The barricade ring IS the map edge**: per-stretch ONE dominant jersey
  design repeated (real lines repeat), fences as accents, some askew/flat,
  uneven spacing, wreckage where roads dead-end into it. Beyond the line:
  BARE dead concrete (no woods, no roads) — rubble, snags, and the fallen.
  All forests/groves live inside; biome edges use blend tiles. The world
  visibly continues beyond the ring and there is no visible void, ever.
- **The camera never clamps** — welded to the character everywhere (user call).
  The buffer band past the barricades is deep enough that escalating sniper
  fire (faster + near-perfect with depth) ends any trip before the true tile
  edge could scroll into view. Sparse fallen raiders past the line sell it.
- Crossing the line: centered warning ("turn back or you will get sniped"),
  3 s grace, then off-screen rounds. Three hits kill; death currently respawns
  at the spawn crossroads (M4 turns this into real raid loss).
- Building doors are **closed and interactive** (F opens/closes, swing animation,
  collision while shut, "press f to open/close" prompt at close range).
  Entrances — inside pocket and outside approach — always spawn clear of props.
- Nights are DARK; the flashlight (E) and the surviving minority of flickering
  street lamps are the light sources until M5 lighting.
- Weather is world-anchored and **never jumps**: raindrops fall to real ground
  points and splash where they land in the puddles' blue; storm tinting fades
  over ~45 s.

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
  flashlight cones, lamp pools, tracers and muzzle flashes are the deliberate
  saturation pops (no rarity colors — cut by user call).
- **Pipeline:** ALL art is generated by a Python script (`tools/gen_art.py`, Pillow,
  deterministic seed, palette loaded from the .gpl). Regenerating is always safe.
  No hand-drawn files, no external art. If an asset looks bad, fix the generator.
- **Rendering:** low-res viewport (**640×360**) integer-scaled to window; nearest-neighbor
  filtering everywhere (`rendering/textures/canvas_textures/default_texture_filter=0`);
  Y-sorted isometric TileMapLayer. Do NOT enable `rendering/viewport/hdr_2d` — it crushes
  2D colors; do glow with additive-blend sprites + lights instead.

## 5. Audio direction

- **Hybrid (amended 2026-08-01, user call).** Mechanical one-shots are synthesized in
  GDScript at runtime (UI ticks, door thunks, sniper crack, flashlight click, rain bed,
  car alarm — and gun sounds in M2: shaped noise bursts with per-class character).
  **Organic sounds are licensed recordings** committed under `assets/audio/` with
  attribution tracked in `assets/audio/LICENSES.md`: per-surface footsteps, thunder,
  and the menu music (DavidKBD's "The Last" pack — more tracks available there for
  later milestones). Game-safe licenses only (CC0 / CC-BY / Pixabay-style).
- **SUBTLE always** — every sound mixed quiet; the user is sensitive to loud or
  obnoxious audio. Distant gunfire stays a *gameplay tell*.

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
2. **Gunplay (v0.7):** aim at mouse, shoot with tracers/flash/shake/sound,
   destructible props. **Plus THE STORY FOUNDATION (user request
   2026-08-01):** the lore in `LORE.md` (the cordon, the wardens, magpie,
   traders mara/kettle/verne) and the first-launch ~2 min cinematic
   "the wire" — 2D painted widescreen shots, letterboxed, parallax drifts,
   animated layers, lowercase subtitles; ends by dissolving through dawn
   mist onto the LIVE generated district (built async behind the final
   shots) — film straight into gameplay, no menu on first boot. Skippable;
   shown once (flag in settings); harness always skips.
   **Plus THE TUNNELS (user request 2026-08-01):** an
   underground tunnel system beneath the district. Entrances: a secret
   passage behind the bookshelf in SOME houses (interact to slide it), and
   exactly TWO interactive manholes out on the streets — open the cover,
   interact with the ladder to climb down; a ladder at every entrance leads
   back up the same way (F both directions). Dark, tight corridors — the
   flashlight matters down there.
3. **Enemies (v0.8):** human scav AI (patrol→chase→shoot), health/death, loot drops.
   Readability: flag hostiles with the bright Apollo reds/oranges (a53030 /
   cf573c accents — armband, headlamp, muzzle glow) so they pop against the
   dark streets; keep it SUBTLE per the audio/visual taste rules.
4. **The loop (v0.9):** Tarkov-style loot — grid inventory with item footprints,
   searchable containers, character doll gear slots (helmet/armor/rig/backpack/
   weapons) — raid timer, death = loss, stash persistence. First real "raid".
   **EXTRACTION ships early, in the 0.6.x line** (user request 2026-08-01) —
   three exits, each its own version, all ending on one summary screen:
   - **toll gate** — a warden in a booth on the district edge. Interact (from
     foot or a car) opens a portrait dialogue: an endless "reply" button that
     keeps him talking lore, a "pay the fee to extract" button, and a way back.
     Paying opens the wire; drive out of bounds and a green counter runs down.
   - **night freight** — one distinct, bigger train. "press f to get on",
     a departure clock counts from ten, then it rolls out under the wire.
   - **the lift** — a green-smoked LZ off a dirt track. Get close and it
     counts down on its own; a helicopter comes in, drops a rope, lifts you.
   - **the summary screen** — "successfully extracted", how you got out, time
     survived, xp, kills (with the minute and the bone), player kills, and
     the haul once the stash exists.
5. **The living raid (v1.0):** human-like "fake player" bots, dynamic lighting pass,
   trader — then iterate on user playtests.
6. **Quests (v1.1):** trader tasks (fetch / kill / extract-with), rewards, unlocks.
7. **A second map (v1.2):** the next district off mara's board — see
   LORE.md §3 for full map canon. HARD RULE (user call 2026-08-01): every
   map is structurally NOTHING like transit (no roads/houses/warehouses/
   tunnels reruns) and built for massive scale and depth: the mills = one
   colossal continuous interior (halls/catwalks/furnaces), harbor = water
   as the map (piers/container canyons/ships/rowboat crossings), old
   ward = alley warren + courtyards + the rooftop road. The spires =
   end-game, unnumbered.
