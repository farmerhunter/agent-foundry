---
id: COLLAB-012
title: Review handoff needs both issue and PR surfaces
domain: agent-collaboration
type: checklist
status: active
version: 5
created: 2026-06-07
updated: 2026-06-09
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

When review sends work back to an Implementer, put the handoff on both the PR and the child issue. Prefer review at a meaningful Epic, sub-Epic, or batch checkpoint instead of forcing review after every small child issue. An open child PR is not automatically an Architect review request.

## Rationale

Agents do not always enter work through the same surface. One may query issues by label; another may inspect PR comments. If detailed feedback exists only on the PR, the issue inbox lacks context. If the issue contains only a summary and the PR has no pointer, the Implementer may miss file-level review. Dual-surface handoff makes the routing signal and the actionable feedback meet.

Review itself is also a coordination cost. For small related issues inside one Epic, repeated per-issue review can turn the human or Architect into a message broker. When the work is low-risk and dependency-gated, let the Implementer complete the planned batch and review the combined evidence at the natural checkpoint. Child PRs remain useful traceability and integration units, but they are not by themselves blocking review gates.

Review is a validation state, not automatically a cross-session wait. In the lightweight scheduler model, a role can be fulfilled by the current session, the user, a separate Reviewer agent, CI/automation, or a batch/Epic checkpoint. The handoff must name the review target so the next action is detectable.

## Guidance

When Architect requests changes:

1. Post detailed code, API, or test feedback on the PR.
2. Post a short child-issue handoff comment that links to the PR feedback.
3. If the latest PR conversation does not already point to the handoff, post a short PR follow-up too.
4. Replace `needs:architect` with `needs:implementer` on the child issue.
5. Leave Project status as `In Review` unless the task is explicitly reopened.

When planning review granularity:

- Prefer Epic, sub-Epic, or batch review for related low-risk child issues.
- Before reviewing an individual child PR, check the issue's `Completion handoff`, the parent Epic queue, and whether a high-risk trigger is present.
- For any issue in `Review`, identify the review target: current Architect session structured self-review, user review, separate Reviewer agent, CI/automation, or batch/Epic checkpoint.
- If the same session switches from producing role to reviewing role, mark it as structured self-review and list residual risks. Do not present it as independent review.
- Require independent user or separate-agent review when the contract says so, the user requests it, or the work has high-risk privacy, security, irreversible architecture, external dependency, cost, or data-retention consequences.
- Review individual issues immediately when they introduce blockers, high-risk changes, unclear dependencies, privacy/security risk, schema/runtime boundary changes, external dependency/provider/cost changes, shared contract changes, or a failed verification signal.
- If the issue says `Completion handoff: batch checkpoint` and no high-risk trigger exists, do not create a blocking per-issue Architect review. Let the batch continue to its checkpoint.
- If a batch review sends work back, include both the batch-level summary and the specific issue or PR links that need action.
- Keep child issues traceable, but do not require a separate Architect interaction for every child issue when the review question is really batch-level.
- When an Implementer finishes evidence-only work, preliminary classification, or any task with Architect-owned decisions, the issue should move to `Review`, not `Done`. Remove `needs:implementer`, add `needs:architect` or `needs:reviewer`, keep the issue open, and post completion evidence plus residual risks.
- For a batch checkpoint, every completed child issue may move to `Review` while the Architect waits for the full batch before reviewing. Batch review reduces interactions; it does not mean child issues skip the review state.

For a review-ready issue or PR, the handoff should include:

```markdown
## Review handoff

Review target: current Architect session structured self-review | user | separate Reviewer agent | CI/automation | batch/Epic checkpoint
Review surface: issue | PR | both
Producer role: Architect | Implementer | Reviewer | Harvester
Residual risks: ...
Independent review required: yes/no, because ...
Done condition: ...
```

The child issue handoff for requested changes should include:

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
- Do not treat an open child PR as sufficient reason to add `needs:architect`; review ownership follows the completion handoff, high-risk triggers, failed verification, or the batch/Epic checkpoint.
- Do not let an Implementer close an issue that still requires Architect-owned taxonomy, policy, privacy, security, harvest, generated-artifact, or Core/Vault decisions.
- Do not leave batch child issues in `Ready` after the producing agent has posted completion evidence; move them to `Review` until the batch is accepted.
- Do not equate `Review` with "wait for another session" unless the handoff names a separate reviewer. If the current session owns the review role, continue with structured self-review instead of stalling.
- Do not hide self-review behind generic review wording. Name the review mode so later agents and the user can judge independence.

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
