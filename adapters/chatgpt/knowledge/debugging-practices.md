# Debugging Practices

Canonical IDs: DEBUG-001

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
