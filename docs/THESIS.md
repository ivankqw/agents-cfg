# impstack, imperfect operator.

## The analogy

```mermaid
flowchart LR
    subgraph FT[Fine-tuning]
        direction TB
        FM[Base model] --> FW[Weights updated] --> TM[Task-specific model]
    end
    subgraph IR[This repo]
        direction TB
        HM[Harness + model] --> CA[Context added] --> OA[Operator-specific agent]
        CA --- CO[Conventions]
        CA --- SK[Skills]
        CA --- AG[Agents]
        CA --- CF[Configs]
        CA --- HO[Hooks]
    end
    FT ~~~ IR
```

The right side is a metaphor. Nothing trains, and no weight changes. The analogy helps me think
about in-context learning as a personal fine-tune that I can read and edit.

## Performance vs generalisation

```mermaid
quadrantChart
    x-axis Broad fit --> One-operator fit
    y-axis Low generalisation --> High generalisation
    quadrant-1 Broad and personal
    quadrant-2 General defaults
    quadrant-3 Weak fit
    quadrant-4 Personal overfit
    Harness teams: [0.25, 0.85]
    Me: [0.85, 0.25]
```

I assume harness teams evaluate across many users and repositories. I can accept less
generalisation because my target distribution is one operator, me.

## Method cards on the factory floor

```mermaid
flowchart BT
    subgraph FF[Factory floor]
        direction BT
        subgraph TH[Thin harness]
            direction LR
            LO[Loop] --- ME[Memory] --- HK[Hooks] --- PE[Permissions]
        end
        subgraph MC[Skills: method cards]
            direction LR
            PR[Procedures] --- ST[Failure stories] --- ER[Evidence rules]
        end
        TH --> MC --> OP[Operator]
    end
```

Garry Tan calls this
["thin harness, fat skills"](https://github.com/garrytan/gbrain/blob/master/docs/ethos/THIN_HARNESS_FAT_SKILLS.md).
I treat skills as method cards on the factory floor, not the factory.

## The correction loop

```mermaid
flowchart LR
    SE[Session] --> TR[Transcript] --> BR[Backpass or reflect]
    BR --> ED[Proposed edit] --> GA[Operator gate]
    GA --> CS[Convention or skill] --> NS[Next session]
    NS --> SE
```

Kun Chen's [backpass](https://github.com/kunchenguid/backpass) gave me the forward-pass and loss-signal
frame. A transcript can expose a failure. I use the gate to choose the habit I want.

## The thinking-loop problem

```mermaid
flowchart LR
    subgraph TD[Today]
        AF[Agent runs fast] --> AC[Operator accepts] --> AT[Skill atrophies]
    end
    subgraph IH[Untested hypothesis]
        JG{Junction gate} --> EB[Explain back] --> DD[Diff the diff]
        DD --> OR[Operator returns] --> JG
    end
    TD ~~~ IH
```

I have not tested `impstack`, short for imperfection stack. The hypothesis puts friction at the
junctions where I lose track of the work and accept the agent's answer.

## What would make me stop

```mermaid
block-beta
    columns 2
    SG["Signal"] WD["What I do"]
    BM["Bare harness matches"] RL["Remove the layer"]
    SE["Skills cause errors"] SS["Shrink or stop"]
```

These are my falsifiers. I am assuming I can measure them across repeated tasks. A good session
tells me little.
