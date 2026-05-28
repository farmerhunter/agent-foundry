# Harvest Workflow Reference

Canonical sources:

- `workflows/harvest-practices.md`
- META-001, META-002, META-003

Route:

```text
session reconstruction
  -> candidate extraction
  -> classification
  -> dedupe against index
  -> decision
  -> human review
  -> approved canonical update
  -> adapter update
  -> report
```

Keep only candidates that are reusable, actionable, specific, evidence-backed, and likely to change future agent behavior.

Decisions:

- `discard`: not reusable or already covered.
- `merge`: improves an existing practice.
- `create`: genuinely new reusable practice.
- `supersede`: replaces an older rule.
- `defer`: promising but under-evidenced.

When the user approves a candidate:

```text
merge/create/supersede
  -> promote to active when applicable
  -> update index
  -> publish relevant adapters
  -> report changed files
```

Before the final report, do a lightweight missed-activation check. Record missed evidence only when there is a concrete missed moment and a specific practice ID: the user identified a violation, review found a specific missed trigger, or the agent can name the practice ID, trigger, and risk clearly. Use `record_asset_usage.py --evidence-type missed`; do not record vague self-scoring.
