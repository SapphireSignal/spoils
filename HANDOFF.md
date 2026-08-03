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

## 2026-08-02 → 08-03 — every backdrop made to move, and four bugs that hid

**Shipped: v0.6.32 → v0.6.44, thirteen releases, plus a README rewrite.**
Living layers for all six menu backdrops (yard, warden, underpass, counter —
den and drain already had one), then a second pass making them **noticeable**
on the user's push. Menu rain rebuilt on the raid's own model. The underpass
door, its wired glass and two lore notices. Mara's arms, pencil and den
silhouette; kettle's beard. A new `--film` harness mode. `gen_art` made
crash-safe. Every base painting stayed byte-identical except where a change
was explicitly asked for, and each of those diffs is quoted in `CHANGELOG.md`.

**The user's words** (the whole day is in `docs/sessions/2026-08-03.md`):
- *"these living layers are very minimal, can we add some more to it, to every
  backdrop, i want it to be noticable"*
- *"dont just amp up the current ones, find new ones on the screen and create
  some, like some flcikering lights, or some pole lines sparks coming off
  them"* — **this is the sharper half of the brief and the one to keep.**
- *"i dont see any rat"* / *"the birds arent moving, they are in the same spot
  the whole time"* / *"they are on the thing on the right, they should be in
  the sky"*
- *"i meant like the actual raindrops coming down on the screen should
  physically hit something on the screen, so remove that water stuff on the
  ground and do what i wanted"* — *"we already have that system in our raids"*
- *"lets keep both the backdrops for now, no harm"* (on the drain/underpass
  camera angles being similar — they ARE, it is a base-art issue, not acted on)
- *"and about that rule, what if the fix needs more rebuild in order to work?"*
  → answered: **the rule is not "never rebuild more", it is "never rebuild more
  SILENTLY". Say what will move, get a yes, then prove the rest did not.**
- *"also make mara skinnier in the den backdrop"*, *"give kettle a beard"*,
  *"make a rectangle see through glass on there and show some blood splatter"*
- *"ill tell you when to be scarce"* — do not self-ration context unasked.

**Learned. Every one of these is now a standing rule in `CLAUDE.md`** — go
there for the full text, this is the index:
- **Never round a position you then read back to accumulate.** Killed the birds
  AND the rat: at 240 fps a 34 px/s walk is 0.14 px a frame and the round puts
  it straight back. Both read as "it isn't there", not as a rounding bug.
- **Every new element must beat the background it lands on — measured.** Failed
  four times in a day (far signal eye, underpass drip, rat, birds).
- **Check whether the UI is on top of it.** The birds flew at screen row 464,
  inside the "play" button.
- **`modulate` MULTIPLIES**, so "force it bright to see if it renders" does not
  work on a dark sprite. Swap the TEXTURE instead.
- **Do not answer "why is X not showing" with a theory. Measure.** I gave two
  confident wrong answers about the birds and the user rejected both, correctly.
  And you cannot diff a shot against the BAKE for this — the vignette darkens
  everything and swamps the signal. Diff CONSECUTIVE FILM FRAMES.
- **Delete the indirection rather than bisecting it.** The birds only worked
  once the two-state + gate logic was thrown away for one flat loop.
- **Release order: bump docs → commit → TAG → smoke → push** (user's call).
- **`gen_art` deletes before it writes** — fixed in v0.6.44 so it purges at the
  END, proven by planting a crash (528 PNGs before, 528 after).

**What went wrong that is worth saying plainly:** the birds cost most of a
session — four wrong explanations, an invalid test, and several scans that
measured wires and rain instead of birds — before anyone cropped the flight
path and looked at it. **Looking should have been the first move, not the
fifth.**

**And the docs lied twice while both gates printed PASS** (third session
running): `DESIGN.md` still described a TWO-backdrop menu with the others as
unwired pitches, thirteen releases out of date; `CLAUDE.md`'s menu node count
still read ~818 when it is 1717 (not a leak — ~740 of those are rain sprites).
Both fixed. A check cannot verify a sentence.

**Picked up at: NOTHING IS IN PROGRESS.** Tree clean, everything pushed, all
gates green at v0.6.44, leaks flat, 240 fps in a raid and 245 on every menu
backdrop. `TASKS.md` is accurate and is the work list. The two most useful
next moves are **B4, the smoker on the bench** (small, queued longest) or
**real 2D shadows** (biggest visual change left, and it kills the
flashlight-through-walls bug at the same time). **M2 — guns — still waits on
the user's explicit "go".** One open note nobody has acted on: the drain and
the underpass share a camera angle and the user has parked it deliberately.

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

*(compressed — the ritual says entries older than the newest three drop to a
few lines, and every fix below is in the repo now.)* No version bump, still
v0.6.25. **~45 unique defects fixed across 16 files.** Both gates printed PASS
throughout — second audit running. Dominant failure mode: **"fix one copy,
leave the twin"** — the same false fact repeated in another file. All of it was
wrong-FACT, never wrong-ACTION; nothing found could have destroyed data.

## 2026-08-02 — the migration was broken and both gates said PASS

*(compressed.)* No game changes. A docs audit after the user asked for the
migration and the security to be solid. **The two commands at the TOP of
`CLAUDE.md` resolved to nothing on this machine** — `godot_console` was never
on PATH — so the documented workflow was unrunnable while both gates were
green. **One doc instruction would have destroyed user data**: `DESIGN.md`
claimed smoke runs pollute a stash file under `%APPDATA%` and told sessions to
clean it up; that folder holds the user's real keybinds, resolution and
volumes, and there is no stash file. The permanent lesson — **a check cannot
verify prose** — is now its own section in `CLAUDE.md`.

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

*(compressed.)* **v0.6.15 → v0.6.25**: OVERCAST weather, a real day-arc, the
boot shader warm-up, indoor weather muffling, and the docs rebuilt around
them. Its renumbering-ORDER claim was wrong and is corrected in a later entry.
