# agents-cfg — point your agent here

This repository is a portable agent configuration for **Claude Code** and **Codex**. It carries
working conventions, a small set of hand-written skills, an adversarial code-review agent, an
advisory pre-push hook, and a review-routing script.

If you are an agent and someone pointed you at this repository, your job is to install it on this
machine. Read this file, then run the steps in **Bootstrap**.

## What installing does

`install.sh` creates symlinks. It copies nothing into place, so an update to this repo takes effect
at once.

| It writes | Purpose |
|---|---|
| `~/.claude/skills/*` | links to skills, both from here and from `~/.agents/skills` |
| `~/.claude/agents/*` | links to `agents/` |
| `~/.claude/hooks/*` | links to `hooks/` |
| `~/.local/bin/*` | links to `bin/`, so `delegate` is on the PATH |
| `~/.claude/CLAUDE.md` | one `@import` per layer, so Claude Code loads the conventions |
| `~/AGENTS.md` | the same conventions concatenated, because Codex reads `AGENTS.md` |
| `~/.codex/AGENTS.md` | link to `~/AGENTS.md` |

It never writes a credential. It never touches `~/.claude/settings.json` — merge
`settings/settings.template.json` by hand.

## Prerequisites

- Linux or macOS. `install.sh` refuses any other system.
- `git`, `python3`, and `bash`. macOS bash 3.2 is enough.
- `node` with `npx`, for third-party skills.

## Bootstrap

Run these four steps in order.

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/install.sh                 # links, and puts skills-lock.json at ~/
cd ~ && npx skills experimental_install # restores third-party skills at their pinned versions
```

The order matters: `install.sh` places `~/skills-lock.json`, and the `skills` command reads that
file from the directory you run it in. Run it from `~` so the skills land in `~/.agents/skills`.

Make sure `~/.local/bin` is on your PATH. Add this line to your shell profile if it is absent:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Verify the install

Conventions that do not load are the most common failure, and it is silent. Check for them:

```bash
cd /tmp && claude -p "Do not use tools. If your instructions contain 'A virtue cannot be graded',
write LOADED, else write MISSING."
```

`MISSING` means `~/.claude/CLAUDE.md` did not import the conventions. Run `./install.sh` again.

## Update

```bash
cd ~/agents-cfg && git pull     # conventions and own skills take effect at once
npx skills update               # refresh third-party skills to their latest versions
```

`npx skills update` refreshes the **installed** skills and rewrites the CLI's own global lockfile at
`~/.agents/.skill-lock.json`. It does **not** touch this repo, so `skills-lock.json` here goes stale
until you refresh it on purpose. Do that after an update you want to keep:

```bash
cd ~/agents-cfg
python3 - <<'EOF'
import json, pathlib
src = json.load(open(pathlib.Path.home() / ".agents/.skill-lock.json"))
src["skills"] = {k: v for k, v in src["skills"].items() if "larksuite" not in v.get("sourceUrl", "")}
pathlib.Path("skills-lock.json").write_text(json.dumps(src, indent=2) + "\n")
EOF
git diff skills-lock.json      # read the pin changes before keeping them
```

Drop the filter line if you want every installed skill in the lockfile. Keeping the two files in
step is a deliberate act: the lockfile is what a new machine rebuilds from, so it should reflect the
set you actually want, not everything that happens to be installed.

## Layout

| Path | Holds |
|---|---|
| `conventions/AGENTS.md` | The portable conventions. This is the payload that gets linked. |
| `skills/` | Skills written here. Third-party skills are declared, never vendored. |
| `agents/reviewer.md` | Independent adversarial reviewer. `model: opus`, `effort: max`. |
| `hooks/` | Advisory `PreToolUse` hooks. They never block. |
| `bin/delegate` | Routes review work to Codex while it has credit, else to the `reviewer` agent. |
| `skills-lock.json` | Which third-party skills to install, and at which commit. Read by `npx skills`. |
| `settings/settings.template.json` | A starting point. Merge by hand. |
| `MACHINE-NOTES.md` | Per-machine setup. Not conventions. |

## The private layer

`install.sh` layers a second repository on top if it exists, at `~/agents-cfg-private` or wherever
`$PRIVATE_CONFIG` points. Employer-specific conventions, private skills and domain memory belong
there, not here.

Nothing in this repository names an employer, a host, or a person. Keep it that way: if a line would
stop being true at a different company, it belongs in the private layer.
