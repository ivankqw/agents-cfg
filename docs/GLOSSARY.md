# Glossary

This reference fixes one meaning for each term used in the documentation.

## Agent system

**Base model.** The harness and the model treated as one starting system. Claude Code with Claude is
one base model. Codex with an OpenAI model is another.

**Harness.** The program that runs the model, gives it tools, manages context, and controls the work
loop. Claude Code and Codex are harnesses in this repository.

**Convention.** A rule that each agent session receives through an instruction file. The portable
conventions live in `conventions/AGENTS.md`.

**Skill.** A Markdown procedure that an agent loads for a matching task. A skill can contain steps,
examples, checks, and judgment that would cost too much context in a convention.

**Fat skill.** A skill with enough examples, constraints, and failure cases to guide judgment during
a task. The term describes context depth rather than file size.

**Own skill.** A skill maintained in this repository under `skills/`.

**Upstream skill.** A skill maintained in another repository. This repository records its source in
`skills-lock.json` or pins its source revision in `pstack-revision.txt`.

## Work roles

**Config.** A named set of model and effort choices for each role. The YAML files under `configs/`
define the available configs.

**Role.** One responsibility in a stretch of agent work.

**Orchestrator.** The role that holds the plan and makes decisions.

**Implementer.** The role that builds from an explicit brief.

**Reviewer.** The role that attacks a finished change. The reviewer must not share model weights
with the implementer when another model is available.

**Lane.** One independent stream of work or review. Two lanes can run against the same fixed commit
for different purposes.

## Installation and state

**Hook.** A program that a harness runs for a configured event. Hooks can add advice even when the
model would not choose to load a skill.

**Lockfile.** The live JSON state that the `skills` CLI writes. It contains source data and machine
state such as timestamps, hashes, and interface choices.

**Catalog.** The planned committed list of upstream skills. Each entry keeps `source`, `sourceType`,
`sourceUrl`, and `skillPath`.

**Portable layer.** The methods and tools that can move between jobs and machines. This repository
holds the portable layer.

**Private layer.** The employer, host, person, and domain details that must stay outside the portable
layer. `install.sh` reads this layer from `~/agents-cfg-private` or `$PRIVATE_CONFIG`.

