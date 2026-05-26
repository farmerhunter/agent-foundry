---
name: architecture-design
description: Use when designing, reviewing, or refactoring software architecture; especially when choosing system boundaries, domain models, adapter layers, storage, UI separation, failure states, MVP scope, or technology choices.
---

# Architecture Design

Use this skill to guide architecture proposals and reviews.

## Default Process

1. Identify stable domain objects and states.
2. Identify independent axes of change.
3. Define boundaries before choosing tools.
4. Preserve meaningful domain differences instead of over-normalizing.
5. Model inevitable failures as explicit state.
6. Keep UI dependent on domain summaries, not raw integration data.
7. Scope MVP around the main path and key boundaries.
8. Choose technologies as boundary implementations.

Read `references/principles.md` for the compact rules and `references/checklist.md` before producing a design.

