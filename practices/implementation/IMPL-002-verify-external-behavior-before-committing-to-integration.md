---
id: IMPL-002
title: Verify external behavior before committing to an integration approach
domain: implementation
type: playbook
status: active
version: 2
created: 2026-06-02
updated: 2026-06-02
tags: [implementation, integration, external-services, experimentation, feasibility]
aliases:
  - IMPL-002
  - experiment before building integration
  - verify third-party behavior first
  - probe before coding
related: [ARCH-001, GOV-002, IMPL-003]
applies_when:
  - planning any integration whose correctness depends on third-party behavior
  - the integration involves web pages, APIs, file formats, protocols, or SDKs not fully under your control
  - assumptions about the external system's behavior have not been verified against the real system
provenance: "Harvested from token-panic Phase 3 planning (2026-06-02). Originally titled 'Verify external automation feasibility before building the adapter'; broadened in v2 to cover all third-party integrations, not only adapters."
---

## Principle

Before writing code that depends on how an external system behaves, run a minimal, isolated experiment to verify that behavior against the real system. Answer "can we even get the data?" before answering "how do we structure the code?"

## Rationale

Every integration with an external system carries assumptions:

- A web page: "this CSS selector will find the data"
- An API endpoint: "it accepts these parameters and returns this shape"
- A file format: "this tool always writes timestamps in ISO 8601"
- A third-party SDK: "version 2.x handles auth the same way as version 1.x"
- A browser automation: "headless Chrome can load this page without being blocked"
- A protocol: "this service speaks standard WebSocket"

If any of these assumptions is wrong, the integration code is built on a false premise. The cost of discovering this after writing the code includes not only wasted implementation effort, but also the side effects of the failed attempts (rate limits, IP blocks, corrupted data).

A minimal pre-implementation experiment verifies the premise before the code exists. The experiment is disposable — a script, not a module — and its only purpose is to confirm or invalidate the approach.

This is not specific to adapter patterns. It applies to any code whose correctness depends on external behavior.

## Guidance

1. Identify the specific assumption the integration depends on. Be precise: not "the API works" but "`GET /v2/usage` returns `{ used, limit }` with a valid Bearer token."
2. Write a minimal standalone script that tests exactly that assumption. It should not be part of the application code.
3. Run it once and observe.
4. If it fails: diagnose why, decide whether the failure invalidates the approach, and record the result. Do not iterate the experiment (see IMPL-003).
5. If it succeeds: capture the verified parameters as the basis for implementation.
6. Record the outcome in a design decision document so future readers know the premise was validated, not assumed.

## Use This When

- A proposed integration depends on behavior you cannot control or guarantee.
- The integration approach involves network access to a remote service.
- The external system is known or suspected to have access controls, rate limits, or anti-automation measures.
- A failed integration could cause user-visible harm (data loss, account restrictions, IP blocks).
- The cost of a false premise is high (e.g., a multi-day implementation built on an unverified assumption).

## Watch Out For

- Do not run the experiment against a service whose ToS prohibit it, unless the user has explicitly authorized it.
- Do not iterate. One probe answers the feasibility question. Repeated attempts can trigger protective measures (see IMPL-003).
- Do not treat a successful experiment as a permanent guarantee. External behavior can change — the integration must handle degradation gracefully.
- Do not build the experiment into the application. It is a throwaway probe, not a module.

## Example 1 — Web page scraping (token-panic)

Phase 3 originally planned to use Playwright to scrape ChatGPT's usage page. The key assumption: Playwright's Chromium can load `https://chatgpt.com/` and extract DOM data.

A three-line experiment tested this: launch browser, navigate, check result. All three variants (headless, headless + flag, headful) failed — Cloudflare blocked Playwright's Chromium at the TLS layer before the page even loaded. The entire browser_scrape approach was invalidated in 15 minutes, before any adapter code existed.

## Example 2 — API integration (generic)

A developer plans to integrate with a payment provider's REST API. The documentation says `POST /v1/charges` accepts `{ amount, currency }`. Before building the full integration layer — with retry logic, error mapping, idempotency keys — a single `curl` command verifies that the documented response shape matches reality and that the auth header format works.

## Related Practices

- [[ARCH-001]] — the experiment verifies the external boundary is viable before tools are chosen for it
- [[GOV-002]] — an experiment is the smallest maintainable mechanism for verifying a premise
- [[IMPL-003]] — constrains what experiments are safe to run and when iteration crosses into risky territory
