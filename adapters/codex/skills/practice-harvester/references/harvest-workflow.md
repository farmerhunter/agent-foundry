# Harvest Workflow Reference

Canonical source: `workflows/harvest-practices.md`

Follow this route:

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

Present candidates as a concise review list. New entries default to `status: proposed` and `review_required: true` unless the user approves activation.

When the user approves a candidate, apply its full chain:

```text
merge/create/supersede
  -> promote to active when applicable
  -> update index
  -> publish relevant adapters
  -> report changed files
```

Before the final report, do a lightweight missed-activation check. Record missed evidence only when there is a concrete missed moment and a specific practice ID: the user identified a violation, review found a specific missed trigger, or the agent can name the practice ID, trigger, and risk clearly. Use `record_asset_usage.py --evidence-type missed`; do not record vague self-scoring.
