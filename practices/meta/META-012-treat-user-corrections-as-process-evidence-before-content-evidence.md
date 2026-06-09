---
id: META-012
title: Treat user corrections as process evidence before content evidence
domain: meta
type: heuristic
status: active
version: 2
created: 2026-06-08
updated: 2026-06-09
tags: [feedback-learning, corrections, harvesting, process-evidence]
aliases:
  - META-012
  - user corrections are process evidence first
  - corrections reveal workflow failures
related: [META-002, META-006, META-011, COLLAB-005]
applies_when:
  - harvesting lessons from a session with user corrections
  - reviewing an agent failure or workflow drift
  - deciding whether correction content belongs in a domain record or process rule
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

When the user corrects the agent's method, first treat the correction as evidence about the process, not merely as content inside the current domain.

## Rationale

The session contained user corrections about drift, loss of complexity, over-emphasis on action planning, weak generalization, and confusion between proposed and current systems. These are process failures, not merely memory-system content.

## Guidance

Analyze corrections for:

- agent failure mode;
- workflow weakness;
- prompting gap;
- review checklist gap;
- handoff risk;
- harvest risk;
- approval-scope confusion;
- generalizable practice evidence.

After that process analysis, decide whether the correction also contains domain content worth routing elsewhere.

When the correction says the agent skipped or compressed the required workflow, do not treat a later `continue`, `approved`, or `do the whole chain` response as retroactive permission to skip the missing step. First name the process failure and restore the missing review checkpoint. Once the user approves the listed items and post-approval chain, continue through canonical mutation, checks, PR/traceability, merge/apply, and adapter/runtime publish automatically unless the implementation departs from the approved list, checks fail, risk increases, or a new unlisted runtime/global target appears.

## Use This When

- The user says the agent drifted, oversimplified, overbuilt, lost nuance, or confused current and proposed systems.
- A correction changes how the agent should harvest, review, plan, or hand off work.
- The same correction could be read as both domain content and workflow feedback.
- The user points out that the agent over-interpreted approval, skipped harvest, published before review, or explained a missed step after the fact.

## Watch Out For

- Do not bury method corrections inside the domain being discussed.
- Do not treat every correction as a new practice; route it first, then apply the generalization gate.
- Do not convert the user's approval of a direction into approval to bypass unshown workflow steps.
- Do not publish adapters or runtime instructions first and then use an explanation as a substitute for the missing harvest report.
- Do not turn the restored review checkpoint into unnecessary repeated approval when the user has already approved a complete listed chain and no escalation condition appears.
- Do not record missed activation evidence unless a specific existing practice should have triggered.

## Activation

- Tier: workflow_embedded
- Phases: harvest, review, handoff, failure_analysis
- Signals: user correction about agent method, drift, oversimplification, overbuilding, lost nuance, or capability confusion
- Evidence: harvest or review output names the process failure before routing any domain content

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: missing opportunities to improve Agent Foundry workflows because user corrections were buried as domain-specific discussion.

## Related Practices

- [[META-002]]
- [[META-006]]
- [[META-011]]
- [[COLLAB-005]]
