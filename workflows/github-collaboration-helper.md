# GitHub Collaboration Helper Workflow Contract

Use this workflow when a user asks for GitHub issue, pull request, role handoff,
or scheduler-state help through a future Agent Foundry collaboration helper.

This Unit A contract is Skill-facing and template-only. It defines user intents,
configuration shape, evidence requirements, and safety boundaries before helper
scripts exist. It does not publish generated Skills, install runtime adapters,
mutate GitHub state, or write Vault/private state.

## Codex Target Activation

Codex users should have one stable helper entry point across projects and
threads:

```text
~/.agent-foundry/bin/agent-foundry-github-collab
```

That file is a launcher, not a deployed copy of the helper implementation. It
reads the machine-local locator at `~/.agent-foundry/config.yaml`, resolves the
selected Agent Foundry Core checkout, and then executes:

```text
<core_root>/scripts/github_collaboration_helper.py
```

This keeps the Core helper source canonical while avoiding project-specific
paths in user-facing instructions. A user working in another repository or a
new Codex thread should not need to know where the Core checkout lives.

Activation evidence for this helper must include:

- the launcher exists at `~/.agent-foundry/bin/agent-foundry-github-collab`;
- the launcher resolves `core_root` through `~/.agent-foundry/config.yaml`;
- read-only or dry-run commands work from a non-Core working directory;
- installed generated runtime guidance, such as the Codex
  `agent-collaboration` Skill, describes the activation gate or points to this
  workflow clearly enough that a new thread can discover the safe path;
- any missing new-thread or manual trial evidence is recorded as an explicit
  blocker or follow-up, not silently treated as complete.

Useful smoke commands:

```text
~/.agent-foundry/bin/agent-foundry-github-collab activation-report
~/.agent-foundry/bin/agent-foundry-github-collab role-config-check --config <core_root>/templates/github-role-routing.template.yaml
~/.agent-foundry/bin/agent-foundry-github-collab --repo farmerhunter/agent-foundry issue-context 222 --comment-limit 3
~/.agent-foundry/bin/agent-foundry-github-collab permission-smoke agent-label
```

The last command must fail closed because `agent-label` mutates scheduler
ownership and is outside AF11 activation scope.

## User-Facing Entry Points

Agents should expose these as natural-language workflows rather than requiring
users to call raw helper internals:

| User asks to... | Agent behavior | Default write behavior |
| --- | --- | --- |
| inspect my inbox | Read open issues for configured `needs:*` labels and summarize role-ready work. | none |
| prepare issue context | Read the issue body, latest comments, dependency gates, parent Epic, and Execution Contract. | none |
| prepare handoff | Draft a durable handoff comment with scope, verification, residual risks, telemetry, and next owner. | preview only |
| audit scheduler state | Compare issue labels, state, PR state, comments, and optional Project mirror for contradictions. | none |
| generate dispatch evidence | Produce evidence that names the actual dispatch mechanism used. | preview only |
| report permission readiness | Report whether auth, repo selection, labels, PR state, and optional Project config are ready for the requested action. | none |

Future helper commands may implement these entry points, but raw command names
remain implementation details until a later accepted Skill or helper publish
gate.

## Repo Selection Contract

Repo selection must be explicit and repo-neutral:

1. Prefer an explicit CLI argument or workflow input such as `<owner>/<repo>`.
2. Otherwise use a repo-scoped environment value such as `AGENT_REPO`.
3. Otherwise infer from the current git remote only after showing the resolved
   `owner/repo`.
4. If the repo cannot be resolved unambiguously, stop with actionable guidance.

Do not ship a default repository, issue number, branch, Project id, cache path,
or maintainer-local path. Do not treat another project as an implicit runtime
dependency.

## Role Routing Config

Role routing config is data, not code. Start from
`templates/github-role-routing.template.yaml` and fill in project-specific
labels and owner roles in the target repository.

Required properties:

- `roles` maps user-facing role names to inbox labels.
- `needs_labels` lists the labels used as next-owner routing requests.
- `completion_handoff.required_fields` names the durable evidence expected
  before a `needs:*` label transition.
- `telemetry.required_for_meaningful_transitions` remains true for AF11 child handoffs unless the comment
  explains why telemetry was skipped under `workflows/coordinate-agent-work.md`.
- `project_v2.mode` defaults to `optional_visual_mirror`.

## GitHub Auth And Retry Expectations

Agents should verify GitHub readiness before making claims about available
state:

- confirm the authenticated account can read the target repo;
- confirm issue and PR reads work before writing comments or labels;
- use bounded retries for transient network, TLS, and rate-limit failures;
- distinguish auth/permission failures from transient network failures;
- keep large issue/PR reads bounded and summarize from durable sources;
- prefer body-file or API-safe comment writing when comments contain Markdown,
  YAML, shell snippets, or backticks.

Retry behavior must not hide permission failures or convert a preview into an
apply. Mutation helpers remain out of scope for Unit A.

## Dispatch Evidence Modes

Dispatch evidence must name the mechanism actually used:

| Mode | Use when | Required evidence |
| --- | --- | --- |
| `live_thread_dispatch` | A real thread or subagent tool accepted the prompt. | target thread/tool id and issue/PR link |
| `github_comment` | The handoff is posted durably for pickup. | comment URL and next-owner label |
| `generated_note` | The agent only prepared text for a human or later tool. | explicit statement that no dispatch occurred |
| `portable_prompt` | The output is a copyable prompt for another environment. | target role, authority sources, and manual bridge warning |

Never describe generated text as a successful thread dispatch unless a real
dispatch mechanism accepted it.

## Project V2 Boundary

Project v2 can be an optional visual mirror when explicitly configured. It is
not the scheduler source of truth.

Default behavior:

- read GitHub issues, PRs, labels, comments, and Execution Contracts first;
- skip Project v2 if config is absent;
- report missing Project config as `optional_project_mirror_unavailable`;
- do not mutate Project fields in Unit A;
- do not block role routing solely because Project v2 is unavailable.

## Skill-Facing Workflow Contract

A future generated Skill can route these user intents to helper-backed behavior
only after the helper implementation and publish gate are accepted:

- "check my implementer inbox";
- "summarize this issue for pickup";
- "draft a reviewer handoff";
- "audit this issue and PR scheduler state";
- "record dispatch evidence";
- "check whether this action has permission to proceed".

The Skill must preserve these rules:

- durable GitHub issue/PR/comment/label state remains authoritative;
- compact rehydration packets are pickup aids, not authority replacements;
- `workflow_telemetry` is required for meaningful AF11 role transitions;
- raw helper commands are not user-facing requirements;
- preview/dry-run output is the default until a later mutation helper gate is
  accepted;
- Project v2 remains optional and config-required;
- runtime/global config, Vault/private state, generated adapters, and
  memory-system records are out of scope.

## Dry-Run Planning Examples

Use `templates/github-dry-run-planning-examples.md` for runtime-neutral preview
examples covering pickup, handoff, batch accept, release queue, dispatch note,
and human-gate live response checklist shapes.

Those examples remain inert planning text. They do not authorize live dispatch,
GitHub comment or label writes, Project v2 mutation, merge, closure, generated
Skill publish, runtime install, Vault/private-state mutation, generated adapter
mutation, or memory-system work.

## Handoff Example

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
    labels_removed:
      - needs:implementer
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
      - changed workflow/docs/templates
      - verification output
  scope_summary:
    included:
      - repo-neutral docs/config/templates
    excluded:
      - helper script implementation
      - mutation helpers
      - Project v2 mutation/default adapter
      - generated Skill publish
  verification_summary:
    passed:
      - python3 scripts/check_consistency.py
      - git diff --check
    blocked: []
  human_gates:
    active: false
    required_phrase: null
  residual_risks:
    - "Template-only Unit A does not prove helper runtime behavior."
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
    github_comments: 2
    labels_added: 1
    labels_removed: 1
    project_writes: 0
  duplicated_context_from_previous_role: low
  notes: "Unit A handoff used durable issue/PR comments and no Project writes."
```

```yaml
workflow_cost_ledger_update:
  subject: AF11 GitHub collaboration helper migration pilot
  transitions:
    total_delta: 1
    by_type:
      implementer_to_reviewer: 1
  rehydration:
    compact_delta: 1
  human_gates_delta: 0
  project_sync_passes_delta: 0
  correction_cycles_delta: 0
  duplicated_context: low
  overhead_class: necessary_delivery_cost
```

## Troubleshooting

- `repo_unresolved`: provide an explicit `<owner>/<repo>` or configure
  `AGENT_REPO`.
- `auth_unavailable`: run GitHub auth setup in the user's environment and retry
  read-only checks.
- `permission_denied`: stop and report the missing permission; do not retry as a
  mutation.
- `project_config_missing`: continue with issue/PR/label/comment state and
  report Project v2 as an unavailable optional mirror.
- `dispatch_unavailable`: post a GitHub comment or portable prompt and label the
  fallback accurately.
- `telemetry_missing`: add `workflow_telemetry` or explain why the transition was
  trivial under `workflows/coordinate-agent-work.md`.
