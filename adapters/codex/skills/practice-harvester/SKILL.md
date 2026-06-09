---
name: practice-harvester
description: Use when the user says "harvest practices", "harvest skills", "harvest assets", "做一次 harvest practice", "discover assets", "发现可打包资产", "提炼实践", "沉淀经验", "import skill", "导入这个 skill", "review practices", "检查 skill rot", "review assets", "检查 asset rot", "publish practices", "发布 practices", "refresh practices and assets", "刷新practices和assets", or asks to extract, persist, deduplicate, merge, review, import, borrow, approve, publish, or refresh reusable engineering practices or assets.
---

# Practice Harvester

This skill maintains Agent Foundry, the user's canonical capability system.

Asset ID: ASSET-META-001. Canonical constraints include META-001 through META-013, GOV-001 through GOV-006, and RUNTIME-001 through RUNTIME-004.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices as behavioral constraints. Do not confuse the skill with the practices it applies.

## Compact Preflight

Before substantial changes, check:

- Duplicate or derived truth source? Apply GOV-001.
- New machinery, layer, script, workflow, or integration? Apply GOV-002 and ARCH-001.
- Transient memory or chat summary used as fact? Apply GOV-003.
- Writing into user-owned runtime or agent configuration? Apply GOV-004 and RUNTIME-001.
- Syncing, publishing, or installing adapters? Apply RUNTIME-003.
- Producing rendered or converted output? Apply TEST-001.

## Short Commands

- `harvest practices` / `做一次 harvest practice`: run the harvest workflow and present a concise review list.
- `discover assets` / `harvest skills` / `harvest assets` / `发现可打包资产`: find repeated workflows that should become skills, subagents, automations, or extensions.
- `import skill <source>` / `导入这个 skill <source>`: run the external skill import workflow.
- `publish practices` / `发布 practices`: publish adapters from current active practices.
- `review practices` / `检查 skill rot`: review for duplicates, stale entries, weak rules, and adapter drift.
- `review assets` / `检查 asset rot`: review reusable assets for usage, overlap, stale triggers, and adapter coverage.
- `refresh practices and assets` / `刷新practices和assets`: pull remote updates, conditionally regenerate adapters, and install to local runtimes. Read `workflows/refresh.md` from the agent-foundry repo.

## Workflow

1. Locate Agent Foundry Core and Vault. Use `AGENT_FOUNDRY_HOME`, then `~/.agent-foundry/config.yaml`, then the current directory only if canonical markers exist. The current project is evidence source, not canonical destination.
2. Select the workflow from the short command or user intent.
3. Read `references/harvest-workflow.md` for harvesting, `references/import-policy.md` for imports, `references/asset-policy.md` for assets, `workflows/refresh.md` from the repo for refresh, or the repository workflow file for publish/review.
4. Read `references/schema.md`.
5. When harvesting skills or assets from a long session, set an explicit evidence window that includes earlier phases, linked issues, PRs, and commits rather than only the latest discussion topic.
6. Run the current capability check before routing or drafting; do not use future architecture concepts as current writable substrate.
7. Route artifacts before abstracting practices: evidence only, design note, research/reference material, project-local decision, workflow update, practice candidate, skill/asset candidate, adapter update, or discard.
8. Apply the generalization gate before drafting practice candidates.
9. Search the practice and asset indexes before creating anything new.
10. For asset discovery, choose create, extend, skip, or defer using the smallest suitable asset rule.
11. Classify practice candidates as principle, pattern, heuristic, playbook, checklist, example, or anti-pattern.
12. Decide for each candidate: discard, merge, create, supersede, extend, skip, or defer.
13. Present a concise review list including rejected-as-practice items, asset decisions, canonical impact, adapter impact, and runtime/global instruction impact when important.
14. Treat approval as scoped to the listed items only. Broad phrases such as "continue", "approved", or "do the whole chain" do not permit skipping unshown harvest steps.
15. For self-referential workflow changes, stop at the review list before canonical mutation. After approval, continue through the listed canonical changes, checks, PR/traceability, merge/apply, and adapter/runtime publish automatically unless the diff departs from the approved list, checks fail, risk increases, or a new unlisted runtime/global target appears.
16. After the user approves a practice or asset change, apply the canonical change and publish relevant adapters automatically.
17. Report candidates, decisions, changed files, and review needs.

## Guardrails

- Apply governance practices GOV-001 through GOV-006 across all projects, not only inside Agent Foundry: protect canonical source of truth, prefer the smallest maintainable mechanism, treat transient context as evidence, preserve maintainability plus native runtime capability, do not use future architecture as current substrate, and mark current versus proposed capability.
- Do not add raw session notes directly into agent skills.
- Do not publish `candidate` or `proposed` entries into default adapters.
- Do not import external skills directly into active adapters.
- Ask for human approval before promoting a practice to `active`; after approval, publish relevant adapters unless the user asks to stage only.
- Record concise, non-sensitive asset usage evidence automatically when an active asset is invoked.
- Treat memory as evidence, not source of truth.
- During harvest, route artifacts before abstraction, treat user method corrections as process evidence first, and require insights to pass a generalization gate before they become practice candidates.
- Do not convert approval of a direction into approval to bypass an unshown harvest review list. If the review list was skipped, stop and add the missing harvest report; after approval of that report, continue through the approved chain without adding another approval gate unless an escalation condition appears.
- Do not narrow `harvest skills` or session-level asset discovery to only the latest subtopic when the user asks to review the whole session or earlier phases.
- Treat native agent learning outputs as candidate inputs; do not suppress native self-growth capabilities in agents that provide them.
- Treat agent runtime directories as shared user-owned environments. When publishing adapters, use managed blocks, namespaced files, ownership markers, backups, dry-runs, and explicit adoption for unmanaged runtime paths; never overwrite unmanaged runtime files by default.
- Separate portable adapter intent from machine-local deployment state. Keep adapter profiles and runtime templates in the repo, but keep enabled targets, detected paths, and adoption decisions in gitignored local manifests; portable snapshots exclude machine-local runtime state by default.
- After every sync or refresh, expose unambiguous state. Report the exact commit hash, unpushed commits, adapters regenerated, runtime updates applied, and next actions required. Do not leave the user guessing about alignment between canonical files, generated adapters, and local runtimes.
- Make adapter fidelity executable. Adapter quality checks must verify the exact contract surface they claim to protect, such as Compact Preflight sections, canonical IDs, published asset IDs, target conventions, and high-fidelity requirements, not just generated file existence or broad text matches.
- Review assets with lifecycle evidence. Asset review should use lifecycle state, usage evidence, overlap, canonical coverage, stale triggers, and published targets before recommending keep, revise, deprecate, archive, split, or merge.
- Sync aggregate usage statistics, not raw evidence. Keep raw usage logs local under `usage/local/`, sync sanitized aggregate rows in `usage/usage-aggregate.yaml`, and keep missed activation or other review-only signals out of shared usage counts unless explicitly summarized through an approved aggregate format.
- When working from another project, locate and validate the Foundry Vault before writing canonical records. Required markers include `indexes/practice_index.yaml`, `indexes/asset_index.yaml`, and `workflows/harvest-practices.md`.
