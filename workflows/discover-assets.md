# Discover Assets Workflow

Use this workflow when the user asks to review recent work history and identify repeated manual workflows that should become reusable assets.

## Invariant

Discovery outputs asset candidates, not canonical practices. Do not create or publish assets without human approval.

## 1. Gather Evidence

Use available evidence in this order:

1. Recent agent sessions and task summaries.
2. Agent memories and rollout summaries for repeated cross-session patterns.
3. Chronicle or other activity history if enabled, for discovery only.
4. Existing practices, assets, adapters, subagents, and automations to avoid duplicates.

Apply:

- META-006: memory can suggest candidates, but Agent Foundry canonical records decide what becomes durable.
- META-007: native agent learning should remain enabled; treat native generated skills and memories as candidate inputs, not bypasses.

If evidence is insufficient, say so and defer.

## 2. Identify Repeated Workflows

Look for work that is repeated, costly, easy to get wrong, context-heavy, or suitable for standardization.

Candidate scope may include coding, research, writing, planning, communication, operations, analysis, and personal workflow management.

## 3. Inclusion Criteria

Include a candidate only if:

- it happened at least twice, or is clearly likely to repeat with high cost;
- inputs are stable enough;
- steps are repeatable;
- output or finish condition is clear;
- packaging would improve speed, quality, consistency, or reliability;
- existing coverage is missing or insufficient.

## 4. Choose Smallest Suitable Asset

Read and apply:

- META-004 Choose the smallest suitable asset.
- META-005 Define asset boundaries before creation.

Recommended form:

- `skill`: reusable workflow or operating guide.
- `subagent`: bounded delegable role or investigation task.
- `automation`: scheduled or recurring check, report, reminder, or monitor.
- `extend_existing`: improve an existing asset.
- `skip`: one-off, vague, sensitive, or already covered.
- `defer`: promising but needs more evidence.

Do not recommend internal repository workflows or adapters as asset types. Workflows and adapters are maintenance machinery; assets are user-facing reusable tools.

Skill is not the default. Recommend `skill` only when the asset is a reusable workflow or operating guide that a general agent should execute directly. Recommend `subagent` when the work is better delegated to a bounded role. Recommend `automation` when timing or recurrence is the core value.

Before recommending `create`, confirm the candidate has:

- clear trigger;
- responsibility;
- non-responsibility;
- inputs;
- process;
- outputs;
- success criteria.

If these are unclear, recommend `defer` or `extend_existing`.

## 5. Dedupe

Before recommending create:

1. Read `indexes/asset_index.yaml`.
2. Read `indexes/practice_index.yaml`.
3. Check existing assets and adapters.
4. Prefer `extend_existing` over duplicate creation.

## 6. Output Review List

Present a concise list:

```text
1. <repeated workflow>
   Evidence: <source/date summary>
   Frequency: high | medium | low | likely-repeat
   Confidence: high | medium | low
   Existing coverage: none | partial | sufficient
   Recommended form: skill | subagent | automation | extend_existing | skip | defer
   Why:
   Boundary: trigger / responsibility / non-responsibility / inputs / outputs
   Success criteria:
   Canonical practices likely used:
   After approval:
```

## 7. Approval

Wait for approval per candidate.

After approval:

```text
create or extend asset
  -> update asset index
  -> publish relevant adapters
  -> record initial evidence if useful
  -> report changed files
```

If a candidate reveals a missing principle, recommend running `harvest practices` for that specific lesson.
