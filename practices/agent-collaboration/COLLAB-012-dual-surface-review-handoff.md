---
id: COLLAB-012
title: Review handoff needs both issue and PR surfaces
domain: agent-collaboration
type: checklist
status: active
version: 2
created: 2026-06-07
updated: 2026-06-08
tags: [agent-collaboration, review, handoff, github, pull-requests]
aliases:
  - COLLAB-012
  - dual-surface review handoff
  - issue and PR review handoff
related: [COLLAB-002, COLLAB-007, COLLAB-008, COLLAB-009]
applies_when:
  - Architect requests changes on a PR
  - an issue is moved from `needs:architect` back to `needs:implementer`
  - another agent reports that it cannot find review feedback
provenance: "Harvested from tiny-ipa M2 review cycle on 2026-06-07, where Implementer could see labels but not the reason for requested fixes until issue and PR comments were both used."
---

## Principle

When review sends work back to an Implementer, put the handoff on both the PR and the child issue. Prefer review at a meaningful Epic, sub-Epic, or batch checkpoint instead of forcing review after every small child issue.

## Rationale

Agents do not always enter work through the same surface. One may query issues by label; another may inspect PR comments. If detailed feedback exists only on the PR, the issue inbox lacks context. If the issue contains only a summary and the PR has no pointer, the Implementer may miss file-level review. Dual-surface handoff makes the routing signal and the actionable feedback meet.

Review itself is also a coordination cost. For small related issues inside one Epic, repeated per-issue review can turn the human or Architect into a message broker. When the work is low-risk and dependency-gated, let the Implementer complete the planned batch and review the combined evidence at the natural checkpoint.

## Guidance

When Architect requests changes:

1. Post detailed code, API, or test feedback on the PR.
2. Post a short child-issue handoff comment that links to the PR feedback.
3. If the latest PR conversation does not already point to the handoff, post a short PR follow-up too.
4. Replace `needs:architect` with `needs:implementer` on the child issue.
5. Leave Project status as `In Review` unless the task is explicitly reopened.

When planning review granularity:

- Prefer Epic, sub-Epic, or batch review for related low-risk child issues.
- Review individual issues immediately when they introduce blockers, high-risk changes, unclear dependencies, privacy/security risk, schema/runtime boundary changes, or a failed verification signal.
- If a batch review sends work back, include both the batch-level summary and the specific issue or PR links that need action.
- Keep child issues traceable, but do not require a separate Architect interaction for every child issue when the review question is really batch-level.

The child issue handoff should include:

```markdown
## Implementer handoff: changes requested

This issue was moved back to `needs:implementer` after Architect review.

Fix branch: `agent/<issue-number>-...`
PR: #...
Detailed review: <PR comment URL>

Next action:
- Checkout the fix branch.
- Apply the requested fix from the PR review comment.
- Add or adjust regression tests for the blocker.
- Push the same branch and move this issue back to `needs:architect` when ready for re-review.
```

## Use This When

- Review feedback crosses from Architect to Implementer.
- A batch of related issues is ready for Architect or Reviewer verification.
- Same GitHub account limitations prevent formal "request changes" review state.
- Labels moved but the next agent asks "what exactly needs fixing?"

## Watch Out For

- Do not rely only on labels. Labels route ownership; they do not carry enough context.
- Do not rely only on PR comments when agents discover work through issue labels.
- Do not ask the Implementer to create a replacement branch unless the existing fix branch is truly unusable.
- Do not create needless per-issue review churn when a batch checkpoint would catch the same risks with less handoff overhead.

## Example

In tiny-ipa M2, issues were returned to `needs:implementer`, but DeepSeek initially could not find why. The fix was to add a durable issue handoff pointing to PR review details and ensure the PR conversation also contained the current handoff.

## Activation

- Tier: workflow_embedded
- Phases: review, handoff, re-review
- Signals: `needs:architect` to `needs:implementer`; PR review requested changes; agent cannot find feedback; same-account PR review limitation
- Evidence: report both the issue handoff URL and PR review/comment URL

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-009]]
