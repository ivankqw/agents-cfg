# Machine notes

Setup that is specific to one machine. Not conventions — do not let these leak into `AGENTS.md`.

## WSL2 (current primary)

- Chrome integration: launch `CLAUDE_CODE_ENABLE_CFC=1 claude --chrome`. The env var bypasses the WSL
  block; the native-messaging bridge is installed on the Windows side (anthropics/claude-code#41625).
  Not available in background jobs.
- Fallback that needs no bridge: Chrome DevTools MCP against a browser started with
  `--remote-debugging-port=9222 --user-data-dir=<dedicated profile>`.
- tldraw offline serves a local HTTP API on Windows. From WSL, plain `curl` cannot reach it — use
  `/mnt/c/Windows/System32/curl.exe`, or the `tq` helper in the `tldraw-offline` skill.

## Whole-session Codex (experimental)

`claudex` runs the Claude Code harness on a GPT model through a local CLIProxyAPI. Caveats:
unofficial subscription routing, no Chrome extension integration, and Claude models error inside it.
Use plain `claude` for Claude models.

## Not portable

Absolute `/home/<user>/...` paths, plugin cache versions, and anything under `~/workspace`.
