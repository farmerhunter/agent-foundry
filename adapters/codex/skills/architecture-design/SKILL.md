---
name: architecture-design
description: Use when designing, reviewing, or refactoring software architecture; especially when choosing system boundaries, domain models, adapter layers, storage, UI separation, failure states, MVP scope, or technology choices.
---

# Architecture Design

Asset ID: ASSET-ARCH-001.

Use this skill to guide architecture proposals and reviews, including serviceability design when a system needs diagnostics, failure taxonomy, debug bundles, or agent handoff for fragile workflows.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices (ARCH-001 through ARCH-008, and DEBUG-001 for serviceability/debug artifact design) as behavioral constraints. Do not confuse the skill with the practices it applies.

## Default Process

1. Identify stable domain objects and states.
2. Identify independent axes of change.
3. Define boundaries before choosing tools.
4. If the design is centered on the current implementation path, run a boundary rewrite and substitution test.
5. Preserve meaningful domain differences instead of over-normalizing.
6. Model inevitable failures as explicit state.
7. Keep UI dependent on domain summaries, not raw integration data.
8. Scope MVP around the main path and key boundaries.
9. Maintain lightweight design docs as context contracts when boundaries, contracts, runtime behavior, or user experience change.
10. Before coding, write a reviewed implementation plan with concrete detail for the current phase (file structure, data flow, IPC contracts, acceptance criteria) and a directional sketch for future phases; review it adversarially to surface gaps.
11. For fragile integrations or parser/capture/import workflows, design diagnostics as agent-actionable reproduction artifacts: trace the flow, define stable failure reasons, avoid default raw-data persistence, and provide a debug bundle path to fixtures/tests.
12. Choose technologies as boundary implementations.

Read `references/principles.md` for the compact rules and `references/checklist.md` before producing a design.
