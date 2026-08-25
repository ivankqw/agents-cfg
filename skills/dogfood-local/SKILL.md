---
name: dogfood-local
description: Run the app on a local server and drive it in a real browser to judge a change before shipping it. Use after any frontend pass, before opening PRs, and whenever a decision is visual ("does this look right") rather than logical. Replaces shipping PR-by-PR to prod just to look at the result.
---

# Dogfood local

Judge a change by using the app, on a local server, before it becomes a PR.

The rule this skill exists to enforce: **prod is for confirming a deploy landed, never for deciding
whether a design is right.** Deciding on prod makes every look cost a merge and a deploy, and forces
visual judgement after the change is already irreversible.

## When to use

- After a frontend pass, before opening the PR.
- Whenever the open question is visual: does this look right, is it readable, is the affordance
  obvious.
- Whenever a batch of branches is in flight and you need to see them together.

Skip it for backend-only work with no rendered surface.

## 1. Gate the pass first

Run the craft gates before you look at the change, on **each pass** rather than once at the end. The
`ship` skill's build phase lists them. A pass that skips them tends to produce the change the next
dogfooding session reverts.

**Done when** the gates have run and their findings are fixed or written down with a reason.

## 2. Build one integration worktree

Do not dogfood a single branch when several are in flight. You will judge a screen no user will ever
see, and you will miss the merge breakage.

Create one throwaway worktree off the default branch and merge every branch in flight into it. Use
the project's own worktree helper if it has one, so gitignored config gets carried across.
`templates/worktree-helper.md` describes what such a helper has to do.

```bash
git worktree add ../<name>-dogfood -b integration/<name>-dogfood origin/main
cd ../<name>-dogfood
for b in <branch> <branch>; do git merge --no-edit "origin/$b"; done
```

A clean merge here is also the cheapest possible check that the branches do not collide. A conflict
at this step is a finding, not an obstacle.

**Done when** every in-flight branch is merged and the tree builds.

## 3. Bring the stack up

Read the project's own instructions first: `make help`, `Makefile`, `README.md`, `docs/local-*`. Do
not invent a startup sequence. Most stacks need install, then a database, then migrations and seed
data, then the dev server. Run the project's own health target if it has one rather than
hand-rolling a check.

**If something already occupies the database port**, a `db-up` style target may report the port as
already answering, skip its own initialisation, and leave migrations failing to authenticate against
a server that is not yours. Run the project's instance on another port instead of fighting the
incumbent, and repoint the connection string to match.

**Done when** the frontend answers and the API health check passes. Check both. A frontend that
loads against a dead API looks fine until you click something.

## 4. Drive it in a real browser

Use the Chrome tools (`mcp__claude-in-chrome__*`). Load the core set in **one** `ToolSearch` call.

Two habits that decide whether this is worth doing at all:

- **Measure, do not squint.** Screenshots rescale between captures and mislead about coordinates.
  Read geometry from the DOM (`getBoundingClientRect`, computed styles, rendered widths) and quote
  the numbers. "The panel is at top -341 while its trigger is at 597" is a finding; "it looks off" is
  not.
- **Verify the built artifact.** After a deploy or rebuild, confirm the bundle actually changed
  (compare the loaded `script[src]` against what the server serves now) before concluding a fix
  failed. A cached bundle has faked a failed fix at least once.

**Local data is yours to shape.** This is the whole advantage over prod: create the state that
exercises the change instead of hunting for a record that happens to have it. Set the amounts, make
the gate pending, empty the field. Do that on prod and you are editing real records.

**Done when** you have driven the actual path a user takes, not just loaded the page.

## 5. Judge, fix, repeat

Fix what looks wrong and go round again from step 1. Two or three fast passes locally beat one pass
through review.

Only when it survives a pass do you open PRs. Then prod's job is narrow: confirm the deployed image
matches the merge commit and the change is present, not to decide whether it was right.

## Stop and ask when

- The startup sequence needs a privileged install such as `sudo apt`. Hand the user the exact
  command rather than guessing at their password or working around the prompt.
- The stack cannot be run locally at all. Say so plainly instead of quietly falling back to prod,
  which is the habit this skill replaces.
