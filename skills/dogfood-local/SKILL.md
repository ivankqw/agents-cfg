---
name: dogfood-local
description: >-
  Runs the app on a local server and drives it in a real browser to judge
  rendered changes before they become pull requests. Use on any change traceable
  to prose requirements, a stakeholder email, or a mockup, and run it BEFORE the
  review lanes, not after: hands-on use found three defects that four diff
  reviews missed, because the wrong code path looked right in the diff. Fires
  on a single frontend pass, and equally on a batch frontier of rendered-surface
  branches — dogfood the whole batch from one integration worktree instead of
  shipping a PR per look. Replaces deciding on production.
---

# Dogfood local

Judge a change by using the app, on a local server, before it becomes a PR.

The rule this exists to enforce: **production is for confirming a deploy landed, never for deciding
whether a design is right.** Deciding on production makes every look cost a merge and a deploy, and
forces the judgement after the change is already irreversible.

## When to use

- After a frontend pass, before opening the PR.
- Whenever the open question is visual: does this look right, is it readable, is the affordance
  obvious.
- Whenever several branches are in flight and you need to see them together.

Skip it for backend-only work with no rendered surface.

## 1. Gate the pass first

Run the craft gates before you look at the change, on each pass rather than once at the end. The
`ship` skill's build phase lists them. A pass that skips them tends to produce the change the next
dogfooding session reverts.

**Done when** the gates have run and their findings are fixed or written down with a reason.

## 2. Build one integration workspace

When several branches are in flight, merge every one into a single throwaway workspace before judging
anything. Dogfooding one branch alone risks judging a screen no user will ever see, and hides the
breakage that appears only when the branches meet.

Use the project's own worktree helper if it has one, so gitignored config comes across;
`../../templates/worktree-helper.md`, at the repo root of this skill's own repository, describes what
such a helper does. Otherwise:

```bash
git worktree add ../<name>-dogfood -b integration/<name>-dogfood origin/main
cd ../<name>-dogfood
for b in <branch> <branch>; do git merge --no-edit "origin/$b"; done
```

A clean merge here is also the cheapest possible check that the branches do not collide. A conflict
at this step is a finding, not an obstacle.

Before you judge anything rendered, prove the workspace: `git log` shows the PRs you expect on the
base, and every gitignored env file the app reads is present. A stale local `main` once had a browser
pass confirming pre-fix code, and a missing `frontend/.env` was reported as a login defect.

A mockup or spec HTML is directional, not a pixel target. When the human says "looks off", ask for
one concrete delta (a font weight, a spacing, a component) and measure that against the live reference
app.

**Done when** every in-flight branch is merged and the tree builds.

## 3. Bring the stack up

Read the project's own instructions first: `make help`, `Makefile`, `README.md`, `docs/local-*`. Most
stacks need install, then a database, then migrations and seed data, then the dev server. Run the
project's own health target if it has one rather than hand-rolling a check.

**If something already occupies the database port**, a `db-up` style target may report the port as
already answering, skip its own initialisation, and leave migrations failing to authenticate against
a server that is not yours. Run the project's instance on another port instead of fighting the
incumbent, and repoint the connection string to match.

**Done when** the frontend answers and the API health check passes. Check both. A frontend that loads
against a dead API looks fine until you click something.

## 4. Drive it in a real browser

Use whatever browser-automation capability the harness offers: a Chrome or Playwright tool, a
computer-use tool, or an equivalent. Where tools must be discovered or loaded before use, load
everything you expect to need in one batch, because loading them one at a time costs a round trip
each.

Two habits decide whether this is worth doing at all:

- **Measure, do not squint.** Screenshots rescale between captures and mislead about coordinates.
  Read geometry from the DOM (`getBoundingClientRect`, computed styles, rendered widths) and quote the
  numbers. "The panel sits at top -341 while its trigger is at 597" is a finding; "it looks off" is
  not.
- **Verify the built artifact.** After a deploy or rebuild, confirm the bundle actually changed by
  comparing the loaded script source against what the server now serves, before concluding that a fix
  failed. A cached bundle has faked a failed fix at least once.

**Local data is yours to shape.** This is the whole advantage over production: create the state that
exercises the change instead of hunting for a record that happens to have it. Set the amounts, make
the gate pending, empty the field. Do that on production and you are editing real records.

**Done when** you have driven the actual path a user takes, not just loaded the page.

## 5. Judge, fix, repeat

Fix what looks wrong and go round again from step 1. Two or three fast passes locally beat one pass
through review.

Only when it survives a pass do you open PRs. Production's job is then narrow: confirm the deployed
build matches the merge commit and the change is present.

## Stop and ask when

- The startup sequence needs a privileged install such as `sudo apt`. Hand the human the exact
  command rather than guessing at a password or working around the prompt.
- The stack cannot be run locally at all. Say so plainly rather than quietly falling back to
  production, which is the habit this skill replaces.
