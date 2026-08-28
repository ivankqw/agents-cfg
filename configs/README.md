# Configs

A config names which model and effort level fills each role for a stretch of work. Switching config
is one decision instead of three, and naming them means you can say "run this on `lean`" and be
understood.

## Roles

| Role | Does | Wants |
|---|---|---|
| `orchestrator` | Holds the plan, makes the decisions, keeps the main context | Judgement over speed. This is the one worth spending on. |
| `implementer` | Builds to a spec in a fresh context, in parallel | Throughput. It works from an explicit brief, so it needs less depth. |
| `reviewer` | Attacks a finished diff | Independence first, depth second. |

## The one rule that is not a preference

**The reviewer must not be the model that wrote the code.** A reviewer sharing weights with the
author shares its blind spots, and a shared blind spot is invisible from the inside. Prefer a
different vendor. Where that is not available, use a different model, and require the reviewer to run
the tests and cite command plus output, because executed evidence does not care whose weights
produced it.

## Reading a config

The `reviewer` entry names the model you *want* reviewing. Where a router tries that model first and
falls back when it is unavailable, the fallback reviewer runs on whatever the agent definition pins,
which is not a contradiction: the config states the intent, the agent definition states the floor.
When the fallback fires, the review is no longer cross-vendor. Say so.

## Choosing

| Config | Harness | Orchestrator | Implementer | Use it when |
|---|---|---|---|---|
| `lean` | Claude Code | Sonnet 5 | Haiku 4.5 | The plan is simple and the volume is high. |
| `default` | Claude Code | Opus 5 | Sonnet 5 | Ordinary work. |
| `deep` | Claude Code | Fable 5 | Sonnet 5 | Risky diffs, migrations, anything pre-deploy. |
| `single-vendor` | Codex | Codex Sol | Codex Sol | Codex owns the session, so cross-vendor review is unavailable. |

## Harness direction is not symmetric

`lean`, `default`, and `deep` assume that Claude Code owns the main session. Claude Code calls the
Codex reviewer through the Codex plugin. This gives those configs their cross-vendor review lane.

Codex has no reciprocal Claude plugin. `claude -p` starts a separate CLI process and does not supply
the reviewer configured by `deep`. Use `single-vendor` when Codex owns the main session. If the work
needs cross-vendor review, start it from Claude Code and select `default` or `deep`.

Cost rises strictly down that list.

## Price, so nobody guesses again

Per million tokens, input / output, from the Anthropic pricing page (checked 2026-08-21):

| Model | Input | Output |
|---|---|---|
| Claude Fable 5 | $10 | $50 |
| Claude Opus 5 | $5 | $25 |
| Claude Sonnet 5 | $2 | $10 |
| Claude Haiku 4.5 | $1 | $5 |

**Fable 5 costs twice what Opus 5 costs.** It is the most capable widely released model, not the
cheap one, so it belongs in `deep` and never in `lean`. Check the live page before trusting these:
<https://platform.claude.com/docs/en/about-claude/pricing>

Two things that move real cost more than the headline rate. Models from 4.7 onward use a newer
tokenizer that produces roughly 30% more tokens for the same text, so a cheaper per-token rate on an
older model is not always cheaper per unit of work. And a cache hit costs a tenth of the input rate,
which usually dominates any model choice on a long session.

Effort level names differ between harnesses, and not every model offers every level. Treat the levels
here as intent: `low` for mechanical work, `medium` for ordinary judgement, `high` and above for
work where being wrong is expensive.
