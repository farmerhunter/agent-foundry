---
id: COLLAB-009
title: Execution contracts gate Implementer work
domain: agent-collaboration
type: checklist
status: active
version: 3
created: 2026-06-07
updated: 2026-06-08
tags: [agent-collaboration, issue-contracts, handoff, branches, verification]
aliases:
  - COLLAB-009
  - Execution Contract
  - issue execution contract
related: [COLLAB-001, COLLAB-002, COLLAB-007, COLLAB-008, COLLAB-010, COLLAB-011, COLLAB-012]
applies_when:
  - moving a child issue to Ready for another agent
  - picking up a GitHub issue as Implementer
  - a task requires a specific branch base, PR target, dependency, or verification path
provenance: "Harvested from tiny-ipa M2/M3 workflow correction on 2026-06-07, where missing branch-base and review-handoff context confused Implementer pickup."
---

## Principle

An Implementer should not infer execution boundaries from scattered context. A ready issue must carry an explicit execution contract.

## Rationale

Agents can code quickly but are brittle around hidden workflow assumptions. If the issue does not say which branch to use, which PR base to target, which dependency gates apply, or what verification is required, another agent may choose a locally reasonable but globally wrong path. The fix is to make the Architect's decision durable and machine-readable in the issue before pickup.

## Guidance

Before moving an issue to `Ready`, the Architect should add:

```markdown
## Execution Contract

Branch strategy: epic integration branch | issue branch to main | stacked PR
Base branch: `...`
Target PR base: `...`
Depends on: #... / none
Role fit: evidence gathering | implementation | verification/review | taxonomy/architecture decision | policy decision | mixed
Architect-owned decisions: ...
Implementer boundary: ...
Expected PR shape: one PR for this issue
Completion handoff: close after evidence | move to Review | open PR | return to Architect | batch checkpoint
Merge rule: ...
Verification required: ...
```

Role fit is required when the issue includes classification, taxonomy, architecture boundary, policy, harvest, privacy, security, or future-system work. If the role fit is mixed, split the issue or state which decisions remain Architect-owned. Implementer evidence may include preliminary classification, but final taxonomy, policy, and architecture decisions need Architect review unless the contract explicitly delegates that authority.

Completion handoff is required when the work will be executed by another agent. If `Architect-owned decisions` is not `none`, the default handoff is `move to Review`: the Implementer posts completion evidence, removes `needs:implementer`, adds the next owner label, keeps the issue open, and sets Project/Roadmap status to `Review`. An Implementer may close the issue directly only when the contract explicitly says `close after evidence` and no downstream review or decision remains.

When the Implementer actually starts work, it should confirm:

```markdown
## Pickup confirmed

Branch strategy: ...
Working branch: `agent/<issue-number>-...`
PR base: `...`
Verification plan: ...
```

Use pickup confirmation only when dependencies are satisfied and implementation is starting. If the execution contract is missing, contradictory, or ambiguous, the Implementer should route the issue back to Architect instead of guessing.

## Use This When

- The issue will be executed by a different agent than the one that planned it.
- The branch strategy is not a trivial direct PR to `main`.
- The issue belongs to an Epic, queue, or dependency chain.
- Review feedback returned an issue to Implementer and the fix branch must be reused.
- The issue includes classification, taxonomy, architecture boundary, policy, harvest, privacy, security, or future-system judgment that could exceed a pure implementation role.
- The issue produces evidence or preliminary classification that another role must accept before downstream work can proceed.

## Watch Out For

- Do not treat an issue body with broad scope as a substitute for the execution contract.
- Do not let an Implementer create a new branch when the contract says to update an existing fix branch.
- Do not move an issue into an Implementer inbox until the contract includes enough information to start or queue safely.
- Do not let an Implementer make final taxonomy, architecture boundary, policy, harvest, privacy, or security decisions unless the Architect explicitly assigned that decision in the contract.
- Do not hand off a mixed issue as if it were pure implementation; split it or constrain the Implementer to evidence, preliminary classification, code edits, or verification.
- Do not write a closure rule that contradicts the review boundary. Evidence-only and preliminary-classification tasks should move to Review unless direct closure is explicitly delegated.

## Example

In tiny-ipa M3, each child issue was given a contract naming `epic/m3-core-audio` as both base branch and PR target, plus dependency gates. DeepSeek could then queue all M3 issues without the user relaying branch rules by hand.

## Activation

- Tier: workflow_embedded
- Phases: before_issue_handoff, pickup, review
- Signals: issue moved to Ready; `needs:implementer`; branch strategy decision; PR base ambiguity; dependency chain
- Evidence: identify the execution contract fields used, or state the issue lacks a contract and needs Architect action

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-002]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-010]]
- [[COLLAB-011]]
- [[COLLAB-012]]
