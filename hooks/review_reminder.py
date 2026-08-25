#!/usr/bin/env python3
"""PreToolUse(Bash) hook: two advisory nudges, neither of which blocks.

1. `git push`  -> a review belongs before the push, not after.
2. bare `codex` -> route Codex delegation through `delegate`, which knows about
   the spend cap and the fallback.

Both matches are command-position only. A bare substring also fires on prose
inside echo and grep arguments, and on paths like .../openai-codex/codex/1.0.4.
The match is textual, so it cannot see shell quoting: a command word inside a
quoted string still reads as command position. That is acceptable for an
advisory nudge.

Fails safe. Any unexpected input produces no output and a zero exit, because a
hook that raises turns a nudge into noise on every tool call.
"""
import json
import re
import sys

REVIEW = (
    "Review gate (advisory): this push ships work. Unless it is trivial "
    "(docs, typo, config), review it BEFORE the push. Afterwards it becomes a "
    "follow-up PR.\n"
    "Run `delegate review <base-ref>`. It tries Codex first and exits 3 telling "
    "you to dispatch the reviewer when Codex is spend-capped.\n"
    "Dispatch the reviewer as a new agent that starts with no memory of this "
    "conversation. A mechanism that shares this session's context inherits the "
    "author's blind spots along with it.\n"
    "Do NOT tell it to skip what you already verified: a happy path checked by a "
    "test that mocks the broken thing is exactly where a shared blind spot hides."
)

CODEX = (
    "Codex routing (advisory): call `delegate` instead of `codex` directly.\n"
    "Codex reports a spend cap only on stderr and exits non-zero, so a bare call "
    "is easy to misread as success. `delegate` does the detection, caches a cap "
    "for 24h, logs which engine served each run, and falls back to the reviewer. "
    "`delegate status` shows the current route."
)

CMD_POS = r"(?:^|[;&|]\s*|\$\(\s*|`\s*)"
GIT_PUSH = re.compile(CMD_POS + r"git\s+push\b")
CODEX_CALL = re.compile(CMD_POS + r"codex\b")


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("tool_name") != "Bash":
        return

    tool_input = data.get("tool_input")
    command = (tool_input if isinstance(tool_input, dict) else {}).get("command", "")
    if not isinstance(command, str):
        return

    notes = []
    if GIT_PUSH.search(command):
        notes.append(REVIEW)
    # Bash is the real bypass around the router; a delegating subagent gets Bash too.
    if CODEX_CALL.search(command) and "delegate" not in command:
        notes.append(CODEX)
    if not notes:
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n\n".join(notes),
        }
    }))


try:
    main()
except Exception:
    pass
sys.exit(0)
