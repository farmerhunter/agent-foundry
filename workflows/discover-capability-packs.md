# Discover Capability Packs Workflow

Use this workflow when an agent or human asks whether repeated practices,
assets, workflows, templates, or adapter projections should become an advanced
capability pack candidate.

This workflow proposes candidates only. It does not activate, export, deploy,
install, publish, or mutate any pack, Vault record, generated adapter, runtime
copy, private state, or memory-system record.

## Skill-First Entry Points

For normal agent use, invoke this workflow with natural-language requests such
as:

- `discover capability packs`
- `evaluate capability pack <path>`

The agent should translate those requests into the evidence-gathering sequence
below. Raw scripts are implementation details or advanced/debug commands, not
the primary user surface.

## Invariant

Capability pack discovery outputs reviewable candidate records, not canonical
pack state.

A capability pack is a bounded reusable capability contract around a recurring
user goal. It is not:

- a single practice;
- a single asset;
- raw evidence;
- generated adapter output;
- an installed runtime copy;
- a local-private workflow history;
- a memory-system record.

## 1. Gather Evidence

Use evidence in this order:

1. Public Core workflows, schemas, docs, fixtures, and issue or PR records.
2. Selected Vault canonical record metadata: practice IDs, asset IDs, lifecycle
   status, tags, triggers, membership, published targets, review cadence, and
   sanitized evidence summaries.
3. Sanitized usage aggregates.
4. Generated adapter presence as downstream projection evidence only.
5. Runtime state only through explicit status or receipt summaries when already
   safe to reference.

Do not copy raw session logs, private Vault history, secrets, local machine
paths, provider credentials, production logs, screenshots with private data, or
runtime manifests into public Core.

Separate observed facts from inference. Observed facts name the evidence source
and layer. Inference names the proposed boundary and why the evidence supports
or rejects that boundary.

## 2. Apply Authority Gates

Reject or defer before scoring when any authority gate fails.

| Gate | Pass condition | Failure result |
| --- | --- | --- |
| Canonical authority | Candidate is grounded in selected Vault canonical records, public Core workflows, or reviewed fixtures. | `rejected_false_positive` |
| Layer boundary | Generated and Runtime artifacts are downstream projection or install evidence only. | `rejected_false_positive` |
| Privacy | Candidate can be described without local-private evidence, secrets, raw logs, or personal history. | `deferred_privacy_review` or `blocked_policy` |
| Pack size | Candidate is broader than one asset/practice but still centered on one user goal. | `rejected_too_narrow` or `rejected_too_broad` |
| Activation safety | Candidate can be proposed without activation, export, runtime apply, or adapter publication. | `blocked_policy` |
| Existing coverage | Candidate does not duplicate an already sufficient pack or baseline bootstrap role. | `baseline_control` or `extend_existing` |

## 3. Score Explainable Signals

Score each signal as `0`, `1`, `2`, or `3`.

- `0`: absent or contradicted.
- `1`: weak or inferred from one source.
- `2`: supported by multiple sources or repeated use.
- `3`: strong, repeated, and backed by canonical metadata plus workflow use.

Required signals:

| Signal | What to inspect |
| --- | --- |
| `shared_user_goal` | One recurring user goal is visible across records or issues. |
| `asset_or_practice_membership` | Multiple practices/assets cohere into a bundle. |
| `workflow_recurrence` | The same steps or handoff shape recur across work. |
| `usage_frequency` | Sanitized usage aggregate or repeated issue history supports recurrence. |
| `validation_path` | The candidate has a review, test, walkthrough, or acceptance route. |
| `adapter_projection_breadth` | Generated adapter targets suggest cross-runtime value. |
| `fixture_or_provenance` | Existing fixture, pack, issue, or reviewed source anchors the candidate. |
| `authority_fit` | Core/Vault/Generated/Runtime/Local Private boundaries remain clear. |

Compute:

```text
total_signal_score = sum(required signal scores)
max_signal_score = 24
```

Then attach qualitative confidence:

- `high`: gates pass, score >= 18, and no high residual privacy or overlap risk.
- `medium`: gates pass, score 12-17, or score is high but residual risk remains.
- `low`: gates pass but score < 12, or evidence is mostly inferred.

Confidence is not an activation decision. A high-confidence candidate still
requires review before activation or export.

## 4. Classify Candidate Outcome

Candidate outcomes are a power-user discovery namespace. They explain whether a
reusable boundary is worth review; they are not persisted pack lifecycle states.

Use the first matching outcome:

| Outcome | Use when |
| --- | --- |
| `candidate` | Gates pass, confidence is medium or high, and the pack boundary is reviewable. |
| `baseline_control` | Evidence is pack-shaped but represents mandatory bootstrap or stable baseline behavior rather than an emergent optional pack. |
| `extend_existing` | Evidence supports changing an existing pack rather than creating a new one. |
| `deferred_overlap` | Boundary overlaps another candidate and needs split/merge analysis. |
| `deferred_insufficient_evidence` | Boundary is plausible but evidence is weak, new, or mostly inferred. |
| `deferred_privacy_review` | Pack may be useful but export/import privacy rules are not ready. |
| `rejected_false_positive` | Candidate is actually generated output, runtime state, raw evidence, private-only workflow, or another non-pack artifact. |
| `rejected_too_broad` | Candidate combines unrelated user goals. |
| `rejected_too_narrow` | Candidate is only one asset, practice, command, or helper. |
| `blocked_policy` | Candidate would require forbidden activation, export, runtime apply, memory-system work, or private-state mutation. |

## 5. False-Positive Controls

Every candidate review must explicitly test these controls:

- Overly broad: does the candidate mix unrelated user goals?
- Overly narrow: is it only one reusable asset or practice?
- Overlapping pack: should it split into base and advanced packs, or extend an
  existing pack?
- Private-only pack: does it depend on local history, secrets, private paths, or
  user-specific state?
- Stale pack: does it rely on outdated assets or low recent usage?
- Runtime wrapper: is it merely generated adapter output, runtime install state,
  or tool availability?
- Bootstrap duplicate: is it already covered by mandatory bootstrap or a stable
  lifecycle baseline?

## 6. Output Candidate Record

Write candidate records using `schemas/capability-pack-candidate.schema.yaml`.

Each record must include:

- proposed pack id and title;
- outcome and confidence;
- observed evidence references by authority layer;
- inferred boundary;
- likely included practices, assets, workflows, templates, or adapter projection
  intent;
- explicit exclusions;
- signal scores and total;
- false-positive control results;
- privacy and exportability rationale;
- runtime/generation impact;
- review handoff.

Use public issue/comment URLs when possible. For selected Vault evidence, cite
record IDs and sanitized aggregate summaries rather than raw private content.

## 7. Review Handoff

Route candidates to Reviewer for false-positive and boundary review when the
issue contract requires it.

Reviewer should check:

- evidence references exist and match the claimed layer;
- observed facts and inference are separate;
- score rationale is understandable to a human;
- rejected/deferred outcomes are justified;
- Generated and Runtime artifacts are not treated as canonical;
- no private evidence is leaked;
- harvest and asset-discovery workflows remain compatible.

After review, Architect decides whether to:

- keep the candidate as evidence only;
- create a follow-up for schema evolution;
- create a follow-up for lifecycle design;
- create a follow-up for privacy-safe export/import;
- create a follow-up for implementation;
- close as rejected or deferred.

## 8. Advanced Workflow Surface

Advanced capability discovery is optional. Basic pack deployment, planning,
update comparison, lifecycle reports, and transfer validation must still work
when no candidate records exist.

Use this sequence only when an issue or human asks for advanced discovery:

1. Run discovery as evidence gathering. Output candidate records or a review
   packet only; do not write canonical pack metadata or selected Vault records.
2. Validate any candidate record against
   `schemas/capability-pack-candidate.schema.yaml`. Candidate records remain
   review artifacts and must not be passed to activation, export, or deployment
   tooling as active pack manifests.
3. If the candidate becomes a reviewed pack manifest, validate it with
   `scripts/plan_capability_pack.py` before any deployment flow. Advanced
   metadata is additive and optional; `manifest_schema_version: 1` packs without
   advanced sections remain valid.
4. For lifecycle review, use
   `scripts/manage_capability_pack_lifecycle.py` in dry-run mode. Review-only
   actions such as `activate`, `exportable`, `deprecate`, `split`, and `merge`
   must report status, gates, rollback/defer guidance, and `writes: none`.
5. For export/import review, use
   `scripts/plan_capability_pack_transfer.py` before sharing or import
   acceptance. Transfer reports must be privacy-safe, dry-run first, and
   `writes: none`.
6. Route the result to the next owner:
   - Reviewer for candidate false-positive and boundary review;
   - Architect for split/merge or lifecycle policy decisions;
   - human for privacy/export, runtime-write, destructive, or final `main` merge
     decisions;
   - Harvester only when a canonical practice or asset change is actually
     required.

Failure states:

- `candidate_schema_version` appears in a pack manifest path: block as
  review-only candidate material.
- Generated or runtime evidence claims canonical authority: reject as
  false-positive or block policy.
- Transfer material contains private/local markers, executable install side
  effects, or missing export policy: block before sharing or import acceptance.
- Lifecycle metadata is malformed, missing hashes, local-private, or destructive:
  block and report rollback/defer/downstream guidance.
- Existing selected Vault edits conflict with imported content: preserve the
  Vault and route to reviewed merge; do not overwrite.

## 9. AF9 Fixture Expectations

Use these fixtures from AF9 #172 while validating the protocol:

| Fixture | Expected treatment |
| --- | --- |
| Multi-agent GitHub collaboration / role dispatch | Positive candidate input. Consider split/merge analysis for base collaboration versus Coordinator automation add-on. |
| Practice/asset lifecycle bootstrap | Baseline control. It is mandatory/stable, not a new optional emergent pack. |
| Provider integration playbook | Plausible candidate with privacy-sensitive evidence. Keep activation/export deferred until privacy-safe evidence references exist. |
| Architecture/frontend workflow design | Deferred overlap candidate. ASSET-UX-001 is newer and needs more usage evidence before exportable status. |
| Runtime adapters as a capability pack | Negative false-positive fixture. Generated/runtime artifacts are downstream only. |
| Document/format workflow | Deferred insufficient-evidence fixture until canonical asset/workflow evidence accumulates. |
