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

Use `workflows/import-external-skills.md`. Capture provenance, user value, concrete function, duplicate target, license and security notes, sensitivity, script/network/file/credential/install/destructive flags, prompt-injection flags, exact post-approval changes, and re-review triggers.

Classify the review outcome as exactly one of:

- `discard`
- `reference_only`
- `defer`
- `merge_into_existing`
- `propose_practice`
- `propose_asset`

`publish_after_approval` is not a terminal import outcome. Adapter or generated Skill publishing is a post-approval action only after an accepted canonical practice or asset change. `reference_only` means sanitized selected Vault `imports/inbox/` review evidence for manual lookup and possible re-review. It cannot activate behavior, publish generated adapters or Skills, mutate runtime, bypass dedupe, or become practice, asset, or capability-pack authority.

Deduplicate against existing practice and asset indexes before proposing canonical changes, then ask for human approval before activation. After approval, publish relevant adapters only through the reviewed adapter publishing path.

## Watch Out For

Never execute external scripts, install dependencies, run `chmod`, fetch network dependencies, write runtime files, publish generated adapters, or copy large prompt packs into active adapters as part of import review. Script-bearing material remains inert unless a later explicit reviewed execution step approves otherwise.

## Example

A public Codex skill may have a good trigger description and workflow. Borrow the structure by creating a canonical candidate, not by copying its entire `SKILL.md` into your active skill directory.

## Related Practices

- [[META-001]]
- [[META-002]]
