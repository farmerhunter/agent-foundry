---
id: COLLAB-007
title: Bootstrap repo-local agent workflow contracts
domain: agent-collaboration
type: playbook
status: active
version: 2
created: 2026-06-07
updated: 2026-06-08
tags: [agent-collaboration, workflow, bootstrap, github, multi-agent]
aliases:
  - COLLAB-007
  - bootstrap repo-local workflow contract
  - project-level agent workflow contract
related: [COLLAB-001, COLLAB-004, COLLAB-008, COLLAB-009, COLLAB-010, COLLAB-012, ARCH-007]
applies_when:
  - starting a new multi-agent repository
  - a user wants work coordinated through issues, PRs, or a GitHub Project
  - an Architect agent is planning Epics, milestones, or executable issues for another agent
  - agents need repeatable handoff rules beyond a single chat session
review_required: false
provenance: "Harvested from tiny-ipa multi-agent workflow iteration on 2026-06-07, where Codex and DeepSeek evolved from manual copy/paste handoff into a GitHub Project, Epic, label, issue contract, and PR workflow."
---

## Principle

When a repository starts using multiple agents, the Architect must create a repo-local workflow contract before expecting Implementers to execute reliably.

## Rationale

Global practices can teach an agent how to discover and obey collaboration rules, but they cannot encode a project's concrete labels, Project URL, branch names, active Epics, issue dependencies, or merge policy. Without a repo-local contract, each agent infers workflow from partial context, which leads to wrong PR bases, missing review feedback, stale labels, and human copy/paste as the real scheduler.

The portable rule is not "copy tiny-ipa's exact process." The portable rule is that Architect agents bootstrap the project's own collaboration layer at the maturity level the project needs.

## Guidance

When acting as Architect in a multi-agent repository:

1. Determine the workflow maturity level:
   - Level 1: simple issue branch, PR, completion comment, merge to `main`.
   - Level 2: Epic coordination, `needs:*` labels, execution contracts, review handoff, and optional Epic integration branches.
   - Level 3: scheduler-like multi-agent coordination with agent queues, dependency graphs, integration QA tasks, and stricter role routing.
2. Create or update repo-local workflow docs such as `docs/development.md`, `docs/agent-workflow.md`, or a similarly discoverable file.
3. Define roles, at minimum Architect and Implementer, and clarify that roles are responsibilities, not identities.
4. Add an issue role-fit gate before handing work to another agent. Classify each issue as evidence gathering, implementation, verification/review, taxonomy or architecture boundary decision, policy decision, harvest/practice decision, privacy/security decision, or mixed.
5. Split mixed issues or constrain the Implementer contract to evidence gathering, preliminary classification, implementation, or verification while reserving final taxonomy, architecture, policy, harvest, privacy, or security decisions for Architect review.
6. Define durable collaboration surfaces:
   - planning and coordination surface;
   - executable issue surface;
   - PR/review surface;
   - machine-readable routing labels;
   - human-visible board status.
7. Define labels and state transitions, including who is responsible for moving work between states.
8. Define branch and PR strategy, including when direct-to-main, Epic integration branches, or stacked PRs are allowed.
9. Define issue comment templates for execution contracts, pickup confirmation, completion evidence, and review handoff.
10. Define merge and closure rules for child issues and parent coordination issues.

Implementers should not invent missing workflow. If a ready issue lacks the expected contract, or asks the Implementer to decide taxonomy, architecture, policy, harvest, privacy, or security boundaries without explicit delegation, route it back to Architect.

## Use This When

- A project moves from one agent to two or more agents.
- The user says future changes should go through issues, Project boards, or PRs.
- A planning agent is about to hand executable issues to another coding agent.
- An agent notices that human copy/paste is acting as the only state transfer mechanism.

## Watch Out For

- Do not put project-specific facts into global practices. Store concrete Project IDs, labels, branch names, Epic numbers, and dependencies in repo-local docs and issue comments.
- Do not force Level 2 or Level 3 process onto a one-off project that only needs simple issue/PR traceability.
- Do not make Implementers responsible for designing the collaboration system while they are executing tasks.
- Do not treat an issue as Implementer-ready merely because it has a `needs:implementer` label; the issue type and decision authority must fit the role.

## Example

In tiny-ipa, the workflow matured from milestone issues to Epic issues, then to `needs:*` labels, execution contracts, Epic integration branches, and a Ready queue. Those concrete choices belong in tiny-ipa docs and issues. The reusable lesson is that the Architect bootstraps the repo-local contract and Implementers follow it.

## Activation

- Tier: workflow_embedded
- Phases: planning, before_issue_handoff, before_edit
- Signals: new multi-agent repo; GitHub Project workflow; issue/PR handoff between agents; role split between planner/reviewer and coder
- Evidence: identify the repo-local workflow document or state that it needs to be created before issue execution

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-004]]
- [[COLLAB-008]]
- [[COLLAB-009]]
- [[COLLAB-010]]
- [[COLLAB-012]]
- [[ARCH-007]]
