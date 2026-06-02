---
id: DEBUG-001
title: Design diagnostics as agent-actionable reproduction artifacts
domain: debugging
type: pattern
status: active
version: 1
created: 2026-06-02
updated: 2026-06-02
tags: [debugging, diagnostics, serviceability, traces, fixtures, agent-handoff, privacy]
aliases:
  - DEBUG-001
  - agent-actionable diagnostics
  - debug bundles for coding agents
  - serviceability artifacts should support reproduction
related: [ARCH-004, ARCH-007, ARCH-008, GOV-003, RUNTIME-004]
applies_when:
  - building diagnostics or serviceability for a local app, integration, parser, importer, or fragile external workflow
  - users need to bring failures back to a coding agent for investigation
  - raw integration data may be sensitive but is sometimes needed for reproduction
  - parser, capture, IPC, adapter, or import failures must become tests
review_required: false
provenance: "Harvested from token-panic serviceability design on 2026-06-02, where Safari capture and parser failures needed privacy-preserving diagnostics that a coding agent could turn into fixture tests."
---

## Principle

Design diagnostics as agent-actionable reproduction artifacts, not only as human-readable logs. A good debug artifact should let an agent identify the failing boundary, reconstruct the minimum input, add a failing test, and verify the fix.

## Rationale

Traditional serviceability explains what happened. Agent-assisted serviceability must also make the next coding step cheap. If a parser fails, an agent should not rely on the user's paraphrase of the page; it needs trace metadata, parser diagnostics, candidate snippets, and optionally redacted or explicitly exported raw input that can become a fixture.

At the same time, raw diagnostic data can include sensitive page text, account identifiers, credentials, or local runtime context. Saving everything by default makes debugging easier once and privacy worse forever. The reusable pattern is metadata-first diagnostics with explicit, user-controlled raw export.

## Guidance

Use a two-layer diagnostics model:

1. **Default metadata trace**
   - generate or propagate a `trace_id` for each user action;
   - record structured events with component, action, status, stable reason, timestamp, and bounded metadata;
   - record sizes, counts, strategy names, allowed URL host/path, and short candidate snippets;
   - do not default-log full raw text, credentials, cookies, localStorage, sessionStorage, screenshots, or large DOM/HTML dumps.

2. **Explicit reproduction bundle**
   - let the user export a debug bundle for one trace;
   - include environment, trace events, parser/importer diagnostics, and schema version or manifest when available;
   - include raw input only when the user explicitly chooses it and understands it may contain sensitive data;
   - prefer redacted input or relevant-line context when full raw input is unnecessary.

For parsers and importers, keep business output separate from diagnostics. Preserve the normal API for production use, and provide a side-channel diagnostics API that reports strategies tried, candidate lines, failure reason, and input scale. Do not make UI parse raw diagnostic data to infer business state.

When a debug bundle is handed to an agent, the expected workflow is:

```text
inspect diagnostics
  -> identify failing boundary
  -> convert raw/redacted input into a fixture when needed
  -> add a failing test
  -> fix parser/capture/adapter logic
  -> run tests/build
  -> ask the user to re-run the original action
```

## Use This When

- A user-facing tool depends on unstable external text, pages, files, APIs, parser rules, or local automation.
- Failures will be diagnosed across sessions or by a different agent than the one that built the feature.
- The user can reproduce the problem locally but cannot easily describe the raw input.
- Sensitive raw data is useful for debugging but should not be saved or synced by default.

## Watch Out For

- Do not confuse a verbose log with a useful reproduction artifact.
- Do not store raw input by default just because it is convenient for debugging.
- Do not put diagnostics into business history, analytics, or domain snapshots unless they are part of the domain.
- Do not let failure reasons remain only free text if later code or agents need to branch on them.
- Do not require raw data when structured diagnostics and candidate snippets already explain the failure.

## Example

In token-panic, Safari assisted capture reads visible ChatGPT/Codex analytics page text and a local parser extracts limit data. The useful debug bundle contains a trace id, capture metadata, parser strategies, candidate lines, and failure reason. Full page text stays in a short-lived memory cache and is written only when the user explicitly exports a bundle with raw text. A coding agent can use that bundle to add a parser fixture and fix the parser without turning ChatGPT page scraping into the core architecture.

## Related Practices

- [[ARCH-004]]
- [[ARCH-007]]
- [[ARCH-008]]
- [[GOV-003]]
- [[RUNTIME-004]]
