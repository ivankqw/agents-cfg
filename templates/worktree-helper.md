# Template: a worktree helper

`git worktree add` gives you a second checkout. It does not give you the files git never tracked,
and those are usually what a project needs to run: `.env`, credentials, local config, keys. A bare
worktree therefore looks correct and fails on the first command that needs one of them.

A helper closes that gap. Drive it from a manifest so one helper serves every project you touch,
rather than writing a bespoke script per repo: the logic is identical, only the file list differs.

## What it has to do

| Command | Behaviour |
|---|---|
| `create <name> <source-ref> [branch]` | Add the worktree, then copy every untracked file the project needs into it. |
| `remove <name>` | **Back the untracked files up first**, then remove the worktree. |
| `sync-secrets <name>` | Re-copy those files into a worktree that already exists. |
| `list` | Show worktrees with their branch and HEAD. |

`remove` is the one to get right. A worktree holds hand-placed files that exist nowhere else, so
deleting it without a backup destroys them. Back up first, delete second, and say where the backup
went.

## Drive it from a manifest, not from the script

Keep the file list in data next to the helper, so adding a secret does not mean editing code:

```yaml
projects:
  <project>:
    repo: /path/to/repo-or-bare-repo
    worktree_root: /path/where/worktrees/live
    secrets:
      - from: <canonical-store>/<project>.env
        to: .env
      - from: <canonical-store>/service-key.pem
        to: config/service-key.pem
```

Point `from` at one canonical store outside every worktree. Copying between worktrees spreads stale
versions and you will not notice which one is current.

## Rules worth building in

- **Refuse to overwrite.** If the target file exists and differs, stop and report it. Silent
  overwrite of a credential is expensive.
- **Report what it copied**, by name. A count tells you nothing when one file is missing.
- **Fail loudly when a source is absent.** A worktree created without its secrets looks fine until
  the first real command.
- **Never commit the files the manifest points at.** The manifest itself is ordinary config and
  belongs in git; the files it names stay untracked.

## Check it works

Create a worktree, then confirm each file in the manifest arrived and holds the expected content.
Then remove it and confirm the backup exists before you trust the helper with real work.

Employer-specific helpers, their manifest, and the canonical store belong in the private layer, not
in this repo.
