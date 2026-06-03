---
id: DEBUG-002
title: Treat bugs as failed assumptions before patching
domain: debugging
type: playbook
status: active
version: 1
created: 2026-06-03
updated: 2026-06-03
tags: [debugging, assumptions, blast-radius, external-services, verification, agent-collaboration]
aliases:
  - DEBUG-002
  - failed assumption before patch
  - search the blast radius before fixing a bug
  - current error gone is not completion
related: [DEBUG-001, IMPL-002, TEST-002, ARCH-007, COLLAB-006]
applies_when:
  - a bug involves an API endpoint, auth, region, credential, quota model, third-party behavior, or user-facing provider text
  - a local patch makes the current error disappear but may leave the same wrong assumption elsewhere
  - mocks or unit tests pass but the bug depends on external facts or cross-layer semantics
  - a user points out that an agent fixed one symptom while missing related UI, docs, tests, or design decisions
provenance: "Harvested from token-panic Kimi/Moonshot debugging (2026-06-03). The first fix changed api.moonshot.ai to api.moonshot.cn, but user review found related platform.kimi.ai and user-facing hint assumptions still present. After coaching, DeepSeek reframed completion as clearing the wrong external assumption across code, UI, tests, and design decisions."
---

## Principle

Treat a bug as evidence that a system assumption may have failed. Before patching a local symptom, name the failed assumption, search where that assumption appears, and define completion as clearing the assumption's blast radius.

## Rationale

Fast debugging often follows a narrow loop:

```text
see error -> find one line -> patch one line -> tests pass -> report done
```

That loop is useful for isolated implementation mistakes, but it fails when the bug comes from a shared assumption. External-service bugs are especially prone to this failure: an endpoint host, auth format, regional console, quota model, or credential rule may appear in adapter code, configuration UI, ViewModels, tests, design decisions, and troubleshooting text.

If only the line that triggered the error is fixed, the product still carries the wrong assumption elsewhere. The next user action or agent handoff reopens the same problem in a different form.

The safer loop is:

```text
see error
  -> identify the failed assumption
  -> search the codebase for that assumption and adjacent names
  -> list affected surfaces
  -> patch the smallest complete set
  -> verify with tests, live probes when appropriate, grep, and documentation checks
```

## Guidance

Before editing code for an assumption-shaped bug, write these six items:

1. **Symptom**: what the user saw and what commands or logs reported. Keep this observational.
2. **Failed assumption**: the wrong belief in one sentence. Be precise: not "Kimi auth is broken", but "this API key belongs to the China region, while code and UI assumed the international endpoint."
3. **Scope search**: the exact keywords or identifiers to search for. Include adjacent brand names, hosts, provider ids, status strings, docs URLs, and user-facing terms.
4. **Affected surfaces**: check adapter, domain, storage, IPC, ViewModel, UI, docs, tests, diagnostics, and live-probe scripts as applicable.
5. **Fix plan**: the smallest complete set of changes that removes the failed assumption from all relevant surfaces.
6. **Verification**: commands and evidence that prove completion. Use unit tests for local behavior, live probes for external facts when safe, grep to prove stale assumptions are gone, and design-doc checks for durable context.

Use this especially when mocks pass. A mock test can prove response parsing, but it cannot prove the real endpoint host, auth region, console URL, or third-party behavior.

## Use This When

- A third-party API returns auth, endpoint, region, permission, schema, or quota errors.
- A bug fix touches a provider integration or external service assumption.
- User-facing text may teach the user the same wrong assumption that caused the bug.
- A test suite passes but the real system still fails.
- A user asks why a fix did not consider UI, docs, tests, or design decisions.

## Watch Out For

- Do not use "tests pass" as the only completion criterion when the bug came from an external fact.
- Do not search only the exact string that failed. Search adjacent names, old hosts, provider aliases, docs URLs, and status messages.
- Do not let the failed assumption remain in design decisions or implementation plans; future agents will reuse those records.
- Do not turn every typo into a heavyweight analysis. Use this when the bug plausibly reflects a shared assumption or cross-layer contract.
- Do not run live probes against risky services or protected workflows without user approval and the constraints from [[IMPL-003]].

## Example

In token-panic, the Kimi adapter initially called `api.moonshot.ai` and returned HTTP 401 with a valid user key. A direct probe showed that the same key worked against `api.moonshot.cn`. The first patch changed the adapter URL and made the live test pass.

User review then found that the configuration UI still pointed users at `platform.kimi.ai`, and the config ViewModel carried the same stale assumption. The real bug was not a single bad URL; it was the failed assumption that this user was using the international Kimi/Moonshot region.

The corrected workflow searched for `moonshot`, `kimi.ai`, `platform.kimi`, `platform.moonshot`, and related Kimi references across `src/` and `design_docs/`. It checked adapter endpoint, auth failure text, ConfigPanel hint, config ViewModel hint, DD-026, adapter tests, main scheduler registration, IPC provider lists, dashboard ViewModel tests, and integration tests. Completion was declared only after stale strings were gone, tests passed, the live probe worked, and the design decision documented the China-region endpoint.

## Related Practices

- [[DEBUG-001]] — diagnostics should make the failing boundary and reproduction path agent-actionable
- [[IMPL-002]] — verify external behavior before building integration code
- [[TEST-002]] — test the connecting pipeline, not only endpoint modules
- [[ARCH-007]] — keep design docs as context contracts so corrected assumptions survive handoff
- [[COLLAB-006]] — verify completion against the original task list, not side effects such as green tests
