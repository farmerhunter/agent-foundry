---
id: META-010
title: Review assets with lifecycle evidence
domain: meta
type: principle
status: active
version: 1
created: 2026-05-27
updated: 2026-05-27
tags: [assets, lifecycle, evidence, review, skill-rot]
aliases:
  - asset lifecycle review needs evidence
  - review assets before skill rot
  - usage evidence drives asset lifecycle
related: [META-004, META-005, META-008, META-009]
applies_when:
  - reviewing existing skills, subagents, automations, or other reusable assets
  - deciding whether to keep, revise, deprecate, archive, split, or merge an asset
  - detecting skill rot or stale reusable workflows
  - adding lifecycle metadata to assets
review_required: false
provenance: "Harvested from the asset lifecycle work on 2026-05-27, where review needed usage evidence, overlap detection, and lifecycle states instead of informal judgment."
---

## Principle

Review reusable assets with lifecycle evidence. Asset status should be based on usage, overlap, coverage, stale triggers, and verification evidence, not only on whether the asset still looks useful.

## Rationale

Skills, subagents, and automations rot when their triggers drift, their scope overlaps with newer assets, or their instructions stop matching the current canonical practices. Without lifecycle evidence, stale assets remain active because nobody remembers why they were created, and useful assets get rewritten because their value is not visible.

Lifecycle review makes asset maintenance explicit. It gives agents a narrow way to recommend keep, revise, deprecate, archive, split, merge, or create follow-up evidence without turning every review into a broad rewrite.

## Guidance

When reviewing assets:

1. Read the asset index and each relevant asset record.
2. Check lifecycle state, review cadence, last usage, usage count, published targets, and canonical practice coverage.
3. Compare assets for overlapping triggers, responsibilities, or canonical practice coverage.
4. Recommend one lifecycle decision per asset:
   - keep active
   - revise
   - deprecate
   - archive
   - split
   - merge
   - gather more evidence
5. Prefer extending an existing asset when the new workflow shares the same trigger, responsibility, and success criteria.
6. Prefer creating a new asset when the workflow has a distinct trigger, responsibility, user-facing output, or verification loop.

## Watch Out For

Do not require the user to approve routine evidence logging. Evidence should be concise, non-sensitive, and automatic when an active asset is invoked.

Do not promote or remove an asset only because it has low usage. Low usage is a review signal, not an automatic lifecycle decision.

