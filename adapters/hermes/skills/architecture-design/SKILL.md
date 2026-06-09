---
name: architecture-design
description: Use when designing, reviewing, or refactoring software architecture; especially when choosing system boundaries, layer taxonomy, domain models, adapter layers, storage, UI separation, failure states, MVP scope, or technology choices.
---

# Architecture Design

Asset ID: ASSET-ARCH-001.

Use this skill to guide architecture proposals and reviews, including layer taxonomy inventory for mixed systems and serviceability design when a system needs diagnostics, failure taxonomy, debug bundles, or agent handoff for fragile workflows.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices (ARCH-001 through ARCH-009, and DEBUG-001 for serviceability/debug artifact design) as behavioral constraints. Do not confuse the skill with the practices it applies.

## Default Process

1. Identify stable domain objects and states.
2. Identify independent axes of change.
3. Define boundaries before choosing tools.
4. For mixed or maturing systems, inventory current layers before designing target movement.
5. Classify paths, modules, records, generated outputs, runtime state, private state, and proposed design evidence by ownership and change behavior.
6. Mark ambiguous areas as `Mixed` or `Needs Architect Classification` instead of forcing premature final taxonomy.
7. If the design is centered on the current implementation path, run a boundary rewrite and substitution test.
8. Preserve meaningful domain differences instead of over-normalizing.
9. Model inevitable failures as explicit state.
10. Keep UI dependent on domain summaries, not raw integration data.
11. Scope MVP around the main path and key boundaries.
12. Maintain lightweight design docs as context contracts when boundaries, contracts, runtime behavior, or user experience change.
13. Before coding, write a reviewed implementation plan with concrete detail for the current phase (file structure, data flow, IPC contracts, acceptance criteria) and a directional sketch for future phases; review it adversarially to surface gaps.
14. When UI actions depend on multiple domain or workflow states, introduce a small interaction ViewModel and tests before reaching for a larger frontend framework.
15. For fragile integrations or parser/capture/import workflows, design diagnostics as agent-actionable reproduction artifacts: trace the flow, define stable failure reasons, avoid default raw-data persistence, and provide a debug bundle path to fixtures/tests.
16. Choose technologies as boundary implementations.

Read `references/principles.md` for the compact rules and `references/checklist.md` before producing a design.
