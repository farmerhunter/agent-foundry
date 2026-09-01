---
id: COLLAB-011
title: Prefer Epic integration branches for multi-agent feature work
domain: agent-collaboration
type: heuristic
status: active
version: 3
created: 2026-06-07
updated: 2026-07-06
tags: [agent-collaboration, git, branches, pull-requests, epics, issue-closure]
aliases:
  - COLLAB-011
  - Epic integration branch default
  - stacked PRs are an exception
  - close accepted Epic child issues at readiness
related: [COLLAB-001, COLLAB-004, COLLAB-007, COLLAB-009, COLLAB-010]
applies_when:
  - a feature spans multiple issues in one Epic
  - multiple agents may work on related files or dependent layers
  - stacked PRs would make final merge state hard to reason about
provenance: "Harvested from tiny-ipa M2 stacked PR integration issue on 2026-06-07, where several PRs were merged into non-main base branches and required a final integration PR. Revised on 2026-07-06 after Agent Foundry AF15 was reopened after an earlier final integration; the reopened child work correctly returned to the Epic integration branch and required a new final PR to main."
---

## Principle

For multi-agent feature work, prefer an Epic integration branch unless a simpler direct-to-main flow is enough or a stacked PR exception is explicitly justified.

## Rationale

Stacked PRs can improve review precision because each layer is reviewed against its dependency. They also increase process fragility: a PR can be "merged" into its base branch without reaching `main`, branch bases can drift, and issue closure can lie about the final integrated state.

An Epic integration branch sacrifices some review precision for reliability. Child issue PRs still preserve scoped review, but final integration into `main` happens through one clear Epic PR.

## Guidance

Default multi-agent feature shape:

```text
main
  <- epic/<epic-short-name>
       <- agent/<issue-number>-<short-description>
```

Use:

- direct issue PR to `main` for independent documentation, tooling, or small fixes outside an active Epic integration branch;
- Epic integration branch for cross-issue feature work, dependency chains, or multi-agent execution;
- stacked PR only when every layer has independent review value, the dependency chain is real, and the Architect documents stack order plus final integration path.

If stacked PRs are used, verify the final commits are reachable from the intended release branch before closing issues or Epics. A GitHub "merged" state is not enough; check the merge destination.

In an Epic integration branch workflow, child issue closure and parent Epic closure have different boundaries:

- Child issues may be closed during Epic readiness when their child PR has merged into the Epic integration branch, the issue has completion and acceptance evidence, next-action labels have been cleared, and the user or workflow contract authorizes child closure.
- The parent Epic should remain open until the Epic branch merges to the intended final branch, the final integration PR is explicitly abandoned, or the user explicitly accepts a non-merge outcome.
- A final Epic PR to `main` remains a separate integration decision even when every child issue is closed.

If an Epic is reopened after a prior final integration because an in-scope user experience, activation, or readiness gap remains, resume work on the Epic integration branch or create a new integration branch derived from current `main`. Do not let reopened child issues drift into unrelated direct-to-main PRs unless the Architect documents why the resumed work is independent. The final state should again be proven by a fresh integration PR or explicit non-merge acceptance, because the older final PR no longer represents the complete Epic boundary.

## Use This When

- A feature has a parent Epic and several child issues.
- The same branch base must receive multiple dependent PRs before `main` should change.
- The team has recently hit branch-base or stacked-merge confusion.

## Watch Out For

- Do not make every tiny change wait for an Epic branch. Direct-to-main PRs remain appropriate for isolated work.
- Do not use stacked PRs as the default just because dependencies exist. Use them only when review precision is worth the operational cost.
- Do not close an Epic until the Epic branch has merged to the intended final branch or the final state is otherwise verified.
- Do not reuse an old final-integration approval or PR after reopening an Epic for additional in-scope work. The reopened branch head and final merge basis must be reverified.
- Do not leave accepted child issues open with stale next-action labels after Epic readiness; close them or write an explicit accepted-but-deferred marker that audits can recognize.
- Do not treat child issue closure as proof that `main` contains the work; final branch reachability still needs verification.

## Example

In tiny-ipa M2, stacked PRs made individual reviews precise but left several changes merged only into non-main bases. The workflow was corrected with a final integration PR. Later M3 work switched to an Epic integration branch as the default. In the role-generic helper Epic, accepted child issues were closed after all child PRs merged into the Epic branch and `agent-audit` was clean; the parent Epic stayed open until the final PR to `main`.

In Agent Foundry AF15, an earlier final integration was superseded when the user identified that the readiness audit still lacked a complete user action workflow. The resumed #329/#330/#331 work targeted the AF15 integration branch, and the Epic closed only after a new final PR merged the updated branch head into `main`.

## Activation

- Tier: workflow_embedded
- Phases: branch_strategy, issue_handoff, merge_review
- Signals: Epic feature branch; stacked PR proposal; multi-issue dependency; PR base not `main`; user asks reliability vs precision tradeoff
- Evidence: state the chosen branch strategy and why direct-to-main or stacked PR is not the default

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-004]]
- [[COLLAB-007]]
- [[COLLAB-009]]
- [[COLLAB-010]]
