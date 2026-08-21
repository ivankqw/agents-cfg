# Working conventions (portable)

Method only. Nothing here names an employer, a repo, or a hostname — if a line
would stop being true at a different company, it belongs in the private layer.

## Verification

- Never state a number, metric, row count, or behaviour as fact unless you measured it yourself in
  this session. Say where it came from.
- A figure reported by a subagent is **unverified** until you re-measure it. Subagents are for
  exploration and critique; numbers you will act on get re-derived by you.
- Tag every number in a claim: `[measured: <command> → <output>]`, `[sourced: <doc>]`, `[estimate]`,
  or `[unverified]`. A virtue cannot be graded; a tag can be checked.
- Measure the thing, not its shadow. Never infer success from the absence of an error string, and
  never read an exit code through a pipe — `cmd | tail` reports `tail`'s status, not `cmd`'s.
- Commit messages and PR descriptions may only assert properties you empirically tested. "Unverified,
  and here is what I could not prove" is an acceptable and useful result.

## Before claiming work is complete

- Re-read your own full diff line by line. List every behaviour you removed, tightened, or made
  stricter — regressions in rewrites are the most common defect, not new logic.
- Name every downstream caller of each changed interface, **including callers outside this repo**
  (internal apps, pipelines, dashboards, MCP consumers). A change that is correct in-repo can still
  break a caller you never looked at.
- Run the tests and paste the real output. Then summarise.

## Scope discipline

- When asked to investigate or diagnose, deliver the diagnosis — and an issue or ADR when the fix
  belongs to another implementer. Do not start implementing until the user approves.
- Do not gate requested work behind an audit or prerequisite you invented. Ask first.

## Review before pushing

Two lanes on the same fixed point. They overlap almost nowhere, so run both; neither substitutes
for the other.

- **Defects and test quality** — `delegate review <base-ref>`. Validates the ref and pins
  `<base-ref>...HEAD` (three-dot, against the merge-base) before spending anything. Dispatch the
  `reviewer` agent FRESH, never a fork — inheriting the author's context inherits the author's blind
  spots. Never tell it to skip what you already verified; that is exactly where a shared blind spot
  hides. Require it to RUN the tests and cite command plus output for anything it calls verified.
  A clean pass with cited evidence is a valid result; never pad findings.
- **Standards and spec conformance** — `/code-review` since the same fixed point. Catches the class
  the defect lane is blind to: code that is correct but implements the wrong thing.

## Validation

- Run the cheapest check that actually exercises the change before declaring work done; report
  actual output, not assumptions.
- At minimum run `git diff --check` and the project's own test command.

## Issue tracker

- The tracker is the planning source of truth; the forge is the review and merge surface.
- Keep the issue id visible in the branch and the PR.
- After every verified milestone, post a short status comment: what changed, what is proven, what is
  still unverified, the next step, and the commands to resume. Do this without being asked — it is
  what survives a context compaction.

## Branches and PRs

- Branch prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`. Never personal prefixes.
- Before pushing: check `git status --short --branch`, keep commits focused, no temp files, rebase on
  the default branch if drifted.
- PR body sections: Description / User-facing or operational impact / What changed / Validation.
- Use a temporary body file for markdown-heavy descriptions so backticks survive the shell; delete it
  afterwards.

## Library and API docs

- Reach for **context7** first on any library, framework, SDK, CLI, or cloud-service question —
  `resolve-library-id`, then `query-docs`. It indexes current documentation; web search surfaces blog
  posts about older versions.
- Fall back to web search when context7 has no entry, or the question is not documentation at all.

## Writing style (ASD-STE100 Simplified Technical English)

Applies to READMEs, docs, PR descriptions, issues and comments. Chat replies, commit messages and
code comments keep normal style.

- Use the active voice. Use the imperative for instructions.
- One instruction per sentence. Instructions ≤20 words; descriptive sentences ≤25.
- One term for one meaning throughout a document.
- Simple verbs: "do", "make sure", "examine", "show" — not "perform", "ensure", "inspect", "surface".
- No idioms, metaphors, or figurative language.
- State a warning as condition + consequence, before the instruction it protects.
- Vertical lists for sequences; tables for decisions.
