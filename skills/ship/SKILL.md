---
name: ship
description: >-
  Run a piece of work from framing to draft PR, calling the right skill at each phase. Stress the plan, apply craft gates to UI, clean the diff, then review it twice. Use when starting issue-backed work, when asked to ship a change or open a PR, or when finishing a branch left in flight.
---

# Ship

`conventions/AGENTS.md` holds the rules: branch naming, PR shape, the verification bar. Read it.
This file holds the order, the skill that owns each phase, and the bar for calling a phase done.

## The flow

| Phase | Skill | Who starts it |
|---|---|---|
| Frame a large or foggy effort | `wayfinder` | this skill invokes it |
| Stress the plan before building | `grilling` | this skill invokes it |
| Ground plan claims in current docs | `grill-with-docs` | this skill invokes it |
| Build UI | `impeccable` and `improve-react`, plus any project skill for the surface | this skill invokes them |
| Judge a frontend change | `dogfood-local` | this skill invokes it |
| Clean the diff | `deslop` for code, `stop-slop` for prose | this skill invokes them |
| Review | `delegate review` and `/code-review` | this skill runs both |
| Lost the thread | `wait-what` | **you** type `/wait-what` |

`wayfinder`, `grill-with-docs` and `improve-codebase-architecture` ship from upstream with
`disable-model-invocation: true`, which blocks a skill from calling them. `install.sh` strips that
flag for the names in `skills-unlock.txt`. `npx skills update` puts it back, so re-run `install.sh`
after an update or these phases go quiet.

`wait-what` stays yours. It only means something when a human says the last message did not land.

## 1. Frame

Read the issue for constraints, project context, and any PR already linked. Create the worktree with
`wt create <name> <source-ref>`.

If the work is large, or spans more sessions than one context holds, invoke `wayfinder` to map it
into decision tickets before building anything.

**Done when** you can state the acceptance criterion in one sentence, and the worktree has its
secrets.

## 2. Stress the plan

Invoke `grilling` on the approach before writing code. A plan that survives questioning costs less
than a rewrite. Skip this for mechanical work with one obvious shape.

If the plan rests on how a library or service behaves, invoke `grill-with-docs` instead, so the
claims get checked against current documentation as the interview runs.

**Done when** the decisions are settled, or the open questions are written down and the user has
answered the ones that block you.

## 3. Build

Build the change. Keep each commit focused on one thing.

For any UI work, invoke `impeccable` first, then `improve-react` for the React-level faults it does
not look at. Run both on **each pass**, not once at the end. If the project ships its own UI skill,
invoke that too: it carries the design system, the house rules, and the verification loop.

**Done when** the change is whole. Nothing scaffolded, nothing left for later.

## 4. Verify

Run the cheapest check that exercises the change. Paste the real command and its real output.

**Done when** every claim has its command and output pasted, every behaviour you removed or
tightened is listed, and each changed interface has its downstream callers named, including callers
outside the repo.

## 4b. Dogfood it, before it becomes a PR

For any change with a rendered surface, invoke `dogfood-local`: run the app locally, drive the actual
path a user takes, and judge it there.

Shipping a PR per look and deciding on prod is the failure this exists to prevent. It makes every
visual judgement cost a merge and a deploy, and it makes the judgement after the change is already
irreversible.

**Done when** you have used the change rather than read its diff, and any fix it prompted has been
through the phase 3 gate again.

## 5. Clean the diff

Invoke `deslop` on the code. Invoke `stop-slop` on any prose you are shipping: a README, a PR body,
an issue comment.

**Done when** the diff carries no leftover scaffolding, and the prose reads as yours.

## 6. Review, two lanes

Run both. They overlap almost nowhere, so one passing says nothing about the other.

- `delegate review <base-ref>` for defects and test quality. Exit 3 means Codex is capped: dispatch
  the `reviewer` agent fresh, with the repo path and the diff command it prints.
- `/code-review` since the same base, for standards and faithfulness to the spec.

**Done when** every finding is fixed in this branch or refuted in writing with evidence.

## 7. Push and open a draft PR

Check `git status --short --branch`, run `git diff --check`, rebase on the default branch if you have
drifted. Push, then open the PR as a draft with the issue id in the title and the four body sections
from the conventions.

**Done when** the draft PR exists and its body carries those sections.

## 8. Report evidence

Comment on the issue: what changed, what is proven and by which command, what is still unverified,
the next step, and the commands to resume.

**Done when** the comment would let a fresh session pick the work up without the transcript.

## Stop and ask when

- The issue carries no acceptance criterion and no runnable verification.
- The right fix belongs to another implementer. Deliver the diagnosis and an ADR-shaped issue.
- A review finding implies a design change rather than a patch. Surface it first.
