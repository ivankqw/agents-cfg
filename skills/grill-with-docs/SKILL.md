---
name: grill-with-docs
description: Grill a plan or decision while grounding every factual claim in current documentation. Use when stress-testing a design that rests on how a library, API, or cloud service actually behaves.
disable-model-invocation: true
---

# Grill with docs

Two moves, in order.

1. Invoke the `grilling` skill and work its rounds.
2. Before accepting any claim about how a library, framework, SDK, CLI, or cloud service behaves,
   look it up — context7 first (`resolve-library-id`, then `query-docs`), web search only if context7
   has no entry. Quote the doc line next to the claim it settles.

A claim about external behaviour that no one looked up is an assumption. Mark it as one.
