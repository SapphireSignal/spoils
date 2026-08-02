"""Autosave — append every user message to docs/sessions/<date>.md as it is sent.

Registered as a UserPromptSubmit hook in .claude/settings.json. The point is
that a chat which dies mid-session still leaves the user's own words on disk:
CLAUDE.md's rule is "quote the user verbatim, paraphrase is where intent
dies", and this makes that automatic instead of dependent on a session
remembering to do it.

THIS IS THE SAFETY NET, NOT THE HANDOFF. It is raw, complete and unreadable
by design. HANDOFF.md stays the curated memory a new session actually reads.

THREE HARD RULES. Each is a real failure mode, not style:

  1. NEVER WRITE TO STDOUT. On UserPromptSubmit -- uniquely among hook events
     -- anything a hook prints to stdout is injected into Claude's context as
     though the user had typed it. One stray print() here would silently
     prepend text to every message the user sends, compounding every turn.

  2. ALWAYS EXIT 0. Exit code 2 on this event BLOCKS the prompt and ERASES
     what the user typed. Nothing this script does is worth losing a typed
     message over, so every path -- including every failure path -- ends at
     exit 0. That is why the body is wrapped and the exception is swallowed.

  3. UTF-8, newline="\\n". PowerShell 5.1 defaults would mangle non-ASCII and
     double the carriage returns; this project has been bitten by both, and
     with core.autocrlf=true a doubled CR means a permanently dirty tree.

Imports are limited to the --checksec vetted list (see SEC_PY_IMPORTS in
scripts/harness.gd). `datetime` is deliberately NOT used -- `time` is already
vetted, and widening a supply-chain allowlist for convenience is exactly the
decision that list exists to stop.
"""

import json
import os
import sys
import time

HEADER = """# session log — %s

Raw autosave. Every message the user sent, appended verbatim as it was sent.

**This is the safety net, not the handoff.** Nothing here is edited,
summarised or trusted as a conclusion — `HANDOFF.md` is the curated memory a
new session reads. Come here when the handoff turns out to be wrong.

"""


def main():
    raw = sys.stdin.buffer.read()
    if not raw:
        return
    data = json.loads(raw.decode("utf-8", errors="replace"))

    # The shipped binary emits "prompt"; the published docs say "user_prompt".
    # Read both, so a rename in either direction cannot silently empty the log
    # while still looking like it works.
    text = data.get("prompt") or data.get("user_prompt") or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return

    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    out_dir = os.path.join(root, "docs", "sessions")
    os.makedirs(out_dir, exist_ok=True)

    day = time.strftime("%Y-%m-%d")
    path = os.path.join(out_dir, day + ".md")
    session = str(data.get("session_id") or "unknown")[:8]

    fresh = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        if fresh:
            f.write(HEADER % day)
        f.write("## %s · session %s\n\n%s\n\n" % (time.strftime("%H:%M:%S"),
                                                  session, text))


try:
    main()
except Exception:
    # A broken autosave must never cost the user a message. Staying silent is
    # the correct behaviour here: stderr would print a hook-error notice on
    # every single prompt, and stdout would poison the context.
    pass

sys.exit(0)
