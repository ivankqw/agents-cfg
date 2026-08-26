---
name: cleanup-crew
description: >-
  Audits the issue tracker for structural rot and fixes it: issues and wayfinder
  maps filed under no project, tickets invalidated by decisions that moved on,
  stale references to closed work, and overlapping duplicates. Verifies every
  premise against the live system before closing anything. Use on a schedule,
  after opening a pull request, or when the board stops matching reality.
---

# Cleanup crew

A tracker rots in predictable ways. This skill finds each kind of rot, fixes what is unambiguous, and
hands back a short list of the judgement calls that are not the agent's to make.

Run it AFK. It reads widely, writes narrowly, and reports once.

`../../conventions/AGENTS.md` holds the verification bar this skill is held to: state a number only
when you measured it yourself, and tag every figure. That bar is the whole point here, because every
destructive action below rests on a claim about the current state.

## Where the project set comes from

Do not hardcode it, and do not infer it from the tracker alone. The repository declares it:

1. Read `docs/agents/issue-tracker.md` if it exists. That is where the tracker and its conventions
   are recorded.
2. Read the working repository's `AGENTS.md` or `CLAUDE.md` for a section naming the canonical
   projects and the rule that decides which one an issue belongs to.
3. Only if neither exists, derive the candidate set from the tracker and **report it as a proposal**.
   Do not start filing against a set nobody has agreed to.

If the repository and the tracker disagree, the repository wins and say so in the report.

## Order of work

Do the cheap structural passes first. They need no judgement, and they make the later passes legible.

### 1. Orphans, filed under no project

Query the team for each wayfinder label in turn: `map`, `task`, `research`, `grilling`, `prototype`.
Then list open issues per project to catch children whose siblings are filed and they are not.

**A child does not inherit its parent's project.** Trackers generally do not do this, which is why
orphans accumulate silently. Assign each orphan the project of the map it hangs from.

Read each issue before writing. Never overwrite a project that is already set. Record it as a
possible misfiling and leave it for the report.

This pass is mechanical and high-volume. **Delegate it** to a subagent with an explicit id list and a
rule to change nothing but the project field. One pass, one field.

### 2. Maps with no project

A map filed outside every project is worse than an orphaned child, because its whole subtree hangs off
it and nothing in the subtree is reachable from a project view. Check every map, not only the ones
already inside the canonical set.

### 3. Invalidated tickets

The worst thing on a board is a ticket that is **top priority and must not be run**. It advertises
itself as the next thing to do while being the one action nobody should take.

Search open issues for a body containing `DO NOT RUN`, `DO NOT EXECUTE`, `CAUTION`, `superseded`,
`invalidated`, or `needs a rewrite`, and cross-reference priority. Anything urgent carrying one of
those markers is a finding.

**Then verify the premise yourself before acting.** A ticket that annotates itself as invalid is
usually right about its method and often wrong about its problem. Measure the live system: the
deployed configuration, the actual row counts, the API's real answer. Then find out which.

Three outcomes, and picking the wrong one destroys real work:

| finding | action |
| -- | -- |
| Premise false **and** nothing left to deliver | **Cancel**, not Done. It was never completed |
| Method dead, payload still wanted | **Rewrite** the body around a live method. Do not close it |
| Framing dead, substance live | **Reframe**: retitle, correct the premise, name the ticket that now owns it |

Never close a ticket whose payload is still wanted merely because its plan went stale.

### 4. Stale references

A closed blocker leaves dangling references behind it. Take everything closed in the last fortnight
and search open bodies for its id and its title. Each hit is a body claiming work is blocked when it
is not, which is enough to stop somebody picking it up.

Fix with a short dated note at the top of the body. Say what changed, and say precisely what did
**not** change. Access being granted is not the same as ownership moving.

Give merged pull requests the same treatment. A ticket reading "cannot proceed until #908 merges" is a
ticket nobody returns to after #908 merges.

### 5. Decisions that were never written down

A decision ticket closed without recording its answer is rot that reads as progress. The board shows
it resolved; the body still shows two options and no choice. Every ticket blocked on it is now blocked
on nothing, and nobody can tell what was decided.

Take the closed decision tickets from the last fortnight and check each body states an outcome. Where
one does not, look for the answer in its comments or its linked commit. If the answer is recoverable,
write it into the body as a dated resolution line. **If it is not recoverable, say so on the ticket**
and on anything that cited it as a blocker: the decision has to be taken again, and pretending
otherwise silently unblocks work onto a choice nobody made.

Never invent the outcome from the options. A plausible reconstruction of a decision is worse than an
admission that it was lost, because it will be built on.

### 6. Overlaps

Group open issues covering the same ground. Report them as merge candidates, with both ids and what
overlaps. **Do not merge them.** Which of two framings survives is a decision, not a cleanup.

## Rules that came from things going wrong

- **Measure the premise, do not read it.** A ticket asserted a key field was "empty everywhere". It
  was populated on every one of ~1,500 rows. Cancelling it on the ticket's own account would have
  been the right call for entirely the wrong reason, and measuring turned up two further corrections
  on the map above it that nobody was looking for.
- **Cancelled and Done are different claims.** Done asserts the work happened. Use Cancelled when the
  reason for the work evaporated. Marking an abandoned ticket Done corrupts every later reading of
  what shipped.
- **Name what a closure does not carry.** Before closing a superseded ticket, list its still-wanted
  parts and where each one went. Where a part went nowhere, say so plainly rather than implying
  coverage that does not exist.
- **A capability that unblocks one payload may not unblock its siblings.** An additive insert path
  does not deliver an update to existing rows. Check the shape of each payload, not just the ticket
  it named as its blocker.
- **A subagent's count is unverified until you re-derive it.** Delegate the sweep; re-measure anything
  you act on.
- **Read the comments before calling a decision lost.** A decision ticket closed Done, whose body
  still poses its question with two options and no choice, looks exactly like a lost decision. Twice
  out of two, the answer was there: once in a resolution comment posted seconds before the close,
  once in a follow-up ticket that executed it. The rot is real but milder than it looks. The body not
  stating the outcome is what needs fixing, and announcing a decision lost when it is merely
  misfiled is its own error.
- **Two tickets can be stale in opposite directions.** One had a dead method and a live payload;
  another had a dead framing and a live defect that was the sharpest bug in the set. A single
  close-if-stale rule would have lost both.

## What to report

One report, in this order:

1. **Fixed without asking.** Counts and ids, grouped by kind of rot.
2. **Corrections to a map or a ticket body**, each with the measurement that justified it.
3. **Judgement calls.** Merge candidates, tickets whose payload may no longer be wanted, closures
   that dropped something with no new home. One question each, with a recommendation.

Keep it short. The value is the fixed board, not the prose about it.

## Do not

- Do not close anything on a hunch. Every closure cites a measurement or an explicit supersession.
- Do not touch state, title, or body during the mechanical project pass.
- Do not invent tickets for gate requirements only a human can confirm are still wanted. Report the
  gap instead.
- Do not run the destructive passes when the project set had to be guessed. Fix the orphans, then
  report the proposed set and stop.
