# Adaptive Isolation for Bounded Collaboration

## Decision

Projects that explicitly enable bounded multi-agent collaboration adopt
`adaptive_isolation` as their default workspace policy. The policy allocates the
cheapest workspace that satisfies the current Work's write, concurrency, Epic,
and risk facts. It does not allocate one permanent worktree per role and does
not introduce a workspace manager service.

Adoption is forward-only. Existing branches and worktrees are inventoried and
handled separately; onboarding never deletes or rewrites historical state.

## User Experience

The common user intent remains one action: enable bounded multi-agent
collaboration for the project. After adoption, the system reports only:

- current Work and owner;
- selected workspace mode;
- status and next action;
- whether terminal cleanup is automatic or held.

Users do not need to choose worktree paths or manage role-specific checkouts.

## Frozen Invariants

1. **Single writer.** One Work has at most one writable branch/worktree owner.
2. **Durable recovery.** Unique work bytes reach a durable commit, PR, or ref
   before handoff or cleanup.
3. **Adaptive topology.** Workspace allocation follows Work facts, not role
   count.
4. **Terminal disposition.** Every Work ends as retained, reclaimed,
   `HOLD_REF`, or `QUARANTINE`, with an owner.
5. **Bounded reclamation.** Only exact, system-created task state that passes
   the standing cleanup policy may be reclaimed automatically.

An independent Hard Boundary finding is never downgraded by this policy.

## Workspace Selection

| Work facts | Default workspace mode |
| --- | --- |
| Read-only inspection | Current checkout; no branch or worktree |
| Serial low-risk edit; clean checkout; no active Epic overlap | Task branch in the current checkout |
| File-writing, concurrent Work, or Epic child Work | One task branch and one isolated worktree |
| Live, privacy/security, destructive, external-effect, `main`, or release Work | Isolated worktree plus only the independently justified evidence and Human gates |

If an Epic integration branch is active, a small edit still uses a child task
branch based on that Epic branch. The shared Epic checkout remains
coordination, integration, and readback only.

## Epic Integration Branches

Adaptive Isolation composes with `COLLAB-011`:

```text
main <- Epic integration branch <- child task branch/worktree
```

The Epic integration branch is durable shared integration authority. Accepted
child Work is merged into it and the child's execution state then becomes
reclaimable. The Epic branch is retained until its separate final `main`
integration and readback. Adaptive Isolation does not change branch policy or
turn the Epic branch into a writable task workspace.

## Work Contract

When workspace state matters, a Lean Work Contract records:

- `Work`: durable objective or issue binding;
- `Risk lane`: the facts that justify the selected mode;
- `Authority`: base, target, and current owner;
- `Workspace mode`: current checkout, task branch, or isolated worktree;
- `Outcome/scope`: the user-visible result and bounded change surface;
- `Evidence`: the proportionate review signal;
- `Terminal disposition`: retain, reclaim, `HOLD_REF`, or `QUARANTINE`.

The contract records decision-relevant facts, not exhaustive filesystem state.

## Lifecycle

```text
PLANNED -> ALLOCATED -> ACTIVE -> REVIEW -> MERGED_RECLAIMABLE -> RECLAIMED
```

Exceptional states:

- `HOLD_REF`: useful committed state exists, but merge or disposition remains
  open;
- `QUARANTINE`: dirty, divergent, ambiguous, unowned, or otherwise unsafe
  state requires a named owner and decision.

Role conversations may persist across Work. Worktrees are replaceable
execution state and must be reconstructable from the issue, commit, and PR
anchors.

## Trigger Reliability

The policy is evaluated at four existing events:

1. bounded-collaboration onboarding;
2. Work dispatch;
3. review or handoff;
4. terminal disposition.

Onboarding records the repository policy. Dispatch binds the current Work,
owner, write intent, concurrency/Epic overlap, base, target, and workspace mode.
An existing exact binding is reused idempotently. A conflicting binding holds
that Work without blocking unrelated Work.

No background daemon or periodic full-repository scan is required for normal
operation.

## Standing Reclamation Policy

Onboarding may approve a standing policy for exact system-created ephemeral
task state. Automatic reclamation requires all of these facts:

- exact Work, root, branch, and owner binding;
- accepted merge/readback or another durable recovery ref;
- no open PR, active owner, or live process;
- a clean worktree, or only explicitly accepted disposable cache;
- exact-target, non-force removal;
- absence readback and surviving authority readback.

Historical, dirty, divergent, integration/release, open-PR, unknown-owner, and
ambiguous state always requires explicit Human disposition. The policy never
authorizes wildcard deletion, force removal, pruning as repair, or history
rewrite.

## Adoption Results

Repository onboarding returns one of three simple results:

- `enabled`: Adaptive Isolation is recorded for new Work;
- `enabled_with_existing_state`: the policy is active, while historical state
  remains separately inventoried;
- `held`: ownership, authority, or policy cannot be established safely.

Enabling the policy does not claim that old workspace state has been cleaned.

## Proportional Review

- Low-risk docs, metadata, and mechanical changes normally need one bounded
  producer and one whole-change Reviewer.
- A separate Tester is added only for a distinct live, process, persistence,
  cross-environment, privacy/security, browser, device, or physical failure
  domain.
- A second substantive design failure triggers re-baselining rather than
  another repair layer.
- Human approval is reserved for actual Human-owned risk or product decisions,
  not routine branch/worktree mechanics already covered by repository policy.

## Non-Goals

This design does not add:

- a workspace manager, daemon, or database;
- per-role permanent worktrees;
- periodic exhaustive cleanup scans;
- a new branch authority beside Git and GitHub;
- mandatory Reviewer/Tester role chains for every Work;
- digest or evidence ceremony unrelated to a named trust boundary;
- retroactive cleanup of existing repository state.

Canonical ownership remains distributed across `COLLAB-009` for Work contracts,
`COLLAB-011` for Epic integration branches, `COLLAB-013` for worktree safety and
reclamation, and `COLLAB-017` for bounded-collaboration onboarding.

## Decision Record

The durable design and Harvest review list are tracked in
[issue #568](https://github.com/farmerhunter/agent-foundry/issues/568).
