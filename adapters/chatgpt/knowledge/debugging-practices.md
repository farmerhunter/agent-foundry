# Debugging Practices

Canonical IDs: DEBUG-001, DEBUG-002

## DEBUG-001 Design Diagnostics As Agent-Actionable Reproduction Artifacts

Design diagnostics as agent-actionable reproduction artifacts, not only as human-readable logs. A useful debug artifact should let an agent identify the failing boundary, reconstruct the minimum input, add a failing test, and verify the fix.

Use a two-layer model:

1. Default metadata trace:
   - generate or propagate a `trace_id`;
   - record component, action, status, stable reason, timestamp, and bounded metadata;
   - record sizes, counts, strategies, and short candidate snippets;
   - do not default-log full raw text, credentials, cookies, localStorage, sessionStorage, screenshots, or large DOM/HTML dumps.

2. Explicit reproduction bundle:
   - let the user export a debug bundle for one trace;
   - include environment, trace events, parser/importer diagnostics, and manifest/schema version when available;
   - include raw input only when the user explicitly chooses it;
   - prefer redacted input or relevant-line context when full raw input is unnecessary.

For parsers and importers, keep business output separate from diagnostics. Preserve the normal production API, and add a diagnostics side channel that reports strategies tried, candidate lines, failure reason, and input scale.

Expected agent workflow:

```text
inspect diagnostics
  -> identify failing boundary
  -> convert raw/redacted input into a fixture when needed
  -> add a failing test
  -> fix parser/capture/adapter logic
  -> run tests/build
  -> ask the user to re-run the original action
```

## DEBUG-002 Treat Bugs As Failed Assumptions Before Patching

When a bug involves API endpoints, auth, region, credentials, quota models, third-party behavior, or user-facing provider text, do not patch the first failing line and stop at green tests. First write:

1. Symptom: what the user saw and what commands or logs reported.
2. Failed assumption: the wrong belief in one precise sentence.
3. Scope search: exact keywords, provider aliases, hosts, docs URLs, status text, and UI terms to search.
4. Affected surfaces: adapter, domain, storage, IPC, ViewModel, UI, docs, tests, diagnostics, and live-probe scripts as applicable.
5. Fix plan: the smallest complete set of changes.
6. Verification: tests, safe live probes when appropriate, grep evidence that stale assumptions are gone, and design-doc checks.

Completion is not "the current error disappeared" or "unit tests pass." Completion is that the failed assumption's blast radius has been checked and stale assumptions have been cleared from code, UI, tests, and docs.
