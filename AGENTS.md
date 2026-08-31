# agents-cfg

My agent setup for Claude Code and Codex: working conventions, a few skills I wrote, an adversarial
code reviewer, an advisory pre-push hook, and a script that routes review work.

If someone pointed you at this repo, install it on this machine. Read this file, then run the steps
under **Bootstrap**.

## What the install does

`install.sh` creates symlinks and copies nothing, so an edit to this repo takes effect at once.

| It writes | Purpose |
|---|---|
| `~/.claude/skills/*` | links to skills, both from here and from `~/.agents/skills` |
| `~/.claude/agents/*` | links to `agents/` |
| `~/.claude/hooks/*` | links to `hooks/` |
| `~/.agents/skills/*` | links repo, private, and pinned pstack skills beside installer-managed skills |
| `~/.codex/prompts/*` | links pinned pstack command stubs |
| `~/.codex/hooks/*` | links advisory hooks |
| `~/.local/bin/*` | links to `bin/`, putting `delegate` on the PATH |
| `~/skills-lock.json` | link to the lockfile, where the `skills` CLI looks for it |
| `~/.claude/CLAUDE.md` | one `@import` per layer, so Claude Code loads the conventions |
| `~/AGENTS.md` | the same conventions concatenated, because Codex reads `AGENTS.md` |
| `~/.codex/AGENTS.md` | link to `~/AGENTS.md` |
| `~/.codex/pstack-models.md` | link to the confirmed Codex pstack model sheet |

It writes no credential. It leaves both harness settings files alone. Merge the files in `settings/`
by hand. The install reports each missing Codex setting.

## Prerequisites

- Linux or macOS. `install.sh` refuses anything else.
- `git`, `python3`, `bash`. The bash 3.2 that ships with macOS is enough.
- `node` with `npx`, for third-party skills.
- `bun`, for the pstack `watch-pr` and `orch` tools.

## Bootstrap

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/bootstrap.sh               # pins pstack, restores skills, and links the setup
```

`bootstrap.sh` is the reproducible path. It checks out the recorded pstack revision under
`~/.local/share/agent-plugins`. It stops if that checkout has local changes.

Matt Pocock and other third-party skills stay in `~/.agents/skills`. Codex discovers that directory
directly. Claude receives links to the same skills. Do not copy these skills into `.codex/skills`.

Bootstrap runs the skills CLI from `~`. This location makes the CLI install into `~/.agents/skills`.

Put `~/.local/bin` on your PATH if it is not there:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Check the install

Conventions that fail to load are the most common problem, and nothing announces it. Test for that:

```bash
cd /tmp && claude -p "Do not use tools. If your instructions contain 'A virtue cannot be graded',
write LOADED, else write MISSING."
```

`MISSING` means `~/.claude/CLAUDE.md` did not import the conventions. Run `./install.sh` again.

Start the next Codex session from `/tmp`, where no project `AGENTS.md` applies. Ask whether its
instructions contain `A virtue cannot be graded`. Then ask it for the pstack `bug-fix` model and the
`setup-pstack` skill. Treat any missing item as an install failure.

Check `~/.codex/config.toml` after install reports missing settings. Merge
`settings/codex.config.template.toml`, then restart Codex. The fragment enables hooks, pstack, and
multi-agent pstack panels. It does not replace user settings.

## Update

```bash
cd ~/agents-cfg && git pull     # conventions and my own skills take effect at once
npx skills update               # move third-party skills to their latest versions
```

`npx skills update` refreshes the installed skills and rewrites the CLI's own global lockfile at
`~/.agents/.skill-lock.json`. It does not touch this repo, so `skills-lock.json` here goes stale
without telling you. Refresh it when you want to keep an update:

```bash
cd ~/agents-cfg
python3 - <<'PY'
import json, pathlib
src = json.load(open(pathlib.Path.home() / ".agents/.skill-lock.json"))
src["skills"] = {k: v for k, v in src["skills"].items() if "larksuite" not in v.get("sourceUrl", "")}
pathlib.Path("skills-lock.json").write_text(json.dumps(src, indent=2) + "\n")
PY
git diff skills-lock.json      # read the pin changes before you keep them
```

Drop the filter line to record every installed skill. Keep the two files in step on purpose: a new
machine rebuilds from this lockfile, so it should hold the set I want rather than whatever happens
to be installed.

## Layout

| Path | Holds |
|---|---|
| `conventions/AGENTS.md` | The conventions. This is the payload the install links. |
| `skills/` | Skills I wrote. Third-party skills are declared, never copied in. |
| `agents/reviewer.md` | Independent adversarial reviewer. `model: opus`, `effort: max`. |
| `hooks/` | Advisory `PreToolUse` hooks. They never block. |
| `bin/delegate` | Routes review work to Codex while it has credit, else to the `reviewer` agent. |
| `skills-lock.json` | Which third-party skills to install, and at which commit. |
| `pstack-revision.txt` | The exact pstack plugin commit to install. |
| `settings/settings.template.json` | A starting point. Merge by hand. |
| `settings/codex.config.template.toml` | Codex settings fragment. Merge by hand. |
| `MACHINE-NOTES.md` | Per-machine setup. Not conventions. |
| `configs/` | Named model and effort assignments per role. Pick one per stretch of work. |
| `templates/` | Patterns to build from, such as a project worktree helper. |
| `MAINTAINING.md` | How to change this repo: add a skill, unlock one, edit a convention, add a hook. |

## Skills that call out to tools

Some skills drive a CLI on top of the prompt. None of them need an `npm install`; they need `node`,
`npx`, and network access.

| Skill | What it runs | Notes |
|---|---|---|
| `impeccable` | its own scripts under `scripts/`, on bare `node` | Run `node <skill-dir>/scripts/context.mjs` once per session, as the skill instructs. `scripts/pin.mjs` writes `$<command>` shortcuts into the project. |
| `improve-react` | `npx react-doctor@latest --json` | Fetched at run time, so the machine needs network. |
| `bin/delegate` | the `codex` CLI | Falls back to the `reviewer` agent when Codex has no credit. |

`impeccable` ships its scripts inside the skill folder, so they arrive with the skill and stay in
step with it. Do not vendor copies elsewhere.

## Optional complexity and Ponytail skills

Bootstrap restores these explicit-use skills from immutable upstream commit archives:

| Source | Revision | Skills |
|---|---|---|
| `saurabhkumar8112/cyclomatic-complexity-skill` | `567886f485063c5f5f94503d5712ef75cbcbbd94` | `cyclomatic-complexity` |
| `DietrichGebert/ponytail` | `2ed6c52c9d7e5e56942508591085fd45dea277d3` | `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help` |

The repository-owned `ponytail` skill has an explicit-request-only trigger. It keeps pstack routing
as the default. It does not copy the broad upstream `ponytail` skill.

Only the five report skill directories come from Ponytail. The install excludes commands, hooks,
plugin manifests, the MCP server, benchmark scripts, publish scripts, runtime configuration, and
persistent state. It does not enable the upstream `full` mode.

Install rewrites the imported frontmatter descriptions after each restore or update, so Codex sees
explicit-request triggers only.

Treat complexity metrics as review guidance. Project limits and measured behavior take precedence
over generic thresholds. Existing acceptance, verification, security, accessibility, and operator
boundaries take precedence over simplification advice.

Ponytail benchmark figures are sourced upstream. They are not measurements of this repository.

## Codex and pstack

Codex loads pstack skills from `~/.agents/skills`. Slash-command stubs load from `~/.codex/prompts`.
The local marketplace points at the pinned checkout. All three paths use the same plugin revision.
When a third-party parent has the same name, install adds pstack as a same-name child. This preserves
the parent skill and exposes the pstack namespaced skill.

Codex cannot expand Claude `@imports`. The install appends `configs/pstack-codex.md` while it builds
`~/AGENTS.md`. It also links the model sheet into `~/.codex` for direct examination.

The harness direction is not symmetric. Claude can call the Codex reviewer plugin. Codex cannot call
the configured Claude reviewer plugin. Use `single-vendor` for Codex-led work. Use `deep` only when
Claude owns the session.

## The private layer

`install.sh` layers a second repo on top when it finds one, at `~/agents-cfg-private` or wherever
`$PRIVATE_CONFIG` points. Employer conventions, private skills and domain memory belong there.

Keep this repo clean of all that. If a line would stop being true somewhere else, it belongs in the
private layer.
