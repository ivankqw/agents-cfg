# agent-config

Portable agent configuration for Claude Code and Codex. Method only — no employer names, no
hostnames, no secrets. Clone this at a new machine or a new job and the workflows stay the same.

## Install

```bash
git clone <this repo> ~/agents-cfg
export CONTEXT7_API_KEY=...        # optional; the MCP step skips servers whose key is unset
~/agents-cfg/install.sh
```

The script is idempotent. Re-run it after you add a skill or edit `mcp/servers.json`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | The portable conventions. Both harnesses read this content. |
| `CLAUDE.md` | One line: `@AGENTS.md`. |
| `skills/` | Curated, employer-neutral skills. |
| `agents/reviewer.md` | Independent adversarial reviewer. `model: opus`, `effort: max`. |
| `hooks/` | Advisory PreToolUse hooks. |
| `bin/delegate` | Routes review work to Codex while it has credit, else to the `reviewer` agent. |
| `settings/settings.template.json` | Starting point. Merge into `~/.claude/settings.json` by hand. |
| `mcp/servers.json` | Server names and URLs. Keys come from the environment. |
| `MACHINE-NOTES.md` | Per-machine setup that does not belong in conventions. |

## How the two harnesses read one source

Claude Code reads `CLAUDE.md` and expands `@imports`, so `install.sh` writes
`~/.claude/CLAUDE.md` with one import per layer. Edits to `AGENTS.md` are live.

Codex reads `AGENTS.md`. Import support is not guaranteed, so `install.sh` concatenates the layers
into `~/AGENTS.md`. **Re-run `install.sh` after editing conventions**, or Codex reads a stale copy.

## The private layer

`install.sh` layers `~/agents-cfg-private` (override with `$PRIVATE_CONFIG`) on top if it exists:
its skills, its `bin/`, and its `AGENTS.md`. At a new job, do not clone it. Everything here still
works; only the employer specifics are absent.

## Rule for what goes where

Ask: would this sentence still be true at a different company? If yes it belongs here. If it names a
repo, a remote, a warehouse, a tracker workspace, or a hostname, it belongs in the private layer.
