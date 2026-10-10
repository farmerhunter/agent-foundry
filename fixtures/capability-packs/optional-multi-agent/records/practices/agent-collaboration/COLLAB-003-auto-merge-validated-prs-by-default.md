---
id: COLLAB-003
title: Auto-merge validated PRs by default
domain: agent-collaboration
type: heuristic
status: active
version: 5
created: 2026-05-26
updated: 2026-08-31
tags: [github, pull-requests, merge, validation, self-review, human-gate]
aliases:
  - COLLAB-003
  - merge after validation unless review requested
  - default auto merge PR flow
  - structured self-review can satisfy low-risk PR review
  - risk-classified main merge
  - meaningful human gate before mechanical merge approval
related: [COLLAB-001, COLLAB-002]
applies_when:
  - a user has authorized auto-merge for PRs
  - a PR was created to complete an issue
  - validation has completed successfully
review_required: true
provenance: "Harvested from explicit 2026AgentApp user workflow preference; v3 refined after tiny-ipa M7 dogfood showed that mechanical final-main approval is a low-value gate compared with meaningful behavior, UX, and risk decisions. v4 refined after tiny-ipa #173/#178 docs-only auto-merge miss showed agents must classify the PR against repo policy before requesting human approval."
---

## Principle

When the user has authorized automatic PR handling, merge a validated PR by default unless a meaningful human decision remains.

Do not treat the final merge button as the primary safety gate. The important gate is whether the change has been correctly classified, reviewed, verified, and either accepted by agents or routed to the human for a real product, UX, risk, or irreversible decision.

## Rationale

Requiring manual review for every small PR slows down agent-assisted development when the user has already delegated that decision. In vibe-coding workflows the user usually does not inspect every branch diff, so asking for repeated "merge?" approvals creates ceremony without improving safety.

Human attention should be spent on decisions only the human can make: behavior changes, user experience quality, product direction, destructive or irreversible changes, privacy/security/trust boundaries, data migration, deployment, external cost, and unclear risk classification.

## Guidance

After opening a PR, run the relevant checks, inspect failures, and fix issues before merging. If checks pass, the latest PR head has acceptable review evidence, the change is low-risk, and the user or workflow contract has authorized auto-merge, record a structured review or acceptance comment and merge the PR using the repository's normal merge method. Then update the linked issue with completion and verification details.

PRs targeting `main` may be auto-merged when all of these are true:

- the issue or repo workflow has delegated low-risk `main` merge authority;
- the PR is scoped to a child issue, small fix, docs/tooling change, or explicitly released direct-to-main task;
- latest-head Reviewer, Architect self-review, CI, or other configured review target has no blocking findings;
- required verification has passed, including browser/walkthrough evidence for user-facing workflow changes;
- `agent-audit` or the repo's scheduler audit is clean enough to proceed;
- no user hold, requested manual review, unresolved requested-changes thread, or unclear risk remains;
- the PR does not touch a high-risk boundary listed below.

Before requesting human approval for a `main`-target PR, classify the action against both the repo policy and the issue contract:

- docs-only, tooling-only, small fix, product runtime, schema/data, deployment/runtime, destructive, privacy/security, UX/product judgment, or external dependency;
- scoped to one issue or cross-issue;
- CI and configured checks status;
- hold, do-not-merge, requested manual review, or unresolved requested-changes state;
- whether the issue contract is stricter than the repo's default auto-merge policy.

If the issue contract is stricter than the repo default, identify the reason and ask its authorized owner to resolve the conflict durably. An explicit hold, do-not-merge instruction, requested manual review or unresolved blocking finding remains binding even without a written risk rationale. The executing agent must not remove that restriction by calling it over-conservative. Once the authority is resolved, proceed under the applicable delegation without asking for the same permission again; COLLAB-001 owns that boundary.

When these conditions hold, do not route the work to `needs:human` merely because the target branch is `main`.

Structured self-review must name:

- why the PR is low-risk;
- which checks or live validations passed;
- the target branch and whether `main` merge authority is delegated;
- residual risks and whether any require follow-up.

For user-visible behavior or UX changes, acceptance evidence must also name the user-facing behavior change, how to try it, and whether human manual verification is required. If human verification is required, stop and provide a Human Decision Contract instead of hiding the decision behind a generic merge approval.

## Use This When

- The user has said PRs can be auto-merged.
- The PR has a clear issue scope and validation evidence.
- The target branch is an Epic integration branch, release branch, or a delegated low-risk direct-to-`main` path.
- The change does not require a product, UX, architecture, security, privacy, data, deployment, or cost decision still pending from the user.

## Watch Out For

- Do not auto-merge when tests fail, CI is red, or review was explicitly requested.
- Do not auto-merge into `main` merely because a non-`main` auto-merge rule exists; require delegated `main` merge conditions and latest-head review evidence.
- Do not invent a new Human merge gate for an already-delegated low-risk PR. Do not ignore `Auto-main-merge allowed: no` or another explicit restriction; resolve contradictory authority with its owner before merging.
- Do not auto-merge destructive, irreversible, privacy-sensitive, security-sensitive, data migration, cost-bearing, or external dependency changes without confirmation.
- Do not auto-merge user-facing behavior or UX changes when the acceptance depends on subjective human trial and that human trial has not happened.
- Do not present structured self-review as independent review.

## Example

For a data fixture PR with passing `validate:data` and `build`, merge it and comment on the issue with the PR number, merge commit, and validation output. For an Epic child PR that only changes repo-local tooling and targets the Epic integration branch, record structured self-review and merge after checks pass.

For a small direct-to-`main` UI bug fix, auto-merge after latest-head Reviewer approval, walkthrough evidence, build checks, and audit pass if the issue contract delegates low-risk `main` merge. If the same PR changes the learner's primary workflow in a way that requires human taste or trial, post the trial path and stop for a human decision before merge or closure.

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-002]]
