# Record Asset Usage Workflow

Use this workflow to record asset usage evidence with minimal user interruption.

## Default Policy

Do not ask the user for approval before recording ordinary usage evidence. Usage evidence is low-risk operational metadata.

Record automatically when:

- an active asset is explicitly invoked;
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

Use concise notes. Do not store raw session transcripts.

## Review

`review assets` should use `usage/asset-usage-log.yaml` as evidence for keep/revise/merge/deprecate/retire decisions.

