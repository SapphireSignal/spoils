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
- **`--checkdocs` has a real hole, now written down honestly in CLAUDE.md:**
  it scans only 3 of 7 docs for bad paths, only sees backticked paths
  starting `scripts/ tools/ docs/ art/ assets/ scenes/`, and tests nothing
  about whether a documented COMMAND resolves.

**Then `--checkdocs` was hardened, and every part fire-tested.** It is now
five parts: (0) the docs it reads exist and are non-empty — before this,
DELETING a doc made every check scan nothing and pass silently; (1) DESIGN.md
as an **optional** version claim — state none and it never fires, state one
and it must agree, so re-adding a version is safe instead of silent rot, and
no fifth number has to be hand-bumped each release; (2) tags unchanged;
(3) the path scan widened to DESIGN.md/README.md/LORE.md and to bare
root-level `.md`/`.bat`/`.godot` names; (4) every `.exe` the docs name must
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

**Picked up at:** The
user's autosave: a prompt-submit hook appending their messages verbatim to a
docs/sessions/ folder (unbackticked deliberately — it does not exist yet, and
`--checkdocs` fired on the backticked form while this entry was being written,
which is the check doing its job). Kept **inside** `--checksec`'s scan — their
call and mine, a noisy gate beats a blind one. Then the smoker (TASKS.md B4).

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

*(Reconstructed at the start of the next session from the outgoing chat's own
summary plus the commits. First-hand for the repo facts; the user quotes are
verbatim from that transcript.)*

**Shipped:** v0.6.15 → v0.6.25 across one long session — the harness stopped
pretending (a smoke test that had been vacuous for three releases), a
readable changelog, then the whole engine-side polish layer: impact
(camera kick, hit-stop, per-sprite hit flash), quiet shader warm-up,
atmosphere (colour grade, dust motes), a fix for the grade dimming
everything, a real day-arc, sun shafts, five playtest fixes, a second tiny
font plus the safehouse move, and finally **overcast weather** (v0.6.25).
Then the whole release history was **renumbered** — 90 releases re-spread
evenly to 15 per minor line, v0.1.0 → v0.6.14. Then `CLAUDE.md` was rebuilt
from 977 lines to ~500 and `TASKS.md` rewritten against reality.

**The user's words:** on the visual direction — *"keep the base art as-is,
just use godot's visual toolkit to turn up the atmosphere"*. On the trailer —
*"were not dropping it, just putting it aside for now"*. On the renumbering:
0.1–0.5 flying past while 0.6 ground on for 76 patches *"read badly"*.

**Learned:**
- **The smoke test can be vacuous.** The door check drove the player with
  `velocity` + `move_and_slide()`, which scales by frame delta; a headless run
  is uncapped, so the player moved a fraction of a pixel and never reached the
  door. Green for three releases while testing nothing. Use `Harness._shove()`.
- **A parse error in `harness.gd` looks exactly like a hang** — the autoload
  fails, `--smoke` silently does nothing. Check the HEAD of the log.
- **A colour grade must not change brightness**; **any gradual full-screen ramp
  must dither in the shader that creates it**; **sort position and draw
  position are different things**; **never skip an rng draw in the builder**.
- **The docs had rotted badly.** `CLAUDE.md` had five stacked "version X
  shipped" blocks, the newest claiming v0.6.6 while the repo was 19 releases
  ahead. It had also pointed at the renumbering undo-map in a *session temp
  folder* that would be deleted — a dead reference for the next session. Moved
  into the repo at `docs/version_renumber_2026-08-02/`.
- **Two previous sessions had recorded false diagnoses as settled fact** — the
  door "opens roughly in place" (it had always swung a correct 90°; the wrong
  measurement was taken from the sprite centroid instead of the free end), and
  two "check this first" leads on the second floor that were both wrong (the
  real cause was draw order). This is why entry rule 4 exists.

**Picked up at:** the smoker on the bench, then the LZ green smoke.

---

## Before the chain

Everything earlier is in `CHANGELOG.md` (every release, what and why) and
`docs/version_renumber_2026-08-02/` (the release-history remap). The project
started 2026-07-31; v0.1.0 → v0.6.14 covers the first three days, and the
renumbering means **any version number quoted in a chat log from before
2026-08-02 is wrong** — check the mapping rather than trusting a transcript.

No per-session record exists before the two entries above, because this file
did not exist. That is the gap this file closes.
