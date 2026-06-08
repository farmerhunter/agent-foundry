# Harvest Workflow Reference

Canonical source: `workflows/harvest-practices.md`

Locate Agent Foundry before writing canonical records. Use `AGENT_FOUNDRY_HOME`, then `~/.agent-foundry/config.yaml`, then the current directory only if it contains canonical markers. The current project is evidence source, not canonical destination.

Follow this route:

```text
session reconstruction
  -> current capability check
  -> artifact routing
  -> generalization gate
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

Before drafting candidates, route important artifacts as evidence only, design note, research/reference material, project-local decision, workflow update, practice candidate, skill/asset candidate, adapter update, or discard. Treat user method corrections as process evidence first. Do not use future architecture concepts, directories, schemas, or workflow categories as current writable substrate.

Rejected-as-practice items should be named when important, especially when they are domain research, project-local decisions, or future architecture rather than generalized Agent Foundry practices.

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
