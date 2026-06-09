---
name: agent-collaboration
description: Use when working on GitHub issues, pull requests, multi-agent repository synchronization, issue completion comments, CLI-posted Markdown comments, converted document deliverables, or resuming after interruption/compaction.
---

# Agent Collaboration

Asset ID: ASSET-COLLAB-001.

This skill applies Agent Foundry collaboration and delivery practices.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices (COLLAB-001 through COLLAB-012, COLLAB-014, TEST-001, IMPL-001) as behavioral constraints. Do not confuse the skill with the practices it applies.

## Core Rules

- COLLAB-001: Code changes made to complete a GitHub issue should go through a feature branch and PR unless the user explicitly approves skipping the PR.
- COLLAB-002: Before marking an issue ready for review or closed, comment with completion scope, linked PR or commit, verification method, verification results, and residual risks.
- COLLAB-003: If the user has authorized auto-merge, merge validated PRs by default unless review, hold, failed checks, or high-risk changes require confirmation.
- COLLAB-004: In multi-agent repositories, fetch or pull before issue work and verify remote sync when another machine may have pushed.
- COLLAB-005: Do not infer that the session is ending after compaction, interruption, or finishing one subtask; continue from the latest user request.
- COLLAB-006: When completing a task list from another agent, verify each item against the original list — not against implementation signals like tests passing or build succeeding.
- COLLAB-007: In a new multi-agent repository, the Architect should bootstrap or locate the repo-local workflow contract and apply an issue role-fit gate before handing issues to Implementers.
- COLLAB-008: Use GitHub Project, issues, labels, comments, PRs, and CI as a lightweight scheduler substrate; keep issue type, status fields, and session-role-task binding semantically coherent.
- COLLAB-009: Ready issues should carry an Execution Contract that defines branch strategy, base branch, PR target, dependencies, role fit, current owner role, Architect-owned decisions, Implementer boundary, completion handoff, reviewer target, merge rule, and verification; completion handoff controls when Architect review is requested.
- COLLAB-010: `Ready + needs:implementer` may be an ordered queue; related low-risk child issues in the same Epic integration branch default to dependency-gated batch execution/review, and obey `Depends on` gates before starting code.
- COLLAB-011: Prefer Epic integration branches for multi-agent feature work; direct-to-main and stacked PRs are explicit alternatives with narrower use.
- COLLAB-012: Review handoff needs both surfaces when changes are requested; `Review` is validation state rather than automatic cross-session waiting, reviewer target must be explicit, and related low-risk work should use Epic/sub-Epic/batch checkpoints unless a high-risk trigger appears.
- COLLAB-014: For complex handoffs, preserve knowledge state before action planning, including research output, rationale, rejected options, user corrections, capability boundaries, unresolved questions, and next actions.
- TEST-001: For converted document deliverables, verify rendered output, fonts, encoding, images, and source-to-output structure rather than relying only on command success.
- IMPL-001: When posting Markdown through CLI comments, avoid shell-interpreted inline bodies for text with backticks, dollar signs, or command examples; prefer `--body-file` or safe quoting.

## Workflow

1. Identify whether the task touches an issue, PR, GitHub Project/Epic workflow, multi-agent sync, document conversion, or CLI comment publishing.
2. Apply the matching canonical rule above.
3. For multi-agent projects, locate the repo-local workflow contract and active issue Execution Contracts before choosing branch or PR behavior.
4. Check issue role fit before pickup or release; split mixed work or constrain Implementers to evidence, preliminary classification, implementation, or verification when final decisions remain Architect-owned.
5. Check completion handoff before work starts; if it says `batch checkpoint`, do not turn each child PR into a blocking Architect review unless a high-risk trigger or failed verification appears.
6. Bind task, owner role, current session, and reviewer target explicitly when work moves between scheduler states; `needs:*` labels route roles, not necessarily different sessions.
7. When a set of related issues has clear dependency gates, treat it as a batch queue instead of forcing one handoff per child issue.
8. Before reviewing an individual child PR, check whether the issue belongs to an Epic batch queue, whether its completion handoff is `batch checkpoint`, whether a reviewer target is named, and whether a high-risk trigger exists.
9. Preserve durable traceability in GitHub issues, PRs, labels, Project state, and comments.
10. Validate with the checks appropriate to the artifact or code path, using batch or Epic review checkpoints when appropriate.
11. Continue from the newest user request after interruptions or context transitions.

## Guardrails

- Do not create direct commits for issue code work unless explicitly approved.
- Do not close or move an issue without a completion and verification comment.
- Do not auto-merge failed, risky, destructive, or explicitly held PRs.
- Do not run destructive sync commands without user confirmation.
- Do not pass complex Markdown to shell commands in double-quoted inline bodies.
- Do not let Implementers infer missing repo workflow, branch base, PR target, or dependency gates; route unclear issues back to Architect.
- Do not let Implementers make final taxonomy, architecture boundary, policy, harvest, privacy, or security decisions unless the Execution Contract explicitly assigns that authority.
- Do not let status surfaces contradict each other; `Ready` is pickup state, `Review` is validation state, and `Done` requires acceptance or closure.
- Do not leave `Review` without a reviewer target: current-session structured self-review, user, separate Reviewer agent, CI/automation, or batch/Epic checkpoint.
- Do not imply self-review is independent review; if the same session switches roles, name structured self-review and residual risks.
- Do not treat an open child PR as automatic `needs:architect`; review ownership follows completion handoff, high-risk triggers, failed verification, or the batch/Epic checkpoint.
- Do not leave a single-deliverable task labeled as an Epic just because it came from roadmap planning.
- Do not treat Project status alone as an agent inbox; use labels plus durable comments.
- Do not publish proposed practices such as COLLAB-013 into default adapters until approved active.
