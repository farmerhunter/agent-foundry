---
id: COLLAB-008
title: Use GitHub Project as a lightweight agent scheduler
domain: agent-collaboration
type: pattern
status: active
version: 14
created: 2026-06-07
updated: 2026-08-10
tags: [agent-collaboration, github-project, scheduler, labels, epics, human-gate, thread-tools, project-readback, kanban, quota, snapshot, batching]
aliases:
  - COLLAB-008
  - GitHub Project as agent scheduler
  - labels as agent inbox
  - needs human routes human decision
  - human decision contract
  - meaningful human gate
  - main merge is not automatically human gate
  - role dispatch resolution order
  - dynamic thread tool surface
  - source thread callback
  - Project enrollment readback
  - roadmap issue Project field audit
related: [COLLAB-002, COLLAB-004, COLLAB-007, COLLAB-009, COLLAB-010, COLLAB-012]
applies_when:
  - using GitHub Project with multiple agents
  - agents need to discover their own next work
  - issue state, review state, and PR state must remain durable across sessions
provenance: "Harvested from tiny-ipa workflow design on 2026-06-07, where Project status, labels, Epics, comments, PRs, and CI formed a minimal agent scheduler; v8 refined after tiny-ipa M7 dogfood to distinguish meaningful human gates from mechanical final-merge approvals; v9 refined after Agent Foundry AF10-B review to require human-gate live responses with review points; v10 refined after Agent Foundry AF11/AF10 Project repair on 2026-06-23 to require transition-gated Project enrollment readback for roadmap scheduler issues without making Project v2 an always-on source of truth. v11 refined after Agent Foundry AF15 closure and Kanban cleanup showed completed issues should remain visible in the Project Done lane rather than be removed or left in Inbox/In Progress; v14 refined after AF18 Kanban repair encountered GraphQL quota exhaustion on 2026-08-10."
---

## Principle

Use GitHub's existing durable objects as a lightweight scheduler before inventing a custom agent-management system.

## Rationale

Two or more agents need shared state. Chat context and human clipboard relay do not scale: they are transient, incomplete, and invisible to other agents. A GitHub Project, with issues, labels, comments, PRs, and CI, already provides the minimum scheduler loop for many small projects.

The key is to distinguish human-readable state from agent-readable routing. Project status is good for a board. Labels are better as queryable inboxes. Comments carry the message body. PRs carry the deliverable and review. CI carries automatic validation.

## Guidance

Map collaboration surfaces explicitly:

```text
GitHub issue = task object
Epic issue = cross-issue coordination memory
Child issue = executable work and acceptance unit
Project status = human-visible state
needs:* label = agent inbox / routing key
issue or PR comment = durable message body
PR = deliverable and review surface
CI = automated validation gate
```

This is a lightweight scheduler substrate, not a full coordinator. It does not maintain an independent Manager/Coordinator entity, persistent session ownership model, or automatic role assignment. Keep the simple mode robust by making the session, role, and task binding explicit whenever work moves between states.

Use these meanings:

```text
task = issue, PR, batch checkpoint, or Epic acceptance unit
role = Architect, Implementer, Reviewer, Harvester, user, or CI responsibility
session = the current agent conversation or runtime instance that may perform one or more roles
owner role = the role currently responsible for the next action on the task
review target = who or what must validate the task before Done
human decision = a judgment, authorization, or missing input that only the user can provide
```

Roles are responsibilities, not identities. A single session may perform multiple roles over time, and the same human account may drive several roles. When a session changes role for a task, say so explicitly in the issue comment, PR comment, or final report.

Coordinator ownership includes the live handoff, not just the durable announcement. After assigning work, dispatch it through the selected role thread or bounded subagent, watch for completion, read the exact verdict, and return the result to the durable scheduler surface. A GitHub comment that merely requests review is not proof that the role was dispatched or that its result was observed.

When initializing persistent role sessions, give each session a role-specific startup contract rather than relying on ad hoc chat history. The startup prompt should name the role, repository path, durable scheduler surfaces, current branch or stage when known, source-of-truth boundaries, tool-surface discovery requirements, allowed and forbidden actions, callback expectations, and stop conditions. At minimum, prepare separate templates for Architect, Implementer, and Reviewer because their authority, risk gates, and no-op behavior differ.

Keep Epics as coordination containers. Do not put `needs:implementer` on an Epic merely because its child issues are ready. If an Epic-level concern requires code, tests, manual QA, data migration, or completion evidence from an Implementer, create a child issue for that executable work.

Keep issue type semantically honest. Use an Epic for coordination across child issues, dependencies, or exit criteria. If the remaining work has collapsed into one concrete deliverable, classify it as a Task even when the Architect performs it directly.

Use exactly one primary next-action label on an active issue unless the work is genuinely blocked:

```text
needs:architect
needs:implementer
needs:reviewer
needs:harvester
needs:human
needs:ci
blocked
```

Use `needs:human` when the next action is not an agent role but a human decision, authorization, verification, or input. Do not leave such work in `needs:architect` merely because the Architect prepared the decision.

Do not route a task to `needs:human` merely because a PR targets `main` if the repo workflow delegates low-risk `main` merge authority and the PR has latest-head review, verification, and clean scheduler evidence. A merge button is not by itself a meaningful human decision.

Typical `needs:human` triggers include:

```text
close an Epic, stage, or migration window
runtime apply or local config rewrite
data migration, deletion, force push, reset, or other destructive action
privacy, security, trust, cost, or external dependency decision
user-visible behavior or UX change that needs manual trial or product acceptance
product or architecture direction choice that the user has not delegated
missing user-specific input such as account, path, remote, runtime, or preference
```

When using `needs:human`, the durable comment must contain a Human Decision Contract, not a generic request to "review" or "approve merge." It should state the decision needed, why human judgment is required, the current agent conclusion, options, consequences, verification already done, residual risks, and an explicit authorization phrase or trial response.

Before asking for approval, explain the same contract in plain language in the live conversation: the background, the concrete decision, the decision basis, the consequences of each option, what has already been verified, and the remaining risk. Do not make the Human open GitHub to discover what the approval means.

When the human is actively present in the current conversation, the live response must summarize the same decision in user-facing terms. Include the review points the human should inspect, the available options and consequences, verification already done, residual risks, and the exact authorization phrase or trial response. Do not make the user open GitHub merely to discover what they are approving.

For user-facing behavior or UX gates, the Human Decision Contract should give the user a concrete trial path:

- how to start the app or feature;
- what scenario to execute;
- what changed from the previous behavior;
- what the agent already verified automatically;
- what subjective or product judgment the human must make;
- what action becomes allowed after acceptance, such as merge, closure, or release.

Legacy or repo-local labels such as these may exist, but do not use them in a new scheduler contract unless the repo has explicitly defined them:

```text
needs:user
needs:merge
```

When changing handoff ownership, change both the label and the durable comment. The label routes the next agent; the comment explains what to do.

`needs:*` labels route the next role. They do not automatically require a different session or a new conversation. If the current session can satisfy the next role, state that explicitly, for example: `Next action: current Architect session will perform structured self-review`.

When the next owner is a separate role session, resolve the dispatch mechanism in this order:

```text
1. Preserve durable GitHub state first: issue or PR label plus handoff comment.
2. Reuse an existing named role thread when live thread tools are available.
3. Spawn a bounded subagent only when existing role-thread dispatch is unavailable, unsuitable, or explicitly not requested.
4. Fall back to a portable prompt for the user or another runtime only after live dispatch and subagent options are unavailable.
```

Do not treat "thread tool unavailable" as "dispatch unavailable" until checking for the current runtime's subagent or multi-agent spawn capability. Conversely, do not spawn a fresh subagent when an existing role thread is available and better preserves the role-session workflow. If falling back to a new subagent, say why and keep the prompt bounded to one issue, PR, or explicit batch.

Treat live thread tooling as a current-session capability, not as a stable product assumption. Before claiming existing role-thread dispatch is available or unavailable, inspect the actual tool surface exposed to the current agent, such as the available tool list or `tool_search` results. In Codex, `list_threads`, `read_thread`, and `send_message_to_thread` may appear in one thread or launch mode and be absent in another. If they are absent, say that the current session lacks the live thread tools; do not claim that Codex removed the feature unless verified from current documentation or release notes. Then continue through the fallback order: subagent or multi-agent tools, automation when appropriate, and finally a portable prompt plus durable GitHub handoff.

When live thread dispatch includes a caller or `source_thread_id`, include it in the dispatched prompt and require a callback after the target role updates durable scheduler state. The callback should summarize what changed, link the issue or PR comments that carry durable evidence, state verification and residual risks, and say whether the target is done, blocked, or returning ownership. If callback tooling is absent or fails, the target role must still leave enough durable GitHub state for the source session or another agent to resume.

Keep scheduler state coherent across surfaces:

- `Ready` means available for pickup, not completed.
- `In Progress` means an agent is actively executing or holding the work.
- `Review` means the producing agent has posted completion evidence and the next owner must validate or decide.
- `Done` means the work has been accepted and closed, or the Epic exit criteria are satisfied.

Do not leave one status surface saying `Ready` while another says `Done`. If a repository uses both GitHub's built-in Project `Status` and a custom roadmap status field, update both to represent the same lifecycle phase.

For Project/Kanban cleanup, align the lane to lifecycle state; do not remove completed work from the Project merely to make the board look clean. Closed and accepted issues should remain visible in the Project's `Done` lane when the roadmap board is the human planning surface. The repair target for a completed issue in `Inbox`, `Todo`, `Ready`, `In Progress`, or `Review` is usually `Status=Done` and corresponding roadmap status, not Project removal.

When a task enters `Review`, its durable comment or contract should name the review target: current session structured self-review, user review, separate Reviewer agent, CI/automation, or batch/Epic checkpoint.

For roadmap or stage-tracked issues, treat Project enrollment as part of the scheduler transition, not as background decoration. When creating, importing, reopening, releasing, accepting, or closing an issue that participates in the roadmap scheduler, such as an issue labeled `stage:AF-*` or routed with `needs:*`, perform a transition-gated Project readback or batch audit before declaring the transition complete. Verify that the issue has a Project item and that key fields such as built-in `Status`, custom `Roadmap Status`, `Stage`, `Owner Role`, and `Risk` are populated consistently with labels, issue state, and the durable handoff comment.

Keep this check bounded. Do not query Project v2 for every ordinary issue read, code edit, or PR diff review. Prefer one batch `issue list` plus one Project item list comparison for a stage, milestone, or release batch instead of per-issue Project GraphQL calls. If Project v2 is slow or transiently fails, retry serially for state repair, record the blocker when appropriate, and continue using labels/comments as the agent inbox for non-transition reads.

Treat Project API quota as a bounded scheduler resource. Read one complete snapshot and the field/option map, calculate the local diff, and use one writer for small mutation batches. Check the remaining quota and reset time before and during repair; stop when the budget is low instead of polling. Persist a resume manifest for unfinished batches, then perform one post-batch readback rather than re-reading the whole Project after every item. Never run concurrent Project writers for the same repair.

## Use This When

- Agents ask "what should I pick up next?"
- The user wants cross-agent interaction to happen through GitHub issues and comments.
- A workflow needs both a human Kanban view and a CLI-searchable agent inbox.

## Watch Out For

- Do not rely on Project status alone for agent pickup. Labels are easier for agents to query.
- Do not treat labels as sufficient scheduler state when the human Kanban view is part of the workflow. A labeled roadmap issue that is missing from the configured Project, or has empty scheduler fields, is invisible or misleading in Project-based planning and must be repaired at transition time.
- Do not rely on labels alone for context. The latest durable comment must explain the next action.
- Do not let Epic coordination issues become fake implementation work. Split executable concerns into child issues.
- Do not keep a completed or closed issue in `Ready`; move it to `Review` for validation or `Done` after acceptance.
- Do not remove closed roadmap issues from the Project as a substitute for moving them to `Done` when the user expects the Kanban board to preserve completed history.
- Do not repeatedly scan or mutate the full Project from inside a per-issue loop; quota exhaustion is a scheduler failure, not a reason to guess fields.
- Do not call Kanban cleanup complete after inspecting only one lane, one issue, or labels alone. Read Roadmap/Project status for the relevant issue set and repair mismatches by lifecycle status.
- Do not keep a single-deliverable policy or implementation issue labeled as an Epic merely because it came from roadmap planning.
- Do not confuse role with session identity. `needs:architect` or `needs:reviewer` routes the next role; it does not always require a different agent or conversation.
- Do not leave `Review` without a review target. The scheduler cannot be checked if no one can tell whether review means current-session self-review, user review, separate reviewer, CI, or batch checkpoint.
- Do not stop after checking only one tool family. Existing role-thread dispatch, subagent spawn, automation, and portable prompt fallback are different mechanisms with different costs and availability.
- Do not rely on remembered tool availability from an earlier session. Re-check the current session's exposed tools before choosing or rejecting live thread dispatch.
- Do not treat live callback as the scheduler source of truth. Callback is a convenience notification after durable issue, PR, label, or Execution Contract state is updated.
- Do not use `needs:human` as a ritual final merge queue when no real human judgment remains.
- Do not let a user-visible behavior or UX decision slip through as "just merge approval"; surface the behavior, trial path, and acceptance question directly.
- Do not ask for approval with only an authorization phrase. A meaningful human gate needs the review points, choices, consequences, verification, and residual risks in the live response as well as the durable contract.

## Example

In tiny-ipa, `Backlog -> Ready -> In progress -> In Review -> Done` remained the human board, while `needs:implementer` and `needs:architect` became the agent inboxes. An Implementer could search labels, read issue contracts, and pick up work without the user copying a message between agent windows.

In Agent Foundry AF15, final closure left #321 and #314 closed but one item briefly remained in a non-Done lane after a GitHub API timeout. The correct repair was to preserve both Project items and verify they showed `Done`, while labels and issue state provided the agent-routing truth.

## Activation

- Tier: workflow_embedded
- Phases: planning, pickup, review, verification
- Signals: GitHub Project board; issue labels for role routing; multi-agent handoff; Epic/child issue hierarchy
- Evidence: report which Project/status, labels, issue comments, and PRs form the scheduler state; for roadmap/stage issue creation or routing, report the Project item readback or batch audit result showing the issue is enrolled and key scheduler fields are populated

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-004]]
- [[COLLAB-007]]
- [[COLLAB-009]]
- [[COLLAB-010]]
- [[COLLAB-012]]
