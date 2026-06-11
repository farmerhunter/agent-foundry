---
id: BOOT-001
title: Bootstrap Orientation
domain: meta
type: checklist
status: active
version: 1
created: 2026-06-11
updated: 2026-06-11
tags: [bootstrap, onboarding]
aliases: [BOOT-001]
---

## Principle

Start from a valid blank Vault, deploy reviewed bootstrap records, then refresh generated runtime outputs from canonical Vault data.

## Rationale

The bootstrap pack is an import path into normal Vault records. It is not a runtime dependency or a hidden source of truth.

## Guidance

- Validate Core and Vault roots before deployment.
- Record pack membership and provenance on deployed records.
- Run refresh only after the selected Vault owns the accepted records.
