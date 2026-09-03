# I overfit coding agents to myself

I use Claude Code and Codex for work that spans design, implementation, review, and release. Both
harnesses arrive with strong models and sensible defaults. Their teams need those defaults to serve
many developers, repositories, and risk profiles. I need one agent system to fit one operator.

That difference drives this repository. I treat the harness and model as a base model. I add a
portable layer of conventions, skills, agent definitions, configs, and hooks. The weights stay
frozen. The context changes the behavior.

I think of the result as personal fine-tuning in context. Machine-learning teams fine-tune weights
against a target distribution. I keep the weights and train the working context against my own
distribution of tasks. I choose the overfit.

## Harness teams optimize for general use

A harness team has to serve users who disagree about good work. One user wants an agent to stop at a
plan. Another wants the agent to open a pull request. One team requires a human before each external
write. Another grants an agent a queue for the night. A shared product must handle all of them.

Harness teams run evaluations across broad task sets. They look for performance that survives a new
repository, a new user, and a new model release. That is the classic machine-learning trade-off
between performance on a target distribution and generalization across other distributions.

The trade-off makes sense for a product team. A default that wins on one person's habits and fails
for everyone else is a poor product default. The team should resist personal quirks in the base
model.

I have the opposite objective. I know the repositories, review standards, and failure patterns that
matter to me. I can spend context on those details. I can accept lower generalization because I do
not sell this configuration to a broad market.

The base model gives me broad capability. My portable layer gives that capability a local shape.

## My weights live in context

The analogy to fine-tuning has limits, but it helps me decide where to put knowledge. A convention
acts like a weight with a high activation rate. Each session receives it. A skill acts like a larger
block of weights behind a task trigger. An agent definition narrows a role. A config chooses which
model fills that role.

I make those choices in files that I can read and review. `conventions/AGENTS.md` holds the rules I
want in each session. `skills/` holds procedures for work such as shipping, browser use, and tracker
cleanup. `agents/reviewer.md` gives review a separate stance. `configs/` records model choices by
role.

The model reads those files at inference time. No training job changes its parameters. A new session
receives a different context and produces different behavior from the same model family.

That mechanism gives me a tight correction loop. A failed session leaves evidence. I can turn a
repeated failure into a convention or a skill example. The next session reads the correction. Kun
Chen's [backpass](https://github.com/kunchenguid/backpass) gives this loop a useful machine-learning
frame. His tool treats an agent session as a forward pass and the transcript as a loss signal.

I keep a human gate. A transcript can expose a gap, but it cannot decide which habit I want.
The operator owns that choice.

## Thin harness, fat skills

Garry Tan named the architecture
["thin harness, fat skills"](https://github.com/garrytan/gbrain/blob/master/docs/ethos/THIN_HARNESS_FAT_SKILLS.md).
His phrase describes the direction I want.

The harness should own the work loop, context management, memory, tools, permissions, and hooks. I
do not want to rebuild those mechanisms in a personal wrapper. Claude Code and Codex teams can test
them across more users and environments than I can.

I keep the harness thin from my point of view. I add little runtime code. `bin/delegate` routes
review work. Two hooks add advice at events. The rest of the portable layer consists of text and
small declarations.

The skills carry more context. A fat skill includes the procedure, the stopping rules, the evidence
standard, and stories from past failures. The stories matter because a bare command leaves room for
the same bad shortcut. A concrete failure tells the model which tempting interpretation caused harm.

`skills/dogfood-local/SKILL.md` gives one example. The skill says when to run a local application,
how to build an integration workspace, and what to measure in a browser. It records cases where
a stale branch or missing environment file created a false diagnosis. A short instruction such as
"test the UI" would lose those distinctions.

`skills/ship/SKILL.md` carries a longer route from framing to a draft pull request. It records failure
patterns around background tasks, test status, stale branches, and human handoffs. Those details
would overload the convention file. They earn their place when the agent ships work.

The split resembles progressive disclosure. The model sees a short skill description in its normal
context. The model loads the full procedure when the task matches. I can add depth without charging
every session for it.

## The context should belong to the operator

Two people can use the same base model and want different behavior. One person wants terse status
updates. Another wants a detailed decision trail. One person accepts same-vendor review. Another
requires model independence before a push.

Harness teams cannot settle those differences with one default. They can expose the controls and
test that the controls work. The operator should supply the working method.

This repository makes my method portable. The portable layer contains rules that can travel between
jobs. The private layer contains employer names, host details, credentials, and domain knowledge.
`install.sh` combines the layers on my machine while Git keeps them apart.

That boundary matters as much as the content. A personal method should survive a new job. Private
facts should stay with the job that owns them. The same agent system can carry my review habits
without carrying a tenant URL or customer name.

The skill boundary lets me consume other people's judgment without claiming it as mine.
`skills-lock.json` records source data for skills installed by the CLI. `pstack-revision.txt` pins
the pstack port, and `install.sh` links that checkout. I can update those sources, inspect the
change, and retain the author's credit.

## Failure stories are training data

Rules sound obvious after someone states them. Their value appears when the model meets an easy
shortcut under pressure.

My conventions say that a number needs a measurement and a source. That rule grew from summaries
that turned estimates into facts. The same file says to read a helper definition before its call
site. A plausible function name can hide a wrong assumption through a syntax check.

The reviewer rule came from another class of failure. A model can review its own work with a stern
prompt and keep the same blind spot. I assign the reviewer role to another model when I can. When I
cannot cross the vendor boundary, I use another model and require executed evidence. The rule lives
in `conventions/AGENTS.md`, while `configs/` makes the model choice visible.

The hooks cover a different weakness. A model can forget to load a skill. A configured hook fires on
an event even when the model makes no routing decision. `hooks/review_reminder.py` adds review advice
before a push. `hooks/cleanup_crew_after_pr.py` adds tracker advice after a pull request opens.

I do not read these examples as proof that my setup beats every default. They show that my failures
repeat. Repeated failures give me material for a local training set.

## The cost is real

Fat skills consume context when they load. Long rules can conflict. A stale anecdote can train the
wrong behavior. An upstream update can change a trigger. A generated instruction file can fall out
of date.

I manage those costs with limits and checks. The convention file stays under its line ceiling.
Skills use narrow descriptions. The installer checks metadata and pinned revisions. The canary in
`docs/INSTALL.md` asks each harness to reveal whether it loaded the expected phrase.

The setup costs maintenance time. I have to remove stale rules, review upstream changes, and
keep the private layer separate. I accept that work because I spend more time operating agents than
maintaining these files. Another operator may reach a different balance.

## The field may absorb this layer

My bet could fail. Harness teams may build strong personal memory, procedure learning, role routing,
and review isolation into their products. Models may infer an operator's method from a small history
without a fat skill layer. Context costs may make large procedures a poor bargain.

I would change my view if the harness could reproduce my working method after I removed this
portable layer. I would test repeated tasks that depend on my review rules, evidence format, and
private boundary. Equal behavior and equal failure rates across those tasks would remove the case
for this repository.

I would change my view if the skills became the main source of errors. A rise in instruction
conflicts, missed triggers, or stale procedures would show that the context layer costs more than it
returns.

I bet on a thin personal wrapper around a strong base model and a fat set of skills that I own or
pin. Harness teams can optimize the common system. I can optimize the context for one
operator. The model stays general, while the work becomes mine.
