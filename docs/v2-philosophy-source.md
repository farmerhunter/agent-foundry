# Agent Foundry V2 Philosophy Source Package

This is an Agent Foundry-specific evidence package for later Human authorship.
It is not Philosophy V2, a canonical practice, a Vault postimage, or authority
to publish adapters or mutate runtime state. Its evidence window begins at the
V1.0 cutoff and ends with the accepted W2 snapshot; the bounded source contract
and seven allowed themes are recorded in the
[#538 prerequisite design](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5338285102).

## Historical evidence

| Theme | Representative durable evidence | What happened |
| --- | --- | --- |
| Core/Vault/Generated/Runtime authority separation | [AF18 lessons #524](https://github.com/farmerhunter/agent-foundry/issues/524) | Work repeatedly exposed that product code, canonical user knowledge, downstream adapters, host connectors and runtime activation have different owners and gates. |
| SQLite authority versus mirrors/projections | [ORCH-04 final-readiness readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458) | The accepted single-machine path retained SQLite owner authority while GitHub, Project and Board surfaces stayed native facts, read-only views or non-authoritative projections. |
| Capability truthfulness and evidence boundaries | [owner-recorded status observation](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327633432) | The public status path reported accepted owner state and explicitly left native reachability unchecked, preventing local completion evidence from becoming a live-host claim. |
| Minimum Responsible Architecture | [architecture evidence #560](https://github.com/farmerhunter/agent-foundry/issues/560) | Review of assurance-driven complexity produced a bounded architecture approach with frozen invariants and a two-substantive-REVISE circuit breaker. |
| Restricted operational-equivalence repair | [governance evidence #561](https://github.com/farmerhunter/agent-foundry/issues/561) | Execution-contract preflight separated environment or mechanics repair from product-boundary changes and required a hard-boundary return when equivalence could not be preserved. |
| Branch/worktree durability and cleanup separation | [worktree lifecycle evidence #562](https://github.com/farmerhunter/agent-foundry/issues/562), [AF18 lessons #524](https://github.com/farmerhunter/agent-foundry/issues/524) | Issue, commit, PR and receipt formed durable authority; worktrees remained replaceable execution state, with HOLD/QUARANTINE classification separated from destructive cleanup. |
| Risk-based Human gates and durable onboarding | [ORCH-04 final-readiness readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458), [AF18 lessons #524](https://github.com/farmerhunter/agent-foundry/issues/524) | Durable Coordinator and Architect owner records were accepted without giving RoleHub authority, while product, privacy, runtime, destructive and final-release decisions kept explicit Human gates. |

## Accepted principles

- Preserve Core, selected Vault, Generated and Runtime as separate authorities
  and lifecycle gates; a Core change does not silently authorize canonical or
  runtime mutation ([#524](https://github.com/farmerhunter/agent-foundry/issues/524)).
- Keep Base Agent Foundry as the supported/default stateless or GitHub-first
  practice/asset/issue/PR layer. For Local Orchestration, use SQLite as the only
  collaboration authority for fresh or existing single-machine projects; do
  not promote mirrors or projections into authority
  ([ORCH-04 readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458)).
- Report capability at the evidence class actually observed. Owner-recorded
  `native_ready` with `native_reachability=not_checked` proves the accepted
  local owner record, not live App Server/thread reachability or cross-host
  continuity
  ([status observation](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327633432)).
- Prefer Minimum Responsible Architecture: freeze the few invariants that protect
  the outcome, and rebaseline after two substantive REVISE cycles instead of
  ratcheting assurance machinery indefinitely
  ([#560](https://github.com/farmerhunter/agent-foundry/issues/560)).
- Permit only restricted operational-equivalence repair after executable
  preflight; return to the hard boundary when the proposed repair changes the
  product contract or cannot preserve observable behavior
  ([#561](https://github.com/farmerhunter/agent-foundry/issues/561)).
- Treat worktrees as replaceable execution state. Make HOLD recoverable from a
  committed ref, use QUARANTINE for unique or ambiguous bytes, and keep
  promotion/reconciliation separate from Human-gated deletion
  ([#562](https://github.com/farmerhunter/agent-foundry/issues/562)).
- Use Human gates in proportion to consequence. Durable two-role onboarding can
  be owner-recorded without creating RoleHub authority; final `main`, tag,
  release, destructive, privacy/security, canonical and runtime decisions stay
  separately gated
  ([ORCH-04 readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458),
  [#524](https://github.com/farmerhunter/agent-foundry/issues/524)).

## Residual limitations

- The accepted owner receipt records `native_reachability=not_checked` and
  `mutation_performed=false`; live App Server/thread access, current host-process
  reachability and cross-host continuity therefore remain unproven
  ([status observation](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327633432)).
- A0-Lite is experimental same-host/manual-custody evidence only. A0-Real,
  real second-device/cross-host operation, device-loss resilience, independent
  credentials/failure domains, hostile-device trust, transport, source unlock
  after an unreturned transfer and convergence remain deferred
  ([ORCH-04 readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458),
  [ORCH-05 #551](https://github.com/farmerhunter/agent-foundry/issues/551)).
- Static, fixture, walkthrough and controlled-local evidence prove only their
  named contracts. UX/usability, performance/latency/scale, real-adopter
  friction, real-device resilience, production readiness and release readiness
  remain unknown, not collected, unavailable or not exposed unless later
  durable evidence establishes them
  ([ORCH-04 readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458)).
- Open [#548](https://github.com/farmerhunter/agent-foundry/issues/548) and
  [#549](https://github.com/farmerhunter/agent-foundry/issues/549) preserve
  historical defect and governance state, but the accepted retained-authority
  evidence means their open state is not an unresolved current capability
  blocker
  ([ORCH-04 readback](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5327657458)).

## Future hypotheses

- Hypothesis: real two-device evidence may justify A0-Real only after independent
  credentials/failure domains, device loss, hostile-device trust, transport,
  unreturned-transfer recovery and convergence are observed rather than
  inferred from A0-Lite
  ([ORCH-05 #551](https://github.com/farmerhunter/agent-foundry/issues/551)).
- Hypothesis: real adopter use may expose usability, latency, scale and friction
  requirements that controlled-local evidence cannot predict; those measurements
  need a separately reviewed evidence contract
  ([ORCH-04 #543](https://github.com/farmerhunter/agent-foundry/issues/543)).
- Human gate: a later author decides whether and how this source becomes
  Philosophy V2 prose. Source acceptance does not accept canonical Vault
  postimages or a new taxonomy
  ([#564](https://github.com/farmerhunter/agent-foundry/issues/564)).
- Human gate: merge to `main`, tag, release, runtime/adapter publication,
  external materialization and Project writes remain separate decisions after
  exact non-`main` finalization readback
  ([#564 contract](https://github.com/farmerhunter/agent-foundry/issues/564#issuecomment-5355324825)).
- Deferred by design: do not introduce a new evidence database, branch manager,
  cleanup daemon, generator or near-duplicate Skill in this lane; reusable
  lesson candidates remain subject to the separate Human canonical review path
  ([#538 prerequisite design](https://github.com/farmerhunter/agent-foundry/issues/538#issuecomment-5338285102)).
