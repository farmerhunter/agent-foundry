---
id: COLLAB-001
title: Git autonomy follows workflow state
domain: agent-collaboration
type: playbook
status: active
version: 2
created: 2026-05-26
updated: 2026-06-09
tags: [github, issues, pull-requests, traceability, commits, workflow-state]
aliases:
  - COLLAB-001
  - issue code changes go through pull requests
  - bind issue work to PRs
  - commit autonomy follows workflow state
  - issue work may commit and open PRs
related: [COLLAB-002, COLLAB-003, COLLAB-004]
applies_when:
  - implementing code for a GitHub issue
  - making documentation or configuration changes for a GitHub issue
  - handing code work between local and remote agents
  - preparing an issue for review or closure
review_required: false
provenance: "Harvested from 2026AgentApp session involving issue #71/#73 traceability gaps."
---

## Principle

When work is explicitly inside an issue, branch, and PR workflow, the agent may create commits, push the task branch, and open a PR after appropriate verification. Higher-risk transitions still require explicit approval: direct commits to `main`, PR merge, issue closure, force push, reset, deletion, data migration, or privacy-sensitive changes.

## Rationale

Blanket "do not commit unless explicitly asked" rules slow down issue-driven collaboration and leave useful work as uncommitted local state that other agents cannot review or continue. At the same time, direct commits to protected branches, merge decisions, destructive Git operations, and issue closure change shared project state and need a clearer approval boundary.

The durable rule should follow workflow state rather than a hardcoded local preference. Once the user or Architect has authorized a task through a GitHub issue, branch strategy, and PR target, commit/push/PR creation are normal execution steps. Acceptance, merge, closure, and destructive operations remain governed review points.

## Guidance

Before editing for an issue, read the issue scope, dependencies, branch strategy, PR target, and completion handoff. If the task is authorized for branch/PR work:

1. create or use the task branch;
2. make the focused changes;
3. run appropriate checks;
4. commit the verified changes with a task-relevant message;
5. push the branch;
6. open or update a PR that references the issue;
7. post completion scope, verification, and residual risks on the issue or PR.

Do not stop for separate permission merely to create the normal task commit, push the task branch, or open the PR. Do stop for approval before merging, closing the issue, committing directly to `main`, force pushing, resetting, deleting files or branches, migrating private data, or changing privacy/security boundaries.

For exploratory changes that are not tied to an issue/branch/PR workflow, show the diff before committing unless the user has explicitly authorized commit-and-PR handling for that work.

## Use This When

- The user says to start work on a numbered GitHub issue.
- The task requires code, documentation, configuration, or workflow changes that should be reviewed, merged, or audited later.
- Multiple agents or machines are collaborating on the same repository.
- A local preference says not to commit unless explicitly asked, but the current work has already entered a governed issue/PR workflow.

## Watch Out For

- Do not treat a local commit message as enough traceability.
- Do not direct-commit to `main` merely because branch creation is inconvenient.
- Do not merge the PR or close the issue unless the completion handoff, user instruction, or repository policy authorizes that transition.
- Do not use commit autonomy to bypass human review for architecture, taxonomy, privacy, security, harvest, or activation decisions.
- Avoid closing or moving the issue without linking the PR or final commit and recording verification evidence.

## Example

For an issue that adds a static demo adapter, create a branch such as `issue-71-static-demo-job`, run validation, commit the change, push the branch, open a PR that references `#71`, and comment on `#71` with the PR, commit, verification results, and residual risks. Merge and close only when the review/acceptance rule for that issue allows it.

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-003]]
- [[COLLAB-004]]
