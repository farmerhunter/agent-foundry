# GitHub Collaboration Dry-Run Planning Examples

Status: AF11 pilot template examples

These examples are inert planning text for Agent Foundry collaboration helpers.
They do not dispatch live threads, write GitHub comments, change labels, mutate
Project v2 fields, merge pull requests, close issues, publish generated Skills,
install runtime files, write Vault/private state, or create memory records.

Use these examples when a helper or agent needs to preview collaboration output
before a reviewed mutation helper exists.

## Common Rules

- Preserve exact issue, PR, branch, head SHA, and base branch when known.
- State whether the output is `generated_note`, `github_comment`,
  `portable_prompt`, or `live_thread_dispatch`.
- For `generated_note` and `portable_prompt`, say plainly that no dispatch
  occurred.
- Include allowed actions, forbidden actions, stop condition, verification, and
  callback requirements.
- Include `workflow_telemetry` for meaningful AF11 transitions.
- Treat compact rehydration packets as pickup aids, not authority sources.
- Keep Project v2 optional unless a later accepted adapter decision changes
  that boundary.

## Pickup Preview

Use this when a role is about to pick up an issue but no durable mutation should
occur yet.

```yaml
dry_run_planning_example:
  mode: generated_note
  intent: pickup_preview
  no_dispatch_occurred: true
  subject:
    issue: 205
    pull_request: 212
    parent_issue: 201
    stage: AF-11
    branch: codex/af11-unit-b-helper
    head_sha: a0615b81b8457d004cc20a8153f487f249781498
    base_branch: main
  next_owner: Reviewer
  allowed_actions:
    - read issue body/comments/labels
    - read PR body/diff/head SHA
    - run scoped verification
    - draft findings or acceptance recommendation
  forbidden_actions:
    - write GitHub comments or labels from this preview
    - mutate Project v2 fields
    - merge or close
    - publish generated Skills or install runtime files
    - write Vault/private/generated state
    - create memory-system records
  stop_condition:
    - blocking finding found
    - head SHA changed
    - authority sources disagree with this preview
  callback_required:
    - findings or no-findings statement
    - verification evidence
    - residual risks
    - workflow_telemetry
```

## Handoff Draft

Use this when preparing a durable handoff comment. The output remains preview
only until a human or later mutation helper posts it.

```yaml
compact_rehydration_packet:
  packet_version: 1
  subject:
    issue: "<issue-number>"
    pull_request: "<pr-number-or-null>"
    parent_issue: "<parent-issue-or-null>"
    stage: "<stage-label>"
    branch: "<branch-name-or-null>"
    head_sha: "<head-sha-or-null>"
    base_branch: "<base-branch-or-null>"
  current_owner: Implementer
  next_owner: Reviewer
  routing_state:
    labels_present:
      - needs:reviewer
    issue_state: open
    pr_state: open
    project_status: optional_visual_mirror
  authority_sources:
    must_read:
      - AGENTS.md
      - agent-collaboration Skill
      - issue body and latest comments
      - PR body, diff, and head SHA
    targeted_read:
      - changed files
      - verification output
  scope_summary:
    included:
      - "<bounded included scope>"
    excluded:
      - mutation helpers
      - Project v2 mutation/default adapter
      - runtime/global/Vault/private/generated mutation
      - memory-system work
  verification_summary:
    passed:
      - "<command>"
    blocked: []
  human_gates:
    active: false
    required_phrase: null
  residual_risks:
    - "<risk>"
```

```yaml
workflow_telemetry:
  transition_type: implementer_to_reviewer
  role_from: Implementer
  role_to: Reviewer
  rehydration_scope: compact
  durable_state_reads:
    github_issues: 1
    github_prs: 1
    github_comments: 2
    project_reads: 0
    local_files: 4
  durable_state_mutations:
    github_comments: 0
    labels_added: 0
    labels_removed: 0
    project_writes: 0
  duplicated_context_from_previous_role: low
  notes: "Preview-only handoff draft; no GitHub mutation occurred."
```

## Batch Accept Preview

Use this only for related low-risk child issues when the parent issue or Epic
contract allows batch review.

```yaml
dry_run_planning_example:
  mode: generated_note
  intent: batch_accept_preview
  no_dispatch_occurred: true
  parent_issue: "<parent-issue>"
  children:
    - issue: "<child-issue>"
      pull_request: "<pr-or-null>"
      head_sha: "<head-sha-or-null>"
      verification:
        - "<command>"
      residual_risks:
        - "<risk>"
  batch_gate:
    allowed_by_contract: "<yes-or-no>"
    high_risk_trigger_present: "<yes-or-no>"
    human_gate_required: "<yes-or-no>"
  forbidden_actions:
    - merge high-risk or main-target PRs without accepted gate evidence
    - close parent Epic or milestone from this preview
    - hide subjective user acceptance behind objective tests
  callback_required:
    - accepted children
    - held children
    - verification summary
    - residual risks
    - workflow_telemetry
```

## Release Queue Preview

Use this when a dependency has completed and the next issue can be released.

```yaml
dry_run_planning_example:
  mode: generated_note
  intent: release_queue_preview
  no_dispatch_occurred: true
  dependency_satisfied:
    issue: 205
    pull_request: 212
    merge_commit: 791b1755f0b7fa1445e745e776be1ba02dba6922
  next_issue:
    issue: 206
    next_owner: Reviewer
    proposed_label: needs:reviewer
  allowed_actions:
    - draft release comment
    - draft compact rehydration packet
    - report required verification
  forbidden_actions:
    - apply labels from this preview
    - mutate Project v2 fields from this preview
    - close dependency issue unless completion evidence is already accepted
  stop_condition:
    - dependency merge cannot be verified
    - next issue body contradicts the proposed owner
    - active human gate exists
```

## Dispatch Note Preview

Use this when an agent needs to describe dispatch state. Do not claim dispatch
success unless the mechanism actually accepted the handoff.

```yaml
dispatch_evidence:
  mode: generated_note
  target_role: Reviewer
  issue: 206
  dispatch_occurred: false
  required_before_claiming_dispatch:
    live_thread_dispatch:
      - target thread or tool id
      - accepted prompt evidence
      - issue or PR link
    github_comment:
      - comment URL
      - next-owner label
    portable_prompt:
      - manual bridge warning
      - target role
      - authority sources
  warning: "Generated text is not a successful thread call."
```

## Human Gate Live Response Checklist

When a human gate is required, the live response must include the review points
needed for a decision, not only the authorization phrase.

```yaml
human_gate_live_response:
  decision: "Merge PR #212"
  review_points:
    - boundary being accepted
    - objective verification already run
    - subjective/manual trial status when relevant
    - residual risks
    - consequences of approve, hold, or request review
  authorization_phrase: "批准合并 PR #212"
  durable_hdc: "link to issue or PR comment"
  note: "Durable HDC is authoritative, but the human should not need to open GitHub to know what to review."
```
