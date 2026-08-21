---
name: ship
description: Take issue-backed work from worktree to draft PR — orient, implement, verify, two-lane review, push, report evidence back to Linear. Use when starting work on a Linear issue, when asked to ship a change or open a PR, or when finishing a branch left in flight.
---

# Ship

`~/work/AGENTS.md` holds the conventions — branch naming, PR body shape, review lanes,
the verification bar. Read it. This file holds the **order**, and the bar for calling
each step done.

Each step names what finishes it. A step is done when its bar is met, not when it feels
close.

## 1. Orient

Read the Linear issue for constraints, project context, and any PR already linked to it.
Create the worktree with `~/work/wt create <name> <source-ref>`.

**Done when** you can state the issue's acceptance criterion in one sentence, and the
worktree has its secrets in place.

## 2. Implement

Build the change. Keep each commit focused on one thing.

**Done when** the change is whole — nothing scaffolded, nothing left for later.

## 3. Verify

Run the cheapest check that actually exercises the change. Paste the real command and its
real output.

**Done when** every claim you intend to make has its command and output pasted, every
behaviour you removed or tightened is listed, and each changed interface has its
downstream callers named — including callers outside the repo.

## 4. Review — two lanes

Run both. They overlap almost nowhere, so one passing says nothing about the other.

- `delegate review <base-ref>` — defects and test quality. Exit 3 means Codex is
  capped: dispatch the `reviewer` agent as a fresh agent with the repo path and the diff
  command it prints.
- `/code-review` since the same base — standards, and faithfulness to the spec.

**Done when** every finding from both lanes is either fixed in this branch or refuted in
writing with evidence.

## 5. Push

Check `git status --short --branch`, run `git diff --check`, and rebase on `origin/main`
if the branch has drifted. Push the branch.

**Done when** the tree is clean, the base is current, and the branch name matches the
repo ruleset.

## 6. Open a draft PR

`gh pr create --draft --base main --head <branch> --title "<type>: <summary> (<issue-id>)"
--body-file <tmp>`. Delete the temp body file afterwards.

**Done when** the draft PR exists, its title carries the issue id, and its body carries
the four sections AGENTS.md names.

## 7. Report evidence to Linear

Comment on the issue: what changed, what is proven and by which command, what is still
unverified, the next concrete step, and the commands to resume.

**Done when** the comment would let a fresh session pick the work up without reading the
transcript.

## Stop and ask when

- The issue carries no acceptance criterion or no runnable verification — ask for one.
- The right fix belongs to another implementer — deliver the diagnosis and an ADR-shaped
  Linear issue instead of code.
- A review finding implies a design change rather than a patch — surface it first.
