# I overfit coding agents to myself

I keep coming back to a machine-learning metaphor for how I use Claude Code and Codex. If you
squint, the harness and its model look like a base model. I pile conventions, skills, agent
definitions, configs, hooks, and private context on top. The weights stay frozen, yet the agent I
work with starts to fit me.

I know the analogy has holes. A harness plus a model differs from a base model, and a directory full
of Markdown does not train weights. I borrow the vocabulary because it helps me think about the
system. The model brings broad capability. The harness runs the loop. I use my context to teach that
pair how I want to work at inference time.

My guess is that the future may or may not follow this shape. Context might remain the place where
each operator teaches an agent their method. I am building on that premise while harness teams and
models keep changing.

## The harness teams have a generalisation problem

Claude Code and Codex have teams whose job differs from mine. They need to serve many developers,
repositories, and risk profiles. One developer wants an agent to stop after a plan. Another wants a
pull request before breakfast. One company requires approval before an external write. Another lets
an agent work through a queue overnight.

Those teams have to balance performance with generalisable behaviour. I assume they run evaluations
across broad task sets, then tune the model and harness so gains survive a new user or repository.
That is the machine-learning problem. A system can fit its test distribution and fail once
the distribution moves.

Their product should resist my quirks. A default built around my habits would make a bad shared
default. The team has to spend its effort on safe loop behaviour, sound context management, useful
tools, and permissions that hold across many environments.

I have a smaller target distribution. I care about my repositories, my review standards, and my
handoffs. I can spend context on details that do not belong in a shared default. In machine-learning
language, I want to overfit the system to one operator. I mean
the useful kind of overfitting, closer to a personal fine-tune than a model memorising noise.

## I put my weights in context

The fine-tuning analogy helps me decide where knowledge belongs. A convention acts like a weight
with a high activation rate because each session reads it. A skill holds a larger block of context
behind a narrow trigger. An agent definition gives one role a stance. A config chooses the model
that fills that role.

I can read and review those choices. `conventions/AGENTS.md` holds rules for each session. `skills/`
holds task procedures. `agents/reviewer.md` gives review an adversarial posture. `configs/` records
which model does each job.

No training job changes the model parameters. A session reads a set of files and behaves in ways
that another session with the same model family may not. I call that difference in-context learning,
and I push it toward the operator because two operators can want opposite things from the same
model.

I split the context into portable and private layers. The portable layer holds my method and can
follow me to another job. The private layer holds employer names, hosts, credentials, and domain
knowledge. `install.sh` combines both on my machine while Git keeps them apart. My review habits can
travel without carrying a tenant URL or customer name.

I use the setup to borrow judgment without pretending I invented it. `skills-lock.json` records
skill sources. `pstack-revision.txt` pins the pstack port. I can examine an update, keep the parts
that fit, and credit the author.

## Thin harness, fat skills

Garry Tan calls this architecture
["thin harness, fat skills"](https://github.com/garrytan/gbrain/blob/master/docs/ethos/THIN_HARNESS_FAT_SKILLS.md).

From my side, the harness should stay thin. Claude Code and Codex should own the work loop, context
management, memory, tools, permissions, and hooks. Their teams can test those mechanisms across
more environments than I can. My wrapper would give me another runtime and a worse test set.

My layer adds little runtime code. `bin/delegate` routes review work, and two hooks add advice. The
skills get fat because they carry the procedure, stopping rules, evidence
standard, and field-shot examples from work that went wrong.

The examples do more work than a bare command. "Test the UI" leaves room for an agent to use a stale
branch or declare success after reading a proxy. A failure story shows the tempting shortcut and its
consequence. The next agent receives something closer to a training example than a policy slogan.

`skills/dogfood-local/SKILL.md` says when to run a local app and what to measure in the browser. It
records cases where stale branches and missing environment files produced false diagnoses.
`skills/ship/SKILL.md` covers the route from framing through a draft pull request, with failure cases
around test status, branch drift, and handoffs. Those details would swamp the convention file.

If you squint again, progressive disclosure looks like sparse activation. The normal context sees
a short skill description, and a matching task loads the heavy procedure. Each session avoids the
cost of the whole library.

## Failure stories become training data

Many rules sound obvious once I write them down. They earn their place when an agent finds the same
shortcut under pressure.

My conventions require a measurement and a source for a number. I wrote that rule after summaries
turned estimates into facts. The same file tells an agent to read a helper before its call site. A
plausible function name once hid false assumptions behind a clean syntax check. I need the next
session to avoid the failure I have seen.

The reviewer rule came from another repeated failure. A model can attack its own diff and retain the
blind spot that wrote the code. I use another model for review when I can. If I cannot cross a vendor
boundary, I use a different model with no shared context and ask for executed evidence.

Hooks cover cases where the model forgets to route itself. `hooks/review_reminder.py` adds review
advice before a push. `hooks/cleanup_crew_after_pr.py` adds tracker advice after a pull request
opens. A hook fires from an event, so it does not depend on the model remembering that a skill
exists.

Kun Chen's [backpass](https://github.com/kunchenguid/backpass) gave this correction loop a
machine-learning frame. Backpass treats an agent session as a forward pass and the transcript as a
loss signal. I keep a human gate in that picture. I can find a gap in a transcript. I use that gap
to decide whether the correction describes a habit I want or an instruction that would make the
system worse.

## Staying in the thinking loop is hard

Agents work fast enough that I can fall out of the thinking loop while the work looks
productive. Things go wrong, the diff keeps growing, and accepting each edit becomes the easy
path. The agent has no trouble producing one more plausible edit. I have to keep enough of the
problem in my head to know whether that edit belongs.

The files in this repository help, but they do not remove that burden. They can make an agent show
evidence, stop at a boundary, or call for another reviewer. They cannot supply my judgment. If I
approve each step because the output looks polished, I have turned the setup into an elaborate way
to automate my own inattention.

I want the system to help me stay in the loop without making me the slowest part of each action.
That means short status updates, checks I can rerun, diffs that tell a coherent story, and explicit
human gates where the consequence deserves one. I need to use pstack's proof checks more. They are
one attempt to turn "I think this worked" into an artifact I can examine.

## The cost can outrun the gain

Fat skills consume context when they load. Long rules can conflict. An old anecdote can teach the
wrong behaviour after the code changes. An upstream update can alter a trigger. A generated
instruction file can drift away from its source.

I put limits and checks around those costs. The convention file has a line ceiling. Skills use
narrow descriptions. The installer checks metadata and pinned revisions. The canary in
`docs/INSTALL.md` asks each harness to reveal whether it loaded an expected phrase. None of that
makes the layer free.

I remove stale rules, review upstream changes, and keep private facts out of the portable
repository. I accept the bill because I spend more time operating agents than maintaining these
files. Another operator may get less value from the same trade.

The context can become the main source of error. More instructions create more chances for a
conflict, a missed trigger, or a procedure that survived past its use. I do not want a museum of
every lesson I have learned. I want a working set that earns its context cost.

## I have a falsifier

Harness teams may make this repository unnecessary. They may build strong personal memory,
procedure learning, role routing, and review isolation into their products. Models may infer my
method from a small history. Context prices may make heavy skills a poor bargain.

I would change my view if a harness reproduced my working method after I removed the portable
layer. I would test tasks that depend on my review rules, evidence format, private boundary, and
handoff style. If the bare harness matched the configured system's behaviour and failure rate, I
would have no case for this repository.

I would change my view if the skills caused more errors than they prevented. I can watch for
instruction conflicts, missed triggers, stale procedures, and time spent nursing the setup. A rise
in those costs would tell me that my in-context fine-tune had overfit the wrong things.

## The next experiment is an imperfection stack

I may call the next experiment `impstack`, short for imperfection stack. The name is another
metaphor. I want to embrace the humanness of the operator instead of designing as if a perfect human
will supervise a perfect agent.

I have not tested this idea. My guess is that an imperfection stack would record where my
attention fails. I want it to catch the moments when I accept an agent's work before I understand
it. A verification step might give me a useful grip on those moments. The tools might take shape
around those limits instead of assuming perfect attention.

For now, I am betting on a thin personal wrapper around strong models and fat skills that I own or
pin. The harness teams can work on generalisation. I can tune the context for one person. The model
keeps its frozen weights, while the analogy gives me a way to train the context around them.
