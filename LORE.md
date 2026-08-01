# SPOILS — lore bible (v0 draft, 2026-08-01)

The story foundation for milestone 2+. Written with the user; the cutscene
ships with M2 (v0.7.0). Everything lowercase in-game, per the font rule.

## the world

- Six years ago something broke the city. Nobody agrees on what — the game
  never says. (Deliberate: the mystery IS the tone. No robots, no monsters —
  the collapse was human.)
- The government's answer was **the cordon**: the WHOLE CITY wired shut
  overnight — lattice fence, floodlights, and the **wardens**, the marksmen
  who hold the line to this day. One rule: *nobody crosses, nothing comes
  out.* (The wardens are the in-game edge snipers; the fallen raiders past
  the barricades are the ones who tested the rule.)
- Inside the wire the city is still all there: district after district,
  each sealed, each stripped a little less the deeper you go. **transit**
  is just the first — the district nearest the wire, the one raiders crack
  before they earn the deeper ones. Names on mara's board for later maps:
  **the mills**, **harbor**, **old ward** (M7+ picks from these; the game
  is the CITY, never one district).
- Everything valuable stayed inside. A trade grew in the cracks: **raiders**
  slip in through gaps and drains, strip the districts, sell what they
  carry out.

## the characters

- **magpie** — the player. A raider; callsign because magpies steal what
  shines. Mute in-game. Carries a creased photo: two kids on a pickup's
  tailgate (never explained in v1 — quest hook for M6).
- **mara** — handler and radio operator. Runs the job board, guides raids,
  knows every gap in the wire. The voice of the game (subtitle VO).
- **kettle** — the fence. Buys anything that shines, asks nothing, counts
  brass like prayer beads. Future trader (M5), quest-giver (M6).
- **verne** — the medic. Patches raiders in the den's back room; the only
  one who tells you not to go. Future trader/healer (M5/M6).

## the cutscene — "the wire" (~2:05, M2 deliverable)

First launch ONLY, after the studio splash; any key skips. 2D painted
widescreen shots (NOT isometric — front/side view cinematic), letterboxed,
parallax camera drifts, animated layers per shot, film grain, lowercase
subtitles, thunder/footsteps foley from the licensed audio, stripped-down
menu guitar as score. Harness always skips (like the splash).

1. 0:00–0:12 "the table" — black, radio crackle; candlelit pan across maps,
   brass, the tailgate photo. mara: "you sure about this one, magpie?"
2. 0:12–0:26 "the last evening" — wide dusk cityscape, six years ago; twin
   rivers of headlights leaving in the rain. "six years since they wired
   the city shut." (the CITY — the game is bigger than any one map)
3. 0:26–0:40 "the wire goes up" — silhouettes hammer lattice panels under
   floodlights; a hand against the mesh; real thunder.
4. 0:40–0:52 "the rule" — warden marksman close-up, breath fog, scope
   glint. Subtitle only: "nobody crosses. nothing comes out."
5. 0:52–1:06 "six years in one corner" — one street corner, three cross-
   fading seasons of decay; the traffic light above it dies mid-shot.
6. 1:06–1:22 "the den" — kettle counting brass, verne rolling bandages,
   mara at the radio wall, the job board: MANY district tags pinned
   (transit, the mills, harbor, old ward — most crossed out or marked
   "warden-heavy"; transit's tag is pulled). Visual lore: one city, many
   districts, this is merely tonight's. kettle: "bring me anything that
   shines." verne: "bring yourself back. that's all."
7. 1:22–1:36 "gearing up" — close-ups, no faces: straps, boots, pack, the
   photo into the jacket. mara: "transit tonight. in through the drain.
   out before the fog lifts." (names the district as ONE JOB of many;
   seeds the M2 tunnels)
8. 1:36–1:50 "the drain" — side-view long shot, magpie through dawn mist
   along the OUTSIDE of the fence line, quiet real footsteps; kneels at a
   roadside manhole, slides the cover, drops in. (matches mara's brief —
   you enter the way you'll leave)
9. 1:50–2:05 "the transition" — inside the wire: a manhole cover slides
   open at the empty crossroads, magpie climbs up into the mist; camera
   rises behind them; dawn fog whites the frame; the title "spoils"
   breathes in it once; the mist thins onto the REAL generated district
   already running — the player character standing beside that same open
   drain. Controls just work. No prompt. (The district builds
   asynchronously behind shots 7–8 using the deploy tech; the tutorial
   raid uses a HAND-VERIFIED PINNED SEED so the route below is dependable;
   the film's last painted frame matches the game's first real frame.)

## the walk-in (first-raid tutorial, M2 deliverable)

Diegetic, no popups, no banner — mara's radio subtitles teach; tiny
lowercase corner hints appear ONLY if the player stalls (a few seconds of
inaction), so good players never see UI. Runs on the pinned tutorial seed
(house with door near spawn, dark interior, drain nearby), then fresh
seeds forever after.

1. land at the open drain — silence; stall-hint "wasd to move" only if idle
2. "that door. f." — the existing door prompt does the work
3. "dark in there. light." — flashlight on e in a genuinely dark interior
4. the first WEAPON on a table inside — "she's yours now. dry-fire once —
   it's safe here." — mouse aim + one shot into shelf cans (destructibles)
5. staged distant warden crack on the way out — "get low." — crouch/prone
   behind a car; fear teaches stances
6. "fog's lifting. out the way you came." — F on the drain ladder, short
   dark tunnel, ladder up beyond the wire
7. epilogue (5 s, letterboxed): the den doorway, kettle weighing the take,
   mara: "and that's the job." — THEN the main menu fades in for the first
   time ever (the menu = the den = home; deploy now means something)

Flags: seen_intro + done_walkin in settings.cfg; any key skips the film;
pause menu offers "skip the walk-in" during the first raid; harness skips
all of it. Future absorption: M4 adds one loot beat ("pocket anything that
shines"); M3 turns the staged crack into a real patrol to hide from.

Flow: first boot = splash → film → raid. Every later boot = splash → menu.
Seen-flag persisted via settings (user://settings.cfg).

## menu backdrop pitches (user picks; build on approval)

1. the wire at dusk — barricade line to the horizon, sweeping floodlights,
   rare distant tracer.
2. the drain — tunnel mouth, manhole light shaft on black water, drip
   rings, dust motes.
3. the den — the traders' back room; radio needle, candle flicker, smoke.
4. the marksman's view — behind a warden nest at night, the whole dark
   district below; scope glint, ember pulse, dying lamps.
5. dawn extraction — misted street, raider silhouette hauling a duffel to
   a fence gap; rolling mist, crows.
6. storm over the cordon — the WHOLE sealed city's skyline under
   double-strike lightning, rain sheets, window lights dying — district
   after district into the dark.
