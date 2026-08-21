#!/usr/bin/env python3
"""PreToolUse(Bash) hook: advisory routing for review and Codex delegation.

Two nudges, never blocking:

1. `git push` -> remind that an adversarial review belongs BEFORE the push.
2. bare `codex ...` -> remind that Codex delegation goes through delegate,
   which is the only path that knows about the spend cap and the fallback.

Advisory by design. The main agent keeps judgement; the user's explicit
instructions always win.

Filename is historical (it once pointed at codex:codex-rescue). The path is
referenced from ~/.claude/settings.json, so it is kept rather than renamed.
"""
import json
import re
import sys

REVIEW = (
    "Review gate (advisory): this push ships work. Unless it is trivial "
    "(docs/typo/config), an adversarial review should run BEFORE the push — "
    "afterwards it becomes a follow-up PR.\n"
    "Run `delegate review <base-ref>`. It tries Codex first and exits 3 "
    "telling you to dispatch the `reviewer` agent when Codex is spend-capped.\n"
    "Dispatch `reviewer` as a FRESH agent, never a fork — inheriting this "
    "conversation's context inherits its blind spots. Give it the repo path, the "
    "command that shows the diff, and what the change claims to do.\n"
    "Do NOT tell it to skip what you already verified: a happy path checked by a "
    "test that mocks the broken thing is exactly where a shared blind spot hides."
)

CODEX = (
    "Codex routing (advisory): call `delegate` instead of `codex` directly.\n"
    "Codex reports a spend cap only on stderr and exits non-zero, so a bare call "
    "is easy to misread as success. `delegate` does the detection, caches a cap "
    "for 24h, logs which engine served each run, and falls back to the `reviewer` "
    "agent. `delegate status` shows the current route."
)


CODEX_CALL = re.compile(r"(?:^|[;&|]\s*|\$\(\s*|`\s*)codex\b")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("tool_name") != "Bash":
        return

    command = (data.get("tool_input") or {}).get("command", "")
    notes = []
    if "git push" in command:
        notes.append(REVIEW)
    # Bash is the real bypass around the router; the plugin subagent only has Bash.
    # Match `codex` only in COMMAND position — a bare substring also matches prose
    # inside echo/grep arguments and paths like .../openai-codex/codex/1.0.4.
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


main()
sys.exit(0)
