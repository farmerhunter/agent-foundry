# Provider Integration Checklist

Canonical IDs: ASSET-IMPL-001, GOV-002, ARCH-001, ARCH-002, ARCH-003, ARCH-004, ARCH-005, ARCH-007, ARCH-008, ARCH-009, IMPL-002, TEST-002, COLLAB-006, DEBUG-001

Use this checklist before declaring a provider integration done.

## Feasibility

- Has the official API or user-mediated source been verified with a minimal probe or current official documentation?
- If not verified, is the provider explicitly deferred instead of partially implemented?
- Is unsafe scraping, stealth, or anti-detection experimentation out of scope unless separately approved?

## Provider Contract

- Is `provider_id` stable and unique?
- Is `source` explicit?
- Is `quota_model` explicit and semantically correct?
- Is refresh behavior clear: scheduler, user-triggered, manual-only, or disabled?
- Is credential shape documented, including any elevated permission risk?
- Is the success payload shape documented?
- Are expected failure states modeled as `auth_required`, `error`, `manual_required`, or another explicit state?

## Implementation

- Do adapter tests cover metadata, missing credentials, success, auth failure, non-OK responses, malformed payloads, schema drift, and network failure?
- Does the adapter preserve meaningful payload differences instead of flattening them into a misleading common model?
- Does config behavior go through a ViewModel or provider config contract?
- Does dashboard behavior go through an interaction ViewModel?
- Are existing provider actions preserved?

## Pipeline Tests

- Does an adapter error still produce renderer-visible output with the correct `provider_id`?
- Does error status propagate through adapter callback, summary generation, IPC push, and renderer subscription boundary?
- Does provider A failure leave provider B state untouched?
- Are null or empty snapshots handled without falling back to `provider_id = unknown`?

## Docs And Handoff

- Is the implementation plan updated to current state?
- Is a design decision recorded or updated?
- Is the interaction contract updated when UI actions or grouping changed?
- Has the original task list been checked item by item before final report?
