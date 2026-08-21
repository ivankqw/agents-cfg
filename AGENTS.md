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
| `~/.local/bin/*` | links to `bin/`, putting `delegate` on the PATH |
| `~/skills-lock.json` | link to the lockfile, where the `skills` CLI looks for it |
| `~/.claude/CLAUDE.md` | one `@import` per layer, so Claude Code loads the conventions |
| `~/AGENTS.md` | the same conventions concatenated, because Codex reads `AGENTS.md` |
| `~/.codex/AGENTS.md` | link to `~/AGENTS.md` |

It writes no credential, and it leaves `~/.claude/settings.json` alone. Merge
`settings/settings.template.json` by hand.

## Prerequisites

- Linux or macOS. `install.sh` refuses anything else.
- `git`, `python3`, `bash`. The bash 3.2 that ships with macOS is enough.
- `node` with `npx`, for third-party skills.

## Bootstrap

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/install.sh                 # links, and places ~/skills-lock.json
cd ~ && npx skills experimental_install # restores third-party skills at their recorded commits
```

Order matters. `install.sh` places `~/skills-lock.json`, and the `skills` CLI reads that file from
whatever directory you run it in. Run it from `~` so the skills land in `~/.agents/skills`.

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
| `settings/settings.template.json` | A starting point. Merge by hand. |
| `MACHINE-NOTES.md` | Per-machine setup. Not conventions. |

## The private layer

`install.sh` layers a second repo on top when it finds one, at `~/agents-cfg-private` or wherever
`$PRIVATE_CONFIG` points. Employer conventions, private skills and domain memory belong there.

Keep this repo clean of all that. If a line would stop being true somewhere else, it belongs in the
private layer.
