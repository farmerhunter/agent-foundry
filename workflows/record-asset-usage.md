# Record Usage Workflow

Use this workflow to record asset or practice usage evidence with minimal user interruption.

## Default Policy

Do not ask the user for approval before recording ordinary usage evidence. Usage evidence is low-risk operational metadata.

Record automatically when:

- an active asset is explicitly invoked;
- an active practice is materially applied and the agent can identify the practice ID;
- the agent can identify asset ID, agent name, project, trigger, and rough outcome;
- recording does not expose sensitive content.

Skip or redact when:

- the work is sensitive;
- the note would include secrets, private data, or confidential details;
- the asset ID is unclear.

## Script

Run:

```bash
python3 scripts/record_asset_usage.py \
  --asset-id ASSET-ARCH-001 \
  --agent codex \
  --project token-panic \
  --trigger "architecture review" \
  --outcome useful \
  --note "Identified tool-centered architecture risk and domain boundary improvements."
```

For practice usage:

```bash
python3 scripts/record_asset_usage.py \
  --practice-id RUNTIME-004 \
  --agent codex \
  --project agent-foundry \
  --trigger "usage evidence aggregation" \
  --outcome useful \
  --note "Applied local raw plus shared aggregate evidence boundary."
```

Use concise notes. Do not store raw session transcripts.

## Data Boundary

`scripts/record_asset_usage.py` writes raw evidence to gitignored `usage/local/usage-log.yaml` and updates sanitized shared counts in `usage/usage-aggregate.yaml`.

Raw local evidence may include project, trigger, and note fields for local audit. It is machine-local by default and should not be synced unless the user explicitly chooses to share it.

Shared aggregate evidence is safe to sync. It records subject type, subject ID, period, agent, hashed machine ID, outcome counts, and last-used date. It does not store prompt text, project names, raw notes, or session transcripts.

To rebuild the aggregate from local raw evidence and optional legacy logs:

```bash
python3 scripts/aggregate_usage.py --include-legacy
```

## Review

`review assets` should use `usage/usage-aggregate.yaml` as its primary evidence for keep/revise/merge/deprecate/retire decisions. Legacy `usage/asset-usage-log.yaml` is fallback or migration input only.
