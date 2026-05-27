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
- active assets whose last useful usage is older than `review_after_days`;
- assets with duplicated or overlapping usage triggers.

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
- archive;
- gather more evidence.

## Automation

Run:

```bash
python3 scripts/review_assets.py
```

Use the report as evidence, not as an automatic mutation. Human approval is required before status changes, merges, retirement, archiving, or broad adapter rewrites.

## Decision Table

- Extend an existing skill when the trigger, responsibility, inputs, and outputs remain inside the asset boundary.
- Create a new skill when the workflow has a distinct trigger, process, and finish condition.
- Create a subagent when the work is a bounded delegable role or investigation.
- Create an automation when the work is scheduled, recurring, or monitor-like.
- Deprecate when a better replacement exists but migration is still needed.
- Retire when the asset should no longer be invoked.
- Archive when the asset is historical and should be excluded from normal review.

## Report

Present a concise review list and wait for approval before applying status changes, merges, retirements, or broad adapter rewrites.
