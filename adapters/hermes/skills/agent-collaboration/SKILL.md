---
name: agent-collaboration
description: Use when working on GitHub issues, pull requests, multi-agent repository synchronization, issue completion comments, CLI-posted Markdown comments, converted document deliverables, or resuming after interruption/compaction.
---

# Agent Collaboration

Asset ID: ASSET-COLLAB-001.

This skill applies Agent Foundry collaboration and delivery practices.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices (COLLAB-001 through COLLAB-005, TEST-001, IMPL-001) as behavioral constraints. Do not confuse the skill with the practices it applies.

## Core Rules

- COLLAB-001: Code changes made to complete a GitHub issue should go through a feature branch and PR unless the user explicitly approves skipping the PR.
- COLLAB-002: Before marking an issue ready for review or closed, comment with completion scope, linked PR or commit, verification method, verification results, and residual risks.
- COLLAB-003: If the user has authorized auto-merge, merge validated PRs by default unless review, hold, failed checks, or high-risk changes require confirmation.
- COLLAB-004: In multi-agent repositories, fetch or pull before issue work and verify remote sync when another machine may have pushed.
- COLLAB-005: Do not infer that the session is ending after compaction, interruption, or finishing one subtask; continue from the latest user request.
- TEST-001: For converted document deliverables, verify rendered output, fonts, encoding, images, and source-to-output structure rather than relying only on command success.
- IMPL-001: When posting Markdown through CLI comments, avoid shell-interpreted inline bodies for text with backticks, dollar signs, or command examples; prefer `--body-file` or safe quoting.

## Workflow

1. Identify whether the task touches an issue, PR, multi-agent sync, document conversion, or CLI comment publishing.
2. Apply the matching canonical rule above.
3. Preserve durable traceability in GitHub issues and PRs.
4. Validate with the checks appropriate to the artifact or code path.
5. Continue from the newest user request after interruptions or context transitions.

## Guardrails

- Do not create direct commits for issue code work unless explicitly approved.
- Do not close or move an issue without a completion and verification comment.
- Do not auto-merge failed, risky, destructive, or explicitly held PRs.
- Do not run destructive sync commands without user confirmation.
- Do not pass complex Markdown to shell commands in double-quoted inline bodies.
