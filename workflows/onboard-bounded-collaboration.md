# Onboard Bounded Collaboration

Use this workflow only when a user explicitly asks to prepare a project for
bounded collaboration. It is a project setup workflow, not a replacement for
normal per-Work dispatch.

## Scope

The legacy planner reads bounded metadata and returns a topology plan. It never
scans a transcript, invokes a native thread API, writes a Vault, changes a
repository, archives/deletes a thread, or creates a hidden registry authority.
It is not the completion authority for **开启多agent协作**.

For that first-use intent, use the owner-composed initialization contract. It
must read, in this order: the project binding owner; the scheduler/Work-root
owner; then the role-topology owner. Only those owner readbacks can establish
completion. Repository workflow text, a prompt, generated Skill text, role
names, caller JSON, or a caller-supplied scheduler reference are never proof
that collaboration is initialized.

The public runtime preflight is locator-only and read-only:

```text
python3 scripts/bounded_collaboration_runtime_bridge.py \
  --projects-root <ledger-owner-root> \
  --project-root <canonical-project-root> \
  --onboarding-key <opaque-key>
```

It discovers the active path/repository binding through LedgerStore and then
replays the scheduler/Work-root owner. It neither loads a topology plugin nor
accepts caller project, scheduler, receipt or apply claims. Ordinary invocation
therefore returns a typed unavailable/hold; it does not expose a topology plan,
install roles, or claim production `native_ready`. Only a trusted in-process
fixture owner may exercise plan composition, and that evidence is never a
runtime readiness claim. Native topology apply remains a separately approved
runtime boundary.

## State machine

`preflight -> repo_contract_only | unavailable | partial_hold | topology_plan_ready -> applying_topology -> verifying_completion -> native_ready | setup_incomplete`

`native_ready` requires one mutually bound fresh receipt containing: an
owner-verified project binding; exactly one active Coordinator and one active
Architect; and an owner-verified durable scheduler/Work-root binding. If the
scheduler or Work-root is missing, unavailable or ambiguous, stop before any
host role creation. Topology without that binding is a hold, not a success.

If ambiguity, a duplicate, legacy adoption, missing capability, privacy
violation, or a partial operation result is found, stop at:

`partial_hold -> rollback_planned -> rolled_back | rollback_incomplete`

`applying_topology` is only a reported receipt state. The Core composition
owner does not itself create native threads; an injected topology owner may
apply one separately authorized plan and must then be freshly reread.

## Preflight and plan

1. Obtain the project binding from its owner. It must provide one opaque project
   reference and digests for the project, repository and root; do not infer any
   of them from a transcript, native thread ID or caller input.
2. Obtain the durable scheduler/Work-root binding from its owner and prove that
   it binds the same project. This preflight is before topology planning or any
   host operation. Missing/ambiguous/unavailable binding is `repo_contract_only`,
   `partial_hold` or `unavailable`, never a fallback to role creation.
3. Check that role binding plus the RoleHub, current-thread, scheduler and
   transient-template projections are explicitly `supported`. Discover, create,
   rename, link and navigate capabilities must also be explicit. `unknown` and
   `unavailable` are fail-closed.
4. Reuse an active RoleHub only with an opaque RoleHub reference. Otherwise
   plan `rename_current_to_role_hub` only for an eligible current thread, or
   `create_role_hub`; each has a preimage, idempotency key and receipt. For
   each durable role, Coordinator and Architect, reuse exactly one active,
   non-legacy match. Zero matches produce one planned create; two or more
   matches are a duplicate hold. A legacy match is a historical reference,
   never an automatic adoption.
5. Implementer, Reviewer, Tester and Harvester are transient per-Work roles.
   Do not create them during project onboarding.
6. Give each planned discover/create/reuse/rename/link/navigate operation a
   preimage, deterministic idempotency key, operation fingerprint and receipt
   slot. Applied/failed receipts require a reference and matching fingerprint;
   unknown, duplicate or missing receipts are held. Preserve repository dirty
   state as metadata only.

## OnboardingSummary

The returned planner summary must include project identity; capability state
(`complete`, `partial`, `unavailable`, or `privacy_held`); reused, created,
unchanged and held entries; adapter-owned active navigation; historical
references; dirty-state preservation; and the next Human action. A `ready`
summary is only a planner result. It is never an initialization claim. The
owner-composed `OnboardingCompletionReceipt` is the only native completion
record; it binds fresh project, topology and scheduler/Work-root readbacks and
uses privacy-safe opaque refs/digests only.

When topology was applied during this attempt, its owner must additionally
return an opaque apply/readback commitment derived from the exact topology-plan
digest, operation-receipt digest, and final RoleHub/Coordinator/Architect plus
topology-readback identity. The final authoritative topology readback must
present that exact commitment. Validate it even if the invoked owner reports
zero mutation/reuse. A missing, changed, replayed or foreign binding is
`setup_incomplete`, not `native_ready`; preserve the applied receipt and do not
retry automatically.

For the same onboarding key, a retry never replays a cached success. Read the
current owner topology again and recompute its stored commitment against the
current project/scheduler digests and exact final identity. A topology
replacement, a missing/invalid operation receipt after a mutation, or any
commitment drift is a typed hold; it cannot be repaired by issuing another
create/reuse call.

The topology owner must also resolve the immutable original completion identity
for that key on every ready-topology path, not a caller cache. An absent record,
key collision or invalid stored receipt is a hold; do not create or overwrite a
successful record to make it pass. Each retry compares the current project,
scheduler/Work-root, approved plan and receipt refs, RoleHub, Coordinator,
Architect and topology readback one by one with that stored receipt. A wholly
self-consistent replacement is still a hold when it differs from the original
completion identity.

## Apply and rollback boundary

An adapter may execute only a `plan_ready` plan whose operation keys have been
explicitly approved. It must record one receipt per operation and read it back.
On the first failure, it must stop, preserve existing threads, mark
`setup_incomplete`, and return a reverse-order rollback plan for operations
with an applied receipt only. It restores preimages or marks attempt-created
objects incomplete; it never deletes or archives. Failure to read back a
rollback is `rollback_incomplete`.

Canonical practice apply, adapter publishing, runtime installation, transcript
migration, and project/release mutation are separate gates. The separate intent
“prepare this repo for multi-agent collaboration” remains repo-contract/bootstrap
work and cannot invoke native topology apply or claim `native_ready`.
