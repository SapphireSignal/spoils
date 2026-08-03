# SPOILS — the handoff chain

**What this file is:** one short entry per chat session, newest first. A chat
does not survive. This file is how the next one inherits what the last one
knew — not just what shipped (that is `CHANGELOG.md`) but what the user
*said*, what turned out to be *wrong*, and where the work was *put down*.

**Read the top two entries and you are caught up.** Then `TASKS.md` for the
work, `CLAUDE.md` for the rules.

---

## How to write an entry (the ritual — do not skip it)

Write your entry **before the session ends**, not after — there is no after.
Practically: write it whenever you finish a batch and are about to push, so a
chat that dies mid-session still leaves a record.

1. **Append at the top**, under the divider. Never edit an older entry —
   the chain is append-only. A past entry being wrong is itself a fact worth
   keeping; correct it in the *new* entry and say what was wrong.
2. **Four headings, always.** Shipped / The user's words / Learned / Picked up
   at. If a heading has nothing in it, write "nothing" — an absent heading
   reads as a lost one.
3. **Quote the user verbatim.** Paraphrase is where intent dies. Their exact
   phrasing is what steers art and feel decisions, and it is the single
   thing most likely to be lost forever.
4. **Record what was WRONG, loudly.** A previous session's confident-but-false
   diagnosis has cost real time on this project twice (the door swing, the
   second-floor leads). If you disproved something, say so here.
5. **Keep it short.** A dozen lines. This file must stay readable at entry
   fifty, or it rots the way `CLAUDE.md` did — 977 lines of stacked history
   nobody trusted.
6. **Compress on the way out.** When an entry is older than the newest three,
   cut it to two or three lines: version range, and anything still load-bearing.
   Detail that still matters belongs in `CLAUDE.md` or `TASKS.md` by then, not
   here.
7. **Run `--checkdocs` before you commit the entry.** It proves the version
   claims in `CLAUDE.md`, `TASKS.md`, `CHANGELOG.md`, the in-game list and the
   git tags all still agree.

---

## 2026-08-02 — the living layers, one scene at a time

**Shipped:** **v0.6.32** — the trainyard's living layer, the first of the four
promoted paintings to get one. Migration re-verified first: `--checksec` and
`--checkdocs` both green at v0.6.31, tree clean, newest tag matching.

**The user's words:** *"im here for the migration, then let's do the living
layers for backdrops 2-5"*.

**How it was done, and this is the pattern for the remaining three:** the
overlays are built at the END of `make_scene_yard()`, after every base draw
and **taking no rng draw**, so the approved painting comes out bit-identical —
proven by hashing all six backdrops before and after the regen, not assumed.
Every anchor came out of the docstring's own landmark list (`SIGNAL_LENS`,
`CAB_LED`, `FAR_LED`, `PUDDLE`, `DRIP_SRC`), and each was confirmed against
the actual pixels before anything was built.

**Learned — five things the render caught that the code could not:**
- **A GLOW'S SIZE IS THE WHOLE READ.** 72 px with a 210-alpha core painted a
  pale disc bigger than the signal head: it read as a MOON rising behind it.
  34 px with a 2 px core reads as a lamp. Same maths, same colours.
- **`CPUParticles2D.color` MULTIPLIES the texture.** `rain_streak` is already
  a 3c5e8b at 20-76% alpha; tinting it 577277 as well took it to (20,42,65)
  at a quarter alpha and the drizzle rendered *invisible*. Use white.
- **ADD CANNOT MAKE A WARM THING WARM OVER A BLUE ONE.** The puddle glint is
  additive gold over a baked 253a5e, and every pixel of it measured warm
  while the streak as a whole read as a cold grey smudge — because addition
  can only push a blue base toward grey. Normal alpha REPLACES, so the gold
  survives. Add is light in air; a reflection on a surface is not that.
- **AN ODD-SIZED SPRITE LANDS ONE PIXEL UP-AND-LEFT.** `dust.png` is 3×3, and
  a sprite centred on P rasterises its middle texel onto P-1. Both indicator
  lamps sat a pixel off their own baked lenses. Measured, corrected, measured
  again — the anchors in the script are now the docstring's plus that offset,
  and it is commented so nobody "fixes" it back.
- **A LIGHT MUST BEAT ITS OWN BACKGROUND, NOT ITS OWN COLOUR.** The far
  signal's eye is baked 752438 against a `de9e41` SUNSET, so a red lamp there
  is *darker than its sky* and reads as a speck of dirt. It is additive; the
  cabinet's lens, on grey steel, is not. Check a light against what is BEHIND
  it — the same lesson the car tarp taught, in the other direction.

**Also worth knowing:** the drizzle is confined to the LEFT of the frame and
leans only 0.06, because at the wires' 0.16 the bottom-most streaks drifted
94 px right over their fall and walked into the button band. And a shot is
taken 40 frames in, so the eave drip is always caught mid-flight — the SPLASH
was proven separately by temporarily flying the drip at 2600 px/s, shooting,
and reverting (verified reverted by grep, not by memory).

**Picked up at:** **the living layers for backdrops 3, 4 and 5** — warden,
underpass, counter, in that order, one version each. Every one of them has
its room already documented in its own `make_scene_*` docstring: the warden's
lamp pool is baked as a solid banded wash with the fuse-box LED left unlit at
(800-820, 258-276) and a moth lane kept clear; the underpass's sodium tube is
baked at ~60% with three ceiling leaks at x = 300, 596 and 736; the counter's
taped splice at (838, 246) has a permanent baked scorch ring under it waiting
for the ember that drips there. Nothing is blocked. All gates green.

---

## 2026-08-02 — four backdrops auditioned, and the den and drain repainted

**Shipped:** **v0.6.28** (the migration audit — see the entry below),
**v0.6.29** (both shipped menu backdrops repainted) and **v0.6.30** (the four
candidate backdrops promoted into the game — **the menu now rotates SIX**).

*(This paragraph originally ended "the menu still rotates den + drain only",
which was true when it was written and false ninety minutes later. Amended
before the push rather than left to rot — that is the correction to the
mid-session-staleness lesson recorded three entries down, and it is the whole
point of it.)*

**On the six:** all four were promoted **byte-identical** to the versions the
user approved — hashes checked both ways, because a promotion that quietly
re-rolls a painting would undo many rounds of their review. Rotation is a
**shuffle bag at 10 s** (`_bag_next`/`_bag_reset` in `main_menu.gd`; shipped
at 30 s in v0.6.30, dropped to 10 on a user call in v0.6.31), with the
seam case closed: a refill that would put the on-screen scene up next swaps it
away, so nothing repeats back to back. Hand-rolled Fisher-Yates because
`Array.shuffle()` is banned project-wide, and deliberately UNSEEDED — the menu
should differ every launch, unlike the fixed district. **Indices 2-5 are still
STATIC**; their living layers are the next version.

**The user's words:** *"im here for the migration"*, then on the gap:
*"Why does the handoff have a gap? I just had the last session spend like 2
hours fixing and making sure the migration would all be clean and working"*.
On the one pitch anyone had painted: *"yes just drop it"*. On choosing:
*"show me the pitches again and what the living layer would be, I will pick a
couple and we make them"*. On the tally: *"nobody is dying out there anymore
it's just me so the tally amount can stay the same forever"*, then *"there's
too many tallies on both the screens let's half the amount of both"*. On a
fix that made things worse: *"this fix is probably worse than how we had it
before, the arms and hands are all messed up"*. On the shipped scenes:
*"can you upgrade the den and the drain paintings a bit to like match all of
these 4"*, *"yes a redesign would be good too for these that's what I meant"*,
and *"the blue and the brown areas of the screen is too much, like all the
colours of the screen should be blended together nicely"*.

**Learned:**
- **PARALLEL AGENTS MUST NEVER RUN REPO-WIDE GIT.** Twice today an agent ran
  `git stash` / snapshot-and-restore on a file another agent was editing.
  **Nothing was lost either time** — verified by hashing — but only by luck.
  Every agent prompt now forbids `git stash/checkout/reset`; read-only git is
  fine. When agents run in parallel, give each ONE file and say so.
- **A FIX THAT REBUILDS MORE THAN WAS COMPLAINED ABOUT WILL BE REJECTED.** The
  shoulder pass rebuilt the whole limb system to fix "shoulders look cropped",
  which moved the arms and detached the hands. Reverted, then redone with a
  hard constraint AND A PROOF: hands pixel-identical, arm centrelines fixed,
  only the width profile and the outer silhouette may change. It worked.
  **Constrain the fix to the complaint and prove the rest is untouched.**
- **AMBIGUOUS SHAPES GET READ AS WHATEVER THE BRAIN SUPPLIES.** A downpipe read
  as "the back of a car". A shoulder read as a hooded figure. A light spill on
  wet tarmac read as **a dead body in blood** — the user asked outright.
  Every time the cure was the same: give the object a lit face, a shade face
  and a visible connection to something. **Light with no visible path back to
  its source cannot read as light; it reads as a stain.**
- **A THING CAN BE DRAWN AND INVISIBLE.** The car tarp's fill was `151d28` and
  the sky behind it is also `151d28`, so two thirds of it never showed and all
  that read was a 3 px rib — a bandstand hoop. Check a fill against what is
  BEHIND it, not just against its own neighbours.
- **DO NOT BUMP THE VERSION BEFORE THE WORK IS FINISHED.** I bumped to v0.6.29
  early; the user then found a problem, and the repo sat RED (`DOCS FAIL`, tag
  lag) while it was fixed. Bump at commit time.
- **I got two things wrong that cost agent runs.** I called the den's VU meter
  needles "kettle's knitting needles" and nearly had an agent pin kettle's
  hands to coordinates on the opposite side of the frame; and I sent the tarp
  fix to `yard.py`, which has no tarp (that agent correctly changed nothing
  rather than inventing one). **Verify what an anchor IS before briefing it.**
- **The den's two-tone was a hard `if warm >= cool` switch**, and that switch
  WAS the visible boundary. One shared neutral ramp that both lamps tint at the
  same value is what makes two lights read as one room.
- Smooth lump functions render as mountain ranges: a smooth function has one
  highest point, and one highest point in a 10 px silhouette is a peak.

**Picked up at:** **THE LIVING LAYERS FOR BACKDROPS 2-5.** The user kept all
four (*"let's add all 4 of those menu backdrops to the game, just like the den
and drain"*), so they are in and rotating, but static. Next version gives them
what den and drain have, using only the five techniques that already exist in
`main_menu.gd` (listed in TASKS.md A1): a breathing additive glow, a 3-frame
sprite swap, a visibility blink on offset timers, dust particles with a fade
ramp, and one travelling sprite that triggers something when it lands. Each
per-scene brief must name the anchor pixel it hangs off and require the base
painting to stay byte-identical — that is one hash instead of a review round.
`tools/pitches/` still holds the four source modules and can be deleted once
the living layers are in. Nothing is blocked. All gates green at v0.6.30.

---

## 2026-08-02 — the chain skipped two releases, and nothing could see it

**Shipped:** **v0.6.28**, plus the record of **v0.6.26 and v0.6.27 that this
file never had**. A third migration audit (6 lenses, 19 candidates, **13
confirmed / 6 refuted** by adversarial verifiers) fixed 13 defects across
CLAUDE.md, TASKS.md, DESIGN.md, CHANGELOG.md and five .gd files. New
**`--checkdocs` part 5**. One real code fix.

**The user's words:** *"im here for the migration"*, then — on being told the
chain had a hole — *"Why does the handoff have a gap? I just had the last
session spend like 2 hours fixing and making sure the migration would all be
clean and working"*. Fair, and the answer was not negligence; see below.

**Learned:**
- **THE GAP, precisely: the last session DID write its entry, on time, at
  `fa00e67` — then worked another ~75 minutes and shipped v0.6.26, v0.6.27
  and three doc commits without ever touching it again.** So the file said
  "still v0.6.25 … tree clean at v0.6.25" while the repo was two releases
  ahead. **An entry written mid-session goes stale the instant the session
  continues.** The entry directly below this one warned about exactly that
  ("a handoff entry written in stages rots exactly like any other doc") and
  it then happened to that very session. Writing early is right; the missing
  half of the rule is **come back and amend before the last push**.
- **No gate could see it, and now one can.** `--checkdocs` read HANDOFF.md
  for dead paths but never for a VERSION. New part 5: the current release
  must be NAMED in HANDOFF.md. **Fire-tested on the real violation** — it
  failed with "HANDOFF.md never mentions v0.6.27" before this entry existed,
  which is a better proof than a planted one. Its honest limit is in the
  code comment: it proves the number is mentioned, never that the entry is
  true.
- **Third audit, third time BOTH GATES WERE GREEN THROUGHOUT.** Stop
  expecting that to change.
- **v0.6.27's changelog OVERCLAIMED ITS OWN BUG, and the overclaim hid a
  real one.** It said dying at the wheel left the car "wedged for the rest
  of the raid" — false: `abandon()` clears `driven`/`_busy` itself two lines
  after nulling `_player`, so the car stayed enterable and the only residue
  was a cosmetic open-door sprite. It also called the two guards "identical"
  and said `enter()` had carried its one "all along" — not identical
  (`enter()` must also test `.dead`), and it arrived in v0.6.43. **Chasing
  that down found the bug the entry had papered over:** `exit_car()` guarded
  only `null`, so F pressed in the ~1.2 s between death and `abandon()`
  stood the corpse up on the pavement. Fixed in v0.6.28.
- **A doc can invent work that was never done.** TASKS.md told every future
  M2 session the gun art was "already generated and waiting" —
  `make_muzzle_flash`, `make_tracer` and `make_impact_frames` have **zero
  call sites**, the save block never emits them, and no such sprite has ever
  existed. It would have sent M2 hunting a manifest key that isn't there.
- **CLAUDE.md commanded work the user had deleted.** Its "VISIBLE POWER
  CABLES" standing rule demanded an interior flex from fixture to power box
  — the exact floor clutter the user had cut ("the cables inside houses are
  gone"). `world_builder.gd` said the same thing directly above the call to
  a function whose own docstring says no cable is drawn.
- **Two more "fix one copy, leave the twin":** CLAUDE.md still said "death
  fade → respawn" (dying ends the raid into the debrief; DESIGN.md had
  already been corrected), and still listed the licensed audio as footsteps
  + thunder only — **the car doors and engine are recordings too**
  (ggbotnet, cc0), with an attribution obligation, stated correctly in four
  other places.

**Picked up at:** **The smoker on the bench (TASKS.md B4)** — still
untouched, still nothing blocked, unchanged from the last three entries.
Rebuild him from the PLAYER's character sheet so his shading matches, black
hat, bigger smoke, seat him on the bench BELOW facing away from the
backrest, move the ground item off his head. Then the LZ green smoke (B4b).

---

## 2026-08-02 — the migration works; the docs still lied in ~50 places

**Shipped:** No game changes, no version bump — still v0.6.25, all five
version sources agree. A migration re-verification that turned into the
second docs audit in two days. **~45 unique defects fixed across 16 files**
(CLAUDE.md 10, gen_art.py 8, DESIGN.md 7, environment_system.gd 2,
world_builder.gd 4, harness.gd 4, TASKS.md 3, LORE.md 2, plus README,
CHANGELOG, extraction/authority/interior_light/night_freight/radio and the
autosave log's header note). New **TASKS.md C5**. Art regenerated to a
byte-identical manifest, proving no rng draw was disturbed.

**The user's words:** *"im here for migration"*, then *"yes go, do the
smoker"* — which they interrupted twice to ask instead for *"verify again
that the migration all worked and everything is good"*. On the audit taking
a while: *"critic is taking a long time, whats going on"*. Offered a choice
between fixing the load-bearing subset or all of them, they chose **fix all
~50 first**, ahead of the smoker.

**Learned:**
- **BOTH GATES PRINTED PASS THROUGHOUT. AGAIN.** Second audit, second time.
  `--checksec`, `--checkdocs` and `--smoke` were green before, during and
  after. Treat green as "nothing mechanical is broken", never as "the docs
  are true".
- **The last session fixed the .md files and some comments, and missed a
  third copy of the camera-clamp lie** at `world_builder.gd:3822` — 3,800
  lines below the header it did fix. Same lie, same file, still claiming a
  clamp the user had explicitly removed.
- **"FIX ONE COPY, LEAVE THE TWIN" IS THE DOMINANT FAILURE MODE, and I did
  it myself mid-session.** I corrected DESIGN.md's render model in one place
  and left its twin at line 185 saying "letterboxed" — creating a fresh
  self-contradiction while fixing a contradiction. The weather statistic
  lived in CLAUDE.md *and* CHANGELOG.md. **Every number in these docs
  exists in two or three places: grep the VALUE across all seven docs and
  the .gd/.py comments before calling a fix done.**
- **The old entry below has the RENUMBERING ORDER INVERTED.** It says
  v0.6.15→v0.6.25 shipped and "then" the history was renumbered. Verified
  the opposite: `f8e83ae` ("renumber the whole release history, evenly") is
  the direct PARENT of `3831421` (v0.6.15). The renumber came **first**, and
  those eleven releases were minted on numbers it had just freed. **So
  v0.6.15…v0.6.25 exist TWICE in this history** — as pre-renumber tags
  (remapped to v0.2.13…v0.3.8) and as today's live releases. Do NOT look
  today's v0.6.15+ up in `tag_commits.json`. Corrected here, not edited
  there — the chain is append-only.
- **The leak baseline had drifted and no gate could see it.** CLAUDE.md
  claimed 932 nodes / 3585 objects; measured 814 / 3354. The *conclusion*
  (no leaks, orphans 0, flat) held — only the figures rotted, in the one
  place the file insists numbers live so they "cannot drift apart".
- **Wrong-fact, not wrong-action.** Nothing found would destroy data — no
  repeat of the phantom "stash file". The danger this time was traps that
  waste a session: a `--extract=` flag that does not extract, a `Q engine`
  key that does not exist, `~62% of sidewalks` whose 0.62 grep lands on
  trainyard boxcar spacing.
- **Three things the docs OVERCLAIMED about `--checksec`**, now written
  down: only 2 of its 7 lists are allowlists that fail closed (the rest are
  denylists that fail open); `harness.gd` is exempt from the network scan;
  and with no `.git` it returns `SEC PASS` having asserted **nothing**.
- **TASKS.md C1 was work that no longer existed** — the changelog rewrap
  shipped in v0.6.16. Parsed all 100 entries: zero wrapped fragments remain.
  Its stated proof ("v0.2.4's three bullets become two") is unreproducible;
  v0.2.4 has two bullets and the first is 269 characters.
- **A 66-agent audit is not self-certifying.** 50 of 55 candidates survived
  adversarial verification — a rate high enough to distrust. Two findings
  looked contradictory on weather; working the Markov chain out by hand
  showed they measured different things (branch weights vs time-share) and
  both were right. **Spot-check the audit before believing the audit.**

**Picked up at:** **The smoker on the bench (TASKS.md B4)** — untouched,
nothing blocked. Rebuild him from the PLAYER's character sheet so his
shading matches, black hat to tell him apart, bigger smoke, seat him on the
bench BELOW facing away from the backrest, and move the ground item over his
head. Then the LZ green smoke (B4b). All gates green, tree clean at v0.6.25.

---

## 2026-08-02 — the migration was broken and both gates said PASS

**Shipped:** No game changes. A migration session that turned into a docs
audit. Fixed **14 confirmed defects** across `CLAUDE.md`, `DESIGN.md`,
`TASKS.md`, `README.md` and the `sfx.gd` header, plus a new **DOCS THAT LIE
ARE THE LIVE RISK** section in CLAUDE.md's SAFETY & TRUST block. No version
bump — nothing in the game changed, so all five version sources still agree
at v0.6.25.

**The user's words:** *"i want my game to be secure, and the migrations to
work"*. On persisting it: *"ok, so make sure thats saved somewhere"*, then
the autosave idea — *"cant we just save everything in real time in the repo
so we will always have it? like this message i send you right now cant it be
instantly logged somewhere in the repo, its like an auto save"*. On the
hardening: *"yes go, make it fail"*. Finally *"yes just do whatever you think
is best"*.

**Learned:**
- **`godot_console` RESOLVES TO NOTHING on this machine.** Not on PATH, no
  alias, no shim, no shell profile exists. It appeared 12x, including as the
  **first two commands at the top of `CLAUDE.md`** — so the documented
  migration was unrunnable, and had been for a long time. The top block is
  now the full exe path; the shorthand is defined once beneath it. PowerShell
  needs backslashes and the Bash tool needs forward slashes, because
  `.claude/settings.json` allowlists them as two separate rules.
- **BOTH GATES PRINTED PASS THROUGHOUT.** That is the headline. A green
  `--checkdocs` never meant the docs were true.
- **A check cannot verify prose, ever.** `DESIGN.md` said the boot scene is
  the menu (it is the splash), said the map is 320×320 (it is 256×256), said
  4 menu backdrops and `CLAUDE.md` said 3 (there are **2**; the storm was
  retired 2026-08-01). All claims, none testable by a script.
- **One doc instruction would have destroyed user data.** `DESIGN.md` told
  every session that smoke runs "pollute the persisted stash file" under
  `%APPDATA%\Godot\app_userdata\` and to clean up after test batches. **There
  is no stash file** — that folder holds the user's real keybinds, resolution
  and volumes. No adversary needed.
- `TASKS.md` B3 sent a grep to `WALL_STYLES`, which does not exist. It is
  `BRICK_STYLES` (gen_art.py ~621).
- **The last session's open permissions question is ANSWERED: `git tag -f`
  works now.** Tested on a throwaway local tag, then deleted. Project
  allowlist covers force ops; no need for `bypassPermissions`.
- **`--checkdocs` HAD a real hole** — it scanned only 3 of 7 docs for bad
  paths and tested nothing about whether a documented COMMAND resolves, which
  is how the top-of-file migration block stayed unrunnable behind a green
  gate. **Closed later in this same session; see the hardening below.** What
  is still true, and is now stated honestly in CLAUDE.md rather than
  overclaimed: it is blind to BACKSLASH paths (`python tools\gen_art.py` is
  not covered), it resolves absolute `.exe` paths only, and it cannot verify
  prose at all.

**Then `--checkdocs` was hardened, and every part fire-tested.** It is now
five parts: (0) the docs it reads exist and are non-empty — before this,
DELETING a doc made every check scan nothing and pass silently; (1) DESIGN.md
as an **optional** version claim — state none and it never fires, state one
and it must agree, so re-adding a version is safe instead of silent rot, and
no fifth number has to be hand-bumped each release; (2) tags unchanged;
(3) the path scan widened to ALL SEVEN docs and to bare root-level
`.md`/`.bat`/`.godot` names (CHANGELOG.md was held out at first as "frozen
history names deleted files" — measured: 4 refs, 0 dead, and HANDOFF.md is
append-only too and was always scanned, so the hole was unearned); (4) every `.exe` the docs name must
resolve on disk, and a `godot_console` COMMAND may not sit in a doc that no
longer defines the shorthand. **All six planted violations FIRED.**
Two things worth keeping: the exe path is never hardcoded in `harness.gd` —
disk is the authority, a copy would be a seventh place to drift. And 4b
fires on the COMMAND shape only, not a prose mention: it false-positived on
this very entry's first run, because the entry quotes `godot_console` to say
it is dead. Narrowed the rule rather than exempting the file — exempting is
what makes a gate lie.

**Then the autosave shipped** — the user's idea: *"cant it be instantly
logged somewhere in the repo, its like an auto save"*. A `UserPromptSubmit`
hook runs `.claude/autosave.py`, appending every message they send, verbatim,
to a docs/sessions/ log. Two things the research caught that would have
bitten us badly: **the published hook docs are WRONG about the field name**
(they say `user_prompt`; the shipped binary emits `prompt` — the script reads
both), and **exit code 2 on this event ERASES the user's typed message**, so
the script exits 0 on every path including failure. On this event alone hook
stdout is injected into Claude's context, so it prints nothing — verified
stdout length 0, UTF-8 intact, zero CR bytes. A settings change needs a
RESTART to take effect.

**Then the migration was COLD-TESTED** — three fresh sessions with no context
each followed CLAUDE.md's onboarding literally (one maximally literal, one
verifying prose against code, one trying to start work). **All three ran the
top-of-file commands verbatim first try and correctly named the version,
the milestone and the next task. All three rated readiness 8/10.** So
migration works. But they confirmed **10 more false claims**, and the lesson
is sharper than the count:

- **The morning's fixes stopped at the `.md` files.** `world_builder.gd:3`
  still said "320x320" and `player.gd:6` + `world_builder.gd:11` still
  described a camera "clamped to an inset diamond" — which `player.gd:379`
  contradicts in its own file, and which the user had explicitly removed.
  That header even supplied a plausible *reason* for the clamp, so a session
  trusting it would have reintroduced exactly what the user asked to be taken
  out. **Fix the code comments in the same pass as the docs; nothing scans
  them.**
- **`BARRIER_INSET` is 66, not the 72 CLAUDE.md claimed** — a value the ring
  never held. Load-bearing: placement maths off by 6 cells. CLAUDE.md's own
  safehouse [174, 73] only computes from 66, so the file contradicted itself.
- **15 buildings, not "~34"** (`--probe-world`: DOORS total=15, one door per
  building). **Three shaders, not "one"**. `DESIGN.md` claimed RoofReveal
  fades walls to 30% — walls are NEVER faded, the user rejected that.
- All ten sat behind `SEC PASS` + `DOCS PASS`. Prose again.

Also fixed: `--smoke` is now written out in full (it is mandatory before every
push and was the one shorthand command a new session could not paste), and its
alarming-but-normal headless output is documented so the ~50 display-server
ERRORs and the exit-time leak warnings stop reading as failures next to the
"Leaks: none" baseline.

**Picked up at:** **The smoker on the bench (TASKS.md B4)** — nothing is
blocked and nothing is half-done. Rebuild him from the PLAYER's character
sheet so his shading matches everything else, give him a black hat to tell
him apart, bigger smoke, and seat him on the bench BELOW facing away from the
backrest. Then the LZ green smoke (B4b).

Everything from this session shipped and is pushed: the 14 doc fixes, the
five-part `--checkdocs`, and the autosave. All gates green, tree clean, still
v0.6.25. The session logs live in `docs/sessions/` and stay **inside**
`--checksec`'s secret scan — the user's explicit call and mine, because a
noisy gate beats a blind one. Verified on the most adversarial input it will
see: a log containing this whole conversation about keys and secret patterns
still passes.

**Two things in this entry were WRONG while it was being written, and both
are corrected above rather than quietly edited away.** It claimed
`--checkdocs` scans only 3 of 7 docs — true when written, closed hours later
in the same session. And its "picked up at" described the autosave as
outstanding after it had already shipped. A handoff entry written in stages
rots exactly like any other doc; read the whole entry before trusting its
last paragraph.

---

## 2026-08-02 — migration hardening

*(Compressed per entry rule 6.)* No game changes. Built this file, added
`--checkdocs`, then `--checksec` (six enforced invariants, **every one
fire-tested by planting a real violation**), and the SAFETY & TRUST section
in `CLAUDE.md` — all at the user's request: *"i want my game to be secure,
and the migrations to work"*, and they asked for *"a chain of migrations
that we will never forget"*. On permissions they declined full bypass:
*"auto is fine, i can run a couple commands whenever you need me to."*

Still load-bearing: **the renumbering left `v0.6.14` on the wrong commit**
(`f8e83ae` instead of `9c79c9b`) — found, fixed, and now guarded by
`--checkdocs` part 2. **Commit messages still carry PRE-renumber version
numbers**, so never read a version out of a commit subject before
`f8e83ae` — use `git tag --points-at`. And the parse-error-looks-like-a-hang
trap bit again: return TYPED arrays, and read the HEAD of the log.

## 2026-08-02 — overcast, and the docs rebuilt

*(Compressed per entry rule 6 on 2026-08-02. Reconstructed originally from
the outgoing chat's summary plus the commits.)*

**v0.6.15 → v0.6.25 in one long session**, on top of the renumbering: the
harness stopped pretending (a smoke test vacuous for three releases), a
readable changelog, then the whole engine-side polish layer — impact, shader
warm-up, colour grade, dust motes, a real day-arc, sun shafts, a second tiny
font, the safehouse move, and **overcast weather**. Then `CLAUDE.md` was cut
from 977 lines to ~500 and `TASKS.md` rewritten against reality.

**Its ORDER claim was wrong and is corrected in the newest entry:** the
renumber came FIRST (`f8e83ae` is the parent of v0.6.15), not after these
releases — so v0.6.15…v0.6.25 name two different things in this history.

Every lesson it recorded now lives in `CLAUDE.md`: the vacuous smoke test
and `_shove`, parse-error-looks-like-a-hang, a colour grade must not change
brightness, ramps dither themselves, sort position ≠ draw position, never
skip an rng draw. User quotes kept: *"keep the base art as-is, just use
godot's visual toolkit to turn up the atmosphere"*; on the trailer *"were
not dropping it, just putting it aside for now"*.

---

## Before the chain

Everything earlier is in `CHANGELOG.md` (every release, what and why) and
`docs/version_renumber_2026-08-02/` (the release-history remap). The project
started 2026-07-31; v0.1.0 → v0.6.14 covers the first three days, and the
renumbering means **any version number quoted in a chat log from before
2026-08-02 is wrong** — check the mapping rather than trusting a transcript.

No per-session record exists before the two entries above, because this file
did not exist. That is the gap this file closes.
