# Working conventions

Method only. Nothing here names an employer, a repo, or a host. If a line would stop being true
somewhere else, put it in the private layer.

## Verification

- State a number, metric, row count, or behaviour as fact only when you measured it yourself in this
  session. Say where it came from.
- Treat a figure a subagent reports as **unverified** until you re-measure it. Subagents explore and
  critique. Numbers you act on, you re-derive.
- Tag every number in a claim: `[measured: <command> -> <output>]`, `[sourced: <doc>]`, `[estimate]`,
  or `[unverified]`. A virtue cannot be graded. A tag can be checked.
- Measure the thing, not its shadow. The absence of an error string proves nothing. Never read an
  exit code through a pipe: `cmd | tail` reports the status of `tail`.
- Assert a property in a commit message or PR description only when you tested it. "Unverified, and
  here is what I could not prove" is a useful result.

## Calling code you did not write

- Read the definition before the call site. Six bugs in one script came from assuming helpers did
  more than they did: one took two arguments and silently discarded a third that looked like a
  default, one wrote a file but set no shell variable, one exported a name that was never assigned,
  and the closing function had a different name than the one called. All six passed a syntax check.
- Guessing an identifier is worse when it works. A guessed resource name that fails costs five
  minutes; one that happens to be right hides the habit until the next environment. Discover it:
  ask the API, and when a config declares no default, find out why.
- Assert your anchors. Before editing by string replacement, check the pattern matches exactly once.
  A silent no-op edit reads as success. The rule caught itself being written: the heading this text
  was first anchored to did not exist.

## Before you claim the work is done

- Re-read your own diff line by line. List every behaviour you removed, tightened, or made stricter.
  Rewrites break things far more often than new code does.
- Name every downstream caller of each interface you changed, including callers outside this repo:
  internal apps, pipelines, dashboards, MCP consumers. A change that is correct in-repo still breaks
  the caller you never opened.
- Run the tests, paste the real output, then summarise.

## Scope

- Asked to investigate or diagnose, deliver the diagnosis. Write an issue or an ADR when the fix
  belongs to someone else. Wait for approval before you implement.
- Do not gate requested work behind an audit or a prerequisite you invented. Ask first.

## Review before pushing

Two lanes on the same fixed point. They overlap almost nowhere, so run both. Neither replaces the
other.

- **Defects and test quality.** `delegate review <base-ref>` validates the ref and pins
  `<base-ref>...HEAD` against the merge-base before it spends anything. Dispatch the `reviewer`
  agent fresh, never as a fork: a fork inherits the author's context and the author's blind spots.
  Never tell it to skip what you already verified, because that is where a shared blind spot hides.
  Require it to run the tests and cite command plus output for anything it calls verified. A clean
  pass with cited evidence is a real result. Padding the findings is not.
- **Standards and spec conformance.** `/code-review` since the same fixed point. It catches what the
  defect lane cannot see: code that works and implements the wrong thing.

## Validation

- Run the cheapest check that exercises the change before you call it done. Report the output, not
  your expectation of it.
- Run `git diff --check` and the project's own test command at minimum.
- A test that has never failed proves nothing. Make it fail before trusting a green run: mutate the
  code or the input and watch it go red. Three tests in one file passed while checking nothing,
  because a regex matched a comment instead of the thing under test.
- Never edit files while a suite runs against them. A mutation run overlapping a full suite gave a
  result that took 1h48m instead of 9m with a changed skip count. That number was unusable, and only
  a second clean run revealed it had been meaningless.

## Issue tracker

- The tracker holds the plan. The forge holds the review and the merge.
- Keep the issue id in the branch name and the PR title.
- After each verified milestone, comment on the issue: what changed, what is proven, what is still
  unverified, the next step, and the commands to resume. Do this unasked. It is what survives a
  context compaction.

## Branches and PRs

- Prefix branches `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`. Never a personal prefix.
- Before pushing, check `git status --short --branch`, keep commits focused, leave no temp files, and
  rebase on the default branch if you have drifted.
- PR body sections: Description, User-facing or operational impact, What changed, Validation.
- Write a markdown-heavy PR body to a temp file so the backticks survive the shell, then delete it.
  A quoted phrase inside `-m` breaks the commit and the push afterwards still looks like it worked.

## Library and API docs

- Reach for **context7** first on any library, framework, SDK, CLI, or cloud service question. Call
  `resolve-library-id`, then `query-docs`. It indexes current docs. Web search returns blog posts
  about older versions.
- Fall back to web search when context7 has no entry, or when the question is not documentation.

## Writing style

ASD-STE100 Simplified Technical English for READMEs, docs, PR descriptions, issues and comments.
Chat replies, commit messages and code comments keep normal style.

- Use the active voice. Use the imperative for instructions.
- One instruction per sentence. Instructions stay under 20 words, descriptive sentences under 25.
- One term for one meaning throughout a document.
- Prefer simple verbs: "do", "make sure", "examine", "show". Avoid "perform", "ensure", "inspect".
- No idioms, no metaphors, no figurative language.
- State a warning as condition plus consequence, before the instruction it protects.
- Vertical lists for sequences. Tables for decisions.
