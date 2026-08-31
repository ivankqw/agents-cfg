---
name: ponytail
description: Use only when the user explicitly names Ponytail or asks to use the ponytail skill. Do not invoke it for ordinary coding, refactoring, review, design, or general simplification requests.
license: MIT
---

# Ponytail

Apply one opt-in simplification pass to the current request. Do not make this a persistent mode.

Read the relevant requirements and code first. Then stop at the first option that meets the request:

1. Remove work that the request does not require.
2. Reuse a suitable project function or pattern.
3. Use the standard library or a native platform feature.
4. Use a suitable dependency that the project already has.
5. Make the smallest correct change and leave a runnable check.

Keep pstack as the default routing workflow. Preserve the requested outcome and fix root causes.

Existing acceptance criteria, verification rules, security controls, accessibility requirements, and
operator boundaries override simplification advice. Project limits and measured behavior override
generic thresholds.

Concept inspired by [Ponytail](https://github.com/DietrichGebert/ponytail) at
`2ed6c52c9d7e5e56942508591085fd45dea277d3`, provided upstream under the MIT License. This skill uses
original concise instructions for this configuration.
