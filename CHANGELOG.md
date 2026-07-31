# Changelog

All notable changes to SPOILS are documented here. Versions follow a simple
`0.minor.patch` scheme while the game is pre-release.

## [0.3.0] — 2026-07-31

### Added
- Pause menu on **Esc** with Back / Settings / Quit.
- Settings panel: display mode (borderless fullscreen or windowed), graphics
  quality (will drive lighting & effects in upcoming milestones), FPS cap
  slider (0–240, 0 = uncapped), VSync toggle, and an on-screen FPS counter.
- Settings persist to disk and re-apply on launch.
- Project README, banner, and this changelog.

### Changed
- Esc no longer quits the game directly — quitting now lives in the menu.

### Fixed
- Fullscreen letterboxing: the view now expands to fill the entire screen at
  the largest whole-number pixel scale — no black frame, on any resolution,
  with pixels staying perfectly crisp.

## [0.2.1] — 2026-07-31

### Fixed
- **High-refresh judder:** movement and camera now update every rendered frame
  instead of at the 60 Hz physics tick. On high-refresh monitors (e.g. 240 Hz)
  the old behavior read as constant stutter.
- **Motion blur/shimmer while walking:** the camera is hard-locked to whole
  pixels every frame, so the low-res screen never resamples mid-scroll.

### Changed
- Game now launches fullscreen (borderless) by default, integer-scaled.

## [0.2.0] — 2026-07-31

First playtest feedback pass.

### Changed
- **Ground rebuilt:** removed all per-tile edge lines and repeating blotches.
  The ground now reads as one continuous surface — six low-contrast concrete
  variants, rare one-off cracks/stains/moss, and dirt patches that blend out
  at their borders instead of ending in hard diamond edges.
- **Buildings rebuilt in brick:** two brick styles with mortar courses and a
  concrete coping cap. Wall pieces are neighbor-aware, so wall runs render as
  continuous walls with framed windows and proper corners — not rows of cubes.
- **Walk animation:** 6-frame cycle (was 4) at a higher frame rate, with real
  leg scissor, foot lifts, and arm swing.

### Added
- New props with deliberately distinct silhouettes: flat ammo crate, steel
  gas cylinder, tire stack, wooden pallet, and a dumpster. Rubble piles now
  carry brick chunks so debris ties into the buildings.

### Removed
- Recolored duplicate props (olive barrel, military crate clone).

## [0.1.1] — 2026-07-31

### Fixed
- `Play.bat` failed to launch (Windows batch needs ASCII + CRLF line endings,
  and the project path argument was being mangled). Batch line endings are now
  enforced via `.gitattributes`.

## [0.1.0] — 2026-07-31

Milestone 1: the walkable world. First playtest build.

### Added
- Godot 4.7 project scaffold, 640×360 pixel-perfect rendering, isometric
  Y-sorted world.
- Deterministic art pipeline (`tools/gen_art.py`): every asset generated from
  the 46-color Apollo palette — floor tiles, wall blocks, props, drop shadow,
  and an 8-direction player sprite sheet.
- 48×48-tile ruined city block: roads with worn lane paint, two building
  shells, scattered props, rubble perimeter.
- Player: 8-direction WASD/arrow movement with collision, follow camera.
- Self-verification harness: headless smoke test (`--smoke`) and screenshot
  capture (`--shot=<name>`).
- `Play.bat` one-click launcher.
