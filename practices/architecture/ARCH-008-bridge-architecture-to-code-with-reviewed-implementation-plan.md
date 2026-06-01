---
id: ARCH-008
title: Bridge architecture to code with a reviewed implementation plan
domain: architecture
type: playbook
status: active
version: 1
created: 2026-06-01
updated: 2026-06-01
tags: [architecture, implementation, planning, review, cross-agent]
aliases:
  - ARCH-008
  - implementation plan as bridge
  - review plan before code
related: [ARCH-001, ARCH-006, ARCH-007]
applies_when:
  - transitioning from architecture/design docs to writing code
  - handing off design intent to another agent or future self
  - the architecture has multiple layers or processes that must agree on contracts
provenance: "Harvested from token-panic implementation planning session (2026-06-01), where a reviewed implementation plan surfaced adapter boundary violations, missing preload files, and data path inconsistencies before any code was written."
---

## Principle

Insert a concrete, reviewed implementation plan between architecture design and code. Make it detailed enough to surface missing files, wrong boundary assignments, and protocol gaps that abstract architecture docs cannot catch.

## Rationale

Architecture docs define principles, boundaries, and domain models at an abstract level. Code is fully concrete. Between them, there is a gap where architectural intent can silently diverge from implementation reality:

- An architecture doc says "adapter only fetches data," but the implementation plan reveals the adapter is also reading storage.
- An architecture doc says "IPC uses contextBridge," but the file structure has no preload script.
- An architecture doc says "data lives in Application Support," but the implementation plan puts it in a repo-local directory.

These gaps are cheap to fix in a plan document and expensive to fix in code. An implementation plan at the right level of detail — file structure, data flow with decision branches, IPC contracts, and acceptance criteria — surfaces them before the first line of code is committed.

The plan also serves as a reviewable artifact. Another agent or human can read it and ask: "Does this actually follow the architecture?" without needing to infer intent from code.

## Guidance

1. Write the implementation plan after architecture docs are stable enough to define boundaries, but before writing substantial code.
2. Use a **detail gradient**:
   - Current phase: specify file structure, data flow with error branches, IPC channels (with direction and payload), storage layout, and acceptance criteria.
   - Future phases: describe only incremental goals and target user experience. Do not pre-specify their file structure or data flow.
3. Have the plan reviewed adversarially. Ask: does every architectural boundary survive translation to concrete files and data flow? Are any files missing? Does any component cross a boundary it shouldn't?
4. Evaluate each review finding with an explicit disposition (accept, partial accept, reject with reason) before merging.
5. Merge accepted changes into the plan before starting implementation.
6. Treat the plan as a living document during the phase — update it if implementation reveals a necessary deviation.

## Use This When

- Architecture docs are written and the team is about to start coding.
- The system has multiple processes, layers, or IPC boundaries where contracts must align.
- Multiple agents will implement from the same design.
- The architect and implementer are different people (or different agents).

## Watch Out For

- Do not over-specify future phases. A directional sketch for Phase N is sufficient; concrete detail for Phase N is premature until Phase N-1 is done.
- Do not let the plan become a waterfall specification. It is a bridge document, not a contract — update it when implementation reveals necessary changes.
- Do not skip the review step. The plan's primary value is surfacing gaps before code; unreviewed, those gaps survive into implementation.
- Do not duplicate architecture rationale in the plan. The plan references architecture docs; it does not re-argue them.

## Example

In token-panic, the implementation plan specified for Phase 1:

- Exact file structure (17 files across main/renderer/shared)
- Data flow with four branches (has key, no key, 401, network error)
- 7 IPC channels with direction and payload types
- 10 acceptance criteria

Codex review of this plan found 5 issues: data path inconsistency with architecture docs, adapter boundary violation (adapter reading storage), missing preload file, ConfigPanel scope ambiguity, and auto-update scope creep. All were fixed in the plan document before any code was written.

The detail gradient meant Phase 1 was implementable immediately, while Phases 2-7 were described in 3-5 lines each — enough to ensure Phase 1 design didn't block them, but not so much that re-planning would be wasted work.

## Related Practices

- [[ARCH-001]] — boundaries before tools; the plan verifies boundaries survive translation to code
- [[ARCH-006]] — MVP validates main path; the plan's Phase 1 detail enforces this
- [[ARCH-007]] — design docs as context contracts; the implementation plan is a specific type of context contract for the architecture→code transition
