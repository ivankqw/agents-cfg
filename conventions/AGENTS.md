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
- Tag closing-summary counts too. Mark each projection `[estimate]`.
- Measure the thing, not its shadow. The absence of an error string proves nothing. Never read an
  exit code through a pipe: `cmd | tail` reports the status of `tail`.
- Run it bare or read `${PIPESTATUS[0]}`. Grepping can miss unpredicted failure wording.
- Assert a property in a commit message or PR description only when you tested it. "Unverified, and
  here is what I could not prove" is a useful result.
- Impact words such as "outage", "live", and "broken" need a measurement or `[unverified]` tag.
- Override an instruction only when a measurement disproves its premise. Cite it and give the undo.
- After a crash or restart, ask every live process for its status.

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
- A template is not production. Diff live state first, then patch only the intended property.

## Before you claim the work is done

- Re-read your own diff line by line. List every behaviour you removed, tightened, or made stricter.
  Rewrites break things far more often than new code does.
- Name every downstream caller of each interface you changed, including callers outside this repo:
  internal apps, pipelines, dashboards, MCP consumers. A change that is correct in-repo still breaks
  the caller you never opened.
- Update each caller and tick it off a written list. Grep output is not an update.
- Run the tests, paste the real output, then summarise.

## Scope

- Asked to investigate or diagnose, deliver the diagnosis. Write an issue or an ADR when the fix
  belongs to someone else. Wait for approval before you implement.
- Do not gate requested work behind an audit or a prerequisite you invented. Ask first.
- A standing grant overrides approval only for its named queue. Say what a merge triggers before
  accepting it. Still verify the reviewed SHA, branch state, checks, and pinned merge head.
- When the human questions architecture, name the forcing boundary and file the real-fix ticket.

## Optional measurement and simplification

- Keep pstack routing as the default entry point. Use complexity or Ponytail skills only when the
  user asks for them.
- Treat complexity metrics as review input. Project limits and measured behavior take precedence
  over generic thresholds.
- Use Ponytail as an explicit opt-in tool. Do not enable its full mode or persistent state.
- Acceptance criteria, verification rules, security controls, accessibility requirements, and
  operator boundaries override simplification advice.
- Ponytail benchmark figures come from upstream. Do not present them as current-repository
  measurements.

## Roles and configs

Three roles do the work, and which model fills each one is a named choice, not a per-task decision.

- **Orchestrator** holds the plan and the decisions. Spend here.
- **Implementer** builds to an explicit brief in a fresh context, in parallel. Throughput matters
  more than depth, because the brief carries the thinking.
- **Reviewer** attacks a finished diff.

**The reviewer must not be the model that wrote the code.** A reviewer sharing weights with the
author shares its blind spots, and a shared blind spot cannot be seen from inside. Prefer a different
vendor. Where that is impossible, use a different model, give it no shared context, and require it to
run the tests and cite command plus output, because executed evidence does not care whose weights
produced it.

Named configs live in `configs/`. Pick one at the start of a stretch of work and say which one you
are on. When a config forces the reviewer to share the author's weights, say so in the PR.

Name the reviewer fallback: independent vendor, context-free different model, then same-vendor.
Declare the rung in the PR. Self-probes do not justify same weights. Switch after the build.

Configs are directional. `lean`, `default`, and `deep` require Claude Code as the orchestrator.
Claude Code can call the Codex reviewer through its plugin. Codex has no reciprocal Claude plugin.
Its only route to Claude is a `claude -p` subprocess. That subprocess can provide an external
cross-vendor pass, but it is not the `deep` reviewer lane. When Codex holds the plan, use
`single-vendor`. Keep its reviewer on a different Codex model from the author.

## Review before pushing

Two lanes on the same fixed point. They overlap almost nowhere, so run both. Neither replaces the
other.

No diff or crash skips a review lane. Name skipped lanes and why. Stop loops with no new signal.

- **Defects and test quality.** `delegate review <base-ref>` validates the ref and pins
  `<base-ref>...HEAD` against the merge-base before it spends anything. Dispatch the `reviewer`
  reviewer as a new agent that starts with no memory of this conversation. A mechanism that shares
  this session's context inherits the author's blind spots along with it. In Claude Code that means
  never dispatching it as a fork.
  Never tell it to skip what you already verified, because that is where a shared blind spot hides.
  Require it to run the tests and cite command plus output for anything it calls verified. A clean
  pass with cited evidence is a real result. Padding the findings is not.
- **Standards and spec conformance.** A second pass over the same fixed point: does the diff follow
  this repo's documented standards, and does it do what the originating issue asked. Use the
  harness's standards-and-spec review command where one is configured; in Claude Code that is
  `/code-review`. It catches what the defect lane cannot see: code that works and implements the
  wrong thing.

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
- Before measuring, state what failure shows. A probe with identical outcomes proves nothing.
- Prove an operational workflow with one real run before merge, even if it needs a throwaway tag.

## Issue tracker

- The tracker holds the plan. The forge holds the review and the merge.
- Keep the issue id in the branch name and the PR title.
- Get it before branching; branches cannot be renamed after a PR opens. Use one branch per issue.
- After each verified milestone, comment on the issue: what changed, what is proven, what is still
  unverified, the next step, and the commands to resume. Do this unasked. It is what survives a
  context compaction.

### Keeping the board true

A tracker decays, and a decayed board costs more than an empty one. The `cleanup-crew` skill runs
these as passes; the rules matter on their own.

- **A stale ticket at top priority is worse than no ticket.** Two tickets once sat at Urgent with a
  `DO NOT RUN` block at the top of the body, so the queue advertised as most important the one action
  nobody must take. When a decision invalidates a ticket, resolve it the same day. Do not annotate it
  and leave the priority alone.
- **Stale has three shapes, and one rule loses two of them.** Cancel a ticket only when its premise is
  false *and* nothing is left to deliver. Rewrite it when the method died but the payload is still
  wanted. Reframe it when the framing died and the substance is live. A blanket close-if-stale rule
  destroys real work.
- **Cancelled and Done are different claims.** Done asserts the work happened. Marking an abandoned
  ticket Done corrupts every later reading of what shipped.
- **Name what a closure does not carry.** List the still-wanted parts of a superseded ticket and where
  each went. Where a part went nowhere, say so, rather than implying coverage.
- **Measure the premise, do not read it.** A ticket that annotates itself as invalid is usually right
  about its method and often wrong about its problem. A ticket asserting a field was empty everywhere
  had it populated on every row.
- **A child issue does not inherit its parent's project.** Set the project explicitly on every child,
  or the subtree becomes unreachable from every project view.

## Branches and PRs

- Prefix branches `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`. Never a personal prefix.
- Before pushing, check `git status --short --branch`, keep commits focused, leave no temp files, and
  rebase on the default branch if you have drifted.
- Copy template headings exactly because CI can gate on text. With no template, use this line.
- PR body sections: Description, User-facing or operational impact, What changed, Validation.
- Write a markdown-heavy PR body to a temp file so the backticks survive the shell, then delete it.
  A quoted phrase inside `-m` breaks the commit and the push afterwards still looks like it worked.

### Releases

Prefer release-tag deploys; state when merges deploy. Agents never cut releases; the operator tags.

## Library and API docs

- Reach for a documentation-lookup tool first on any library, framework, SDK, CLI, or cloud service
  question. Where context7 is configured, call `resolve-library-id` then `query-docs`. Such a tool
  indexes current docs; web search returns blog posts about older versions.
- Fall back to web search when context7 has no entry, or when the question is not documentation.

## Writing style

ASD-STE100 Simplified Technical English for READMEs, docs, PR descriptions, issues and comments.
Chat replies, commit messages and code comments keep normal style.

Execute terse or mistyped chat instructions from context; ask only if readings change the work.

- Use the active voice. Use the imperative for instructions.
- One instruction per sentence. Instructions stay under 20 words, descriptive sentences under 25.
- One term for one meaning throughout a document.
- Prefer simple verbs: "do", "make sure", "examine", "show". Avoid "perform", "ensure", "inspect".
- No idioms, no metaphors, no figurative language.
- State a warning as condition plus consequence, before the instruction it protects.
- Vertical lists for sequences. Tables for decisions.
