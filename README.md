# agent-config

Portable agent configuration for Claude Code and Codex. Method only — no employer names, no
hostnames, no secrets. Clone this at a new machine or a new job and the workflows stay the same.

## Install

```bash
git clone <this repo> ~/agents-cfg
~/agents-cfg/bootstrap-skills.sh   # fetches third-party skills into ~/.agents/skills
export CONTEXT7_API_KEY=...        # optional; the MCP step skips servers whose key is unset
~/agents-cfg/install.sh            # links everything into ~/.claude
```

## Third-party skills are declared, not vendored

Most skills come from upstream repos and are managed by `npx skills`, which keeps them in
`~/.agents/skills` with a lockfile. This repo deliberately does **not** copy them in: a copy
freezes them at one commit and stops `npx skills update` from reaching them. `install.sh` symlinks
`~/.agents/skills/*` into `~/.claude/skills`, so updates flow through with no further work.

Run `npx skills update` periodically. Only skills written here live in `skills/`.

The script is idempotent. Re-run it after you add a skill or edit `mcp/servers.json`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | The portable conventions. Both harnesses read this content. |
| `CLAUDE.md` | One line: `@AGENTS.md`. |
| `skills/` | Skills written here. Third-party skills are **not** vendored — see below. |
| `bootstrap-skills.sh` | Installs the third-party skills from upstream via `npx skills`. |
| `skill-lock.reference.json` | Record of what was installed and at which commit. Reference, not consumed. |
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
