# Publish Adapters Workflow

Use this workflow when updating Codex, Claude Code, ChatGPT, Hermes, or other agent-specific outputs from canonical practices and active assets. This normally runs automatically after the user approves a new or changed practice or asset.

## Invariant

Adapters are downstream outputs. Direct programming agents should receive full fidelity through progressive loading when the target environment supports it.

Before publishing, read `workflows/transform-canonical-to-adapters.md` and `adapters/adapter_profiles.yaml`.

Current AF-3 capability:

- use `scripts/publish_adapters.py` for selected Core/Vault root validation and deterministic publishing;
- pass `--core-root` and `--vault-root` when Core and Vault are split;
- blank Vault publishing is valid and reports `nothing to publish`;
- nonblank Vault publishing currently generates minimal transitional adapter files from Core adapter profiles plus selected active/revised Vault records;
- full semantic regeneration of every adapter file from canonical sections remains future generator work.

Example:

```bash
python3 scripts/publish_adapters.py --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault --output-root /tmp/agent-foundry-adapters --apply
```

The publish script prints an operation-context preflight before writing. If running the workflow manually, verify the report says:

- operation: `publish`;
- Core is the tooling/profile source;
- Vault is the selected canonical record source;
- allowed writes are limited to the generated adapter output root;
- runtime install paths are forbidden until the install workflow runs.

## 1. Select Practices

Publish only practices with:

- `status: active` or `status: revised`;
- domain relevant to the adapter;
- actionable guidance that should influence agent behavior.

Do not publish `candidate`, `proposed`, `superseded`, or `archived` entries into default adapters.

For assets, publish only assets with:

- `status: active` or `status: revised`;
- relevant triggers and success criteria;
- a target agent listed or implied by `published_to`.

Do not publish `candidate`, `proposed`, `deprecated`, or `retired` assets into default adapters.

## 2. Choose Adapter Profile

Use `adapters/adapter_profiles.yaml` as the source of truth.

- Codex: full fidelity skill folders.
- Claude Code: full fidelity `CLAUDE.md` plus command files.
- Hermes: full fidelity skill folders.
- ChatGPT: full fidelity custom/project instructions plus knowledge files.
- DeepSeek: no direct programming adapter; use through another agent.

## 3. Transform

Follow `workflows/transform-canonical-to-adapters.md`.

For full fidelity adapters:

- keep entry instructions short;
- include workflow and practice details in references or knowledge files;
- preserve short command vocabulary;
- preserve canonical ID mapping;
- preserve asset ID mapping when publishing assets;
- preserve approval then automatic publish semantics.

## 4. Preserve Source Mapping

Each adapter should mention the canonical practice IDs it summarizes. This makes drift detection and manual review easier.

When an adapter publishes an asset, it should also mention the asset ID.

## 5. Validate

Check:

- adapter does not contradict canonical entries;
- adapter does not include proposed/unapproved content;
- adapter trigger conditions are clear;
- adapter size is appropriate for the target agent;
- human approval gates are still present.
- no direct DeepSeek adapter is generated.
- asset IDs are visible for audit when assets are published.

Then run:

```bash
python3 scripts/check_consistency.py
python3 scripts/test_foundry_roots.py
```

If unavailable, follow `workflows/check-consistency.md` manually.

## 6. Report

```text
Adapters updated:
- <path>

Canonical practices included:
- <id> <title>

Assets included:
- <id> <title>

Excluded:
- <id/title> because <reason>
```
