# Transform Canonical Practices To Adapters

Use this workflow whenever publishing agent-specific adapters from canonical practices.

## Invariant

Adapters may differ in format, but they must preserve equivalent behavior for their target workflow. Full fidelity means full access through progressive loading, not one large instruction dump.

## 1. Read Profiles

Read:

- `adapters/adapter_profiles.yaml`
- `schemas/adapter-profile.schema.yaml`
- `indexes/practice_index.yaml`
- `indexes/asset_index.yaml`

For each target adapter, identify:

- whether it is a direct programming agent;
- fidelity level;
- supported packaging features;
- output paths;
- included domains;
- command vocabulary.
- active assets relevant to the adapter.

## 2. Select Canonical Practices

Include only entries with:

- `status: active` or `status: revised`;
- domain included by the adapter profile;
- guidance relevant to the target workflows.

Exclude:

- `candidate`
- `proposed`
- `superseded`
- `archived`

For assets, include only active or revised assets relevant to the adapter. Exclude candidate, proposed, deprecated, and retired assets.

## 3. Group By Skill Or Workflow

Default grouping:

- `practice-harvester`: META entries plus harvest/import/publish/review workflows and schema.
- `architecture-design`: ARCH entries plus architecture checklist.
- asset records: publish active assets as available commands, skills, subagents, automations, or knowledge entries depending on adapter profile.

## 4. Map Canonical Sections

Use this mapping:

| Canonical section | Adapter use |
|---|---|
| `id` | canonical mapping and audit |
| `title` | rule heading |
| `Principle` | compact rule |
| `Guidance` | operational instruction |
| `Use This When` | triggers |
| `Watch Out For` | guardrails |
| `Example` | include in full fidelity references when helpful |
| `Rationale` | compress or omit unless needed for judgment |

## 5. Apply Fidelity

### Full

Provide:

- short dispatcher or skill body;
- command vocabulary;
- workflow references;
- schema references;
- compact principles;
- checklist;
- canonical ID mapping;
- approval and publish semantics.

Use progressive loading when the platform supports it.

### Standard

Provide:

- short dispatcher;
- compact rules;
- approval semantics;
- canonical ID mapping.

### Compact

Provide:

- command vocabulary;
- essential guardrails only.

## 6. Validate

For each adapter, verify:

- all included IDs are active or revised;
- omitted active IDs are intentionally out of scope;
- command vocabulary is present;
- approval then automatic publish semantics are preserved;
- adapter profile is followed;
- canonical IDs are visible for audit;
- asset IDs are visible for audit when assets are included;
- no direct DeepSeek adapter is generated.
- adapter instructions do not disable native memory, native skill creation, or self-improvement unless explicitly requested.

## 7. Report

```text
Adapter: <id>
Fidelity: full | standard | compact
Outputs changed:
- <path>
Canonical IDs included:
- <id> <title>
Asset IDs included:
- <id> <title>
Not included:
- <id> because <reason>
```
