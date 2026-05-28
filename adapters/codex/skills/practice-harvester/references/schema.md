# Practice Schema Reference

Canonical source: `schemas/practice-entry.schema.yaml`

Required frontmatter:

```yaml
id:
title:
domain:
type:
status:
version:
created:
updated:
tags:
```

Domains:

- `meta`: Agent Foundry capability lifecycle governance.
- `governance`: Cross-project source-of-truth, maintainability, durable-record, and runtime-capability constraints.
- `architecture`: System design, boundaries, domain modeling, and change management.
- `runtime`: Safe local runtime deployment and synchronization.
- `agent-collaboration`: Human/agent/GitHub collaboration.
- `implementation`: Implementation-level coding hazards.
- `testing`: Verification obligations.

Recommended frontmatter:

```yaml
aliases:
related:
supersedes:
superseded_by:
applies_when:
review_required:
provenance:
```

Required sections:

- `Principle`
- `Rationale`
- `Guidance`

Recommended activation section:

```text
## Activation

- Tier: always_preflight | task_router | workflow_embedded | review_only | reference_only
- Phases: planning, before_edit, verification, final_report
- Signals: semicolon-separated trigger signals
- Evidence: what the agent should report or record when the practice is applied
```

Only `active` and `revised` entries are published into default adapters.

Do not put a practice under `meta` only because it is abstract. Use `meta` only for Agent Foundry capability lifecycle rules. Use `governance` for cross-project operating constraints.

Only `always_preflight` practices belong in the compact preflight kernel. Do not add every practice to global adapter text.
