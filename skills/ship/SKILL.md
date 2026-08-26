---
name: ship
description: >-
  Runs a change from framing through to a draft pull request, calling the right
  skill at each phase. Stresses the plan, applies craft gates to any UI, cleans
  the diff, then reviews it along two independent axes. Use when starting
  issue-backed work, when asked to ship a change or open a PR, or when finishing
  a branch left in flight.
---

# Ship

`../../conventions/AGENTS.md`, at the repo root of this skill's own repository, holds the rules:
branch naming, PR shape, the verification bar. Read it. This file holds the order, the skill that
owns each phase, and the bar for calling a phase done.

## Keep moving

The phases are a route, not a set of checkpoints to report from. Walk the whole route in one go.

- **A "Done when" line is a self-check, not a stopping point.** Read it, satisfy it, start the next
  phase in the same turn. Do not summarise the phase and wait. The only pauses are the ones in
  [Stop and ask when](#stop-and-ask-when), and that list is short on purpose.
- **Blocked on one thing is not blocked.** Do every part that does not depend on the answer, then
  state the assumption you are proceeding under, or ask the one question at the point it actually
  blocks you. Never hold finished work hostage to an unanswered question.
- **Finish the batch, not the first item.** When the work is a frontier of several issues, ship one,
  then take the next without being told. The flow ends when the frontier is empty or a real blocker
  is hit, not when one PR opens.
- **A phase that does not apply is skipped, not discussed.** No dogfood phase on a change with no
  rendered surface. Note it in one clause and move on.
- **Report once, at the end.** One report covering what shipped, what is proven and by which command,
  and what is left. Not a report per phase.

## Delegate the building, keep the deciding

Run the phases as an orchestrator. Your context is for the design and the judgement; spend other
agents' context on the searching and the typing.

- **Dispatch a fresh agent for anything wide** — a grep sweep, a log trawl, a survey of many files.
  Keep the findings, not the file dumps.
- **Parallelise construction across independent files, one agent per file.** Never two agents in the
  same file. Send them in a single message so they run at once.
- **Never delegate a decision.** Scope, design, which rule is the right rule, and judging a finding
  stay with you. A subagent handed a decision returns a confident guess.
- **Re-derive any number you act on.** A figure a subagent reports is unverified until you measure it
  yourself. Tag it in the PR accordingly.
- **The reviewer must not be the agent that wrote the code**, and must never be a fork of this
  session: a fork inherits the author's blind spots along with the context.

## The flow

| Phase | Skill | Who starts it |
|---|---|---|
| Frame a large or foggy effort | `wayfinder` | this skill invokes it |
| Stress the plan before building | `grilling` | this skill invokes it |
| Ground plan claims in current docs | `grill-with-docs` | this skill invokes it |
| Build UI | `impeccable` and `improve-react`, plus any project skill for the surface | this skill invokes them |
| Judge a rendered change | `dogfood-local` | this skill invokes it |
| Clean the diff | `deslop` for code, `stop-slop` for prose | this skill invokes them |
| Review | two independent passes, defects and standards | this skill runs both |
| Lost the thread | `wait-what` | the human starts it |

Some harnesses gate whether one skill may invoke another. In Claude Code the gate is the
`disable-model-invocation` frontmatter field, and this repo's `install.sh` clears it for the names in
`skills-unlock.txt`; a skill update restores the flag, so re-run the installer or those phases go
quiet. On a harness with no such gate, ignore this and read the referenced skill's file when its
phase arrives.

## 1. Frame

Read the issue for constraints, project context, and any PR already linked. Create an isolated
workspace for the change. Use the project's own worktree helper if it has one, so gitignored config
comes across; `../../templates/worktree-helper.md` describes what such a helper does. Otherwise
`git worktree add ../<name> -b <branch> <source-ref>`.

If the work is large, or spans more sessions than one context holds, invoke `wayfinder` to map it
into decision tickets before building anything.

**Done when** you can state the acceptance criterion in one sentence, and the workspace has the
config the project needs to run.

## 2. Stress the plan

Invoke `grilling` on the approach before writing code. A plan that survives questioning costs less
than a rewrite. Skip this for mechanical work with one obvious shape.

If the plan rests on how a library or service behaves, invoke `grill-with-docs` instead, so the
claims get checked against current documentation as the interview runs.

**Done when** the decisions are settled, or the open questions are written down and the human has
answered the ones that block you.

## 3. Build

Build the change. Keep each commit focused on one thing.

For any UI work, invoke `impeccable` first, then `improve-react` for the React-level faults it does
not look at. Run both on each pass rather than once at the end. If the project ships its own UI
skill, invoke that too: it carries the design system, the house rules, and the verification loop.

**Done when** every function in the diff has a real implementation, no TODO or stub markers remain,
and every new code path is exercised by at least one test.

## 4. Verify

Run the cheapest check that exercises the change. Paste the real command and its real output.

**Done when** every claim has its command and output pasted, every behaviour you removed or
tightened is listed, and each changed interface has its downstream callers named, including callers
outside the repo.

## 5. Dogfood it, before it becomes a PR

For any change with a rendered surface, invoke `dogfood-local`. That skill owns the method and the
bar for this phase.

## 6. Clean the diff

Invoke `deslop` on the code. Invoke `stop-slop` on any prose you are shipping: a README, a PR body,
an issue comment.

**Done when** both report no remaining findings, or each remaining finding is refuted in writing.

## 7. Review, two independent axes

Run both. They overlap almost nowhere, so one passing says nothing about the other.

- **Defects and test quality.** Review `<base-ref>...HEAD` for what breaks. Dispatch this to a
  genuinely separate reviewing agent, never a forked continuation of the session that wrote the diff,
  because a fork inherits the author's blind spots. Give it the repo path, the exact diff command,
  and what the change claims to do. Require it to run the tests and cite command plus output for
  anything it calls verified. Where the harness offers no separate agent, run the pass yourself as a
  deliberately skeptical second read and say that is what you did.
- **Standards and spec conformance.** A second pass since the same base ref: does the diff follow
  this repo's documented standards, and does it do what the originating issue asked. Use the
  harness's standards-and-spec review command if one is configured, otherwise read the conventions
  doc and the issue and compare them to the diff yourself.

**Done when** every finding is fixed in this branch or refuted in writing with evidence.

## 8. Push and open a draft PR

Check `git status --short --branch`, run `git diff --check`, rebase on the default branch if you have
drifted. Push, then open the PR as a draft with the issue id in the title and the body sections the
conventions name.

**Done when** the draft PR exists and its body carries those sections.

## 9. Report evidence

Comment on the issue: what changed, what is proven and by which command, what is still unverified,
the next step, and the commands to resume.

**Done when** the comment would let a fresh session pick the work up without the transcript.

## Stop and ask when

Stop only where proceeding under any assumption would be unsafe, or would make the work useless if
the guess is wrong. Before you stop, deliver everything that does not depend on the answer, and say
explicitly what you left out and why.

- **The action is destructive and not reversible**, and the intent is not already unambiguous. A
  deletion, a force-push, a production write with no restore point.
- **Two readings of the request lead to materially different work**, and the cheaper one is not
  obviously right. Ask the one question; do not survey the options.
- **A review finding implies a design change rather than a patch.** Surface the finding, keep
  shipping the rest of the branch.

These are not reasons to stop:

- A phase finished. Start the next one.
- The issue has no acceptance criterion. Write one from the issue, state it, proceed.
- A decision has an obvious default. Take it, name it in the PR, move on.
- The fix belongs to another implementer. Deliver the diagnosis *and* the ADR-shaped issue, then take
  the next item off the frontier.
- You want to check the plan is still wanted. It is. It was asked for.
