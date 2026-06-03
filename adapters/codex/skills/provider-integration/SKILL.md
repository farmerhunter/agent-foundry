---
name: provider-integration
description: Use when adding or reviewing a new provider/API adapter, including official API feasibility, provider candidate review, adapter tests, config/dashboard ViewModel integration, pipeline tests, docs, and verification.
---

# Provider Integration Playbook

Asset ID: ASSET-IMPL-001.

Use this skill to add or review provider integrations end to end. It is for official API and user-mediated providers; it does not authorize stealth, anti-detection, or unsafe browser automation.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it applies canonical practices GOV-002, ARCH-001 through ARCH-005, ARCH-007 through ARCH-009, IMPL-002, TEST-002, COLLAB-006, DEBUG-001, and DEBUG-002. Do not confuse the skill with the practices it applies.

## Default Process

1. Verify external API behavior first with a minimal disposable probe or official documentation check. If the API cannot be verified, mark the provider deferred instead of writing adapter code.
2. Write a provider candidate review: provider_id, source, quota_model, refresh semantics, credential shape, success payload, failure states, UI actions, diagnostics needs, risks, and decision.
3. Record the design decision before implementation when the provider changes source, quota model, credential risk, or user-facing workflow.
4. Write adapter tests first: metadata, missing credential, success response, auth failure, non-OK response, malformed response, schema drift, and network failure.
5. Implement the smallest adapter and domain changes needed. Preserve existing provider semantics and avoid over-normalizing payloads.
6. Route configuration through a config ViewModel or equivalent contract. Do not add provider-specific JSX branches when a provider list/action contract should own the behavior.
7. Route dashboard action availability through the dashboard interaction ViewModel. Preserve existing provider actions, especially ChatGPT/Codex manual/Safari actions.
8. Add pipeline tests for the glue between adapter output and renderer-visible summary: provider_id preservation, error status propagation, null-safety, and multi-provider isolation.
9. When debugging provider failures involving endpoint, auth, region, credential, quota model, external behavior, or user-facing text, first write Symptom, Failed assumption, Scope search, Affected surfaces, Fix plan, and Verification. Do not patch one line and stop at green tests.
10. Update implementation plan, design decisions, and interaction contracts to match the final implementation.
11. Before final report, re-read the original task list and verify each item, including documentation and design-review items that tests do not cover.

Read `references/checklist.md` before implementing or reviewing a provider.
