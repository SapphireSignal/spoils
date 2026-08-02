# Version renumbering — 2026-08-02

The whole release history was re-spread evenly at the user's request:
0.1–0.5 had gone by in a handful of releases while 0.6 ran to 76 patches.
All 90 releases became **15 per minor line, v0.1.0 → v0.6.14**.

**Commits were never rewritten. Only tag names moved.** Every new tag
points at exactly the commit its old name pointed at.

- `old_to_new.json` — the mapping, `{"v0.6.76": "v0.6.14", ...}`
- `tag_commits.json` — each old tag with its commit sha and new name
- `old_tag_list.txt` — the tag list as it was before

These are kept so the renumbering can be undone exactly. They are also
why any version number quoted in a chat log from before this date is
wrong — check the mapping rather than trusting the transcript.
