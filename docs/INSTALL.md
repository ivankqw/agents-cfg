# Install agents-cfg

Use this guide to put the portable layer on a fresh Linux or macOS machine. The bootstrap path pins
pstack, restores upstream skills, and runs the installer.

## Prepare the machine

Install these commands first:

- `git`
- `python3`
- `bash`
- `node` with `npx`

Install `bun` if you use the pstack `watch-pr` or `orch` tools. `install.sh` warns when `bun` is
absent and continues without those tools.

Put `~/.local/bin` on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add the same line to your shell profile if a new terminal loses the setting.

## Bootstrap the portable layer

Run the remote bootstrap for the shortest setup:

```bash
curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
```

Use a clone when you want to read the scripts before you run them:

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/bootstrap.sh
```

`bootstrap.sh` refuses unsupported operating systems and missing prerequisites. It refuses a
pstack checkout with local changes. Fix the reported condition and repeat the command.

The bootstrap script uses `~/agents-cfg` unless `AGENTS_CFG_DIR` names another directory. It clones
the pstack source named by `PSTACK_REPO` and checks out the commit in `pstack-revision.txt`.

## Add a private layer

Keep employer and domain instructions in a separate repository. Put that repository at
`~/agents-cfg-private`, or set `PRIVATE_CONFIG` to its path before bootstrap:

```bash
export PRIVATE_CONFIG="$HOME/path/to/private-agent-config"
~/agents-cfg/bootstrap.sh
```

`install.sh` reads `AGENTS.md`, `skills/`, and `bin/` from the private layer when those paths exist.
Do not put credentials in either repository.

## Merge harness settings

The installer leaves harness settings under your control. Merge these templates by hand:

- `settings/settings.template.json` into `~/.claude/settings.json`
- `settings/codex.config.template.toml` into `~/.codex/config.toml`

Replace `HOME_PATH` in the Codex template with your home directory. Restart the harness after you
change its settings.

## Verify Claude Code

Run the canary outside any project:

```bash
cd /tmp && claude -p "Do not use tools. If your instructions contain 'A virtue cannot be graded',
write LOADED, else write MISSING."
```

The expected output is:

```text
LOADED
```

`MISSING` means Claude Code did not load `~/.claude/CLAUDE.md`. Run `~/agents-cfg/install.sh` and
repeat the canary.

## Verify Codex

Start a new Codex session from `/tmp`. Ask whether its instructions contain `A virtue cannot be
graded`. Ask for the pstack `bug-fix` model and the `setup-pstack` skill.

Treat a missing phrase, model, or skill as an install failure. Run `~/agents-cfg/install.sh` and read
its Codex settings report. Merge any missing setting from
`settings/codex.config.template.toml`, restart Codex, and repeat the check.

## Update the setup

Sync the portable layer and upstream skills, then refresh the generated files and links:

```bash
cd ~/agents-cfg
bin/skills-sync run
./install.sh
```

`bin/skills-sync run` pulls the repository, restores missing catalogued skills, and updates installed
upstream skills. It normalizes and validates `skills-catalog.json`, commits a change, and pushes it.
If a concurrent sync wins the push race, the command rebuilds its generated catalog state and
retries the push once. The final install refreshes links and regenerates the Codex instruction file.

Use `bin/skills-sync run --no-push` when you want to review the generated commit before you push it.
See [Keep upstream skills in sync](SYNC.md) for removal safeguards, ignored skills, lockfile
locations, and schedule generation.

Run both verification checks after an update.

## Uninstall the setup

The repository has no uninstall script. Remove links one at a time so you do not delete a file that
you own.

First, list links created under the harness and shared directories:

```bash
find "$HOME/.claude" "$HOME/.codex" "$HOME/.agents/skills" "$HOME/.local/bin" \
  -type l -print
```

Examine each target with `readlink`:

```bash
readlink <link-path>
```

Use `unlink <link-path>` for links that point into `~/agents-cfg`, the private layer, or the pinned
pstack checkout. Keep regular files and unrelated links.

Examine `~/.claude/CLAUDE.md` and `~/AGENTS.md`. Remove them if they contain the generated imports or
header from `install.sh`. The installer does not edit `~/.claude/settings.json` or
`~/.codex/config.toml`, so remove their merged entries by hand.

Delete the repository and pstack checkout after no remaining link points into them.
