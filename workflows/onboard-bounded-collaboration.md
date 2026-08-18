# Onboard Bounded Collaboration

Use this workflow only when a user explicitly asks to prepare a project for
bounded collaboration. It is a project setup workflow, not a replacement for
normal per-Work dispatch.

## Scope

Normal onboarding uses the RH1 public locator-only runtime-composition
preflight below and, only after separate trusted authorization, the
owner-composed native apply path. The legacy planner is a read-only
compatibility diagnostic/router: a closed v1 request returns only the closed v2
`owner_composed_route_required` result or a typed hold. It never returns a
topology, mutation, or rollback plan; performs no dispatch or apply; and never
reports readiness. It is not the completion authority for
**开启多agent协作**.

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

The trusted native boundary is deliberately not a CLI feature. A trusted
in-process runtime first obtains the read-only I1 plan, then supplies an opaque,
non-serializable, one-shot permit to a distinct permit-bound topology owner for
the second I1 call. The permit is never present in a plan, receipt, JSON, file,
environment, configuration or public output. It binds the fresh canonical
project UUID, project/root mapping digests, scheduler binding, exact plan,
runtime/host identities and the fixed fresh-operation budget: at most two
`thread/start` calls and two `thread/name/set` calls, one each for Coordinator
and Durable Architect. This is not a global thread limit. Existing unrelated
threads and later Work-scoped Implementer, Reviewer, and Tester threads remain
allowed. RoleHub is an optional logical read-only projection, not a native
thread or readiness prerequisite; this workflow never discovers, creates,
reuses, renames, links, or navigates it. Missing, expired, replayed or drifted
permits hold before the receipt store or host is touched. An exact completed
retry uses only the unbound read-only owner and performs no native mutation.

Before the protected topology receipt store is even opened, the owner validates
the owner-derived lowercase UUID and digest mapping and resolves only
`<projects-root>/<project-id>/role-topology.db`; symlinks, escapes, malformed
identity, absent project authority or mapping drift are holds. Thread title or
cwd is never a project-binding fallback.

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
3. Read the owner-backed native topology. A fresh default operation owns only
   Coordinator and Durable Architect. Reuse an exact completed owner receipt
   without mutation; plan only the missing pair when no protected receipt or
   partial legacy state conflicts with the fresh operation.
4. Treat legacy three-role protected receipts as read-only migration holds.
   Do not auto-adopt, delete, rename, or reinterpret them. RoleHub state,
   current-thread eligibility, caller capability reports, and caller receipts
   neither block nor establish owner-composed readiness.
5. Keep Implementer, Reviewer, and Tester Work-scoped. Their later threads are
   outside the fresh default onboarding operation and its 2-start/2-name
   budget.
6. Preserve repository dirty state as metadata only. Unknown owner state,
   ambiguous native results, privacy exposure, or partial mutation holds
   without automatic retry, adoption, or caller-directed repair.

## Diagnostic route and completion receipt

The legacy planner returns only the closed v2 compatibility route or typed
hold. Its empty operations and rollback operations are diagnostic facts, not an
apply surface. It accepts, infers, executes, and serializes no locator values;
the caller must supply `projects_root`, `project_root`, and `onboarding_key`
freshly to the public runtime bridge.

The owner-composed `OnboardingCompletionReceipt` is the only native completion
record. It binds fresh project, topology, and scheduler/Work-root readbacks and
uses privacy-safe opaque refs/digests only. RoleHub projection state is absent
from this authority and cannot satisfy readiness.

When topology was applied during this attempt, its owner must additionally
return an opaque apply/readback commitment derived from the exact topology-plan
digest, operation-receipt digest, and final Coordinator/Architect plus
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
scheduler/Work-root, approved plan and receipt refs, Coordinator, Architect and
topology readback one by one with that stored receipt. A wholly
self-consistent replacement is still a hold when it differs from the original
completion identity.

## Apply boundary

The legacy planner has no apply or rollback boundary. It cannot authorize an
adapter, native host, or caller receipt. After the RH1 locator-only preflight,
only the separately authorized trusted in-process owner may consume its
one-shot permit and apply the owner-composed two-role plan. A partial or
ambiguous native result is `setup_incomplete`; preserve its protected receipt
and do not retry, adopt, delete, or manufacture a rollback plan.

Canonical practice apply, adapter publishing, runtime installation, transcript
migration, and project/release mutation are separate gates. The separate intent
“prepare this repo for multi-agent collaboration” remains repo-contract/bootstrap
work and cannot invoke native topology apply or claim `native_ready`.
