# Onboard Bounded Collaboration

Use this workflow only when a user explicitly asks to prepare a project for
bounded collaboration. It is a project setup workflow, not a replacement for
normal per-Work dispatch.

## Scope

The planner reads metadata supplied in its input and returns a plan. It never
scans a transcript, invokes a native thread API, writes a Vault, changes a
repository, archives/deletes a thread, or creates a hidden registry authority.
The adapter that performs an approved plan remains the authority for native
thread identifiers and navigation.

## State machine

`preflight -> plan_ready -> applying -> ready`

If ambiguity, a duplicate, legacy adoption, missing capability, privacy
violation, or a partial operation result is found, stop at:

`partial_hold -> rollback_planned -> rolled_back | rollback_incomplete`

`applying` is only a reported receipt state. The Core planner does not itself
perform an operation.

## Preflight and plan

1. Bind a project by its explicit `project_id`, repository and integration
   branch. Do not infer it from a transcript or a native thread ID.
2. Check that role binding plus the RoleHub, current-thread, scheduler and
   transient-template projections are explicitly `supported`. Discover, create,
   rename, link and navigate capabilities must also be explicit. `unknown` and
   `unavailable` are fail-closed.
3. For each durable role, Coordinator and Architect, reuse exactly one active,
   non-legacy match. Zero matches produce one planned create; two or more
   matches are a duplicate hold. A legacy match is a historical reference,
   never an automatic adoption.
4. Implementer, Reviewer, Tester and Harvester are transient per-Work roles.
   Do not create them during project onboarding.
5. Give each planned discover/create/reuse/rename/link/navigate operation a
   preimage, deterministic idempotency key, operation fingerprint and receipt
   slot. Applied/failed receipts require a reference and matching fingerprint;
   unknown, duplicate or missing receipts are held. Preserve repository dirty
   state as metadata only.

## OnboardingSummary

The returned summary must include project identity; capability state
(`complete`, `partial`, `unavailable`, or `privacy_held`); reused, created,
unchanged and held entries; adapter-owned active navigation; historical
references; dirty-state preservation; and the next Human action.

## Apply and rollback boundary

An adapter may execute only a `plan_ready` plan whose operation keys have been
explicitly approved. It must record one receipt per operation and read it back.
On the first failure, it must stop, preserve existing threads, mark
`setup_incomplete`, and return a reverse-order rollback plan for operations
with an applied receipt only. It restores preimages or marks attempt-created
objects incomplete; it never deletes or archives. Failure to read back a
rollback is `rollback_incomplete`.

Canonical practice apply, adapter publishing, runtime installation, transcript
migration, and project/release mutation are separate gates.
