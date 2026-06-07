---
id: COLLAB-011
title: Prefer Epic integration branches for multi-agent feature work
domain: agent-collaboration
type: heuristic
status: active
version: 1
created: 2026-06-07
updated: 2026-06-07
tags: [agent-collaboration, git, branches, pull-requests, epics]
aliases:
  - COLLAB-011
  - Epic integration branch default
  - stacked PRs are an exception
related: [COLLAB-001, COLLAB-004, COLLAB-007, COLLAB-009, COLLAB-010]
applies_when:
  - a feature spans multiple issues in one Epic
  - multiple agents may work on related files or dependent layers
  - stacked PRs would make final merge state hard to reason about
provenance: "Harvested from tiny-ipa M2 stacked PR integration issue on 2026-06-07, where several PRs were merged into non-main base branches and required a final integration PR."
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

## Use This When

- A feature has a parent Epic and several child issues.
- The same branch base must receive multiple dependent PRs before `main` should change.
- The team has recently hit branch-base or stacked-merge confusion.

## Watch Out For

- Do not make every tiny change wait for an Epic branch. Direct-to-main PRs remain appropriate for isolated work.
- Do not use stacked PRs as the default just because dependencies exist. Use them only when review precision is worth the operational cost.
- Do not close an Epic until the Epic branch has merged to the intended final branch or the final state is otherwise verified.

## Example

In tiny-ipa M2, stacked PRs made individual reviews precise but left several changes merged only into non-main bases. The workflow was corrected with a final integration PR. Later M3 work switched to an Epic integration branch as the default.

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
