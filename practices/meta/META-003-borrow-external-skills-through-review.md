---
id: META-003
title: Borrow external skills through review
domain: meta
type: playbook
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [external-skills, imports, security, provenance]
aliases:
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

Use `workflows/import-external-skills.md`. Capture provenance, check license and scripts, extract candidate practices, deduplicate against `indexes/practice_index.yaml`, then ask for human approval before activation. After approval, publish relevant adapters automatically.

## Watch Out For

Never execute external scripts, install dependencies, or copy large prompt packs into active adapters without explicit approval.

## Example

A public Codex skill may have a good trigger description and workflow. Borrow the structure by creating a canonical candidate, not by copying its entire `SKILL.md` into your active skill directory.
