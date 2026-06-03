---
id: TEST-002
title: Test the connecting pipeline, not only the endpoints
domain: testing
type: anti-pattern
status: active
version: 1
created: 2026-06-03
updated: 2026-06-03
tags: [testing, integration, pipeline, glue-code, error-paths]
aliases:
  - TEST-002
  - test the glue not just the endpoints
  - adapter and ViewModel tests don't prove the pipeline works
  - error path pipeline testing
related: [ARCH-005, ARCH-008, IMPL-002]
applies_when:
  - a system has multiple independently-tested modules connected by glue code
  - an adapter's output is transformed by a callback before reaching the renderer
  - the connecting code does filtering, fallback construction, or provider_id propagation
  - error paths produce null/empty values that downstream code must handle
provenance: "Harvested from token-panic Kimi adapter bug (2026-06-03), where generateSummary(null) produced provider_id='unknown', breaking the renderer's provider_id filter. Adapter tests passed. ViewModel tests passed. The connecting code had no tests."
---

## Principle

When a system connects independently-tested modules through glue code (callbacks, transformations, fallback construction), test that connecting code at least as thoroughly as the modules it connects. Adapter tests + ViewModel tests passing does not mean the pipeline works.

## Rationale

Layered architectures naturally create three types of code:

1. **Endpoint modules** — adapter input→output, normalize functions, ViewModel pure functions. Easy to test: known inputs, expected outputs, no side effects.
2. **Glue code** — the callbacks, error fallback construction, IPC pushes, and provider_id propagation that connect endpoints. Harder to test: involves multiple module boundaries, error states, and side effects.
3. **Renderer** — the component that consumes the final output.

The tendency is to test category 1 thoroughly (it's easy) and skip category 2 (it's awkward). But category 2 is where silent failures happen:

- An adapter returns `{ snapshot: null, error: { status: 'auth_required' } }` — adapter tests pass.
- The main-process callback receives null and calls `generateSummary(null)` — no test covers this.
- `generateSummary(null)` returns `{ provider_id: 'unknown', ... }` — summary tests pass (null input is tested).
- The renderer's `useSnapshot('kimi')` filters for `provider_id === 'kimi'` — filter is correct.
- The renderer never updates, loading state is permanent deadlock — **pipeline broken, no single module at fault**.

The minimum viable pipeline test is: construct the error input at the adapter boundary, run it through the connecting code, and assert the output reaches the consumer boundary with the correct identifier.

## Guidance

For each adapter→renderer pipeline, add these tests:

1. **Provider identity preservation**: when the adapter returns null or error, does the connecting code still produce output with the correct `provider_id` so the renderer can consume it?
2. **Error status propagation**: does the error status from the adapter surface in the renderer-visible summary?
3. **Null-safety**: does the connecting code handle `snapshot = null` without producing `provider_id = 'unknown'` or crashing?
4. **Multi-provider isolation**: does an error from provider A affect provider B's pipeline?

The test does not need Electron, IPC mocks, or React. It can be a pure function chain:

```ts
// Input: what the adapter returns on error
const errorSnapshot = makeErrorSnapshot(adapter.id, adapter.name, ...);
// Run through the connecting transformation
const summary = generateSummary(errorSnapshot, lastSuccess);
// Assert renderer-visible properties
expect(summary.provider_id).toBe(adapter.id);
expect(summary.status).toBe('auth_required');
```

## Use This When

- Adding a new provider adapter to an existing multi-provider system.
- Adding error-handling logic to a callback that connects adapter output to renderer input.
- The renderer filters incoming data by provider_id or similar identifier.
- A bug is found where the renderer shows "loading" indefinitely despite the adapter completing.
- Tests exist for adapter input→output and ViewModel input→output, but not for the code between them.

## Watch Out For

- Do not require full Electron/IPC/React integration tests for this. A pure function chain test is sufficient for the connecting transformation.
- Do not test only the happy path. The error path (null snapshot, auth_required, network error) is where provider_id loss typically occurs.
- Do not assume that `generateSummary(null)` preserves identity. If the domain function has a null→'unknown' fallback, the glue code must construct an explicit error snapshot first.

## Example

In token-panic, the Kimi adapter was added with 9 adapter tests (metadata, auth_required, success, 401, 403, 500, network, code!=0, missing-data) and 8 ViewModel tests (balanceProviders array, action availability, provider isolation). All passed.

But when a user configured a Kimi API key that failed to authenticate, the dashboard showed "加载中…" indefinitely. The root cause: the main-process callback received `result.snapshot = null` from the adapter, called `generateSummary(null)`, and got back `provider_id = 'unknown'`. The renderer's `useSnapshot('kimi')` filter never matched, so the loading state never cleared.

The fix was adding 5 pipeline tests:

```ts
it('should produce summary with correct provider_id for Kimi on auth_required', () => {
  const ers = makeErrorSnapshot('kimi', 'Kimi', 'official_api', 'balance', 'No key', 'auth_required');
  const summary = generateSummary(ers);
  expect(summary.provider_id).toBe('kimi'); // not 'unknown'
});

it('should never produce unknown provider_id from errorSnapshot', () => {
  for (const pid of ['kimi', 'deepseek', 'openai_platform', 'chatgpt']) {
    const ers = makeErrorSnapshot(pid, pid, 'official_api', 'balance', 'test', 'error');
    expect(generateSummary(ers).provider_id).toBe(pid);
    expect(generateSummary(ers).provider_id).not.toBe('unknown');
  }
});
```

These tests cover the exact gap where the bug lived: the transformation between adapter output and renderer input, on the error path, for all providers.

## Related Practices

- [[ARCH-005]] — UI consumes domain summaries; the pipeline test verifies that summaries reach the renderer with correct identity
- [[ARCH-008]] — implementation plan should surface pipeline gaps; the pipeline test captures the error-path gap that static review may miss
- [[IMPL-002]] — verify before building; the pipeline test verifies that error paths preserve identity before users encounter them
