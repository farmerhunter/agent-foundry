# Usage Guide

This guide is for day-to-day Agent Foundry use. It keeps the user path short and leaves internal workflow details in the workflow/reference docs.

**中文要点：** 这是日常使用指南。先看短命令和用户流程；内部 workflow 细节不用先读。

## How It Works

Agent Foundry is local-first and separates four working layers:

- **Core**: public workflows, schemas, scripts, templates, docs, adapter profiles, runtime templates, and validation tooling.
- **Selected User Vault**: canonical `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregates.
- **Generated output**: adapter files produced from Core plus the selected Vault.
- **Runtime files**: downstream installed copies under tools such as Codex, Claude Code, Hermes, Trae, or ChatGPT manual imports.

```text
work session or external skill
  -> harvest / import / discover
  -> human approval
  -> canonical practice or asset in selected User Vault
  -> publish adapters from Core plus selected Vault
  -> install to local runtimes
  -> use short commands to invoke assets
```

**中文要点：** Core 是 public tooling；selected User Vault 是 canonical records；generated output 和 runtime files 都是下游投影，不是 source of truth。

## Core Rule

Prefer short commands from `docs/commands.md`, such as `harvest practices`, `refresh practices and assets`, or `check Agent Foundry status`.

The agent may discover, draft, and recommend practices or assets. You approve each meaningful new item or change before it becomes active. After approval, the agent should update canonical Vault records, update indexes, publish relevant adapters, and report changed files.

External skills are reviewed inputs. An import outcome is one of `discard`, `reference_only`, `defer`, `merge_into_existing`, `propose_practice`, or `propose_asset`. Reference-only material stays as sanitized review evidence under selected Vault `imports/inbox/`; it does not activate behavior, publish adapters, or mutate runtime files.

**中文要点：** 日常用短命令。重要新增/变更必须经你批准后才会 active。外部 skills 先 review；`reference_only` 只是证据，不会激活或 publish。

## Tester Evidence

For risky user-visible or stateful changes, you can ask for Tester evidence before accepting the work. Tester plans or gathers evidence; Tester does not approve the change.

Use Tester when the question is: what was tested, why is it enough, and what risk remains? Skip Tester when a docs check, static check, or unit test already gives enough confidence.

For the full role-based issue and PR flow, see `docs/multi-agent-collaboration.md`.

**中文要点：** Tester 负责测试计划和证据，不替代 Reviewer、Architect 或 Human approval。

## Collaboration Readiness

Before using a repo for multi-agent GitHub issue/PR work, ask for a collaboration readiness check:

```text
check collaboration readiness for this repo
检查这个 repo 的 collaboration readiness
```

The report should tell you whether role labels, routing templates, Execution Contracts, Testing Contracts, issue/PR routing, and optional Project/Kanban visibility are present or drifted. Normal users should read `readiness_status`, the short summary, and `recommended_next_actions` first. Raw JSON is evidence/debug output.

Branch-aware readiness also tells you whether work appears to belong on `main`,
an integration branch, a release branch, a stacked PR, or a multi-branch flow.
Use `main` for V1.x maintenance in Agent Foundry, and
`codex/v2-local-first-orchestration` for V2 integration. If a generic Core
update belongs on `main` while V2 work is active, split the work, land the
generic update on `main`, record the later forward-merge need, and verify every
branch line named by the action plan.

For a new project, ask for setup planning:

```text
prepare this repo for multi-agent collaboration
为这个 repo 准备 multi-agent collaboration
```

For an existing project, ask for an audit:

```text
audit existing collaboration setup
审计现有 collaboration setup
```

Recommended actions use four categories:

- `informational_only`: record evidence or degraded optional mirrors; no mutation is needed.
- `agent_handled_existing_workflow`: route through normal Agent Foundry issue, comment, label, PR, or role handoff workflow.
- `explicit_human_gate`: use a Human Decision Contract for product, governance, privacy, final integration, closure, or meaningful Project policy choices.
- `unsupported_deferred_repair_apply`: describe the repair but do not execute it in AF15.

The action-plan report is read-only: `mutation_performed: false`, repair entries keep `apply_supported_now: false`, and the workflow does not perform live repair/apply, Project v2 mutation, generated Skill/adapter publish, or capability-pack deploy/apply.

Branch action-plan concepts are also read-only:

- `current_branch_ok`: continue normal scoped work.
- `switch_context_required`: stop editing in this checkout and route or prepare
  a separate reviewed context.
- `split_work_recommended`: split mixed branch-line work instead of hiding it
  in one PR.
- `forward_merge_needed_later`: record the later merge need; do not merge
  automatically.
- `verify_on_multiple_lines`: verify every named branch line before claiming
  cross-line readiness.
- `architect_decision_required`: route custom or policy-sensitive branch
  strategy to Architect.

**中文要点：** 新 repo 先要 setup checklist；老 repo 先 audit drift。Action plan 只读，给出下一步，不自动 repair/apply。
Branch action plan 也只读：它可以提示 split、switch context、forward-merge 或多线验证，
但不会自动 checkout、retarget、merge、reset 或 clean。

## First-Time Setup

On a new machine, use `docs/deployment.md` for the full split Core/Vault install flow. Short version:

```bash
python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
python3 scripts/foundry_config.py status
python3 scripts/runtime_manifest.py init
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable codex       # or claude-code, hermes, trae
python3 scripts/runtime_manifest.py plan
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
python3 scripts/install_foundry.py --apply             # only after reviewing dry-run/status output
python3 scripts/sync_status.py
```

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, runtime directories, or ChatGPT project files as canonical truth. Recreate local state from Core plus the selected Vault, then verify with `sync_status.py`.

**中文要点：** 新机器从 Core + selected Vault 重建；不要复制另一台机器的 runtime/local、config 或 runtime directories。

## Daily Workflow

Use these requests for ordinary work:

- `refresh practices and assets` at the start of a session, after switching machines, or when local agent rules may be stale.
- `check Agent Foundry status` or `python3 scripts/sync_status.py` for read-only machine status.
- `harvest practices` after a session when reusable lessons should become durable practices.
- `discover assets` when repeated manual work should become a reusable skill, subagent, automation, or extension.
- `review practices` and `review assets` periodically to prevent skill rot and asset rot.

**中文要点：** session 开始先 refresh；只读检查用 status；沉淀经验用 harvest；重复工作用 discover assets；定期 review 防止 rot。

## Refresh Practices And Assets

Command:

```text
refresh practices and assets
刷新practices和assets
```

Expected behavior:

- check local state and avoid losing real work;
- pull remote git updates when appropriate;
- regenerate adapters if canonical practices or assets changed;
- dry-run or install to enabled local runtimes through the reviewed path;
- report current commit, unpushed work, generated output state, runtime receipts, and updated runtimes.

**中文要点：** refresh 会先保护本地状态，再 pull、regenerate adapters、dry-run/install，并汇报 commit、未 push 工作、generated output 和 runtime receipts。

## Status And Drift

Run status before applying runtime writes, after long idle periods, after switching machines, or when a rule appears not to affect an agent.

```bash
python3 scripts/sync_status.py
```

`sync_status.py` separates Core repo progress, selected Vault state, generated output, runtime receipt state, manual targets, and human-gated runtime writes. If generated output is missing or stale, publish adapters first. If runtime receipt is missing or drifted, review generated output, run install dry-run, read status, then apply only when the runtime write is expected.

**中文要点：** status 分层报告 Core、Vault、generated output、runtime receipt 和 manual targets。Runtime drift 不要通过编辑 Vault records 修。

## Capability Pack Safety

Capability packs are reviewed bundles that can add or change practices, assets, generated output, and runtime-facing behavior. Normal users should use Skill-first requests; raw scripts are implementation details or advanced/debug details.

Use these normal-user requests for consumption flows:

```text
review capability pack lifecycle <pack-id>
preview capability pack transfer <path>
list capability packs
recommend capability packs for my setup
preview capability pack deployment <pack-path>
apply reviewed capability pack <pack-path>
verify capability pack <pack-id>
update capability pack <pack-id-or-path>
disable capability pack <pack-id>
```

Every normal-user pack report should include pack identity, display status, inspected layers, changed layers, whether the path is `writes: none`, exact selected Vault write target for accepted apply paths, next safe action, and rollback or defer guidance.

State names such as `recommended`, `compatible`, `merge_required`, `drifted`, and `generated_missing` are transient display or comparison values unless the report explicitly names a canonical `lifecycle_status`. Do not write `recommended`, `compatible`, `merge_required`, `drifted`, `generated_missing`, or similar transient terms as lifecycle values.

Normal-user flows do not create packs, run candidate discovery, publish exports, or make maintainer release decisions. Use power-user workflows only when you explicitly ask to scan, propose, assemble, release, export, split, or merge capability packs.

**中文要点：** capability pack 默认走 Skill-first。普通用户报告必须说明 inspected layers、writes、next safe action 和 rollback/defer。不要把 transient display terms 当成 canonical lifecycle status。

## Optional First-Party Starter Packs

Starter packs are optional after setup and first value. Do not make a new user choose them before the normal harvest, refresh, or status loop works.

| Pack | Normal-user use |
| --- | --- |
| `pack.bootstrap.minimal` | Minimal bootstrap capability and prerequisite for optional starter packs. |
| `pack.multi-agent.optional` | GitHub issue/PR collaboration starter with durable comments, role labels, review handoff habits, collaboration readiness audit, and dry-run repair planning. |

Architecture-boundary, source-of-truth, Generated/Runtime downstream, and Local Private evidence-exclusion guidance belongs in `pack.bootstrap.minimal` at the current stage. It is not a standalone optional starter pack.

Core catalog pages carry version, manifest hash, provenance, compatibility, and review evidence. Those details are for ordinary/complete review, not mandatory beginner onboarding. After accepted deployment, the selected User Vault remains canonical; Core catalog entries are discoverability metadata.

**中文要点：** starter packs 是 setup 后的可选项。当前 standalone optional pack 只有 `pack.multi-agent.optional`；architecture-boundary guidance 属于 bootstrap。

## First-Party Pack Selection Principles

A first-party Core capability pack should be standalone only when it has independent user value beyond bootstrap, a cohesive reusable goal, enough mature payload beyond a thin checklist, clear audience and lifecycle behavior, low coupling to mandatory bootstrap/governance behavior, and public-safe sanitized evidence.

After deployment, the selected User Vault remains canonical. `recommend`, `preview`, `verify`, `update`, and `disable` surfaces are read-only unless a later reviewed apply step is accepted. Generated, Runtime, and Local Private artifacts cannot be pack authority.

Provider, frontend, private-project, raw selected Vault export, Generated, and Runtime candidates stay deferred or rejected unless a later issue defines safe public fixtures and review gates.

**中文要点：** standalone pack 必须有独立用户价值和成熟 payload。Vault 仍是 canonical；Generated/Runtime/Local Private 不能成为 pack authority。

## Power-User Capability Pack Maintenance

Power-user capability-pack workflows are advanced maintenance-level workflows. They are available when you explicitly ask to scan, propose, evaluate, assemble, release, review exportability, deprecate, split, or merge capability packs.

Use these advanced maintenance requests:

```text
scan capability pack candidate boundaries
discover capability packs
evaluate capability pack <path>
assemble capability pack draft <candidate-id>
review capability pack release <pack-id-or-path>
review capability pack exportability <pack-id-or-path>
review capability pack deprecation <pack-id>
review capability pack split or merge <pack-id>
```

These workflows may surface taxonomy, versioning, distribution, privacy, or compatibility decisions for review. They produce review packets by default, not active artifacts. They must not create, activate, export, publish, or deploy a pack without a later reviewed step. A review packet should include identity, evidence sources, authority layer, proposed boundary or version decision, privacy/distribution/compatibility/generated/runtime impact, required gate, `writes: none`, next safe action, and rollback or defer guidance.

Candidate discovery is a power-user diagnostic review-list flow. It does not run automatically during normal-user pack consumption, and it does not create candidate files, manifests, selected Vault records, exports, generated output, or runtime changes by default. A later reviewed power-user step must accept the review list before draft assembly or durable candidate-record work begins.

Use plan commands before apply commands when operating manually or debugging:

```bash
python3 scripts/plan_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/apply_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/manage_capability_pack_lifecycle.py --vault-root <vault-root> --pack-id <pack-id> --action disable
```

**中文要点：** power-user workflows 只在明确要求时使用，默认输出 review packet。没有后续 reviewed step，不得 create/activate/export/publish/deploy pack。

## Harvest Practices

Use this after coding, design, debugging, or coordination work when reusable lessons should become durable practices.

```text
harvest practices
做一次 harvest practice
```

Long prompt:

```text
Harvest reusable practices from this session using Agent Foundry. Keep the details hidden and present a concise review list. For each new or changed practice, show the title, why it matters, whether it merges into an existing rule or creates a new one, and what adapters would be updated after approval. Wait for my approval per practice before applying.
```

Approval example:

```text
I approve practice 1 and 3. Apply them, promote them to active, update the index, and publish the relevant adapters.
```

**中文要点：** harvest 用于沉淀可复用经验；先给 review list，逐条批准后才 apply/publish。

## Import External Skills

Use this when you find a useful public skill, prompt pack, article, repo, or local skill folder and want Agent Foundry to review it before any active behavior changes.

```text
Evaluate this external skill for Agent Foundry: <URL or local path>. Use the import workflow, but keep the report concise. Show provenance, license/security concerns, useful candidate practices, duplicates found, and what would be imported after approval. Do not activate or publish anything until I approve each candidate.
```

Expected outcomes:

- `discard`: not useful or not safe enough to keep.
- `reference_only`: keep sanitized evidence for lookup or later re-review only.
- `defer`: wait for a license, privacy, dependency, or design decision.
- `merge_into_existing`: propose a bounded change to an existing practice or asset.
- `propose_practice`: propose a new practice candidate.
- `propose_asset`: propose a new reusable asset candidate.

`Publish after approval` is not an import outcome. It is a later `post_approval_actions` item only after you approve a specific candidate and the required canonical practice or asset exists.

`reference_only` is safe evidence, manual lookup, and future re-review only. It must not activate behavior, publish generated Skills or adapters, write runtime files, or become practice, asset, or capability-pack authority. External scripts remain inert during review.

**中文要点：** import external skills 先 review provenance、license/security、duplicates 和 candidates。`reference_only` 不会激活；external scripts 在 review 期间必须 inert。

## Discover Assets

Use this when repeated workflows should become reusable assets such as skills, subagents, automations, or extensions of existing assets.

```text
discover assets
发现可打包资产
```

Approval example:

```text
I approve asset candidate 1. Create or extend the asset, update the asset index, and publish relevant adapters.
```

**中文要点：** discover assets 用于把重复 workflow 沉淀成 reusable asset；仍然需要批准后才创建或扩展。

## Review Practices And Assets

Use `review practices` periodically to prevent duplicated, stale, weak, or missed practice activation. Use `review assets` to detect unused skills, overlapping subagents, stale automations, weak triggers, or missing adapter coverage.

```text
review practices
review assets
检查 asset rot
```

**中文要点：** 定期 review practices/assets，防止 stale、重复、弱激活或 adapter coverage 缺口。

## Consistency Checks

If something feels off, run the consistency checker manually:

```bash
python3 scripts/check_consistency.py
```

It validates indexes, practice frontmatter, asset fields, cross-references, adapter ID references, and runtime manifest integrity.

**中文要点：** 状态不对时先跑 consistency checker。

## Approval Style

Prefer approving by numbered items:

```text
I approve 1, 3, and 4.
我批准第 1、3、4 条。
```

The agent should apply only approved practices or assets and publish relevant adapters automatically.

**中文要点：** 按编号批准最清晰；agent 只应应用已批准项目。

## What You Should See

For harvest, import, discover, or review flows, the agent should show a compact review list.

```text
1. Boundaries before tools
   Action: merge into ARCH-001
   Why: strengthens the existing rule with a new heuristic
   After approval: update ARCH-001, update index, publish architecture-design adapter

2. Keep derived indexes generated
   Action: merge into GOV-001
   Why: reinforces the source-of-truth boundary for generated views
   After approval: update GOV-001, update index, publish relevant adapters
```

The agent should not force you to read the full internal workflow unless you ask.

**中文要点：** 你应该看到简洁 review list，而不是被迫阅读完整内部 workflow。
