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

AF10-A follow-up work owns the detailed compact rehydration packet and authority-source rules.

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
