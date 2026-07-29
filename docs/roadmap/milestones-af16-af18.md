# Roadmap Milestones AF-16 Through AF-18

This file contains detailed AF-16 through AF-18 collaboration-control plans moved out of `docs/roadmap.md` to keep the main roadmap readable.

Return to the main roadmap: ../roadmap.md

## Why These Stages Belong Together

AF-16, AF-17, and AF-18 are one collaboration-control path:

1. AF-16 makes collaboration branch-aware so work lands on the right line.
2. AF-17 makes generated Skills load only relevant canonical practice context.
3. AF-18 makes multi-agent collaboration bounded, cost-aware, portable, and human-controllable.

Do not merge these stages into the AF-13 through AF-15 file. AF-13 through AF-15 are V1.x capability and workflow additions. AF-16 through AF-18 are the post-V1 collaboration safety and control path that determines whether larger V2 and multi-agent work can proceed without branch drift, context bloat, or stale role-thread execution.

## AF-16: Branch-Aware Collaboration And Safety

Goal: make issue and PR work branch-line aware so V1.x maintenance, V2 integration, AF18 integration, stacked PRs, and custom branch policies cannot silently mix.

AF-16 is V1.x maintenance. It does not authorize live repair, PR retarget, checkout switching, merge, reset, or Project mutation. It gives agents and humans a read-only branch-readiness surface and safe action plan.

Accepted outputs:

- Execution Contracts use `Branch strategy`, `Target branch`, `PR target`, affected branches, verification branches, and forward-merge expectations.
- Branch readiness distinguishes `mainline-maintenance`, `integration-branch`, `release-branch`, `trunk-based`, `stacked-pr`, `multi-branch`, and `custom`.
- The collaboration helper reports wrong PR base, stale checkout, dirty worktree, branch-line drift, and unsupported repair without applying fixes.
- Docs explain when work should split, when current checkout is safe, and when Architect/Human routing is required.

Current status: completed as collaboration helper and docs maintenance. The exact issue table should be refreshed from GitHub after API quota is available; current Core behavior is represented by `scripts/github_collaboration_helper.py`, `docs/multi-agent-collaboration.md`, and `workflows/github-collaboration-helper.md`.

Acceptance criteria:

- Branch-sensitive work is not pickup-ready without an explicit branch contract.
- V1.x maintenance defaults to `main`.
- V2 work defaults to `codex/v2-local-first-orchestration`.
- AF18 work defaults to `codex/af18-collaboration-cost-policy-integration`.
- The helper remains read-only for branch repair and reports unsupported actions instead of executing them.

## AF-17: Semantic Practice Loading And Adapter Reachability

Goal: reduce irrelevant runtime context while preserving canonical practice authority.

AF-17 is V1.x maintenance. It improves generated Skill behavior so collaboration and architecture work can route to the right canonical practice references without loading every practice into every thread.

Accepted outputs:

- Generated Skills expose semantic practice routes instead of unconditional large context packs.
- Full practice references remain reachable when their route condition applies.
- Adapter packaging preserves canonical source metadata and generated-reference reachability.
- Tests catch missing generated references or stale route declarations.

Current status: completed as semantic practice loading and generated Skill reachability maintenance. The exact issue table should be refreshed from GitHub after API quota is available; current behavior is represented by generated Skill route declarations and reachability tests.

Acceptance criteria:

- Agents can run thin preflights first and load deeper practices only when signals require them.
- Generated adapters preserve canonical practice IDs and source paths.
- Missing or stale generated references fail validation instead of silently dropping authority.
- Runtime context is reduced without making practice authority ambiguous.

## AF-18: Collaboration Cost-Control And Control Plane

Goal: make Agent Foundry's multi-agent collaboration cost-aware, bounded, portable, and human-controllable before it becomes an assumed runtime substrate.

AF18's user value is direct: a user should be able to run multi-agent collaboration without losing control of token growth, branch target, role ownership, duplicate dispatches, successor context, or Human attention. GitHub remains the durable authority; active execution contexts should be bounded and replaceable.

AF18's design is `Codex-first, portable-core`:

- GitHub issues, PRs, comments, labels, and exact SHAs are the current durable authority binding.
- Codex is the only MVP runtime/dogfood adapter.
- Core semantics stay portable; native Codex task, visible-thread, or subagent ids are adapter metadata.
- The active AF18 integration branch is `codex/af18-collaboration-cost-policy-integration`.
- Future AF18 PRs target the integration branch unless a specific Human Decision Contract authorizes direct-to-`main`.

### AF18 Control-Plane Concepts

AF18 Core owns these portable concepts:

- `Work`: one bounded objective/root budget normally anchored to one issue.
- `ExecutionRun`: one execution context within a Work.
- `DispatchClaim`: idempotent claim for a semantic transition boundary.
- `SuccessorPacket`: compact cursor-only continuation packet for successor context.
- `TransitionReceipt`: privacy-safe control-plane evidence for a transition.
- `WorkSummary`: compact Human-facing projection of current objective, owner, decisions, evidence, risk, and next action.
- `AttentionSummary`: Human-facing projection only for material attention events.
- Resource observations with `observed`, `estimated`, or `unavailable` provenance; unavailable is never zero.

Coordinator internals are modeled separately:

```text
CoordinatorSession -> CoordinationWindow -> coordination operation
```

Project work remains:

```text
Issue -> Work -> ExecutionRun
```

Do not force every Coordinator operation to become one Human-visible Work.

### AF18 Policy Layers

Do not collapse policy layers:

- Current `low_limit` is emergency containment and readback protection.
- Future resource profiles such as economy/normal/performance require dogfood calibration and Human policy freeze.
- `EffectiveControlSnapshot` records the exact source/version/band, window/root-budget constraints, measurement rules, and stop conditions used by a released literal contract.
- Runtime receipts record facts; they do not self-tune policy.

If a future run uses #442 values, label the evidence `low_limit_experiment`, not normal operation.

### AF18 Issue Path

Current canonical path:

| Step | Record | Status | Meaning |
| --- | --- | --- | --- |
| Emergency reset | #439 | Accepted reset authority | Retire ultra-long role threads from live execution and use bounded durable role set. |
| Hard low-limit gate | #440 / PR #441 | Completed | Fail closed on missing or excessive low-limit context/budget controls. |
| Threshold policy | #442 / PR #443 | Completed | Define emergency `low_limit` bands; not normal operating policy. |
| Cost evidence baseline | #432 / #433 | Historical/design input | Token-growth evidence and initial cost-aware collaboration design inputs. |
| Runtime-owned capture | #436 / #446 / #447 | Superseded input to MVP path | Runtime-owned observation evidence informed #449/#451. |
| Integrated MVP scope | #449 | Accepted and closed | Defines bounded MVP path, portability, Human attention, and roadmap to calibration/freeze. |
| MVP-1 control plane | #450 / PR #453 | Completed | Static/read-only portable control-plane and Human summary proof. |
| MVP-2 observation bridge | #451 | Current Human gate | Release only with literal `EffectiveControlSnapshot`; Option A is low_limit experiment, not normal policy. |
| MVP-3 dogfood | #452 | Held | Starts only after #451 is accepted. |
| Post-MVP operational readiness | #454 | Dependency-held | Starts only after #450/#451/#452 have independent acceptance evidence; reconciles calibration, policy freeze, adapter enablement, Human UX, recovery/rollback, limited rollout, and final readiness. |
| Parent Epic/readiness | #418 / #426 / #427 | Held | Final publish/runtime activation/readiness remain later gates. |

### AF18 Current Active Gate

Current active decision is #451:

- Option A: release #451 as a bounded `low_limit_experiment` with literal `EffectiveControlSnapshot`.
- Option B: hold #451 until a normal operating policy exists after dogfood calibration and Human freeze.

Until #451 is resolved:

- Do not release #452.
- Do not release #454.
- Do not resume #435's old pre-reset implementation route.
- Do not treat #442 values as normal Coordinator/session policy.
- Do not activate runtime/config/hooks, generated publish, external execution, final AF18 readiness, or policy freeze.

After #450, #451, and #452 have independent acceptance evidence, #454 becomes
the Architect reconciliation gate for post-MVP operational readiness. #454 must
keep #418 as the sole AF18 Epic/roadmap authority, treat #449 as the MVP
decision record rather than a replacement roadmap, and reconcile #426/#427
without releasing, closing, or rewriting them by implication.

### AF18 Cleanup Rules

Older AF18 issues may be closed or superseded only after compact evidence comments, not by silent label cleanup:

- #435 is stale as an active implementation route and should not keep `needs:implementer`.
- #444/#445/#433/#436/#432 need narrow closure/supersession packets before closing.
- #426/#427/#451/#452/#454/#418 remain open gates.

### AF18 Acceptance Criteria

AF18 is not complete until:

- the integration branch contains all accepted AF18 code and docs;
- MVP-1, MVP-2, and MVP-3 are accepted in order;
- post-MVP operational readiness is reconciled through #454;
- runtime-owned observation proves availability/provenance/fail-closed behavior;
- dogfood produces calibration evidence without self-tuning policy;
- Human reviews and freezes any normal operating policy;
- final activation/publish/readiness gates are explicitly accepted.

AF18 completion does not imply V2 local-first orchestration completion, memory-system implementation, generated adapter publish, runtime activation, or direct-to-main merge.
