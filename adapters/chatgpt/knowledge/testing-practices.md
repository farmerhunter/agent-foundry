# Testing Practices

Canonical IDs: TEST-001, TEST-002

## TEST-001 Render-Verify Format Conversions

For converted document deliverables, verify rendered output, font/encoding behavior, images, and source-to-output structure rather than relying only on command success.

## TEST-002 Test The Connecting Pipeline, Not Only The Endpoints

When a system connects independently-tested modules through glue code (callbacks, transformations, fallback construction, IPC pushes, provider_id propagation), test that connecting code as thoroughly as the modules it connects. Adapter tests + ViewModel tests passing does not mean the pipeline works.

The minimum viable pipeline test: construct the error input at the adapter boundary, run it through the connecting code, and assert the output reaches the consumer boundary with the correct identifier.

Common failure: an adapter returns `null` on error, the connecting code calls `generateSummary(null)`, which returns `provider_id = 'unknown'`, and the renderer's provider_id filter never matches — permanent loading deadlock. Test error paths through the full pipeline.
