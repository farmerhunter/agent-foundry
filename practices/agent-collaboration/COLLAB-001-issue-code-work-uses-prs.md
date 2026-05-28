---
id: COLLAB-001
title: Issue code work uses PRs
domain: agent-collaboration
type: playbook
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [github, issues, pull-requests, traceability]
aliases:
  - issue code changes go through pull requests
  - bind issue work to PRs
  - COLLAB-001
related: [COLLAB-002, COLLAB-003, COLLAB-004]
applies_when:
  - implementing code for a GitHub issue
  - handing code work between local and remote agents
  - preparing an issue for review or closure
review_required: false
provenance: "Harvested from 2026AgentApp session involving issue #71/#73 traceability gaps."
---

## Principle

Code changes made to complete a GitHub issue should go through a feature branch and pull request unless the user explicitly approves skipping the PR.

## Rationale

Direct commits make it hard for reviewers and other agents to see which code belongs to which issue. If history is later rewritten, squashed, or synchronized across machines, the issue can lose its visible connection to the implementation.

## Guidance

Before coding for an issue, create a branch named for the issue or task. Open a PR that references the issue, include the completion summary and verification results, and merge only after the relevant checks pass. If the user explicitly asks for direct commits, record the affected commit and file locations in the issue comments.

## Use This When

- The user says to start work on a numbered GitHub issue.
- The task requires code changes that should be reviewed, merged, or audited later.
- Multiple agents or machines are collaborating on the same repository.

## Watch Out For

- Do not treat a local commit message as enough traceability.
- Avoid closing or moving the issue without linking the PR or final commit.

## Example

For an issue that adds a static demo adapter, create a branch such as `issue-71-static-demo-job`, open a PR that references `#71`, run validation, merge the PR, and comment on `#71` with the PR, commit, and verification results.

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-003]]
- [[COLLAB-004]]
