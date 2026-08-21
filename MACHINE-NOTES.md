# Machine notes

Setup that applies to one machine. These are not conventions, so keep them out of
`conventions/AGENTS.md`.

## WSL2

- Chrome: launch `CLAUDE_CODE_ENABLE_CFC=1 claude --chrome`. The env var gets past the WSL block.
  The native-messaging bridge lives on the Windows side, per anthropics/claude-code#41625.
  Background jobs cannot use it.
- Fallback with no bridge: Chrome DevTools MCP against a browser started with
  `--remote-debugging-port=9222 --user-data-dir=<dedicated profile>`.
- tldraw offline serves an HTTP API on Windows. Plain `curl` from WSL cannot reach it. Use
  `/mnt/c/Windows/System32/curl.exe`, or the `tq` helper in the `tldraw-offline` skill.

## Whole-session Codex

`claudex` runs the Claude Code harness on a GPT model through a local CLIProxyAPI. It routes an
unofficial subscription, drops Chrome extension integration, and errors on Claude models. Use plain
`claude` for those.

## What does not travel

Absolute `/home/<user>/...` paths, plugin cache versions, and anything under `~/workspace`.
