---
id: META-007
title: Native agent learning is candidate input
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [native-learning, memory, skills, hermes, governance]
aliases:
  - META-007
  - native skills can suggest but foundry canonizes
  - do not disable native self-growth
related: [META-001, META-003, META-006]
applies_when:
  - using Hermes native memory or self-improvement
  - importing agent-native generated skills
  - reconciling native agent learning with Agent Foundry
review_required: false
provenance: "Extracted from Hermes self-growth and Agent Foundry boundary discussion."
---

## Principle

Native agent learning should remain enabled and useful. Agent-native memories, auto-generated skills, self-improvement artifacts, and project-local instructions are candidate inputs for Agent Foundry, not replacements for it.

## Rationale

Systems such as Hermes may improve themselves through memory, skill creation, and local skill refinement. Disabling those capabilities would reduce the agent's local effectiveness. The risk is not native learning itself; the risk is letting native outputs silently become durable cross-agent truth without review, dedupe, provenance, and publication control.

## Guidance

Allow native agent systems to:

- remember local context;
- create or refine local skills;
- search session history;
- suggest repeated workflows;
- produce candidate procedures or prompts.

Route durable or cross-agent outputs through Agent Foundry:

- native memory finding -> `discover assets` or `harvest practices`;
- native generated skill -> `import skill <path>`;
- native usage insight -> `record_asset_usage.py`;
- native workflow improvement -> proposed canonical practice or asset update.

Do not deploy Agent Foundry in a way that disables Hermes memory, autonomous skill creation, or local self-improvement unless the user explicitly asks for a locked-down environment.

## Watch Out For

Avoid two failure modes:

- bypass: native generated skills become cross-agent assets without review;
- suppression: Agent Foundry instructions prevent a capable agent from using its native memory and self-improvement tools.

## Related Practices

- [[META-001]]
- [[META-003]]
- [[META-006]]
