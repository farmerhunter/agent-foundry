---
id: COLLAB-003
title: Auto-merge validated PRs by default
domain: agent-collaboration
type: heuristic
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [github, pull-requests, merge, validation]
aliases:
  - merge after validation unless review requested
  - default auto merge PR flow
  - COLLAB-003
related: [COLLAB-001, COLLAB-002]
applies_when:
  - a user has authorized auto-merge for PRs
  - a PR was created to complete an issue
  - validation has completed successfully
review_required: false
provenance: "Harvested from explicit 2026AgentApp user workflow preference."
---

## Principle

When the user has authorized automatic PR handling, merge a validated PR by default unless the user asks for manual review or a hold.

## Rationale

Requiring manual review for every small PR slows down agent-assisted development when the user has already delegated that decision. The important boundary is validation quality, not ritual waiting.

## Guidance

After opening a PR, run the relevant checks, inspect failures, and fix issues before merging. If checks pass and the user has not requested review, merge the PR using the repository's normal merge method. Then update the linked issue with completion and verification details.

## Use This When

- The user has said PRs can be auto-merged.
- The PR has a clear issue scope and validation evidence.
- The change does not require a product or architecture decision still pending from the user.

## Watch Out For

- Do not auto-merge when tests fail, CI is red, or review was explicitly requested.
- Do not auto-merge destructive, irreversible, or security-sensitive changes without confirmation.

## Example

For a data fixture PR with passing `validate:data` and `build`, merge it and comment on the issue with the PR number, merge commit, and validation output.

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-002]]
