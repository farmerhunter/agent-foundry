---
id: COLLAB-017
title: Onboard a bounded collaboration project
domain: agent-collaboration
type: playbook
status: active
version: 6
created: 2026-08-05
updated: 2026-09-18
tags: [agent-collaboration, onboarding, bounded-collaboration, logical-role-directory, privacy, human-handoff, adaptive-isolation, pending-identity, fresh-only, peer-handshake]
aliases:
  - COLLAB-017
  - bounded project collaboration onboarding
  - one-time collaboration onboarding
  - 开启多agent协作
  - public runtime-composition onboarding
  - coordinator architect native topology
  - logical role directory projection
related: [COLLAB-016, COLLAB-001, COLLAB-002, COLLAB-009, COLLAB-011, COLLAB-013]
applies_when: A project explicitly asks for one-time preparation to use bounded multi-agent collaboration by default.
review_required: true
provenance: AF18 #497/#500 and #515; Human-approved canonical onboarding apply plus successful metadata-only Codex host dogfood; #548 owner-composed public runtime preflight boundary; v5 adds forward-only Adaptive Isolation adoption from Agent Foundry #568; v6 harvests fresh-only pending-identity and peer-handshake failure evidence from 2026-09-17 native onboarding dogfood.
---

## Principle

Make project onboarding a visible, one-time preparation step. The normal durable native topology is Coordinator + Durable Architect. Route the explicit first-use intent `开启多agent协作` to the public runtime-composition preflight, inspect the owner-bound project, produce a deterministic plan and OnboardingSummary, and, after separate explicit native-apply authorization, verify only those two durable roles before daily collaboration begins.

## Rationale

Onboarding prepares the two durable coordination roles that have ongoing responsibility. Implementer, Reviewer, and Tester remain Work-scoped and on demand. RoleHub is an optional logical read-only role-directory/front-door projection derived from owner receipts and scheduler/Work state; it is not a native thread, scheduler, controller, authority, telemetry store, or readiness prerequisite. A successful plan is not proof that native threads exist, so a separately authorized metadata-only host apply must verify reuse or creation, naming, and same-object readback. Keeping this apply separate from Work dispatch, Vault publication, runtime activation, and main/release preserves user control, privacy, and a clear failure boundary.

## Guidance

- Route the explicit first-use intent `开启多agent协作` to the public, locator-only runtime-composition preflight. It accepts only `projects_root`, `project_root`, and `onboarding_key`, reads owner-backed project and scheduler/Work-root bindings, and returns a plan, completion readback, or typed hold. The ordinary public path is read-only: unavailable topology ownership is a hold, not an invitation to create native roles.
- Keep repository bootstrap a distinct intent. A repository contract, prompt, or bootstrap result does not establish owner-backed onboarding completion and must not be substituted for the runtime-composition preflight.
- Accept only explicit onboarding intent. Run a read-only preflight and produce a plan, summary, or fail-closed hold.
- Reuse or propose fresh deterministic Coordinator and Durable Architect role records only when identity and capability are unambiguous. Legacy, duplicate, ambiguous, missing-capability, privacy, dirty-preservation, partial-operation, or rollback-incomplete states must hold with the next Human action.
- When native apply is explicitly authorized, materialize or reuse only Coordinator and Durable Architect; set or verify each requested title only after a preimage check, then read back the same objects. Treat a successful receipt as host metadata proof, not RoleHub activation.
- A pending creation handle is not a durable role identity. Do not message peers or claim initialization until the public owner surface resolves and reads back the final identity. If no public capability can resolve a pending handle, return a typed HOLD and do not repeat creation.
- Make the reuse policy explicit. Under `fresh_only`, do not inspect, read, reuse, rename or archive historical role sessions; create exactly the two requested durable roles once and leave all old state untouched. A `reuse_allowed` path may inspect only the public owner surface and must hold on ambiguity.
- A peer handshake is optional post-onboarding proof when explicitly requested. It must bind both final identities and one token through explicit reply targets and fresh readback. It is not scheduler, GitHub, Work-dispatch or merge authority.
- Keep RoleHub logical. Derive any role-directory or front-door projection from owner receipts and scheduler/Work state. Do not create a native RoleHub thread or use one as scheduler, controller, authority, telemetry store, or readiness evidence.
- Treat a pre-existing RoleHub-titled thread as non-authoritative metadata. Do not adopt, rename, delete, or use it to satisfy readiness.
- Until matching owner-composed runtime evidence is integrated and installed, report the native onboarding path as unavailable or held; do not fall back to the old three-thread claim.
- If navigation or another host primitive is unavailable, report the exact fallback state and continue only within the approved metadata boundary; do not infer that the missing capability exists.
- Keep Work roles transient. Do not materialize Implementer, Reviewer, Tester, or Harvester threads as part of onboarding.
- Record `adaptive_isolation` as the repository's forward-only default workspace policy for new bounded Work. Return `enabled`, `enabled_with_existing_state`, or a typed `held` result; do not require the user to select worktree paths.
- Treat existing branches and worktrees as separate inventory. Onboarding does not delete, rewrite, adopt, or claim cleanup of historical state.
- Bind new writable Work to one owner and one writable task branch/worktree. Delegate workspace selection and terminal reclamation to `COLLAB-009`, `COLLAB-011`, and `COLLAB-013`; do not create a second scheduler, branch authority, workspace manager, or daemon.
- Native create, reuse, rename, link, navigate, delete, archive, history scan, migration, and hidden registry or Vault writes remain separately bounded operations. A separately approved adapter-owned plan/apply gate is required for native operations; this practice covers only minimal create/reuse and owner-readback proof. Fresh-only onboarding authorizes none of the historical-state operations.
- Preserve project history and dirty changes. Do not retain raw transcripts, prompts, tool output, identities, secrets, or other private session content in onboarding records.
- Treat the OnboardingSummary as a handoff, not proof that native operations succeeded. It must name the plan, holds, Human action, evidence, and residual risk.

## Activation

- Tier: task_router
- Phases: explicit onboarding intake, public runtime-composition preflight, plan handoff, Human review
- Signals: `开启多agent协作`, project requests one-time collaboration setup, missing durable Coordinator/Architect role records, onboarding hold
- Evidence: owner-backed project and scheduler/Work-root preflight, deterministic plan, OnboardingSummary, repository workspace-policy result, and any separately authorized native-operation receipt with accepted, initialized, optional acknowledged and ready states, readback, fallback, and privacy-safe metadata only

## Watch Out For

- This practice does not create a native RoleHub thread, link or navigate a RoleHub authority, delete or archive history, scan transcripts, write hidden registries, write the Vault, publish adapters, activate runtime behavior, or claim rollback success.
- The public runtime-composition preflight is not native completion. Native topology apply remains a separate trusted, in-process permit-bound operation with owner readback; a missing, stale, or unavailable owner state must remain a typed hold.
- A plan or summary is not an active collaboration session. Daily behavior starts only after the separately authorized native apply and target-project readback.
- Do not silently repair legacy or ambiguous state; hold and name the next Human decision.
- Do not turn a pending handle into an identity by scanning private sessions, databases or transcripts. Do not create a replacement merely because public resolution is unavailable.

## Example

When a project asks to start bounded collaboration, the Coordinator checks the durable project records and reports whether Coordinator and Architect identities are uniquely reusable. It returns a plan and OnboardingSummary. If the project has duplicate legacy role records, onboarding holds and asks the Human to choose; it does not rename or delete anything.

## Review Notes

Approved for canonical publication under AF18 #500 and harvest-extended from #515. Revised after #548 clarified that host thread lifecycle APIs do not provide RoleHub control semantics. Native navigation, Work dispatch, runtime activation, and adopter-facing smoke remain separate gates.

Adaptive Isolation is an onboarding default for future Work, not proof of historical cleanup or a global requirement for repositories that have not adopted bounded collaboration.

## Related Practices

- [[COLLAB-016]]
- [[COLLAB-001]]
- [[COLLAB-002]]
- [[COLLAB-009]]
- [[COLLAB-011]]
- [[COLLAB-013]]
