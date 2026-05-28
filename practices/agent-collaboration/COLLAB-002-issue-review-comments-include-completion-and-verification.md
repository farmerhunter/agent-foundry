---
id: COLLAB-002
title: Issue review comments include completion and verification
domain: agent-collaboration
type: checklist
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [github, issues, review, verification]
aliases:
  - issue completion comment standard
  - review-ready issue comment
  - COLLAB-002
related: [COLLAB-001, COLLAB-003]
applies_when:
  - preparing a GitHub issue for review
  - closing an issue after implementation
  - handing work back to the user
review_required: false
provenance: "Harvested from 2026AgentApp issue completion workflow feedback."
---

## Principle

An issue moved to review or closure must include a comment that states what was completed, how it was verified, and what the verification showed.

## Rationale

Reviewers should not have to reconstruct completion state from commits, branches, or local command history. A concise issue comment creates a durable handoff for humans and agents.

## Guidance

Before marking an issue ready for review or closed, add a comment with:

- completion scope;
- linked PR and final commit when applicable;
- verification commands or manual checks;
- verification results;
- known residual risks or skipped checks.

## Use This When

- The user asks to move an issue to review.
- The issue is ready to close.
- Work was completed by another agent and needs independent confirmation.

## Watch Out For

- Do not write only "done" or "fixed".
- Do not rely on the final chat response as the durable record.

## Example

After validating a release checklist, comment with `npm run validate:data`, `npm run build`, browser checks, pass/fail results, and remaining non-blocking findings.

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-003]]
