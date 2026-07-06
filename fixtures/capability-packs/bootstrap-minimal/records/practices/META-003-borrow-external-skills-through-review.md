---
id: META-003
title: Borrow external skills through review
domain: meta
type: playbook
status: active
version: 2
created: 2026-05-26
updated: 2026-07-06
tags: [external-skills, imports, security, provenance]
aliases:
  - META-003
  - external skill import path
  - borrow skills safely
related: [META-001, META-002]
applies_when:
  - evaluating public skill repositories
  - importing a community skill
  - adapting internet prompt packs
review_required: false
provenance: "Initial Agent Foundry system design."
---

## Principle

External skills are inputs for review, not trusted source-of-truth content.

## Rationale

Public skills may be useful, but they can also be generic, stale, overbroad, insecure, license-incompatible, or misaligned with personal practices. Direct import increases skill rot and supply-chain risk.

## Guidance

Use `workflows/import-external-skills.md`. Capture provenance, check license and scripts, extract candidate practices or assets, deduplicate against canonical indexes, then return one review outcome: `discard`, `reference_only`, `defer`, `merge_into_existing`, `propose_practice`, or `propose_asset`.

Keep `post_approval_actions` separate from the import outcome. Adapter or generated Skill publishing can only happen after a specific canonical practice or asset is approved and the later publish gate is accepted.

Record `reference_only` material as sanitized selected Vault `imports/inbox/` review evidence for lookup or later re-review. It must not activate behavior, publish adapters, mutate runtime files, bypass dedupe, or become practice, asset, or capability-pack authority.

## Watch Out For

Never execute external scripts, install dependencies, `chmod` files, fetch dependencies, write canonical practices/assets, publish generated adapters, mutate runtime files, or copy large prompt packs into active adapters during import review.

## Example

A public Codex skill may have a good trigger description and workflow. Borrow the structure by creating a canonical candidate, not by copying its entire `SKILL.md` into your active skill directory.

## Related Practices

- [[META-001]]
- [[META-002]]
