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

**Shipped:** No game changes. A docs-and-memory session. Built this file.
Added `--checkdocs` to the harness and wired it into `--smoke` so a stale
handoff is a red build instead of something the next session discovers
hours in. Fixed three stale claims in `CLAUDE.md`: a GitHub tag range frozen
at "v0.1.0…v0.2.0" for twenty-odd releases, a perf baseline claiming ~34k
nodes against the real ~7.9k, and a missing mention of `scripts/ui_state.gd`
(the `Ui` autoload). Also added a **SAFETY & TRUST** section to `CLAUDE.md`
at the user's request — prompt injection, reversibility, and why the
permission classifier is kept. Then, when they asked for actual protection
rather than documentation, `--checksec`: six enforced invariants (remote
unchanged, zero network calls, vetted python imports only, shelling out
confined to `harness.gd` and only to git, no tracked secrets, exactly the
eight known autoloads). It runs inside `--smoke`.

**The user's words:** *"im scared something might get lost or break because
we just did a whole renumbering thing"* — and they asked for migration to be
*"a chain of migrations that we will never forget"*. That fear was
well-placed; see below. Also confirmed they want the smoke-test version
check: *"yes i do want to add a check to the smoke test that compares the
version CLAUDE.md claims against the actual newest git tag"*.

They then asked, carefully and in sequence, whether the commands they were
being handed were *"arbitrary, risky and can result in data loss, system
corruption, or data exfiltration"*, then *"can someone do that to me?"*, then
*"couldnt you tell if something like that was going on before anything
becomes bad?"* — and finished with *"add this to .md make sure every chat
will always know that"*. They are security-aware and they audit what they
run. **Hand them short, legible commands and explain the undo.** On
permissions they declined full bypass: *"auto is fine, i can run a couple
commands whenever you need me to."*

**Learned:**
- **The renumbering left one tag on the wrong commit — now FIXED.**
  `v0.6.14` had been left on `f8e83ae` ("renumber the whole release history,
  evenly", the bookkeeping commit) instead of `9c79c9b`, the release it
  marks — almost certainly the renumbering script tagging its last entry
  against HEAD rather than the recorded sha. 89 of the 90 were correct. The
  user ran `git tag -f` + a tag force-push; local and remote both point at
  `9c79c9b` now and `--checkdocs` is green.
- **Permissions.** The user's global settings run `permissions.defaultMode:
  "auto"`, so a classifier judges each command and blocks force operations —
  that is why the tag fix needed their hand. They asked to widen it, so
  `.claude/settings.json` now carries an allowlist for git, python, godot and
  skills. **Untested:** it was written mid-session and project settings load
  at startup, so a force op was still blocked afterwards. First session after
  this: try `git tag -f` on a throwaway tag. If it is still blocked, the auto
  classifier overrides allow-rules and only
  `defaultMode: "bypassPermissions"` will change it — the user's call, they
  deliberately picked the narrower option over full bypass.
- **A check that only ever passes is decoration.** Every one of the six
  `--checksec` invariants was verified to actually FIRE by planting a real
  violation of it — a `HTTPRequest` in a .gd, an `import boto3`, an
  `OS.execute` outside the harness, a fake AWS key, a bogus autoload in
  `project.godot`, a second git remote. All six were caught, then removed.
  **Do this for any check added later.** Writing it and seeing green proves
  nothing.
- **`--checksec` scans uncommitted files too** (`ls-files --cached --others
  --exclude-standard`). Tracked-only would make a freshly written backdoor
  invisible until it was already committed.
- **The parse-error-looks-like-a-hang trap bit again, exactly as CLAUDE.md
  warns.** `_sec_tracked_files` returned untyped `Array`, so every downstream
  `var x := rel.to_lower()` failed to infer — a parse error, the autoload
  failed to load, and the run sat on the menu for three minutes looking slow.
  A `grep` on the output hid the cause, because the error is at the HEAD and
  the verdict only ever prints at the END. **Return typed arrays, and read
  the head of the raw log.**
- **Rejected on purpose: scanning repo files for injection-shaped phrases.**
  The realistic injection surface is content from OUTSIDE the repo, which a
  repo scan cannot see, and the phrases false-positive against LORE.md. It
  would have looked like protection while providing none.
- **Commit messages still carry pre-renumber version numbers.** Only tags
  moved. `git log` shows "v0.6.76: menu housekeeping" on a commit whose tag
  is `v0.6.13`+. **Never read a version out of a commit subject** for
  anything before `f8e83ae` — use `git tag --points-at`.
- `--checkdocs` now verifies all 90 renumbered tags against
  `docs/version_renumber_2026-08-02/tag_commits.json`, so this class of
  damage can never go unnoticed again.

**Picked up at (previous session):** The smoker on the bench (TASKS.md B4),
then the LZ green smoke (B4b) — both unchanged from that session's plan. Nothing is
blocked; `--checkdocs` and `--smoke` are green.

---

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
