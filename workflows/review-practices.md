# Review Practices Workflow

Use this workflow for periodic cleanup and anti-rot review.

## Review Targets

Review:

- candidate/proposed entries older than 30 days;
- active entries with overlapping aliases or tags;
- entries that have not influenced adapters;
- adapters that mention stale canonical IDs;
- large or generic practices that no longer guide behavior.
- practices with weak, noisy, stale, or missing activation signals;
- missed-activation evidence indicating a practice should have triggered but did not.

## Decisions

For each reviewed entry choose:

- keep active;
- revise;
- merge;
- supersede;
- archive;
- keep proposed pending user decision.

## Checks

- Run `python3 scripts/review_practices.py` and use the report as review input. The script validates Core/Vault roots, reads practice and asset records from the selected Vault, and reads adapter evidence from Core.
- Is the practice still actionable?
- Is it specific enough?
- Does it duplicate another practice?
- Does it conflict with a higher-priority rule?
- Should it move to a different type or domain?
- Is the adapter summary still accurate?
- Is its activation tier correct?
- Has it been missed often enough to strengthen signals or promote tier?
- Is an `always_preflight` entry noisy enough to demote?

## Approval Route

The review report should produce recommendations, not automatic mutations. Present a compact approval list:

```text
1. GOV-002
   Action: revise_activation
   Why: missed activation evidence count is 2
   After approval: update GOV-002 Activation, publish adapters, run checks, install supported runtimes
```

When the user approves selected items:

1. apply only the approved canonical changes;
2. update indexes or asset records when needed;
3. publish relevant adapters;
4. run `check_consistency.py`, `check_activation.py`, and `check_adapter_quality.py`;
5. run `install_foundry.py --apply` for supported local runtimes unless the user asks to stage only;
6. report changed files, checks, and any manual ChatGPT import needed.

Do not change lifecycle state, activation tier, or `always_preflight` coverage without explicit approval.

## Activation Review

Use activation evidence as review input, not an automatic mutation.

Recommend tier changes when evidence supports them:

- promote to `always_preflight` only for frequent, high-impact, low-noise rules;
- demote from `always_preflight` when the trigger is noisy, narrow, or better handled inside a workflow;
- use `workflow_embedded` when the rule only matters inside a specific workflow;
- use `review_only` when the rule mainly helps cleanup or lifecycle decisions.

Human approval is required before changing activation tier or adapter preflight coverage.

## Report

Report every recommendation and wait for human approval before applying lifecycle, activation, adapter, or broad canonical changes.
