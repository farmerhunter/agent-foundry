# Coordinate Agent Work

Status: AF10-A foundation
Scope: Coordinator workflow telemetry, Epic ledger, role handoff measurement, and collaboration overhead reporting.

## Purpose

This workflow defines the minimum telemetry that Coordinator-led role orchestration should record before AF11 pilot work begins.

The goal is not billing-grade token accounting. The goal is to make coordination overhead visible enough to decide when multi-thread role orchestration is worth its cost, when a compact handoff is enough, and when a single-thread or batch checkpoint is safer and cheaper.

## Non-Scope

- No memory-system implementation.
- No memory directories, schemas, MCP write tools, or automatic memory writing.
- No runtime or global config mutation.
- No live Vault or private-state mutation.
- No generated adapter publish.
- No new `needs:coordinator` label.

## Telemetry Principles

- Treat telemetry as coordination evidence, not as a blocking runtime dependency.
- Prefer small fields that agents can fill during real handoffs.
- Mark estimates as estimates; do not imply access to hidden billing telemetry.
- Preserve authority sources. A compact telemetry block does not replace required issue, PR, Project, roadmap, or Skill reads for risky transitions.
- Record why full rehydration was needed when it was needed.
- Treat correction cycles as high-value evidence, not merely waste.

## Role Callback Telemetry

Role callbacks, review handoffs, and Coordinator summaries may include this optional block:

```yaml
workflow_telemetry:
  transition_type: implementer_to_reviewer
  role_from: Implementer
  role_to: Reviewer
  rehydration_scope: compact | full | none
  rehydration_sources:
    - AGENTS.md
    - agent-collaboration skill
    - issue body/comments
    - PR metadata/comments
    - Project fields
  durable_state_reads:
    github_issues: 1
    github_prs: 1
    github_comments: 2
    project_reads: 1
    local_files: 0
  durable_state_mutations:
    github_comments: 1
    labels_added: 1
    labels_removed: 1
    project_writes: 0
  estimated_tokens:
    input: 8000-12000
    output: 1000-2500
    confidence: low | medium | high
  duplicated_context_from_previous_role: low | medium | high
  reason_full_rehydrate_required: "independent review of PR targeting main"
  notes: "Repeated issue/PR state and verification context from Implementer handoff."
```

### Required Fields

Use these fields whenever telemetry is included:

- `transition_type`
- `role_from`
- `role_to`
- `rehydration_scope`
- `durable_state_reads`
- `durable_state_mutations`
- `duplicated_context_from_previous_role`

### Optional Fields

Use these when the information is reasonably available:

- `rehydration_sources`
- `estimated_tokens`
- `reason_full_rehydrate_required`
- `notes`

## Transition Types

Use stable transition names so AF10 can compare handoffs:

- `coordinator_to_architect`
- `architect_to_implementer`
- `implementer_to_reviewer`
- `reviewer_to_architect`
- `architect_to_human`
- `human_to_architect`
- `architect_to_coordinator`
- `coordinator_state_repair`
- `epic_readiness_review`
- `closure_correction`

If a transition does not fit, use a short lower-case identifier and add a note.

## Rehydration Scope

Use `none` when no context reconstruction was needed.

Use `compact` when the role can work from a durable state packet plus targeted authority reads.

Use `full` when the transition needs independent review, merge, closure, privacy/security boundary checks, runtime/global/Vault/private-state boundaries, stale state repair, or human-gated decision support.

## Compact Rehydration Packet

A compact rehydration packet is a durable pickup aid. It reduces repeated narrative context, but it does not replace authority sources.

Use this shape when a role can safely start from summarized state plus targeted readbacks:

```yaml
compact_rehydration_packet:
  packet_version: 1
  subject:
    issue: 195
    pull_request: null
    parent_issue: 192
    stage: AF-10
  current_owner: Architect
  next_owner: Reviewer
  routing_state:
    labels_present:
      - needs:reviewer
    labels_removed:
      - needs:architect
    project_status: In Progress
    roadmap_status: Review
    owner_role: Reviewer
  authority_sources:
    must_read:
      - AGENTS.md
      - agent-collaboration skill
      - issue body
      - latest issue comments since release
    targeted_read:
      - PR body and diff
      - Project fields when state coherence is part of acceptance
      - changed workflow or script files
    optional_context:
      - roadmap milestone summary
      - parent Epic progress comment
  dependency_state:
    satisfied:
      - "#194 complete after PR #199 merge"
    blocked: []
  scope_summary:
    included:
      - compact packet field review
      - authority-source rule review
    excluded:
      - permission model decision
      - runtime or Vault mutation
      - memory-system work
  verification_summary:
    passed:
      - python3 scripts/check_consistency.py
    not_run: []
    blocked: []
  human_gates:
    active: false
    required_phrase: null
  residual_risks:
    - "Packet is a pickup aid, not an authority source."
  workflow_telemetry:
    transition_type: architect_to_reviewer
    rehydration_scope: compact
```

### Packet Fields

Use these fields for AF10 and AF11 dispatches when compact rehydration is allowed:

- `packet_version`: packet schema version. Start with `1`.
- `subject`: issue, PR, parent issue, stage, branch, head SHA, and base branch when available.
- `current_owner` and `next_owner`: role names, not necessarily separate sessions.
- `routing_state`: labels, issue state, PR state, Project Status, Roadmap Status, Owner Role, and any known state repairs.
- `authority_sources`: the exact sources the next role must read before acting.
- `dependency_state`: satisfied, pending, blocked, or intentionally deferred dependencies.
- `scope_summary`: included work, excluded work, and forbidden actions.
- `verification_summary`: commands or checks already run, with pass/fail/blocked status.
- `human_gates`: whether a human decision is active and the exact authorization phrase if one exists.
- `residual_risks`: open risks the next role must preserve.
- `workflow_telemetry`: optional telemetry block from this workflow.

### Authority Source Rules

Authority sources are not interchangeable with summaries.

Always read these sources before risky transitions:

- repository instructions such as `AGENTS.md`;
- the applicable generated Skill or workflow instruction;
- the current issue body and latest issue comments;
- PR body, diff, head SHA, and review comments when a PR exists;
- labels and issue/PR state;
- Project fields when acceptance depends on Project or Roadmap coherence;
- latest user instruction when a human gate, trial, or approval is active.

Treat the compact packet as sufficient only for orientation when:

- the source thread names the exact issue or PR;
- dependencies are already satisfied in durable GitHub state;
- the next role can verify current labels and issue/PR state with targeted reads;
- no active human gate, merge, closure, privacy/security decision, runtime/global write, live Vault/private-state mutation, generated adapter publish, memory-system action, or destructive operation is required.

### Full Rehydration Triggers

Use `full` rehydration when any of these are true:

- independent review must validate behavior, safety, or acceptance criteria;
- the action is a main-branch merge, issue closure without already delegated authority, Epic/stage/window closure, or HDC;
- privacy/security boundaries, runtime/global config, live Vault/private-state, generated adapters, memory-system records, data migration, or destructive operations are involved;
- issue/PR labels, Project fields, branch state, roadmap state, or comments conflict;
- the packet is stale, missing required authority sources, or does not name exact issue/PR/head state;
- the task depends on user-visible behavior acceptance or final-user walkthrough output;
- the next role is asked to make architecture, policy, taxonomy, or permission decisions not already accepted.

### Fallback Rules

If compact rehydration fails validation, do not guess from memory or thread history.

Fallback order:

1. Re-read the issue, PR, comments, labels, Project fields, relevant workflow files, and repo instructions.
2. Record the missing or stale packet field in the next durable comment or callback.
3. Use `rehydration_scope: full` in workflow telemetry.
4. Route to Architect or Human when the missing information changes authority, permission, acceptance, privacy, or closure state.
5. Continue with compact mode only after the missing authority source has been read and the contradiction is resolved.

### Source Callback Interaction

Callbacks are transient coordination. Durable state is authoritative.

Use callbacks to carry compact packets and speed pickup, but verify them against:

- GitHub issue or PR state for routing;
- comments for accepted decisions, handoffs, HDCs, and completion evidence;
- Project fields only when available and relevant;
- local files or branch state only after confirming the intended branch/head.

When thread tools are unavailable, post the packet as a GitHub issue or PR comment and identify that GitHub comment as the durable pickup source.

## Epic Workflow Cost Ledger

For an Epic, milestone, or pilot flow, Coordinator should maintain a compact ledger in the parent issue or a linked durable comment:

```yaml
workflow_cost_ledger:
  subject: AF11 pilot
  parent_issue: 192
  evidence_issue: 189
  transitions:
    total: 0
    by_type: {}
  rehydration:
    none: 0
    compact: 0
    full: 0
  human_gates: 0
  project_sync_passes: 0
  correction_cycles: 0
  duplicated_context:
    low: 0
    medium: 0
    high: 0
  estimated_tokens:
    input: unknown
    output: unknown
    confidence: low
  overhead_notes: []
```

## Overhead Classification

During AF10-B analysis, classify observed overhead into these buckets:

- `necessary_review_cost`: independent review, human gate, closure readiness, privacy/security boundary.
- `avoidable_duplication`: repeated summaries or rehydration that a compact state packet could replace.
- `state_sync_cost`: GitHub labels, issue state, PR state, Project Status, Roadmap Status, Owner Role, and milestone readbacks or repairs.
- `human_gate_cost`: HDC writing, live user-facing decision surfacing, approval wait, and post-approval verification.
- `correction_value_cost`: extra work that exposed a real readiness gap or prevented incorrect closure.
- `tool_surface_cost`: work caused by missing, variable, or unreliable thread, Project, GitHub, or automation tools.

## Usage Guidance

Add telemetry when it will inform AF10 or AF11 decisions. Do not add it to every trivial comment.

Prefer telemetry on:

- cross-role handoffs;
- review handoffs;
- HDCs;
- closure gates;
- correction/reopen cycles;
- Project state repair;
- AF11 pilot dispatch and callback;
- final AF10-B analysis.

Skip telemetry for:

- minor typo comments;
- single-file edits with no role transition;
- repeated comments that add no new state;
- commands that do not affect durable workflow state.

## Safety Boundary

Telemetry does not authorize action. Permission still follows the issue contract, repo instructions, latest user instruction, PR target, and collaboration practices.

When in doubt, record the uncertainty in `notes` and perform the normal permission or rehydration checkpoint before mutating durable state.
