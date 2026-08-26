#!/usr/bin/env python3
"""PostToolUse(Bash) hook: nudge `cleanup-crew` once a pull request is opened.

Opening a PR is the moment tracker rot becomes visible and cheap to fix: the
issue just moved state, its siblings may now reference work that landed, and
whatever the branch superseded is still fresh enough to name. Waiting for the
weekly scheduled run means the next person reads a board that disagrees with
main.

Advisory only. It prints context and never blocks, because a hook that can stop
a PR from being opened is a hook that gets disabled.

Fires on the forge CLIs rather than on `git push`, so it lands once per PR
instead of once per push. Match is command-position only: a bare substring also
fires on prose inside echo and grep arguments. The match is textual, so it
cannot see shell quoting -- a command word inside a quoted string still reads as
command position. Acceptable for an advisory nudge.

Fails safe. Any unexpected input produces no output and a zero exit, because a
hook that raises turns a nudge into noise on every tool call.
"""
import json
import re
import sys

NUDGE = (
    "Tracker hygiene (advisory): a PR just opened, so the board is now one step "
    "behind main. Run the `cleanup-crew` skill before you move on.\n"
    "Cheapest two passes, and the ones that pay off now: (1) anything this "
    "branch superseded -- reframe or cancel it while you still remember what it "
    "was for; (2) open issues whose bodies reference the work that just landed "
    "as still blocking.\n"
    "Verify each premise against the live system before closing anything. A "
    "ticket that annotates itself as invalid is usually right about its method "
    "and often wrong about its problem.\n"
    "Never close a ticket whose payload is still wanted -- rewrite it instead. "
    "And when you do close one, name where its still-wanted parts went."
)

CMD_POS = r"(?:^|[;&|]\s*|\$\(\s*|`\s*)"
# GitHub and GitLab. `gh pr create` and `glab mr create`, however they are flagged.
PR_CREATE = re.compile(
    CMD_POS + r"(?:gh\s+pr\s+create|glab\s+mr\s+create)\b"
)


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("tool_name") != "Bash":
        return

    tool_input = data.get("tool_input")
    command = (tool_input if isinstance(tool_input, dict) else {}).get("command", "")
    if not isinstance(command, str) or not PR_CREATE.search(command):
        return

    # A failed `gh pr create` is not a PR. Skip the nudge when the tool errored,
    # so a bad base ref or a dirty tree does not trigger a cleanup pass.
    response = data.get("tool_response")
    if isinstance(response, dict):
        if response.get("is_error") or response.get("interrupted"):
            return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": NUDGE,
        }
    }))


try:
    main()
except Exception:
    pass
sys.exit(0)
