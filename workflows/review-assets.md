# Review Assets Workflow

Use this workflow to prevent asset rot.

## Review Targets

Review:

- active assets with no usage evidence;
- assets with overlapping triggers or purpose;
- assets not published to relevant direct programming agents;
- assets with stale canonical practice links;
- automations that no longer matter;
- subagents whose role is too broad or vague.

## Evidence

Read:

- `indexes/asset_index.yaml`
- `usage/asset-usage-log.yaml`
- `workflows/record-asset-usage.md`
- relevant adapters
- relevant canonical practices

## Decisions

For each asset choose:

- keep active;
- revise;
- merge;
- deprecate;
- retire;
- gather more evidence.

## Report

Present a concise review list and wait for approval before applying status changes, merges, retirements, or broad adapter rewrites.
