# How the setup works

I use one repository to shape two agent harnesses. Claude Code and Codex have different instruction
and extension systems, so `install.sh` gives both harnesses the same working method. The design keeps
stable rules in a small convention file and loads detailed procedures as skills.

The [glossary](./GLOSSARY.md) defines each layer term.

## The base model supplies general capability

I treat a harness and its selected model as one base model. The harness supplies the work loop,
tools, context controls, permissions, and memory. The model supplies language and judgment. I can
change either part without rewriting the rest of this repository.

`configs/default.yaml` describes the Claude Code arrangement. `configs/single-vendor.yaml` describes
the no-Claude fallback. The config selects models for roles, while the harness owns execution.

## Conventions set the default method

Each session receives the portable conventions from `conventions/AGENTS.md`. Claude Code reads a
symlink through an `@import`. Codex reads a generated `~/AGENTS.md` because its documented behavior
does not include Claude imports. `install.sh` creates both forms in its `instruction files` block.

The convention file stays below 200 lines. `MAINTAINING.md` records that ceiling and asks one
question of each line. Would removing the line cause a mistake? The ceiling protects model attention
and pushes narrow procedures into skills.

The private layer can add another convention file. `install.sh` imports or concatenates
`$PRIVATE_CONFIG/AGENTS.md` when the file exists. I can carry the portable layer across jobs without
carrying employer details.

## Skills load detailed procedures on demand

An agent sees a skill description before it sees the skill body. The description tells the agent
when to load the procedure. The body can carry worked examples, failure cases, and verification
steps for one kind of work. This progressive disclosure keeps narrow guidance out of every session.

I keep own skills under `skills/`. The current set includes `cleanup-crew` and `dogfood-local`.
`install.sh` links each own skill into `~/.agents/skills`. It links that shared directory into
Claude Code.

I consume upstream skills from their source origin. `skills-lock.json` records sources for the
`skills` CLI. `bootstrap.sh` runs `npx skills experimental_install` from the home directory, and
`bin/skills-update` runs `npx skills update`. The repository stores the lockfile and does not copy
those skill folders.

[Matt Pocock's skills repository](https://github.com/mattpocock/skills) supplies recorded skills.
`skills-lock.json` is the current list of names and source paths.

[pstack](https://github.com/michael-denyer/pstack-claude) comes from @poteto's original pstack work.
`bootstrap.sh` clones the port from the source named by `PSTACK_REPO`. It checks out the commit in
`pstack-revision.txt`. `install.sh` links pstack skills and Codex prompt files from that checkout. The
repository neither copies pstack nor adds it to `skills-lock.json`.

`npx skills` installs ordinary upstream skill folders under `~/.agents/skills`. The installer uses
symlinks for own skills, pstack, and harness exposure. Each lockfile entry keeps the upstream source
and revision data.

Herdr runs Codex implementation agents in observable terminal panes. `skills-lock.json` records the
`herdrdev/herdr` skill source. `bootstrap.sh` stops if restoration does not create the Herdr skill.

## Agents isolate a responsibility

An agent definition gives one role its own prompt and model. `agents/reviewer.md` defines the Sonnet
reviewer for the default review lane. `install.sh` links agent definitions into `~/.claude/agents`.

The reviewer must not use the model that wrote the change. `conventions/AGENTS.md` states the rule,
and `configs/README.md` explains the reason. Models can share blind spots with another run of the
same weights. A different model gives the review another failure pattern. The single-vendor config
uses a different OpenAI model when Codex holds every role.

The default config dispatches the reviewer as a fresh Claude Sonnet subagent. The reviewer receives
the repository path and diff range, but none of the author's conversation context.

## Configs make role choices explicit

A config assigns a harness, model, and effort to each role. `configs/default.yaml` and
`configs/single-vendor.yaml` hold those choices. `configs/README.md` explains when to use each
config.

Named configs turn several model choices into one operator decision. They expose compromises.
For example, `configs/single-vendor.yaml` marks its reviewer as `cross_vendor: false` and requires a
different model with no shared context.

`configs/pstack-codex.md` maps pstack roles to confirmed Codex model names. `install.sh` appends that
file to the generated Codex instructions and links it at `~/.codex/pstack-models.md`.

## Hooks fire on configured events

The model decides whether to load a skill. A hook does not depend on that decision. The harness runs
a hook when a configured event matches.

`hooks/review_reminder.py` adds advice before a shell command that contains `git push`. It asks the
operator to dispatch the Sonnet reviewer as a fresh subagent. `hooks/cleanup_crew_after_pr.py` adds
tracker advice after a pull request opens. Both hooks catch errors and exit without blocking work.

`install.sh` links each hook into `~/.claude/hooks` and `~/.codex/hooks`. It does not edit harness
settings. `settings/settings.template.json` and `settings/codex.config.template.toml` show the
registrations that an operator must merge.

## MCP declarations keep credentials outside Git

`mcp/servers.json` declares MCP server names and URLs. A server can name a header environment
variable through `header_env`. The installer skips that server when the variable has no value.

A tenant URL identifies an account, so the executor declaration uses `url_env` with
`EXECUTOR_MCP_URL`. The installer reads the URL from the environment and skips the server when the
variable has no value. The file stores no API key or tenant URL.

The MCP installation block calls both the Claude and Codex CLIs when they are present. Codex accepts
bearer-token environment variables, but it cannot reproduce arbitrary HTTP header names. The
installer prints a skip reason for those entries.

Hermes support remains experimental. `docs/INSTALL.md` describes the manual context, skill, MCP, and
canary steps. The installer does not edit `~/.hermes/config.yaml`.

## The layers keep different change rates apart

I can change a model through a config, refine a procedure in one skill, or add an event reminder in
a hook. Each change has one home. The harness can improve while the portable layer keeps my method,
and an upstream skill can improve without losing its source history.
