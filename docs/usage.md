# Usage Guide / 使用指南

This guide is for day-to-day Agent Foundry use. You do not need to remember the internal workflows.

这份指南面向日常使用 Agent Foundry 的场景。你不需要记住内部 workflow 细节。

## How It Works / 工作方式

Agent Foundry is a local-first system with separate Core, selected User Vault, generated output, and runtime layers.

Agent Foundry 是 local-first 系统，并区分 Core、selected User Vault、generated output 和 runtime layers。

```text
work session or external skill
  -> harvest / import / discover
  -> human approval
  -> canonical practice or asset in selected User Vault
  -> publish adapters from Core plus selected Vault
  -> install to local runtimes
  -> use short commands to invoke assets
```

Core contains public workflows, schemas, scripts, templates, docs, adapter profiles, runtime templates, and validation tooling.

Core 保存 public workflows、schemas、scripts、templates、docs、adapter profiles、runtime templates 和 validation tooling。

The selected User Vault contains canonical `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregates.

selected User Vault 保存 canonical `practices/`、`assets/`、`indexes/`、`imports/` 和 shared sanitized usage aggregates。

Installed files under `~/.codex`, `~/.claude`, `~/.hermes`, and `~/.trae-cn` are downstream runtime copies.

`~/.codex`、`~/.claude`、`~/.hermes` 和 `~/.trae-cn` 下的已安装文件是下游 runtime copies。

## Core Rule / 核心规则

For daily use, prefer the short commands in `docs/commands.md`, such as `harvest practices`, `refresh practices and assets`, or `check Agent Foundry status`.

日常使用时，优先使用 `docs/commands.md` 中的短命令，例如 `harvest practices`、`refresh practices and assets` 或 `check Agent Foundry status`。

The agent may discover, draft, and recommend practices or assets. You approve each meaningful new item or change before it becomes active.

Agent 可以发现、起草并推荐 practices 或 assets。每个重要新增项或变更都需要你批准后才能 active。

After approval, the agent should apply the approved item, update the canonical Vault records, update indexes, publish relevant adapters, and report changed files.

批准后，agent 应应用已批准项目，更新 canonical Vault records，更新 indexes，发布相关 adapters，并汇报 changed files。

## First-Time Setup / 首次设置

On a new machine, use `docs/deployment.md` for the full split Core/Vault install flow.

新机器上，使用 `docs/deployment.md` 中完整的 Core/Vault 分离安装流程。

Short version:

简版流程：

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

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, runtime directories, or ChatGPT project files as canonical truth.

不要把另一台机器的 `runtime/local/`、`~/.agent-foundry/config.yaml`、runtime directories 或 ChatGPT project files 当作 canonical truth 复制。

Recreate local state from Core plus the selected Vault, then verify with `sync_status.py`.

应从 Core 加 selected Vault 重建本机状态，再用 `sync_status.py` 验证。

## Daily Workflow / 日常流程

Daily operation should start from what you want done, not from the script that might implement it. Ask the agent in natural language, then review the visible outcome before approving durable changes.

日常操作应从你的意图开始，而不是从可能实现它的 script 开始。用自然语言告诉 agent 目标，然后先 review 可见结果，再批准 durable changes。

Use this ordinary loop:

普通日常 loop：

1. Start with `check Agent Foundry status` when you need a read-only answer about Core, selected Vault, generated output, runtime receipts, or manual targets.
2. Use `refresh practices and assets` at the start of a session, after switching machines, or when local agent rules may be stale.
3. Use `harvest practices` after real work when you want to preserve reusable lessons.
4. Review the numbered candidate list. Approve only the items you want promoted or merged.
5. After approval, expect selected Vault records, indexes, and relevant generated adapters to change; runtime writes still follow the reviewed status or install path.
6. Run `check Agent Foundry status` again when you need the next safe action or troubleshooting boundary.

1. 需要 read-only 了解 Core、selected Vault、generated output、runtime receipts 或 manual targets 状态时，先用 `check Agent Foundry status`。
2. 在 session 开始、切换机器后，或本地 agent rules 可能 stale 时，使用 `refresh practices and assets`。
3. 完成真实工作并想沉淀可复用经验时，使用 `harvest practices`。
4. Review 编号 candidate list。只批准你想 promote 或 merge 的项目。
5. 批准后，预期 selected Vault records、indexes 和相关 generated adapters 会变化；runtime writes 仍走 reviewed status 或 install path。
6. 需要 next safe action 或排查边界时，再运行 `check Agent Foundry status`。

Use `discover assets` when repeated manual work should become a reusable skill, subagent, automation, or extension.

发现重复手工工作值得变成 reusable skill、subagent、automation 或 extension 时，使用 `discover assets`。

Use `review practices` and `review assets` periodically to prevent skill rot and asset rot.

定期使用 `review practices` 和 `review assets`，避免 skill rot 和 asset rot。

For normal capability-pack use, stay with the Skill-facing requests in [Capability Pack Safety](#capability-pack-safety--capability-pack-安全规则). Do not run candidate discovery, release review, split, merge, export, or transfer workflows unless you explicitly want a power-user maintenance review packet.

普通 capability-pack 使用请留在 [Capability Pack Safety](#capability-pack-safety--capability-pack-安全规则) 中的 Skill-facing requests。除非你明确需要 power-user maintenance review packet，否则不要运行 candidate discovery、release review、split、merge、export 或 transfer workflows。

Raw CLI commands are secondary. Use them when the agent asks for a deterministic verification command, when you are debugging, or when [Deployment](deployment.md) tells you to operate runtime/install state directly.

Raw CLI commands 是 secondary。只有当 agent 要求 deterministic verification command、你正在 debug，或 [Deployment](deployment.md) 要求你直接处理 runtime/install state 时再使用。

## Refresh Practices And Assets / 刷新 Practices 和 Assets

Command:

命令：

```text
refresh practices and assets
刷新practices和assets
```

Expected behavior:

预期行为：

- Check local state and avoid losing real work.
- 检查本地状态，避免丢失真实工作。
- Pull remote git updates when appropriate.
- 在合适时 pull remote git updates。
- Regenerate adapters if canonical practices or assets changed.
- 如果 canonical practices 或 assets 发生变化，重新生成 adapters。
- Dry-run or install to enabled local runtimes through the reviewed path.
- 通过 reviewed path 对 enabled local runtimes 做 dry-run 或 install。
- Report current commit, unpushed work, generated output state, runtime receipts, and updated runtimes.
- 汇报 current commit、未 push 工作、generated output state、runtime receipts 和已更新 runtimes。

If refresh reports generated output as stale, the normal next step is adapter publish through the reviewed path. If it reports runtime drift, read the status output first; runtime install or repair is a separate step, not an implicit side effect of harvest.

如果 refresh 报告 generated output stale，普通 next step 是通过 reviewed path publish adapters。如果报告 runtime drift，先阅读 status output；runtime install 或 repair 是单独步骤，不是 harvest 的隐式副作用。

## Status And Drift / Status 和 Drift

Run status before applying runtime writes, after long idle periods, after switching machines, or when a rule appears not to affect an agent.

在 apply runtime writes 前、长时间 idle 后、切换机器后，或某条 rule 看起来没有影响 agent 时，运行 status。

```bash
python3 scripts/sync_status.py
```

`sync_status.py` separates Core repo progress, selected Vault state, generated output, runtime receipt state, manual targets, and human-gated runtime writes.

`sync_status.py` 会分开报告 Core repo progress、selected Vault state、generated output、runtime receipt state、manual targets 和 human-gated runtime writes。

If generated output is missing or stale, publish adapters first. If runtime receipt is missing or drifted, review generated output, run install dry-run, read status, then apply only when the runtime write is expected.

如果 generated output missing 或 stale，先 publish adapters。如果 runtime receipt missing 或 drifted，先 review generated output，运行 install dry-run，读取 status，最后只有 runtime write 符合预期时才 apply。

Do not repair runtime drift by editing Vault records.

不要通过编辑 Vault records 来修复 runtime drift。

For runtime target changes, Trae setup, cross-machine restore, or manual target repair, escalate to [Deployment](deployment.md). For complete architecture and governance references, use [System Design](system-design.md) and [Lifecycle Compatibility](lifecycle-compatibility.md).

需要 runtime target changes、Trae setup、cross-machine restore 或 manual target repair 时，升级查看 [Deployment](deployment.md)。需要完整 architecture 和 governance reference 时，查看 [System Design](system-design.md) 与 [Lifecycle Compatibility](lifecycle-compatibility.md)。

## Capability Pack Safety / Capability Pack 安全规则

Capability packs are reviewed bundles that can add or change practices, assets, generated output, and runtime-facing behavior.

Capability packs 是经过 review 的 bundles，可能新增或改变 practices、assets、generated output 和 runtime-facing behavior。

For normal users, capability-pack consumption is Skill-first. The agent should
translate your intent into the reviewed planning, apply, lifecycle, update, or
status workflow. Raw scripts remain implementation details or advanced/debug
commands.

对 normal user 来说，capability-pack consumption 是 Skill-first。Agent 应把你的意图转换成 reviewed planning、apply、lifecycle、update 或 status workflow。Raw scripts 只作为 implementation details 或 advanced/debug commands。

Power-user or transfer/debug requests remain available outside the normal-user
consumption path: `discover capability packs`, `review capability pack lifecycle <pack-id>`,
and `preview capability pack transfer <pack-path>`.
These keep raw scripts behind implementation details and advanced/debug
workflow surfaces.

Use these normal-user requests for consumption flows:

正常工作优先使用 Skill-first 请求：

```text
list capability packs
recommend capability packs for my setup
preview capability pack deployment <pack-path>
apply reviewed capability pack <pack-path>
verify capability pack <pack-id>
update capability pack <pack-id-or-path>
disable capability pack <pack-id>
```

The user-visible report for every normal-user pack request should include:

- pack identity: id, title, version, source, and whether the pack is reviewed;
- display status: available, recommended, compatible, incompatible, deployed,
  update available, blocked, or not installed;
- layers inspected: Core, selected Vault, generated output, runtime receipts,
  manual targets, or Local Private exclusions;
- changed layers, if any;
- `writes: none` for list, recommend, preview, verify, update comparison,
  disable review, and transfer preview paths;
- exact selected Vault write target for accepted apply paths;
- next safe action;
- rollback or defer guidance.

每个 normal-user pack 请求的用户可见报告都应包含：

- pack identity：id、title、version、source，以及是否 reviewed；
- display status：available、recommended、compatible、incompatible、deployed、update available、blocked 或 not installed；
- inspected layers：Core、selected Vault、generated output、runtime receipts、manual targets 或 Local Private exclusions；
- changed layers，如果有；
- list、recommend、preview、verify、update comparison、disable review 和 transfer preview 路径必须显示 `writes: none`；accepted apply 路径必须显示确切的 selected Vault write target；
- next safe action；
- rollback 或 defer guidance。

State names in normal-user output are display, comparison/report, transfer, or
runtime/generated statuses unless the report explicitly names a canonical
`lifecycle_status`. Do not write `recommended`, `compatible`, `merge_required`,
`drifted`, `generated_missing`, or similar transient terms as lifecycle values.

Normal-user flows do not create packs, run candidate discovery, publish exports,
or make maintainer release decisions. Use power-user workflows only when you
explicitly ask to scan, propose, assemble, release, export, split, or merge
capability packs.

Normal-user output 中的 state names 默认是 display、comparison/report、transfer 或 runtime/generated statuses，除非报告明确写出 canonical `lifecycle_status`。不要把 `recommended`、`compatible`、`merge_required`、`drifted`、`generated_missing` 等 transient terms 写成 lifecycle values。

Normal-user flows 不创建 packs、不运行 candidate discovery、不发布 exports，也不做 maintainer release decisions。只有当你明确要求 scan、propose、assemble、release、export、split 或 merge capability packs 时，才使用 power-user workflows。

## Power-User Capability Pack Maintenance / Power-User Capability Pack 维护

Power-user capability-pack workflows are advanced maintenance-level workflows.
They are available when you explicitly ask to scan, propose, evaluate,
assemble, release, review exportability, deprecate, split, or merge capability
packs. They do not create strict permissions or hidden access control; the
distinction is about risk, review depth, and output shape.

Power-user capability-pack workflows 是 advanced maintenance-level workflows。只有当你明确要求 scan、propose、evaluate、assemble、release、review exportability、deprecate、split 或 merge capability packs 时才使用。这里不创建 strict permissions 或 hidden access control；区别在于 risk、review depth 和 output shape。

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

Warning: these workflows may create taxonomy, versioning, distribution,
privacy, or compatibility decisions for review. They must not create, activate,
export, publish, or deploy a pack without a later reviewed step.

警告：这些 workflows 可能生成需要 review 的 taxonomy、versioning、distribution、privacy 或 compatibility decisions。未经后续 reviewed step，不得 create、activate、export、publish 或 deploy pack。

Power-user outputs are review packets by default, not active artifacts. A review
packet should include:

- requested maintenance flow and pack or candidate identity;
- evidence sources and authority layer;
- proposed boundary, draft membership, version or taxonomy decision;
- privacy, distribution, compatibility, generated, and runtime impact;
- candidate discovery outcome, transfer/import state, comparison/report
  classification, or canonical `lifecycle_status`, clearly labeled by
  namespace;
- required Reviewer, Architect, or Human gate;
- `writes: none`;
- next safe action and rollback or defer guidance.

Power-user output 默认是 review packet，不是 active artifact。Review packet 应包含：

- requested maintenance flow 以及 pack 或 candidate identity；
- evidence sources 和 authority layer；
- proposed boundary、draft membership、version 或 taxonomy decision；
- privacy、distribution、compatibility、generated 和 runtime impact；
- candidate discovery outcome、transfer/import state、comparison/report classification 或 canonical `lifecycle_status`，并清楚标出 namespace；
- 必需的 Reviewer、Architect 或 Human gate；
- `writes: none`；
- next safe action 和 rollback 或 defer guidance。

Candidate outcomes, split/merge outcomes, exportability findings, and release
classifications are review/report values unless a later reviewed lifecycle step
persists a canonical pack `lifecycle_status`. Do not treat a review packet as an
activation, export, publication, or runtime deploy authorization.

Candidate outcomes、split/merge outcomes、exportability findings 和 release classifications 默认是 review/report values，除非后续 reviewed lifecycle step 持久化 canonical pack `lifecycle_status`。不要把 review packet 当作 activation、export、publication 或 runtime deploy authorization。

Candidate discovery is a power-user diagnostic review-list flow. It does not run automatically during normal-user pack consumption, and it does not create candidate files, manifests, selected Vault records, exports, generated output, or runtime changes by default. A later reviewed power-user step must accept the review list before draft assembly or durable candidate-record work begins.

Candidate discovery 是 power-user diagnostic review-list flow。它不会在 normal-user pack consumption 中自动运行，也不会默认创建 candidate files、manifests、selected Vault records、exports、generated output 或 runtime changes。必须先由后续 reviewed power-user step 接受 review list，才能开始 draft assembly 或 durable candidate-record work。

Use plan commands before apply commands when operating manually or debugging:

手动操作或 debug 时，先使用 plan commands，再使用 apply commands：

```bash
python3 scripts/plan_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/apply_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/manage_capability_pack_lifecycle.py --vault-root <vault-root> --pack-id <pack-id> --action disable
```

The pack path is fail-closed. If metadata is malformed, duplicated, ambiguous, has a same-version hash mismatch, points outside allowed paths, or would overwrite local edits without a reviewed update flow, the system should refuse before writing Vault or runtime files.

Pack path 是 fail-closed 的。如果 metadata malformed、duplicated、ambiguous、出现 same-version hash mismatch、路径越界，或会在没有 reviewed update flow 的情况下覆盖本地改动，系统应在写 Vault 或 runtime files 前拒绝。

Runtime files still need the normal publish, dry-run install, status, and reviewed apply path. ChatGPT remains manual import.

Runtime files 仍然需要走正常的 publish、dry-run install、status 和 reviewed apply path。ChatGPT 仍然是 manual import。

## Harvest Practices / 沉淀 Practices

Use this after coding, design, debugging, or coordination work when reusable lessons should become durable practices.

在 coding、design、debugging 或 coordination 工作后，如果有可复用经验需要变成 durable practices，使用此流程。

Command:

命令：

```text
harvest practices
做一次 harvest practice
```

Long prompt:

较完整的 prompt：

```text
Harvest reusable practices from this session using Agent Foundry. Keep the details hidden and present a concise review list. For each new or changed practice, show the title, why it matters, whether it merges into an existing rule or creates a new one, and what adapters would be updated after approval. Wait for my approval per practice before applying.

用 Agent Foundry 从这次 session 中提炼可复用实践。隐藏内部细节，只给我一个简洁的 review list。对每条新增或变更的 practice，说明标题、为什么重要、会合并到已有规则还是创建新规则，以及批准后会更新哪些 adapters。每条 practice 等我批准后再应用。
```

Approval example:

批准示例：

```text
I approve practice 1 and 3. Apply them, promote them to active, update the index, and publish the relevant adapters.

我批准第 1 和第 3 条。请应用它们，提升为 active，更新 index，并发布相关 adapters。
```

## Import External Skills / 导入外部 Skills

Use this when you find a useful public skill, prompt pack, article, repo, or local skill folder.

发现有价值的 public skill、prompt pack、article、repo 或本地 skill folder 时，使用此流程。

Prompt:

Prompt：

```text
Evaluate this external skill for Agent Foundry: <URL or local path>. Use the import workflow, but keep the report concise. Show provenance, license/security concerns, useful candidate practices, duplicates found, and what would be imported after approval. Do not activate or publish anything until I approve each candidate.

请评估这个外部 skill 是否适合加入 Agent Foundry：<URL 或 local path>。使用 import workflow，但报告保持简洁。展示 provenance、license/security concerns、有价值的 candidate practices、duplicates found，以及批准后会导入什么。每个 candidate 未经我批准前不要 activate 或 publish。
```

Approval example:

批准示例：

```text
I approve candidate 2. Import it, promote it to active, update the index, and publish the relevant adapters.

我批准第 2 个 candidate。请导入它，提升为 active，更新 index，并发布相关 adapters。
```

## Discover Assets / 发现 Assets

Use this when repeated workflows should become reusable assets such as skills, subagents, automations, or extensions of existing assets.

当重复 workflows 应沉淀为 skills、subagents、automations 或已有 assets 的 extensions 时，使用此流程。

Command:

命令：

```text
discover assets
发现可打包资产
```

Approval example:

批准示例：

```text
I approve asset candidate 1. Create or extend the asset, update the asset index, and publish relevant adapters.

我批准第 1 个 asset candidate。请创建或扩展该 asset，更新 asset index，并发布相关 adapters。
```

## Review Practices / Review Practices

Use this periodically to prevent duplicated, stale, weak, or missed practice activation.

定期使用此流程，避免 duplicated、stale、weak 或 missed practice activation。

Prompt:

Prompt：

```text
Review Agent Foundry for skill rot. Run the practice review workflow, summarize the recommendations, and give me an approval list. Look for duplicates, stale entries, weak or missed activation, adapter drift, and proposed items that need decisions. Do not archive, supersede, change activation tiers, or publish anything without my approval.

请 review Agent Foundry，检查 skill rot。执行 practice review workflow，总结 recommendations，并给我一个可批准的清单。重点看 duplicates、stale entries、weak or missed activation、adapter drift，以及需要决策的 proposed items。未经我批准，不要 archive、supersede、修改 activation tiers 或 publish。
```

## Review Assets / Review Assets

Use this periodically to prevent unused skills, overlapping subagents, stale automations, weak triggers, or missing adapter coverage.

定期使用此流程，避免 unused skills、overlapping subagents、stale automations、weak triggers 或 missing adapter coverage。

Command:

命令：

```text
review assets
检查 asset rot
```

## Consistency Checks / Consistency Checks

If something feels off, run the consistency checker manually:

如果感觉状态不对，可以手动运行 consistency checker：

```bash
python3 scripts/check_consistency.py
```

It validates indexes, practice frontmatter, asset fields, cross-references, adapter ID references, and runtime manifest integrity.

它会验证 indexes、practice frontmatter、asset fields、cross-references、adapter ID references 和 runtime manifest integrity。

## Approval Style / 批准方式

Prefer approving by numbered items:

优先按编号批准：

```text
I approve 1, 3, and 4.

我批准第 1、3、4 条。
```

The agent should apply only approved practices or assets and publish relevant adapters automatically.

Agent 应只应用已批准的 practices 或 assets，并自动发布相关 adapters。

## What You Should See / 你应该看到什么

For harvest, import, discover, or review flows, the agent should show a compact review list.

对于 harvest、import、discover 或 review flows，agent 应展示简洁的 review list。

Example:

示例：

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

除非你要求，agent 不应强迫你阅读完整内部 workflow。
