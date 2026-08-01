# SPOILS — session handoff (read this first)

2D isometric extraction shooter, pixel art, Godot 4.7, Windows. **Read
`DESIGN.md` for the full game design & workflow contract** — it is the source
of truth for what we're building. `CHANGELOG.md` records everything shipped.
This file carries everything a fresh session needs that isn't in those two.

## Where we are

- **Version v0.6.11** (v0.6.10: car caps brightened to READ — invisible-dark
  ≠ missing, wheel-arch bites fixed, attic-dark roof holes, sniper volleys,
  zoom ladder to 6x w/ glide, no wide zoom; v0.6.11: 3D pass — iso pillars,
  domed cylinders, tire tori, sloped rubble). Older (v0.6.6-v0.6.9: prone stance on Z,
  splash screen + menu music + full audio suite, lattice-fence barricade
  line, 3D barrels, complete vehicles, wheel zoom ladder w/ edge
  auto-tighten, anti-banding dither film, clip audit in gen_art — generation
  FAILS on canvas-edge content, keep it that way). Older baseline: v0.6.5
  ("the barricade update"), committed & pushed. Map
  **"transit"** (user-named), 320×320 total with the PLAYABLE district inside
  a randomized barricade ring (inset 31 cells); the world visibly continues
  beyond it but escalating sniper fire owns the buffer (fallen-raider bodies
  past the line sell it). Camera NEVER clamps (user call). Doors interactive
  (F, with prompt), flashlight (E, real click), DARK nights, flickering lamps,
  world-anchored rain, ~45 s weather tint fades, dip-free time-budgeted
  deploys, fresh seeded layout per deploy.
- **Milestone 1 (walkable world) is DONE** (~18 user feedback passes, see
  CHANGELOG v0.2.0 → v0.6.5).
- **NEXT: Milestone 2 — GUNPLAY, to ship as v0.7.0.** Mouse aim, hitscan with
  tracers, muzzle flash, screen shake, destructible props, first synthesized
  gun sounds. The user starts it by saying "go".
- After that (design doc §8): M3 human enemies (0.8), M4 the loop with
  TARKOV-STYLE loot: grid inventory, containers, character doll gear slots
  (0.9), M5 fake-player bots/lighting/trader (1.0), M6 quests (1.1), M7 second
  map (1.2). **User calls 2026-08-01: NO machine enemies (human AI only), NO
  rarity color tiers on loot.**

## Versioning policy (user-agreed, do not drift)

Patch bumps (0.6.x) for polish/fix/content batches. Minor bumps ONLY when a
design-doc milestone lands (0.7 guns, 0.8 enemies, 0.9 loop). **1.0 = the
complete v1 game.** The in-game changelog (CHANGELOG_ENTRIES in
`scripts/main_menu.gd`) must gain an entry EVERY version — the menu's corner
version label derives from its newest entry (single source of truth). Also
update CHANGELOG.md. Tag releases (`git tag vX.Y.Z`, push with `--tags`).

## What exists (systems map)

- `tools/gen_art.py` — generates ALL art deterministically from
  `art/palettes/apollo.gpl` (46 colors) into `art/gen/` + `manifest.json`
  (sizes, origins, collision shapes, variant families — the game hardcodes
  none of it). `tools/gen_font.py` (invoked by gen_art) builds the lowercase
  bitmap font. `tools/gen_banner.py` → repo banner.
- `scripts/world_builder.gd` — 320×320 planned map, FRESH SEED PER DEPLOY
  (build(root, seed_text); harness --seed pins it; ALL randomness through the
  seeded _rng — `Array.shuffle()` is banned, use `_shuffle()`). Road grid with
  center dashes both axes, dirt roads, forests + interior groves + lone trees
  on green pockets, ~34 buildings (thin-wall shells, modular roofs, ONE floor
  look per building, interactive Door on a visible side, entrance pockets kept
  clear inside AND out), lane-correct road vehicles (some broken + litter),
  sparse mostly-dead street lamps, sticks, clustered scatter, puddle spots.
  BARRICADE RING at inset 31 = the advertised map edge (art axis x/y, flats
  walkable-over, road breaches get wreckage) + sparse bodies past it; tree
  density tiers off through the buffer band. Border collision at the true
  diamond edge is only a backstop. build() is a COROUTINE with TIME-BUDGETED
  yielding (~2.4 ms/frame via _tick() — never fixed work-counts; that caused
  deploy fps dips).
- `scripts/environment_system.gd` — day/night tint (20 min, continuous
  gradient loop — endpoints MUST match or midnight snaps), world-anchored
  rain (drop pool falls to real ground points, splash pool stays put, roofed
  cells skipped, all puddle-blue), long storms, double-strike lightning,
  puddles, night_amount broadcast to "street_lamps" group.
- `scripts/street_lamp.gd` — working/dead lamps; working ones glow + cast a
  PointLight2D pool at night with per-lamp flicker/dropouts.
- `scripts/door.gd` — closed-by-default door: F toggles, 4-frame swing,
  thin wall-line collider disabled while open, group "doors".
- `scripts/edge_guard.gd` — barricade-line sniper: centered warning ("turn
  back or you will get sniped") on crossing barrier_f, 3 s grace, off-screen
  tracer rounds, ESCALATING interval/accuracy with depth, 3 hits = death.
- `scripts/player.gd` — render-rate movement (NOT physics tick), THREE
  stances: stand / crouch (ctrl, hold-or-toggle) / prone (Z toggle, 0.32x
  speed, crouch input exits it; char_prone.png sheet, same layout as the
  others), flashlight cone on E (8 facings; smooth light textures may rotate,
  sprites never), hp/take_hit/hurt-flash/died + respawn, camera UNCLAMPED and
  welded to the character, snapped to SCREEN pixels (see rule 1).
- `scripts/main.gd` — deploy screen ("deploying to transit", animated
  dots) → texture prewarm → awaited async world build → environment → edge
  guard → pause menu; death fade → respawn. `scripts/main_menu.gd` — 3
  rotating backdrops, title shine, changelog viewer. `scripts/settings.gd` —
  display/res/quality/fps/vsync/show-fps + rebindable keys + pixel_scale (the
  integer window scale) + 0.2s-window fps counter. `scripts/keybinds_panel.gd`,
  `scripts/settings_panel.gd`, `scripts/pause_menu.gd`, `scripts/ui_theme.gd`
  (bitmap font + near-black/light-border buttons), `scripts/sfx.gd`
  (ALL synthesized: UI blips, door thunks, sniper crack, flashlight click,
  per-surface footsteps via play_step(kind, quiet), thunder, rain bed
  (set_rain), car alarm stream, splash ping; heavy streams render on a
  Thread), `scripts/music.gd` (menu theme, threaded render, play_menu/
  stop_menu), `scripts/splash.gd` + `scenes/splash.tscn` (SapphireSignal
  studio card — THE BOOT SCENE; harness args skip it instantly),
  `scripts/car_alarms.gd` (armed intact cars: proximity alarm + flashing
  light overlays from manifest "lights" coords, once per car until death),
  `scripts/authority.gd` (state seam: spawn_player, damage_player),
  `scripts/harness.gd` (see Verification; also --shot-splash=<name>).

## Verification workflow (design doc §7 — never skip)

After ANY art change: `python tools\gen_art.py`, then delete orphan imports:
`python -c "import pathlib; [p.unlink() for p in pathlib.Path('art/gen').glob('*.png.import') if not p.with_suffix('').exists()]"`
then `godot_console --headless --path . --import`.
- Smoke: `godot_console --headless --path . -- --smoke` → must print SMOKE PASS
  (covers movement, crouch, border, roofs, doors, edge sniper, pause).
- Shots: `godot_console --path . -- --shot=<name>` (+ optional flags:
  `--scene=menu`, `--menu=pause|settings|changelog`, `--backdrop=N`,
  `--at=X,Y`, `--face=N|S|E...`, `--crouch`, `--weather=rain`, `--tod=0..1`,
  `--flashlight`, `--seed=<text>`). Read the PNG yourself, judge it, iterate,
  send the user a 2× upscale (scratchpad) of the good one.
- `--seed=<text>` pins the district; ALWAYS pair `--probe-world` (prints
  lamp/vehicle/door counts + shot-aimable cells) with the same seed you then
  shoot, or your coordinates aim at a different world.
- Perf: `godot_console --path . -- --perf [--weather=rain --tod=0 ...]` →
  prints avg fps / worst frame ms / node count. v0.6.3 baseline on the user's
  240 Hz box: 240 avg, worst ~5 ms, ~34k nodes.
- Godot: `D:\Godot\Godot_v4.7.1-stable_win64_console.exe` (CLI) / non-console
  exe in Play.bat. Console exe for everything scripted.

## Hard-won rules (violating these caused user complaints — never regress)

1. **User's display: 240 Hz, desktop 1680×1080 (stretched, non-native — do
   not relitigate it).** ALL motion updates in `_process` at render rate.
   Rendering is NATIVE RES (`canvas_items` stretch + integer scale) with ONE
   EXPLICIT screen-pixel grid (multiples of 1/Settings.pixel_scale world px):
   the player's TRUE position stays continuous, but each frame the rendered
   sprite+shadow park on the grid and the camera is defined off that SAME
   snapped point (constant character-to-camera offset — see player._process).
   120 px/s walking = exactly 1 screen px/frame at 240 Hz. Do NOT round the
   camera to whole WORLD pixels (halves scroll rate → "low fps walk", v0.6.3),
   do NOT let camera and sprite round independently (shimmer, v0.6.4), and
   snap_2d_transforms_to_pixel stays OFF — engine auto-snap fights the grid
   at half-pixel positions. Static props/splashes sit on whole world pixels
   (_add_prop rounds); the player settles to whole world px when idle.
2. **Text**: only the generated lowercase bitmap font (no capitals anywhere,
   user preference). If text ever looks blurry: the .fnt import silently
   failed — delete `art/gen/spoils_font.fnt.import` + `.godot/imported/
   spoils_font*` and reimport (Godot caches import failures for unchanged
   files).
3. **RANDOMIZE placement/variants everywhere.** The user repeatedly and
   angrily flagged hand-placed grids and cloned props ("do you not understand
   that yet?"). Counts, positions, variants, offsets — all rolled. Baked
   variation (sizes/damage/poses) in the generator; NEVER runtime
   scale/rotation (breaks pixel grid).
4. **Symmetry & flushness**: character must be symmetric (arms/neck history);
   walls identical on all sides; roofs flush with walls, trim lines continuous
   through corners. The user zooms in and checks corners.
5. Palette purity: every game sprite from Apollo only (white font/dust/rain +
   alpha assets exempt by design). One palette per asset.
6. Interior reveal: roof fades to 0 ONLY when the player is inside the
   interior cells; walls always stay visible (user rejected wall fading).
   Buildings: one door each, on a camera-visible side (south/east) — CLOSED
   until F-toggled, flush in the wall plane (an open-leaning leaf clipped
   through walls: user complaint). Floors: ONE uniform tile per building
   (per-cell variants read as patchwork: user complaint). Entrances must stay
   prop-free inside and outside (couch-in-doorway complaint).
7. Menus: buttons near-black translucent with light border (hue-based fills
   blended into backdrops); menu buttons exactly centered, self-centering;
   settings panel fixed width; VSync ON greys the FPS cap slider.
8. PowerShell 5.1 quirks: no `&&`; heredocs don't work (use the Bash tool for
   python heredocs, or scratchpad files); .bat files must be ASCII+CRLF; git
   line-ending warnings are normal noise; `git commit` exit 255 with warnings
   still commits — verify with `git log`.
9. Costly-to-rediscover: Godot won't mode-switch displays (no exclusive-res
   change); stretch `viewport`+`integer` ignores `expand` (manual
   content_scale_size math in settings.gd); iso prisms need w == 2*d, d even;
   brick/pattern period must divide 64 for seam continuity.

## User preferences (communication & product)

- Plain, short, non-technical summaries; they playtest and react — build,
  verify, ship, send screenshots, stop. Milestones proceed on their "go".
- Very sensitive to frame pacing and visual artifacts (spots 1px issues, fps
  wobbles, single-frame hitches — always explain honestly, fix structurally;
  loading moments get masked behind transitions like the deploy screen).
- Dislikes clutter, clones, visible grids/patterns, anything "off"/asymmetric.
- Wants the world to feel alive/real (weather, time, POIs, furniture).
- GitHub: https://github.com/SapphireSignal/spoils (PRIVATE, account
  SapphireSignal, branch main, tags v0.1.0…v0.6.2). Push after each batch.
  Commits end with the Claude Co-Authored-By trailer.

## Registered-but-inert (activate in later milestones)

- LIVE: interact(F → doors), flashlight(E), prone(Z). Still inert:
  reload(R), weapon slots(1/2/3) — wire in M2 (guns).
- Settings "graphics quality" is stored but drives nothing until M5
  lighting/effects.
- Night darkness + flashlight + lamp lights shipped in v0.6.3, deepened in
  v0.6.5 (CanvasModulate + PointLight2D — real 2D lighting still expands in
  M5). Known minor: monitor panel-stretch shimmer is out of our control. One
  ~30 ms frame on the menu→game scene swap remains (hard cut, invisible in
  motion; the fps counter blips ~200 for one window) — everything after holds
  refresh rate; fixing it needs keep-menu-resident scene switching, deferred.
