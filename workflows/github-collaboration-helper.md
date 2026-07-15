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

Execution Contract role fields are machine-readable. Use lowercase single-token
role values and machine handoff values:

```markdown
## Execution Contract

Owner role: implementer
Review role: reviewer
Acceptance role: architect
Completion handoff: to:reviewer
Branch strategy: mainline-maintenance
Target branch: main
Reviewer target: separate Reviewer agent, contract-validation focused
Human review prompt: only when a real human gate is needed
```

Keep natural-language reviewer descriptions, human prompts, and trial
instructions in separate fields such as `Reviewer target:`, `Human verification
needed:`, or `Human review prompt:`. Do not encode them in `Owner role:`,
`Review role:`, `Acceptance role:`, or `Completion handoff:`.

Branch-aware Execution Contract fields are also machine-readable:

```markdown
Branch strategy: mainline-maintenance | integration-branch | release-branch | trunk-based | stacked-pr | multi-branch | custom
Target branch: main | <integration-branch> | <release-branch>
Affected branches: <optional comma-separated branch list>
Verification branches: <optional comma-separated branch list>
PR target: <expected PR base branch>
Forward-merge expectation: none | record later forward-merge | verify on multiple lines
```

`Target branch` is canonical. Treat `Branch target` only as a legacy
compatibility input when reading old issues; do not use it in new examples.

Agent Foundry presets:

- V1.x maintenance uses `Branch strategy: mainline-maintenance` and
  `Target branch: main`.
- V2 integration uses `Branch strategy: integration-branch` and
  `Target branch: codex/v2-local-first-orchestration`.
- V2 merge-back to `main` remains a later readiness and Human-gated decision.

For custom or unknown branch strategies, route to Architect rather than
guessing. For stacked PRs or multi-branch work, emit review/action-plan
guidance; do not checkout, create a worktree, retarget the PR, rebase, merge,
reset, clean, or apply a repair.

## Tester Routing

Use `needs:tester` only when a task needs explicit test planning, a test
matrix, evidence execution, or residual-risk handoff before the next decision.
Tester is an evidence role. Tester does not approve, reject, merge, close,
replace Reviewer acceptance, decide Architect-owned product semantics, or
replace Human trial.

Use Tester when risk comes from user-visible state, route mocks versus real
backend behavior, imported data shape, runtime/generated/Vault boundaries,
unsafe writes, stale state, copy leaks, answer leaks, or a human trial that
needs objective evidence first. Skip Tester when a small static, unit, docs, or
copy check fully answers the user confidence question.

Tester-oriented Execution Contracts use `Owner role: tester` or
`Completion handoff: to:tester`. Do not use `Review role: tester`; route
accepted Tester evidence to Reviewer, product ambiguity to Architect, defects
to Implementer, and subjective trial to Human.

```markdown
## Execution Contract

Owner role: tester
Review role: reviewer
Acceptance role: architect
Completion handoff: to:reviewer

## Testing Contract

Testing Responsibility: tester
Tester Trigger:
  - user-visible state changes need evidence before review
user_value_or_risk: user can trust the workflow does not leak stale or unsafe state
user_journey_or_state_chain: preview -> apply -> verify
evidence_required:
  - route_mocked_browser
  - negative_adversarial
test_matrix:
  - scenario: preview keeps writes disabled
    risk: unsafe_write
    evidence_type: route_mocked_browser
    fixture: route_mock
    command_or_method: not_available
    expected_signal: preview reports writes none
    owner: tester
    residual_gap: does not prove backend persistence

## Test Evidence Handoff

to: reviewer
commands:
  - python3 scripts/check_consistency.py
environment: local
artifacts:
  - not_available
result_summary: passed
residual_risks:
  - human wording acceptance still requires Human trial
```

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

## GitHub Operation Policy

Use a hybrid GitHub operation policy. Each role/session must discover the
current GitHub connector or structured tool surface before choosing a write
path; do not assume Architect, Coordinator, Reviewer, Implementer, Harvester, or
future runtime sessions expose identical tools.

Preferred routing order:

1. Use GitHub connector or structured tools when the current session exposes a
   clear, bounded path for straightforward low-risk issue/PR reads, top-level
   comments, issue create/update, label add/remove, and PR metadata reads.
   Record observed connector behavior as session evidence, not a universal
   runtime guarantee.
2. Use repo-local helper paths first when scheduler semantics, issue context,
   handoff shaping, dispatch evidence, telemetry, audit, dry-run previews, or
   fail-closed permission checks matter.
3. Use controlled `gh api` with a body-file or structured JSON payload when
   connector tools are unavailable, incomplete, unclear, or failing and the
   write is still inside the authorized workflow.
4. Use bare `gh issue comment --body` only as a last resort for short
   low-risk comments. Apply bounded retry or fallback and record TLS, EOF,
   timeout, or rate-limit-like failures explicitly.

Current Agent Foundry helper behavior:

- `scripts/github_collaboration_helper.py` remains read-only, dry-run, or
  fail-closed for GitHub comment writes.
- `permission-smoke agent-comment` must remain forbidden until a later reviewed
  mutation-helper gate adds a comment-write apply path.
- Do not document or imply that `agent-comment --apply` or an equivalent
  comment-write helper exists in the current helper.

Project v2 was not meaningfully evaluated by the #272 pilot. Treat Project v2
as an optional visual mirror and scheduler metadata surface only; do not derive
a generalized Project v2 connector or mutation policy from this workflow.

Workflow authorization does not override product/runtime approval prompts. If a
runtime asks for shell approval despite a workflow-approved action, stop for the
user or switch to an already available approved connector/helper path. Do not
claim workflow policy suppresses app-level prompts.

## Scheduler Audit

Use `scheduler-audit` only for transition-gated scheduler readback, such as an
Implementer pickup, Reviewer handoff, or AF stage repair pass. Do not run it as
an always-on preflight for ordinary inbox reads, issue context reads, PR diff
review, or code edits.

The helper supports deterministic fixture input:

```text
agent-foundry-github-collab scheduler-audit \
  --config templates/github-role-routing.template.yaml \
  --issues-json <fixture> \
  --project-items-json <fixture> \
  --json
```

It also supports bounded live reads when the caller provides an explicit batch
selector:

```text
agent-foundry-github-collab --repo <owner>/<repo> scheduler-audit \
  --config templates/github-role-routing.template.yaml \
  --stage AF-11 \
  --project-owner @me \
  --project-number 3 \
  --json
```

Use `--issues 224,225` for a smaller explicit batch, or `--stage AF-11
--limit <n>` for a bounded stage audit. When live Project readback is requested,
the helper reads `gh project item-list` once per audit batch and compares the
returned items against all selected issues. It must not perform `gh project
item-add`, `gh project item-edit`, label changes, comments, closure, dispatch,
runtime install, adapter publish, Vault writes, generated adapter writes, or
memory writes.

JSON output is the primary contract:

```yaml
status: ok | findings | degraded
repo: owner/repo
audit_scope:
  mode: issues | stage | fixture
  issue_numbers: []
  stage: AF-11
  limit: 20
  project_owner: "@me"
  project_number: 3
sources:
  issues: live_gh | fixture
  project_items: live_gh | fixture | skipped
  config: templates/github-role-routing.template.yaml
project_v2:
  mode: optional_visual_mirror
  availability: ok | config_missing | unavailable | permission_denied | auth_unavailable
retry_summary:
  project_item_list:
    attempts: 1
    transient_failures: []
findings:
  - issue: 224
    severity: error | warning | info
    code: missing_project_item | empty_project_field | project_field_mismatch | closed_issue_not_done | open_needs_label_status_mismatch | multiple_needs_labels | no_next_owner_label
    message: human-readable summary
    expected: {}
    actual: {}
dry_run_repair_plan:
  - action: add_project_item | set_project_field | adjust_label | post_handoff_comment
    issue: 224
    field: Owner Role
    value: Implementer
    mutation_performed: false
mutation_performed: false
```

Project v2 failures are first-class audit state. Transient `EOF`, `499`, TLS,
timeout, and rate-limit-like failures use bounded retries. If Project readback
still fails, the helper returns `status: degraded`, preserves
`mutation_performed: false`, and keeps issue/label findings that can be audited
without the Project mirror. Auth, permission, malformed fixture, unresolved repo,
and incomplete required input errors fail closed instead of being retried as
transient failures.

## Collaboration Readiness

Use `collaboration-readiness` when a user asks whether a new or existing
repository is ready for role-based GitHub collaboration.

Skill-facing requests should come first:

```text
check collaboration readiness for this repo
prepare this repo for multi-agent collaboration
audit existing collaboration setup
```

The helper command is the secondary/debug surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> collaboration-readiness \
  --config templates/github-role-routing.template.yaml \
  --stage AF-15 \
  --json
```

The report is read-only and must include `mutation_performed: false`. It checks
role labels, routing config, Execution Contract values, Testing Contract values,
issue/PR routing state, and optional Project/Kanban visibility. Raw JSON remains
the evidence/debug layer; user-facing guidance comes from `readiness_status`,
`summary`, and `user_readiness_action_plan.recommended_next_actions`.

Branch-aware readiness also checks generic branch strategy fields before any
Agent Foundry-specific preset. Supported strategies are
`mainline-maintenance`, `integration-branch`, `release-branch`, `trunk-based`,
`stacked-pr`, `multi-branch`, and `custom`. The generic checks cover required
branch fields, expected PR base versus actual PR base, local dirty/staged/
unstaged/untracked/ahead/behind state, degraded or unknown remote reads, and
forbidden repair/apply actions. V1/V2 rules are an additional preset layer, not
the only branch model.

Valid `readiness_status` values are:

- `ready`: sampled evidence is ready for normal collaboration workflow.
- `needs_setup`: missing labels, routing template, contracts, or other setup
  gaps should be routed through existing Agent Foundry workflow.
- `needs_human_decision`: a Project/governance/product/privacy/final
  integration/closure choice needs a Human Decision Contract.
- `degraded`: at least one source is unavailable or partial, and the report
  records what is unknown instead of guessing.
- `blocked`: core GitHub evidence is unavailable enough that the user should
  unblock source access before relying on the report.

The report may include `dry_run_repair_plan` items, but every item must keep
`apply_supported_now` set to `false` until a later reviewed repair/apply issue
changes that boundary.

Recommended actions use these categories:

| Category | Meaning | Current handling |
| --- | --- | --- |
| `informational_only` | Evidence, status, or degraded optional mirrors that do not need mutation. | Explain and record; no workflow mutation required. |
| `agent_handled_existing_workflow` | A bounded issue/comment/label/PR/role-handoff action can proceed through existing Agent Foundry gates. | Route with durable issue or PR comments and `needs:*` labels. |
| `explicit_human_gate` | The action changes product, governance, privacy/security, final integration, closure, or meaningful Project policy. | Post a Human Decision Contract before action. |
| `unsupported_deferred_repair_apply` | The helper can describe the repair, but AF15 must not execute it. | Leave deferred or create a later gated issue. |

Branch action-plan concepts:

| Concept | Meaning | Current handling |
| --- | --- | --- |
| `current_branch_ok` | Current branch evidence matches a sampled contract. | Continue normal scoped work. |
| `switch_context_required` | Current checkout is not the target branch. | Stop editing here; route or prepare a separately reviewed context. |
| `split_work_recommended` | Request mixes branch lines, stacked work, or cross-line effects. | Split work or record ordered sub-work. |
| `forward_merge_needed_later` | Another line needs the accepted change later. | Record follow-up; do not merge automatically. |
| `verify_on_multiple_lines` | Cross-line readiness needs evidence on every named line. | Verify each branch line before acceptance. |
| `architect_decision_required` | Strategy is custom, unknown, or policy-sensitive. | Route to Architect before implementation or merge. |

Safe multi-branch UX for V2 work interleaved with generic Core updates:

1. Split the generic Core update from V2-only work.
2. Land the generic Core update on `main` first through the normal reviewed
   path.
3. Record `forward_merge_needed_later` for V2.
4. Use `verify_on_multiple_lines` before claiming cross-line readiness.
5. Keep checkout/switch, branch/worktree creation, PR retarget, rebase, merge,
   reset, clean, and repair/apply unsupported in the helper.

For new-project setup, use the action plan to confirm:

- standard role labels exist: `needs:architect`, `needs:implementer`,
  `needs:reviewer`, `needs:tester`, `needs:harvester`, and `needs:human`;
- the role-routing config is present and uses lowercase role tokens;
- Execution Contract and Testing Contract examples use machine-readable role
  and handoff values;
- human gates are named for product, governance, privacy/security, final
  integration, closure, or destructive decisions;
- optional Project fields and role options are visible if a Project mirror is
  configured;
- residual risks and the next safe workflow action are explicit.

For existing-project audit, use the action plan to identify drift:

- missing or extra `needs:*` routing labels;
- malformed Execution Contract or Testing Contract values;
- issue/PR routing that does not match next-owner state;
- missing or degraded Project v2 visibility;
- safe next actions grouped as informational, agent-handled, human-gated, or
  unsupported/deferred.

Project v2 remains an optional visual mirror. A degraded or unavailable Project
read should appear in the report without blocking issue/PR/label findings that
can still be read through REST. The helper must not perform full Project scans
by default, Project writes, label repair, comments, merges, closure, runtime
writes, Vault writes, generated adapter publishing, capability-pack publishing,
or V2 local-ledger implementation.

The action-plan shape is compatible with future local-first telemetry/backfill
work: it separates observed facts, unknown/degraded sources, action category,
owner role, and workflow route. AF15 does not implement V2, does not create a
Foundry Board or Local Collaboration Ledger, and does not make GitHub Project
the source of truth.

## Foundry Board Preview

Use `foundry-board` when a user needs a board-shaped, read-only view of current
local-first orchestration state before sync or write-back exists.

Skill-facing request:

```text
show Foundry Board
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> foundry-board \
  --ledger-root usage/local/collaboration-ledger \
  --issues 293,294,295 \
  --json
```

The report is read-only. It reads accepted Local Collaboration Ledger replay as
the board source of truth, may show imported candidate events as separate
review state, and treats bounded issue/PR/Project reads as remote mirror or
drift evidence only. It must keep:

```text
mutation_performed: false
apply_supported_now: false
full_project_scan_performed: false
```

The user-facing board should include:

- lanes such as `planned`, `ready`, `in_progress`, `tester_evidence`, `review`,
  `architect_acceptance`, `human_gate`, `blocked`, `stale_conflict`, `done`, and
  `superseded`;
- owner role and next owner role;
- target branch and branch-readiness status;
- latest evidence and evidence refs;
- accepted local ledger, imported candidate, and remote mirror state authority;
- confidence for migrated or inferred records;
- Project mirror status such as `in_sync`, `drift`, `degraded`,
  `not_configured`, or `unknown`;
- recommended next actions and forbidden actions.

GitHub issue/PR/Project evidence remains optional mirror evidence. A label,
issue-state, or Project mismatch should appear as mirror drift or conflict
evidence; it should not replace accepted local ledger replay and should not
cause the helper to write Project fields, close issues, retarget PRs, or repair
branch state. #360 candidate backfill events stay candidate/imported state until
a later reviewed migration gate accepts them.

The read-only MVP is allowed to say what a user or agent should do next through
existing workflow gates. It is not allowed to perform live repair/apply, Project
v2 mutation, GitHub write-back, real migration/backfill writes, branch
repair/apply, checkout/switch, PR retarget, rebase, merge, reset, clean,
runtime/Vault/private/generated mutation, generated Skill/adapter publish, or
capability-pack deploy/apply.

## Local Collaboration Ledger Storage And Replay

Use `local-ledger-report` when V2 local-first orchestration needs to inspect
the first durable local ledger slice without reading live GitHub.

Skill-facing request:

```text
show local collaboration ledger report
```

Debug/helper surfaces:

```text
agent-foundry-github-collab local-ledger-append \
  --ledger-root usage/local/collaboration-ledger \
  --event-json <event.json>

agent-foundry-github-collab local-ledger-report \
  --ledger-root usage/local/collaboration-ledger \
  --json
```

Default storage is append-only JSONL at
`usage/local/collaboration-ledger/events.jsonl`. Tests and temporary reviews
should pass an explicit `--ledger-root` under a temporary directory. The replay
surface derives work-item state from assignment, dispatch, callback, review,
acceptance, merge, closure, blocked, and sync-readback events. Every event must
carry provenance, confidence, and explicit `unknown` or `not_available` fields
when evidence is incomplete.

The report must include #266 telemetry for event count, active event count,
replay time, degraded evidence count, and user-facing output size. It is a
local source-of-truth slice for replay evidence, not a GitHub sync authority.

Forbidden in this MVP:

- #360 existing-project backfill;
- #361 ledger-backed Foundry Board behavior;
- #362 Project sync-plan generation;
- GitHub Project mutation or real GitHub write-back;
- issue closure automation;
- runtime/Vault/private/generated mutation;
- generated Skill/adapter publish;
- release/tag work;
- memory-system work.

## Existing Project Ledger Backfill Preview

Before previewing an existing adopter project, present a ten-minute guided
onboarding packet in user-facing language. The packet is the primary Human
interface; raw JSON is debug/evidence only. The packet should say at every
step:

- what the user says to start: "onboard this existing project into V2 Local
  Orchestration as a ten-minute read-only trial";
- what the agent reads: bounded issues, PRs, labels, comments, branch/status,
  durable issue/PR evidence, and relevant helper docs;
- what may be written: temporary JSON, HTML, and isolated local ledger evidence
  under an explicit temp root or user-supplied trial root;
- what must not be touched: adopter repo files, live GitHub Project fields,
  runtime/Vault/private/generated state, generated Skills, and capability
  packs;
- the one Human decision required now: fallback-set confirmation,
  candidate accept/skip/inspect evidence, local apply decision, sync apply
  choice, or final trust/readiness judgment;
- stop/defer conditions: wrong path or branch, unclear provenance, implied live
  mutation, unsafe Project/sync operation, or user cannot identify the next
  safe action.

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> guided-onboarding \
  --issues <explicit-current-issue-list> \
  --prs <optional-current-pr-list> \
  --trial-root /private/tmp/agent-foundry-guided-onboarding-trial
```

The packet is not itself a valid Human trial. For #390-style acceptance, the
trial must use response capture:

```text
agent-foundry-github-collab --repo <owner>/<repo> guided-onboarding \
  --issues <explicit-current-issue-list> \
  --trial-root /private/tmp/agent-foundry-guided-onboarding-trial \
  --trial-response-json /private/tmp/agent-foundry-guided-onboarding-trial/responses.json \
  --transcript-out /private/tmp/agent-foundry-guided-onboarding-trial/transcripts/trial.json
```

The protocol must report `blocked_waiting_for_human_response` and stop when the
next required Human response is missing. A transcript entry is required before
the agent treats a step as progressed. Captured responses should include the
step number, Human choice, Human response, optional timestamp, evidence refs,
and notes. The transcript may be written only inside the explicit trial root.
It is local evidence, not accepted local ledger authority.

Base remains the default mode for ordinary project work. Local Orchestration is
selected only through explicit trial/user intent, local capability config,
ledger manifest/state, an issue/task contract, or an accepted capability
profile. Do not infer Local Orchestration from merely seeing a GitHub project or
stage label.

If a stage-based query returns no candidates, do not imply the adopter project
must have a matching `stage:*` label. Fall back to explicit issue/PR selection
from durable GitHub evidence and report the selected issue/PR numbers. For
example, a renewed tiny-ipa trial should rehydrate current durable state; the
expected readback before #390 is #276-#281 closed and #282 labeled
`needs:user`, unless fresh GitHub evidence changes it. Do not reuse the stale
#386 active-item snapshot.

Candidate review stays non-authoritative: each candidate should show
`accept`, `skip`, `inspect evidence`, or `defer`, and no project state changes
until a later reviewed local apply accepts the candidate into the isolated
ledger.
Before local apply, show the isolated ledger location, cleanup boundary, and
no-effect guarantee. Project sync remains dry-run decision support with
visible `not executed` status until a separate reviewed and Human-gated apply
path is authorized.

Final structured Human evaluation is required before #390 can ask for
acceptance again. Capture clarity of starting context, confidence in
current-state evidence, candidate non-authority clarity, isolated
ledger/no-effect clarity, Project sync `not executed` clarity, next-step
actionability, remaining friction, and final decision:
`accepted`, `accepted_with_cleanup`, `rejected`, or `deferred`.

Use `local-ledger-backfill-preview` when an existing GitHub-first project needs
candidate Local Collaboration Ledger events for review before any authoritative
migration.

Skill-facing request:

```text
preview existing project ledger backfill
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> local-ledger-backfill-preview \
  --issues <bounded-issue-list> \
  --prs <bounded-pr-list> \
  --project-owner @me \
  --project-number <number> \
  --json
```

The preview may read bounded issue, PR, comment, label, milestone, and optional
Project mirror evidence. It produces candidate events compatible with
`local-ledger-append`, but does not append them. The report must separate
accepted local ledger state from candidate imported state and surface
contradictory history, stale labels, superseded work, missing evidence, owner
mismatches, closed issue not mirrored Done, Project Done while issue is open,
and degraded Project readback.

The report must include #266 telemetry for source count, API attempts, degraded
source count, candidate count, conflict count, and manual review count.

Forbidden in this preview:

- authoritative migration of candidate events without later approval;
- GitHub or Project mutation;
- branch repair/apply or PR retarget;
- #361 ledger-backed Foundry Board behavior;
- #362 Project sync-plan generation;
- runtime/Vault/private/generated mutation;
- generated publish or capability-pack deploy/apply;
- memory-system work.

Adopter-side validation note: the tiny-ipa trial validation request for #386/#387
is recorded at
https://github.com/farmerhunter/tiny-ipa/issues/27#issuecomment-4934556479.
If a maintainer response arrives before review, incorporate or answer it in the
cleanup/readiness evidence. If no response is present before final V2 readiness
resumes, the #376 Human Decision Contract must explicitly say the adopter-side
response is pending and ask whether Human defers that response.

## Accepted Migration Apply

Use `local-ledger-migration-apply` when reviewed backfill candidates have an
explicit accept/reject/skip decision and should be recorded in the accepted
Local Collaboration Ledger.

Skill-facing request:

```text
apply reviewed migration candidates
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> local-ledger-migration-apply \
  --ledger-root usage/local/collaboration-ledger \
  --candidate-events-json /tmp/backfill-preview.json \
  --decision-json /tmp/migration-decisions.json \
  --json
```

The candidate input should come from a reviewed `local-ledger-backfill-preview`
report or an equivalent candidate event list. The decision JSON must name
candidate event ids and the reviewed decision for each item: `accept`, `reject`,
or `skip`. The helper appends deterministic local ledger events, so reruns skip
already-recorded decisions instead of duplicating state.

The report must show before/after local replay summaries, appended and skipped
decision counts, provenance, manual review notes, #266 telemetry, and
compensating-event guidance. Accepted candidate events become local ledger
events; rejected or skipped candidates are recorded as evidence so the review
decision remains durable without rewriting history.

Allowed write scope:

- append-only local ledger JSONL under the selected `--ledger-root`;
- no GitHub issue/PR write-back;
- no GitHub Project mutation.

Forbidden in this apply step:

- #371 local action apply;
- #372 Project sync apply;
- #373 mixed-state recovery implementation;
- #378 management surface implementation;
- GitHub issue/PR mutation;
- GitHub Project mutation;
- issue closure automation;
- destructive ledger history rewrite;
- branch repair/apply or PR retarget;
- runtime/Vault/private/generated mutation;
- generated Skill publish or capability-pack deploy/apply;
- main merge, release, or tag work.

## Local Orchestration Action Apply

Use `local-ledger-action-apply` when an approved Foundry Board next action or
local orchestration action should become an accepted append-only Local
Collaboration Ledger event.

Skill-facing request:

```text
apply approved local board action
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> local-ledger-action-apply \
  --ledger-root usage/local/collaboration-ledger \
  --action-json /tmp/local-actions.json \
  --json
```

Supported action families are `assignment`, `handoff`, `blocked`,
`unblocked`, `review_result`, `architect_acceptance`, `human_approval`,
`local_done`, `closure`, `supersession`, and `recovery`. The action input must
name the work item, evidence refs when available, owner or target role when
relevant, required gate, approving role, and capability layer when the action is
not clearly local orchestration. `base`, `local_orchestration`, and `mixed`
must remain explicit report values rather than branch-derived assumptions.

Gate enforcement:

- `review_result`, `local_done`, and `closure` require reviewer approval.
- `architect_acceptance` requires architect approval.
- `human_approval` requires human approval.
- If the named `approved_by_role` does not match the required gate, the helper
  must fail closed before appending any ledger event.

The report must include before/after local replay state, appended and
idempotently skipped events, evidence refs, owner role, required gate, residual
risks, #266 telemetry, and forbidden remote side effects. Re-running the same
approved actions must not duplicate local state.

Forbidden in this apply step:

- #372 Project sync apply;
- #373 mixed-state recovery implementation beyond visible residual risks;
- #378 management surface implementation;
- GitHub issue/PR mutation;
- GitHub Project mutation;
- branch repair/apply or PR retarget;
- runtime/Vault/private/generated mutation;
- generated Skill publish or capability-pack deploy/apply;
- main merge, release, or tag work;
- destructive ledger history rewrite.

## Project Sync Plan Dry Run

Use `project-sync-plan` when V2 local-first orchestration needs to preview how
accepted local board/ledger state would mirror into GitHub Project fields.

Skill-facing request:

```text
preview GitHub Project sync plan
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> project-sync-plan \
  --ledger-root usage/local/collaboration-ledger \
  --issues <bounded-issue-list> \
  --project-owner @me \
  --project-number <number> \
  --json
```

The report must be dry-run only:

```text
mode: dry_run
mutation_performed: false
writes_supported_now: false
```

The sync plan reads the ledger-backed Foundry Board as local source of truth and
uses GitHub Project as an optional mirror. It should describe proposed
operations with before/after values, idempotency keys, evidence refs, gate
classification, and readback requirements. It should classify conflicts for
missing fields/options, ambiguous items, Project Done while issue open, issue
closed while Project is not Done, owner mismatch, local/remote freshness,
degraded Project readback, privacy-sensitive values, and branch-line mismatch.

Human gates include built-in Project Status side effects, issue closure/reopen
implications, privacy/security-sensitive sync, broad Project policy/schema
changes, and any future transition from dry-run to write/apply.

For adopter onboarding, `project-sync-plan` is decision support only. Live sync
or apply remains separately reviewed and Human-authorized. Degraded Project
visibility should be retried later or carried as `unknown` / `not_available`
unless the current step actually requires Project write/readback evidence.

Forbidden in this dry-run:

- live Project mutation or GitHub write-back;
- issue closure automation;
- real sync/apply;
- branch repair/apply, checkout/switch, PR retarget, rebase, merge, reset,
  clean, force push, or destructive action;
- runtime/Vault/private/generated mutation;
- generated publish or capability-pack deploy/apply;
- memory-system work;
- release/tag work;
- final V2 readiness closure.

## Project Sync Apply Gate

Use `project-sync-apply` only after a `project-sync-plan` has been reviewed and
accepted or revalidated. This is the V2 apply contract for GitHub Project mirror
operations, but current Core support is intentionally fake/mock backed: it
validates the plan, classifies gates, simulates targeted Project write/readback
results, and records local `sync_readback` evidence. It must not mutate a live
GitHub Project unless a later explicit gate adds and approves that behavior.

Skill-facing request:

```text
apply accepted Project sync plan
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> project-sync-apply \
  --ledger-root usage/local/collaboration-ledger \
  --sync-plan-json /tmp/project-sync-plan.json \
  --acceptance-json /tmp/project-sync-acceptance.json \
  --fake-project-write-json /tmp/fake-project-write-results.json \
  --json
```

The acceptance file must include `accepted: true` and durable `evidence_refs`.
Human-gated operations, such as built-in `Status` changes or
privacy/security-sensitive values, stay skipped unless their exact
`idempotency_key` appears in `human_approved_idempotency_keys`.

The fake write result file is keyed by operation `idempotency_key`. Each result
should include `status` and optional `readback` or error/degraded evidence.

The apply report must include applied operations, skipped operations, Human
gates, partial failures, appended local sync-readback events, idempotent skips,
before/after local replay summaries, residual risks, forbidden actions, and
#266 telemetry.

Human gates remain required for:

- built-in Project Status side effects;
- issue closure/reopen implications;
- privacy/security-sensitive Project values;
- broad Project policy/schema changes.

Forbidden in this apply step:

- live issue closure/reopen automation;
- broad Project scan by default;
- broad Project policy/schema mutation;
- privacy/security-sensitive Project writes without Human gate;
- #373 mixed-state recovery implementation;
- #378 management surface implementation;
- branch repair/apply or PR retarget;
- runtime/Vault/private/generated mutation;
- generated publish or capability-pack deploy/apply;
- main merge, release, or tag work;
- destructive git operation, reset, clean, or force push.

## Mixed-State Recovery Report

Use `mixed-state-recovery` when local-first ledger state, GitHub issue/PR
evidence, Project mirror state, candidate migration evidence, or branch-line
evidence disagree. This is the V2 recovery UX for messy overlap between
local-first and GitHub-first operation. It explains what is trusted, what is
candidate-only, what is mirror-only, what conflicts, and which safe next action
is available.

Skill-facing request:

```text
review mixed local and GitHub state
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> mixed-state-recovery \
  --ledger-root usage/local/collaboration-ledger \
  --issues 370,371,372 \
  --candidate-events-json /tmp/backfill-preview.json \
  --project-owner @me \
  --project-number 3 \
  --json
```

The report must classify:

- `local_newer`;
- `remote_newer`;
- `remote_only`;
- `candidate_only`;
- `partial_sync`;
- `stale_comment`;
- `branch_line_drift`;
- `superseded_work`;
- `degraded_project`;
- `out_of_band_human_edit`.

Recovery remains report-only. Safe next actions usually point to
`local-ledger-backfill-preview`, `local-ledger-migration-apply`,
`local-ledger-action-apply`, `project-sync-plan`, or a Human/Architect gate.
The helper must not guess authority from GitHub issue labels or Project fields,
rewrite ledger history, repair branches, retarget PRs, or mutate GitHub/Project
state.

Forbidden in this recovery step:

- hidden repair;
- guessing authority from GitHub issue or Project mirror;
- destructive ledger cleanup or rewrite;
- live GitHub issue/PR mutation;
- live GitHub Project mutation;
- branch repair/apply or PR retarget;
- runtime/Vault/private/generated mutation;
- generated Skill publish or capability-pack deploy/apply;
- main merge, release, or tag work.

## Operational Cockpit

Use `operational-cockpit` when V2 local-first orchestration needs a dogfoodable
management surface rather than raw JSON from separate helper commands. The
surface is a local operational cockpit and decision-support report. It is not a
replacement for GitHub Project; Project remains the richer remote
collaboration/control surface and optional mirror.

Skill-facing request:

```text
show the V2 operational cockpit
```

Debug/helper surface:

```text
agent-foundry-github-collab --repo <owner>/<repo> operational-cockpit \
  --ledger-root usage/local/collaboration-ledger \
  --issues 370,371,372,373 \
  --candidate-events-json /tmp/backfill-preview.json \
  --project-owner @me \
  --project-number 3 \
  --html-out /tmp/agent-foundry-operational-cockpit.html \
  --json
```

The ViewModel must keep identifiers stable across CLI JSON, human-readable
output, static HTML, and Skill-facing summaries. Required sections are:

- overview;
- board;
- item detail;
- migration review;
- local apply review;
- sync handoff;
- mixed-state recovery;
- health;
- telemetry.

The cockpit must tell users when to:

- stay local;
- open or check GitHub Project;
- run `project-sync-plan`;
- run accepted `project-sync-apply`;
- retry degraded Project later.

Report generation is no-write for product state. Writing the static HTML file is
only the local report artifact; it must not mutate GitHub, Project, runtime,
Vault, generated artifacts, or capability-pack state. HTML must not fetch
external assets, enable analytics, or expose local-private paths. Degraded or
unknown environment/version evidence must stay visible instead of being guessed
clean.

Forbidden in this cockpit step:

- live GitHub Project mutation;
- automatic sync/apply cadence;
- GitHub issue/PR write-back as product behavior;
- runtime/Vault/private/generated mutation;
- generated Skill publish;
- capability-pack deploy/apply;
- main merge, release, or tag work;
- branch repair/apply or destructive action.

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
