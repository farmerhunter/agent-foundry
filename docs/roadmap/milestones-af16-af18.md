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

## AF-18: Bounded Collaboration Control Plane

Goal: make Agent Foundry's multi-agent collaboration cost-aware, bounded, portable, and human-controllable before it becomes an assumed runtime substrate.

The user-facing capability is **Bounded Collaboration**. Internally, AF18 is the
**Contract-Driven Collaboration Control Plane**: explicit contracts and durable
receipts make collaboration predictable without implying trusted runtime
observation that is not available.

AF18's user value is direct: any environment that already applies the multi-agent-collaboration practice should transparently receive bounded, human-controllable collaboration. Users do not opt into an "AF18" product mode or need to understand AF18 internals. GitHub remains the durable authority; active execution contexts should be bounded and replaceable.

AF18's completed user-facing slice is the bounded collaboration path. It is deliberately honest about unavailable runtime metrics while still enforcing the contract-driven controls that do not depend on those metrics: bounded Work, ownership, duplicate prevention, hold/disable, logical successor packets, Human summaries, durable terminal handoff, and candidate-only learning capture. This slice becomes part of the existing multi-agent-collaboration practice after Human-approved canonical practice application, adapter publish, and one adopter dogfood/readback. It does not require a separate AF18 opt-in.

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
- `RoleConversation`: a stable Human-facing relationship to one role.
- `ContextWindow`: a bounded context within a `RoleConversation`, joined to its
  successor by a privacy-safe capsule rather than by full chat history.
- `RoleHub`: one optional project-level projection and entry directory for all
  roles. It is not a role-specific thread, policy authority, telemetry store,
  or execution controller.

Every role uses the same Human-continuity model:

```text
RoleConversation -> ContextWindow -> role operation
```

For Coordinator, the role operation is a coordination operation; the
`CoordinatorSession` / `CoordinationWindow` names describe that specialization,
not a second competing lifecycle. A RoleConversation may span many Issues.

Project work remains:

```text
Issue -> Work -> ExecutionRun
```

Do not force every role operation to become one Human-visible Work. A Work is
created or bound only when an Issue contract requires bounded execution,
evidence, acceptance, or routing.

The Core defines the continuity semantics, capsule exclusions, successor
relationship, and state invariants. An adapter measures context and maps a
ContextWindow to a native mechanism. For Codex, a context refresh may require
creating a successor thread, passing the capsule plus durable anchors,
confirming it is usable, marking the predecessor `superseded`, and repointing
the RoleHub entry. The predecessor is not deleted or blindly archived. If an
adapter cannot perform that transition, it must expose one recovery path rather
than pretend the old thread has lost its history.

### AF18 Policy Layers

Do not collapse policy layers:

- Current `low_limit` is emergency containment and readback protection.
- Three provisional policy-v0 profiles exist as static/read-only policy source
  and Human readout. They are not a final policy freeze, auto-tuning, or
  activation; calibration and a Human policy-freeze decision still determine
  any normal operating policy.
- `EffectiveControlSnapshot` records the exact source/version/band, window/root-budget constraints, measurement rules, and stop conditions used by a released literal contract.
- Runtime receipts record facts; they do not self-tune policy.

If a future run uses [#442](https://github.com/farmerhunter/agent-foundry/issues/442)
values, label the evidence `low_limit_experiment`, not normal operation.
`low_limit` remains emergency-only and does not prove a normal operating
default, policy final freeze, auto-tuning, or activation.

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
| MVP-2 low-limit experiment context | [#451](https://github.com/farmerhunter/agent-foundry/issues/451) / [PR #455](https://github.com/farmerhunter/agent-foundry/pull/455) (`a148b8c4f20c75a58b7f60db221c323f7f6e9ca8`) | static/read-only | Static/reference low-limit experiment context only; it does not prove trusted context observation, normal operating thresholds, or activation readiness. |
| MVP-3 dogfood | #452 | Accepted and closed | Supplies bounded dogfood evidence; it does not freeze normal policy or authorize activation. |
| Post-MVP operational readiness | #454 | Accepted and closed | Decomposes calibration, policy freeze, RoleConversation/adaptor successor transition, recovery/rollback, LearningSignal harvest input, limited rollout, and final readiness. |
| Unavailable trusted-observation evidence | [#467](https://github.com/farmerhunter/agent-foundry/issues/467) / [PR #468](https://github.com/farmerhunter/agent-foundry/pull/468) | trusted live evidence required | The proposed observation bridge is unavailable evidence, never a successful bridge; it does not prove trusted live context observation. |
| Calibration evidence | [#457](https://github.com/farmerhunter/agent-foundry/issues/457) / [PR #466](https://github.com/farmerhunter/agent-foundry/pull/466) (`d6b628d32a17fb3628db4a48bdae4f11ef975759`) | static/read-only | Closed historical calibration input only: `context_age_hours` and `total_context_tokens` are unavailable/not_exposed, so this does not prove normal numeric calibration or a final policy freeze. |
| Policy freeze HDC | [#458](https://github.com/farmerhunter/agent-foundry/issues/458) | candidate-only | A candidate Human decision path for normal policy and rollback conditions; it does not prove a frozen policy, auto-tuning, or activation. |
| RoleConversation/adaptor successor | [#459](https://github.com/farmerhunter/agent-foundry/issues/459) / [PR #475](https://github.com/farmerhunter/agent-foundry/pull/475) (`637c422f73bc2d2cba76d64bcbb425aed69f55fe`) | static/read-only | Merged static deterministic dry-run controls; they do not prove a real Codex capability, live UX, or activation. |
| Recovery/rollback readiness | [#460](https://github.com/farmerhunter/agent-foundry/issues/460) / [PR #475](https://github.com/farmerhunter/agent-foundry/pull/475) (`637c422f73bc2d2cba76d64bcbb425aed69f55fe`) | static/read-only | Merged static deterministic dry-run controls; they do not prove a real Codex capability, live UX, or activation. |
| LearningSignal harvest contract | [#461](https://github.com/farmerhunter/agent-foundry/issues/461) | accepted Core + durable handoff | Accepted Core identity/index contract plus privacy-safe Work terminal handoff and candidate-only persistence; it is not automatic Harvest or publication authorization. |
| Provisional policy source/readout | [#469](https://github.com/farmerhunter/agent-foundry/issues/469) / [PR #473](https://github.com/farmerhunter/agent-foundry/pull/473) (`8ab846e19b268281899aa8c4747f50c08b7862ec`) | static/read-only | Static portable policy-source and Human readout only; it does not prove runtime enforcement, final freeze, or activation. |
| Privacy-safe telemetry aggregation | [#470](https://github.com/farmerhunter/agent-foundry/issues/470) / [PR #474](https://github.com/farmerhunter/agent-foundry/pull/474) (`6a6a3bc3fdf621d27a4c7b43b8366dbb890a45a4`) | static/read-only | Static privacy-safe telemetry-aggregation only; it does not prove a trusted live telemetry channel or activation. |
| W10 provisional-policy evidence | [#471](https://github.com/farmerhunter/agent-foundry/issues/471) | local deterministic/reference only | W10 local deterministic/reference-only evidence; it is not trusted live evidence or a formal Harvest. |
| Provisional-policy no-change hold | [#472](https://github.com/farmerhunter/agent-foundry/issues/472) (CLOSED) | static/read-only | No-change hold retains provisional policy-v0 and forbids parameter divergence or final freeze without a new Human HDC; it does not prove a new policy or activation. |
| Limited real-mode rollout | [#462](https://github.com/farmerhunter/agent-foundry/issues/462) | AF19 candidate / held | Full trusted-metrics real-mode rollout is no longer an AF18 MVP gate. The bounded collaboration controls are usable through the existing collaboration practice; #462 moves to AF19 for trusted observation, calibration, and higher-order rollout evidence. |
| Parent Epic/readiness | #418 / #426 / #427 | AF18 transparent integration | #418 remains the Epic authority; #426 applies the accepted collaboration practice and publishes selected adapters; #427 performs one adopter dogfood/readback. Trusted runtime and production gates move to AF19. |

### AF18 Next Gated Work

The remaining AF18 route is deliberately user-facing and transparent:

1. Human approves the canonical collaboration-practice application.
2. Selected adapters publish that practice to environments that already use
   multi-agent collaboration; there is no separate AF18 opt-in.
3. One adopter runs a bounded dogfood and readback through #427.

Trusted runtime observation, P3/P4 evidence, normal-policy calibration/freeze,
native successor/runtime activation, and main/release are AF19 enhancement
gates. They must not block the AF18 bounded collaboration path.

Until these gates are explicitly accepted:

- Do not resume #435's old pre-reset implementation route.
- Do not treat #442 values as normal Coordinator/session policy.
- Do not release #426/#427 or main/release without their Human gates.
- Do not activate runtime/config/hooks, generated publish, external execution,
  final AF18 readiness, final policy freeze, auto-tuning, or activation.

### AF18 Cleanup Rules

Older AF18 issues may be closed or superseded only after compact evidence comments, not by silent label cleanup:

- #435 is stale as an active implementation route and should not keep `needs:implementer`.
- #444/#445/#433/#436/#432 need narrow closure/supersession packets before closing.
- #452 and #454 are complete evidence/design inputs.
- #426/#427 remain AF18 integration/adopter gates; #418 remains the AF18 Epic
  authority. AF19 owns the trusted-runtime and production gates.

### AF18 Acceptance Criteria

AF18 is complete when:

- the integration branch contains all accepted AF18 code and docs;
- MVP-1, MVP-2, and MVP-3 are accepted in order;
- the historical/reference evidence in #457 and #469-#471 is retained with its non-trusted status;
- the bounded collaboration control path is integrated into the existing multi-agent-collaboration practice;
- a Human approves the canonical practice application and the selected adapters are published;
- one adopter dogfood/readback confirms the transparent default user experience;
- metrics remain explicitly `unavailable/not_exposed`, with no unsupported cost, model, auto-tuning, or enforcement claims;
- the AF18 integration branch contains all accepted AF18 code and docs.

The explicit readiness matrix is:

| Record | Milestone | Lifecycle | Roadmap status |
| --- | --- | --- | --- |
| #457 | AF-18 | Done | Done |
| #458 | AF-19 | Active | Blocked |
| #462 | AF-19 | Active | Blocked |
| #469-#471 | AF-18 | Done | Done |
| #493 | AF-19 | Active | Ready |
| #494 | AF-19 | Active | Blocked |

AF18 completion does not imply trusted runtime metrics, normal policy freeze, native successor activation, Vault migration, production/main release, or V2 local-first orchestration completion. Those belong to AF19 or later independent gates.

## AF-19: Adaptive and Observed Collaboration

AF-19 is the follow-on milestone for capabilities that exceed AF18's transparent bounded collaboration path. It must not block AF18 adoption by existing multi-agent-collaboration environments.

AF19 scope:

- a trusted runtime-owned producer for context age, token consumption, and effective model/reasoning mapping;
- calibration evidence and a Human-approved normal policy freeze;
- native successor/runtime activation and full real-mode rollout evidence for [#462](https://github.com/farmerhunter/agent-foundry/issues/462);
- production activation, generated publish beyond the AF18 adopter path, and final main/release readiness.

AF19 does not include the deferred selected-Vault SQLite/shadow lane in [#492](https://github.com/farmerhunter/agent-foundry/issues/492); that remains an optional, separately reopened storage-architecture effort.
