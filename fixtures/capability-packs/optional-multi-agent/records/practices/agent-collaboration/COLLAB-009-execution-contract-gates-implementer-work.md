---
id: COLLAB-009
title: Execution contracts gate Implementer work
domain: agent-collaboration
type: checklist
status: active
version: 22
created: 2026-06-07
updated: 2026-08-31
tags: [agent-collaboration, issue-contracts, handoff, branches, verification, transition-gates, approvals, scope-lock, capability-boundary, proportionality, lean-delivery, adaptive-isolation]
aliases:
  - COLLAB-009
  - Execution Contract
  - issue execution contract
related: [COLLAB-001, COLLAB-002, COLLAB-007, COLLAB-008, COLLAB-010, COLLAB-011, COLLAB-012, PROD-003, TEST-005]
applies_when:
  - moving a child issue to Ready for another agent
  - picking up a GitHub issue as Implementer
  - a task requires a specific branch base, PR target, dependency, or verification path
  - applying or removing a `needs:*` label
  - routing work to Reviewer, Architect, Harvester, or human decision
  - choosing whether exact paths, a separate Tester, or a repeated Human gate are proportionate to the current Work
provenance: "Harvested from tiny-ipa M2/M3 workflow correction on 2026-06-07, where missing branch-base and review-handoff context confused Implementer pickup; v11 adds risk-classified main merge and meaningful user-facing human gate fields after tiny-ipa M7 dogfood. v12 adds explicit risk-reason requirements for contracts that are stricter than repo default auto-merge policy after tiny-ipa #173/#178 docs-only auto-merge miss. v13 adds AF10-B human-gate live-response and coordination-cost routing refinements. v14 adds related visible-item semantics inventory as a gate for user-facing metrics, statuses, and affordances after tiny-ipa M11 Progress feedback. v15 adds explicit tool-approval versus Human-gate boundaries after AF15 role threads repeatedly blocked on ordinary GitHub operations; v17 adds AF18 scope-lock and capability-lane boundaries. v18 harvests the bounded operational-equivalence repair and blocker-admission rules from Agent Foundry #560 and #561. v19 harvests W10 M7/M8 Lean Delivery dogfood from Agent Foundry #567. v20 adds the Adaptive Isolation workspace and terminal-disposition fields approved in Agent Foundry #568. v21 clarifies the Lean Delivery mechanical bring-up and semantic repair budgets after the approved Agent Foundry #571 harvest."
review_required: true
---
## Principle

Make a Work ready by recording enough current decisions for its next owner to act without guessing. A contract is a compact execution agreement, not a mandatory form or a new authority. Scale detail and review to the consequence of failure.

## Rationale

Missing scope, ownership or handoff sends fast implementation in the wrong direction. Repeating every possible gate for every Work creates the opposite failure: progress stalls on evidence mechanics. Keep the ordinary path short, add only relevant clauses, and preserve the explicit limits of an already-released contract.

## Guidance

### Ordinary Work contract

Read existing issue/repo/Epic instructions first and reference decisions already recorded. For a bounded Work, make these facts clear in prose or the existing template:

- Outcome and scope: one user-visible result; in-scope path family and excluded effects.
- Authority and owner: current decision owner, writer, dependencies, and decisions not delegated.
- Workspace and delivery: base, target PR branch, writer binding and chosen workspace mode.
- Evidence: public behavior, meaningful failure, focused checks and accepted residuals.
- Handoff: next owner, review mode, merge/closure rule and terminal workspace disposition.

An ordinary implementation must be runnable from that agreement. Missing consequential authority or a contradictory dependency returns to the decision owner; a missing decorative heading does not. For lower-risk local code/docs, exact changed paths may freeze at review within the agreed path family/scope cap. Freeze exact targets earlier for destructive, live, privacy/security or other protected effects.

Separate only the lanes implicated by the change: code, canonical data, generated output, runtime activation, Project operations and evidence may have different owners. Do not enumerate unrelated lanes as mandatory work. Preserve a stop condition against implicitly expanding into an unavailable lane.

For adopted bounded collaboration, use a read-only current checkout for inspection, a clean task branch for serial low-risk edits without Epic overlap, and one isolated task worktree for writable Epic-child, concurrent or other non-exempt work. Keep one writer per Work. COLLAB-011 owns Epic branch preference; COLLAB-013 owns editing, rebind and cleanup safety. Choose retain, reclaim after authorized readback, HOLD_REF or QUARANTINE at handoff; readiness does not require deleting history.

### Review, repair and stop

Use the cheapest route that supplies the required signal. A single-session low-risk change may use clearly labelled self-review when the contract allows it. A bounded lower-risk change normally needs one independent whole-change Reviewer; add a separate Tester only for a materially different process, persistence, live-provider, privacy/security, browser, device or cross-environment observation. Do not call the same test command under a different role evidence independence.

For architecture, trust, privacy/security, destructive operations and final transitions, retain the specialist and Human decisions justified by those effects. COLLAB-001 governs permission; COLLAB-003 governs delegated merge. Do not override an explicit hold or contract prohibition by calling it over-conservative.

A blocker must identify the prevented error, consequence, violated outcome/invariant or Hard Boundary, missing proof, cheapest relevant correction and residual risk. Data loss, unauthorized or incorrect external mutation, credential/privacy/security exposure and invalid trust crossing cannot be downgraded to meet a deadline. Speculative extra guarantees do not block the accepted goal.

Classify failed evidence before changing the product: product behavior, Collector/test expectation, or external environment/binding. Keep substitute evidence honestly labelled. If a real prerequisite cannot be substituted, record one resume condition and stop same-environment permutations or speculative implementation.

The repair budget counts semantic changes, not every unpublished bring-up edit:

- Syntax/import/cwd/PYTHONPATH/collection/fixture/runnable-doc/validator-oracle corrections are mechanical only while outcome, owner, authority, public API, path family, dependencies, assertions, evidence meaning and capability claim remain unchanged.
- Mechanical corrections must not skip, xfail, deselect, filter, weaken assertions, substitute evidence, or add a dependency/path family. Reach a green unpublished checkpoint before presenting the candidate.
- Ownership, currentness, receipt truth, Mission transition, cancellation/retry/lifecycle, process/persistence or dependency changes are semantic. Use one consolidated semantic repair and one re-review as the normal budget.
- A second substantive failure returns the goal, invariants, scope and proof plan for re-baselining, never a safety waiver. Repeated mechanical-looking failures that expose omitted production callers, exports, runnable docs, validators or path inventory also need that correction, not a serial patch chain.

Ordinary code identity is the base, reviewed/tested candidate head, merged tree, changed paths and semantic readback. Add byte digests only for a named immutable-artifact, privacy/security, supply-chain or forensic boundary. A historical manifest does not impose perpetual byte equality on a valid successor.

### Handoff without role churn

A next role is a responsibility, not necessarily a new session. Record the producing artifact, verification/residuals and next decision before changing routing labels. Use current repository field mappings rather than inventing a second Project status.

| Handoff | Required meaning |
| --- | --- |
| Ready / needs:implementer | Dependencies satisfied; executable scope, authority, branch and checks available |
| move to Review / needs:reviewer | Named review target, candidate, focus, checks, expected result and forbidden actions; real dispatch evidence or fallback if another session is needed |
| return to Architect / needs:architect | The unresolved architecture, taxonomy, Harvest, policy or acceptance decision is explicit |
| needs:human | A concrete user-owned decision, options, recommendation, consequences, verification, risk and approval phrase are visible both durably and in chat |
| close after evidence | Closure is expressly delegated and no later acceptance remains |
| batch checkpoint | Explicit contract opt-in lets the producer continue only the authorized dependency-bounded batch; Architect decisions remain at the agreed checkpoint |
| open PR | A deliverable, not automatic merge permission or an automatic Architect inbox |

Remove a needs label only after the transition evidence exists. A plain "please review" does not identify the next owner. Existing contracts do not acquire batch/auto-merge/operational-equivalence permission from a newer practice. For legacy contracts without a batch handoff, return through the ordinary per-issue Architect review rather than silently continuing the queue.

At actual pickup confirm the task branch/base, dependencies and checks briefly. A blocked dependency is queued/held, not a fictitious pickup. Architecture or policy work can use delegated self-review only when explicitly permitted, low-risk, objectively checked and labelled; it never becomes independent ACCEPT.

### User-visible and protected work

For UI/status/workflow changes, bind the primary scenario, starting state, action semantics and the related visible items that share a user question or transition, even across pages. Name the domain or ViewModel owner, where the next action lives, and the representative walkthrough. Do not demand a whole-page inventory when one cluster is affected; do not treat an actionability defect as copy-only work.

Separate objective verification from subjective product acceptance. Add Human trial only when required by the actual decision/contract; state what to try and judge. Do not invent scores or a new trial gate, or repeat acceptance for materially unchanged content. COLLAB-015 owns closure claims and remaining activation evidence.

A protected-operation supplement names exact approved effects/targets, preconditions, stop/recovery and the required independent observation. Surface the Human decision basis before its phrase. A tool approval is not a second product gate, and availability of a tool is not product authorization.

### Explicit operational-equivalence exception

This is not a blanket extension of mechanical bring-up. An already-released Work may opt in literally and non-retroactively to one correction in exactly one dimension: test collection/loading, runtime binding to the same registered worktree, or one exact source-to-target git worktree move.

For a test-command correction, executable preflight binds unchanged sources/config/tooling and exact file-qualified node-set equality; no skip/filter/deselection/xfail, ordering/concurrency, fixture, coverage or warning-policy change. For worktree correction, bind repository/common-dir/registry, HEAD/base/branch/index, candidate diff and untracked state, applicable submodule/LFS state and Work/role identity; verify the disposable writable-root probe and absence readback. Use digests only where this opted-in evidence identity requires them; regenerable caches are classification/count evidence.

Record the before/after result. Content, dependencies, config/API/schema/fixture/evidence semantics or Hard-Boundary changes are outside this exception. Ambiguity, a second repair, multiple dimensions or failed/partial movement returns to Architect with no automatic retry or alternative reconstruction. The ordinary unpublished mechanical budget does not grant worktree moves, live retries or relaxation of an exact one-pass contract.

## Use This When

Prepare/pick up/handoff a Work; route review; choose review effort; classify a failed check or repair; or interpret an explicitly opted-in operational-equivalence exception. Do not require an Execution Contract to answer an ordinary informational question.

## Watch Out For

- Respect an old Work's exact limits until its authorized owner changes them.
- Missing approval rationale is not authority to merge; missing optional form fields is not a safety defect.
- Do not grant broad queue draining or auto-resume from one child handoff.
- Never mistake an accepted design, dispatched message or fixture result for deployed user capability.

## Example

A documentation fix names the affected docs family, current base, one writer, link/consistency checks and one Reviewer. It needs no device test or new telemetry. A cleanup task separately names exact targets and recovery; the docs contract does not grant cleanup.

## Activation

- Tier: workflow_embedded
- Phases: planning, pickup, handoff, review
- Signals: authorizing/executing a Work; contract ambiguity; choosing review effort; substantive repair; explicit operational_equivalence
- Evidence: the next owner can act within the scope, checks and handoff; missing consequential decisions are visible

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-002]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-010]]
- [[COLLAB-011]]
- [[COLLAB-012]]
- [[PROD-003]]
- [[TEST-005]]
