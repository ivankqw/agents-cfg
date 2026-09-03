# Keep upstream skills in sync

I want the same upstream skills on each machine. The current lockfile mixes that intent with local
state, so two healthy machines can produce different files.

Tim Penkin described the catalog pattern in
[One Catalog, Every Machine](https://www.penkin.me/ai/development/tools/dotfiles/2026/07/30/syncing-claude-skills-across-machines.html).
The design below adapts that pattern to this repository.

## Why the lockfile drifts

The `skills` CLI writes its live lockfile at `~/.agents/.skill-lock.json`. The file records the
source fields needed to restore a skill. It records machine state.

The machine state includes installation timestamps, update timestamps, skill-folder hashes, and UI
choices such as `lastSelectedAgents`. A second machine can install the same source catalog at another
time and produce a different lockfile. A raw file copy creates churn without changing the set of
skills that the operator wants.

The committed `skills-lock.json` has the same mixed shape. `README.md` and `MAINTAINING.md`
tell the operator to copy and filter the live file by hand. That process can miss an update
or retain machine state.

## The planned catalog

The sibling implementation lane plans to turn the committed file into a normalized catalog. Each
skill entry will keep these fields:

- `source`
- `sourceType`
- `sourceUrl`
- `skillPath`

The catalog will omit timestamps, UI state, and per-machine hashes. It will describe the requested
upstream skills rather than one machine's installation history.

## The planned sync command

The sibling lane plans to add `bin/skills-sync`. This branch documents the contract and does not
provide the command.

The planned command will run these steps in order:

1. Pull the portable-layer repository.
2. Install catalogued skills that the machine lacks.
3. Update the installed upstream skills.
4. Normalize the live lockfile into the committed catalog fields.
5. Validate that each catalogued skill folder exists under `~/.agents/skills`.
6. Commit catalog changes with the hostname when the normalized catalog changed.

The command must stop when a catalogued folder is missing after installation. A missing folder means
the catalog cannot restore the declared setup.

The commit hostname will identify the machine that observed the upstream change. The catalog content
will remain portable because it excludes host paths and local state.

## The planned schedule

The sibling lane plans to supply a job that runs once a day. macOS will use a `launchd` entry. Linux
will use a `cron` entry.

The scheduled job will call `bin/skills-sync` from the repository clone. It will create a commit
when normalized catalog content changes. Operators can review and push that commit through the
usual Git workflow.

## Use the current update path

Until `bin/skills-sync` lands, use the existing commands:

```bash
cd ~/agents-cfg
git pull --ff-only
./bin/skills-update
./install.sh
```

To keep a live lockfile change before `bin/skills-sync` lands, follow the copy-and-filter recipe in
`MAINTAINING.md`. Read the diff before you commit it. The planned command will replace that manual
normalization step.
