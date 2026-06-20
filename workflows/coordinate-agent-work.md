# Coordinate Agent Work

Status: AF10-B optimization model
Scope: Coordinator workflow telemetry, Epic ledger, role handoff measurement, collaboration overhead reporting, and token-cost optimization guidance.

## Purpose

This workflow defines the minimum telemetry that Coordinator-led role orchestration should record before AF11 pilot work begins.

The goal is not billing-grade token accounting. The goal is to make coordination overhead visible enough to decide when multi-thread role orchestration is worth its cost, when a compact handoff is enough, and when a single-thread or batch checkpoint is safer and cheaper.

AF10-B telemetry should support three-way comparison:

1. Single-agent baseline: what happened, or what is expected to happen, when one session owns the whole task.
2. Unoptimized collaboration counterfactual: what a full three- or four-agent workflow would likely cost if every role handoff used full rehydration and separate review by default.
3. Optimized collaboration observed result: what happened after compact packets, batch checkpoints, bundled human gates, and selective role dispatch were applied.

Use this comparison as decision support for workflow routing. It should help answer whether collaboration was worth its coordination cost, whether optimization reduced avoidable overhead, and when a future task should stay single-agent.

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
- Keep telemetry layers separate. `workflow_cost_ledger` values are transition-scoped estimates; observed goal or runtime token counters are separate calibration data, not the same accounting field.
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
  observed_goal_tokens:
    value: unknown
    source: null
    notes: "Optional observed thread/goal counter; do not add to estimate totals."
  overhead_notes: []
```

## Workflow Comparison Telemetry

Use this optional block when AF10 needs to compare a task, issue batch, Epic, milestone, or pilot across the three routing modes. It can be recorded in an issue comment, parent Epic comment, PR summary, or final Coordinator analysis.

```yaml
workflow_comparison_telemetry:
  subject: "AF10 follow-up #215"
  comparison_scope:
    unit: issue | issue_batch | pr | epic | milestone | pilot | session_goal
    issue_count: 1
    pr_count: 0
    user_visible_scope: false
    risk_class: low | medium | high | mixed
    human_gate_count: 0
  single_agent_baseline:
    source: observed | estimated | unavailable
    transitions: 0
    rehydration:
      none: 1
      compact: 0
      full: 0
    role_dispatches: 0
    correction_cycles: 0
    elapsed_time: unknown
    ledger_estimated_tokens:
      input: unknown
      output: unknown
      confidence: low | medium | high
    observed_goal_tokens:
      value: unknown
      source: null
      notes: "Optional observed session or goal counter; not billing-grade."
  unoptimized_collaboration_counterfactual:
    source: estimated
    assumed_agents: 3 | 4
    assumed_transitions: 0
    assumed_full_rehydrates: 0
    assumed_compact_rehydrates: 0
    assumed_role_dispatches: 0
    assumed_human_gates: 0
    duplicated_context: low | medium | high
    ledger_estimated_tokens:
      input: unknown
      output: unknown
      confidence: low | medium | high
    assumptions:
      - "Each role handoff performs full rehydration."
  optimized_collaboration_observed:
    source: observed | estimated | mixed
    transitions: 0
    rehydration:
      none: 0
      compact: 0
      full: 0
    role_dispatches: 0
    batch_checkpoints: 0
    bundled_human_gates: 0
    correction_cycles: 0
    avoided_transitions: 0
    ledger_estimated_tokens:
      input: unknown
      output: unknown
      confidence: low | medium | high
    observed_goal_tokens:
      value: unknown
      source: null
      notes: "Keep separate from ledger estimates."
  quality_guardrails:
    blocking_findings_missed: 0
    blocking_findings_caught: 0
    failed_verification: 0
    reopened_issues: 0
    human_holds: 0
    late_closure_corrections: 0
  savings_analysis:
    optimized_vs_unoptimized:
      transition_delta: unknown
      full_rehydrate_delta: unknown
      estimated_token_delta: unknown
    optimized_vs_single_agent:
      overhead_delta: unknown
      quality_or_parallelism_benefit: unknown
    recommendation: single_agent | optimized_collaboration | full_collaboration | insufficient_data
    confidence: low | medium | high
    notes: "Decision-support estimate, not billing-grade accounting."
```

### Comparison Rules

- Use `single_agent_baseline` for the one-session route. Prefer observed data when a comparable task was actually done by one session; otherwise mark it as `estimated` or `unavailable`.
- Use `unoptimized_collaboration_counterfactual` for the three- or four-agent route without AF10-B optimization. This is usually estimated, not actually executed. State assumptions explicitly.
- Use `optimized_collaboration_observed` for the real optimized workflow when compact packets, batch checkpoints, bundled human gates, or selective role dispatch were used.
- Keep `ledger_estimated_tokens` separate from `observed_goal_tokens` in every mode. Observed counters can calibrate estimate bands only when scope and time window are named.
- Keep quality guardrails beside savings. Lower token or transition cost is not a win if blocking findings are missed, verification fails, issues reopen, or the human needs corrective holds.
- Prefer normalized comparisons for similar task classes: risk class, issue count, PR count, user-visible scope, and human-gate count.
- Mark confidence as `low` until at least three comparable flows exist for the same class.
- Do not close a telemetry enhancement issue with only one ad hoc report when the intended deliverable is reusable measurement support.

## Telemetry Layer Rules

Use ledger estimates to compare transition shapes, not to claim exact model or billing usage.

Record observed token counters separately when the runtime exposes them. Name the source, scope, and time window, for example `goal tokensUsed` for one Coordinator thread goal. Do not sum observed counters with ledger estimates unless the scopes are proven compatible.

When estimates and observed counters differ, analyze the delta instead of forcing equality. Typical delta sources include repeated durable reads, tool output context, hidden prompt or system overhead, live coordination turns, final closure work, or separate role threads not covered by the observed counter.

Use workflow comparison telemetry when the question is about route selection, not just one transition. The comparison layer may include observed single-agent data, estimated unoptimized collaboration data, and observed optimized collaboration data in the same block, but it must label each source separately.

## Overhead Classification

During AF10-B analysis, classify observed overhead into these buckets:

- `necessary_review_cost`: independent review, human gate, closure readiness, privacy/security boundary.
- `avoidable_duplication`: repeated summaries or rehydration that a compact state packet could replace.
- `state_sync_cost`: GitHub labels, issue state, PR state, Project Status, Roadmap Status, Owner Role, and milestone readbacks or repairs.
- `human_gate_cost`: HDC writing, live user-facing decision surfacing, approval wait, and post-approval verification.
- `correction_value_cost`: extra work that exposed a real readiness gap or prevented incorrect closure.
- `tool_surface_cost`: work caused by missing, variable, or unreliable thread, Project, GitHub, or automation tools.

## Token Optimization Rules

Use these routing rules after AF10-B when they do not weaken authority reads, review independence, or human gates:

1. Prefer single-session serial work for low-risk, single-issue tasks when no independent review, human gate, closure gate, protected runtime/Vault/generated/memory boundary, stale state, or policy decision is active.
2. Use compact rehydration packets for ordinary handoffs. The packet should name exact `must_read` and `targeted_read` authority sources so the next role avoids whole-history rereads while still verifying current state.
3. Escalate to full rehydration for independent review, merge, issue closure, Epic or milestone closure, human gates, privacy/security/runtime/Vault/generated/memory boundaries, stale or conflicting scheduler state, and architecture or policy decisions.
4. Use batch checkpoints for related low-risk children only when the issue or Epic contract explicitly opts in with `Completion handoff: batch checkpoint` and no high-risk trigger is present.
5. Dispatch a separate role session only when independence, parallelism, risk isolation, or the issue contract makes the extra rehydration cost valuable. Otherwise, state the current-session role switch and use structured self-review when allowed.
6. Bundle human-gate review points, options, consequences, verification, residual risks, and the authorization phrase or trial response in one live request. This reduces approval correction loops and makes the gate meaningful.
7. Sample telemetry for meaningful transitions. Skip trivial comments, typo fixes, and no-state-change updates, or record an explicit skip reason instead of adding noisy ledger entries.
8. Track expected savings qualitatively until enough comparable before/after flows exist. Use transition count, full rehydrate count, duplicated-context level, correction cycles, and observed goal counters as the first quantitative indicators.
9. When comparing routing options, use the three-way comparison shape: single-agent baseline, unoptimized collaboration counterfactual, and optimized collaboration observed result.

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
- route-choice comparisons between single-agent, unoptimized collaboration, and optimized collaboration.

Prefer compact telemetry for routine handoffs. If filling the telemetry block would cost more than the transition teaches, skip it and state why in the durable comment.

Skip telemetry for:

- minor typo comments;
- single-file edits with no role transition;
- repeated comments that add no new state;
- commands that do not affect durable workflow state.

## Safety Boundary

Telemetry does not authorize action. Permission still follows the issue contract, repo instructions, latest user instruction, PR target, and collaboration practices.

When in doubt, record the uncertainty in `notes` and perform the normal permission or rehydration checkpoint before mutating durable state.
