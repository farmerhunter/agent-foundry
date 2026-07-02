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

External skills are handled as reviewed inputs. An import outcome is one of `discard`, `reference_only`, `defer`, `merge_into_existing`, `propose_practice`, or `propose_asset`. Reference-only material stays as sanitized review evidence under the selected Vault `imports/inbox/`; it is useful for lookup or later re-review, but it is not active behavior and cannot publish adapters or mutate runtime files. Publishing is a post-approval action after an approved canonical change.

外部 skills 会被当作 reviewed inputs 处理。一次 import outcome 只能是 `discard`、`reference_only`、`defer`、`merge_into_existing`、`propose_practice` 或 `propose_asset`。Reference-only material 会作为 sanitized review evidence 留在 selected Vault 的 `imports/inbox/`；它可用于查阅或后续 re-review，但不是 active behavior，也不能 publish adapters 或修改 runtime files。Publishing 是 approved canonical change 之后的 post-approval action。

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

Use `refresh practices and assets` at the start of a session, after switching machines, or when local agent rules may be stale.

在 session 开始、切换机器后，或本地 agent rules 可能 stale 时，使用 `refresh practices and assets`。

Use `check Agent Foundry status` or `python3 scripts/sync_status.py` when you only need a read-only answer to whether this machine is current.

只需要 read-only 检查这台机器是否 current 时，使用 `check Agent Foundry status` 或 `python3 scripts/sync_status.py`。

Use `harvest practices` after a session when you want to preserve reusable lessons.

想在一次 session 后沉淀可复用经验时，使用 `harvest practices`。

Use `discover assets` when repeated manual work should become a reusable skill, subagent, automation, or extension.

发现重复手工工作值得变成 reusable skill、subagent、automation 或 extension 时，使用 `discover assets`。

Use `review practices` and `review assets` periodically to prevent skill rot and asset rot.

定期使用 `review practices` 和 `review assets`，避免 skill rot 和 asset rot。

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

## Optional First-Party Starter Packs / 可选 First-Party Starter Packs

Starter packs are optional after setup and first value. Do not make a new user
choose them before the normal harvest, refresh, or status loop works.

Starter packs 是 setup 和 first value 之后的可选项。不要让新用户在正常 harvest、refresh 或 status loop 可用之前必须选择它们。

The official Core catalog currently exposes:

当前 official Core catalog 暴露：

| Pack | Normal-user use / 普通用户用途 |
| --- | --- |
| `pack.bootstrap.minimal` | Minimal bootstrap capability and prerequisite for optional starter packs. / 最小 bootstrap capability，也是 optional starter packs 的前置条件。 |
| `pack.multi-agent.optional` | GitHub issue/PR collaboration starter with durable comments, role labels, and review handoff habits. / GitHub issue/PR 协作 starter，覆盖 durable comments、role labels 和 review handoff habits。 |

Architecture-boundary, source-of-truth, Generated/Runtime downstream, and Local
Private evidence-exclusion guidance belongs in `pack.bootstrap.minimal` at the
current stage. It is not a standalone optional starter pack.

Architecture-boundary、source-of-truth、Generated/Runtime downstream 和 Local Private evidence-exclusion guidance 当前阶段属于 `pack.bootstrap.minimal`，不是 standalone optional starter pack。

Use the normal-user requests in this order when evaluating a starter pack:

评估 starter pack 时，按这个顺序使用 normal-user requests：

```text
list capability packs
recommend capability packs for my setup
preview capability pack deployment <pack-path>
apply reviewed capability pack <pack-path>
verify capability pack <pack-id>
update capability pack <pack-id-or-path>
disable capability pack <pack-id>
```

`list`, `recommend`, `preview`, `verify`, update comparison, and disable review
paths should report `writes: none`. Accepted apply paths must name the exact
selected Vault write target before writing. Generated adapters and runtime
installs remain separate downstream follow-up, never catalog authority.

`list`、`recommend`、`preview`、`verify`、update comparison 和 disable review 路径应报告 `writes: none`。Accepted apply 路径必须在写入前说明确切 selected Vault write target。Generated adapters 和 runtime installs 始终是独立 downstream follow-up，不能成为 catalog authority。

Core catalog pages carry version, manifest hash, provenance, compatibility, and
review evidence. Those details are for ordinary/complete review, not mandatory
beginner onboarding. After accepted deployment, the selected User Vault remains
canonical; Core catalog entries are discoverability metadata.

Core catalog pages 保存 version、manifest hash、provenance、compatibility 和 review evidence。这些细节属于 ordinary/complete review，不是 beginner onboarding 的必选内容。Accepted deployment 后 selected User Vault 仍然是 canonical；Core catalog entries 是 discoverability metadata。

### First-Party Pack Selection Principles / First-Party Pack 选择原则

A first-party Core capability pack should be standalone only when it has
independent user value beyond bootstrap, a cohesive reusable goal, enough mature
payload beyond a thin checklist, clear audience and lifecycle behavior, low
coupling to mandatory bootstrap/governance behavior, and public-safe sanitized
evidence.

First-party Core capability pack 只有在具备 bootstrap 之外的独立用户价值、cohesive reusable goal、超过 thin checklist 的成熟 payload、清晰 audience 和 lifecycle behavior、对 mandatory bootstrap/governance behavior 的低耦合，以及 public-safe sanitized evidence 时，才应成为 standalone pack。

After deployment, the selected User Vault remains canonical. `recommend`,
`preview`, `verify`, `update`, and `disable` surfaces are read-only unless a
later reviewed apply step is accepted. Generated, Runtime, and Local Private artifacts cannot be pack authority.

Deployment 后 selected User Vault 仍然是 canonical。`recommend`、`preview`、`verify`、`update` 和 `disable` surface 默认 read-only，除非后续 reviewed apply step 被接受。Generated、Runtime 和 Local Private artifacts 不能成为 pack authority。

Provider, frontend, private-project, raw selected Vault export, Generated, and
Runtime candidates stay deferred or rejected unless a later issue defines safe
public fixtures and review gates.

Provider、frontend、private-project、raw selected Vault export、Generated 和 Runtime candidates 需要继续 defer 或 reject，除非后续 issue 定义 safe public fixtures 和 review gates。

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

Use this when you find a useful public skill, prompt pack, article, repo, or local skill folder and want Agent Foundry to review it before any active behavior changes.

发现有价值的 public skill、prompt pack、article、repo 或本地 skill folder，并希望 Agent Foundry 在任何 active behavior change 前先 review 时，使用此流程。

Prompt:

Prompt：

```text
Evaluate this external skill for Agent Foundry: <URL or local path>. Use the import workflow, but keep the report concise. Show provenance, license/security concerns, useful candidate practices, duplicates found, and what would be imported after approval. Do not activate or publish anything until I approve each candidate.

请评估这个外部 skill 是否适合加入 Agent Foundry：<URL 或 local path>。使用 import workflow，但报告保持简洁。展示 provenance、license/security concerns、有价值的 candidate practices、duplicates found，以及批准后会导入什么。每个 candidate 未经我批准前不要 activate 或 publish。
```

Expected outcomes:

预期 outcomes：

- `discard`: not useful or not safe enough to keep.
- `reference_only`: keep sanitized evidence for lookup or later re-review only.
- `defer`: wait for a license, privacy, dependency, or design decision.
- `merge_into_existing`: propose a bounded change to an existing practice or asset.
- `propose_practice`: propose a new practice candidate.
- `propose_asset`: propose a new reusable asset candidate.

- `discard`：不值得保留，或安全性不足。
- `reference_only`：只保留 sanitized evidence，供查阅或后续 re-review。
- `defer`：等待 license、privacy、dependency 或 design decision。
- `merge_into_existing`：提出对已有 practice 或 asset 的 bounded change。
- `propose_practice`：提出新的 practice candidate。
- `propose_asset`：提出新的 reusable asset candidate。

`Publish after approval` is not an import outcome. It is a later `post_approval_actions` item only after you approve a specific candidate and the required canonical practice or asset exists.

`Publish after approval` 不是 import outcome。它只是后续 `post_approval_actions` 项，只能在你批准某个具体 candidate 且所需 canonical practice 或 asset 已存在后发生。

`reference_only` is safe evidence, manual lookup, and future re-review only. It must not activate behavior, publish generated Skills or adapters, write runtime files, or become practice, asset, or capability-pack authority.

`reference_only` 只表示 safe evidence、manual lookup 和 future re-review。它不能 activate behavior、publish generated Skills 或 adapters、写 runtime files，也不能成为 practice、asset 或 capability-pack authority。

External scripts remain inert during review. The agent should not execute scripts, install dependencies, fetch packages, run `chmod`, write generated adapters, mutate runtime files, or change canonical Vault records while evaluating the source.

Review 期间 external scripts 必须保持 inert。Agent 在评估 source 时不应 execute scripts、install dependencies、fetch packages、运行 `chmod`、写 generated adapters、修改 runtime files，或改变 canonical Vault records。

Approval example:

批准示例：

```text
I approve candidate 2 as propose_practice. Create the approved canonical candidate, update the index if needed, and then publish adapters only if the approved post_approval_actions say to publish.

我批准第 2 个 candidate，outcome 为 propose_practice。请创建已批准的 canonical candidate，必要时更新 index；只有 approved post_approval_actions 要求 publish 时，才发布 adapters。
```

Reference-only example:

Reference-only 示例：

```text
Keep candidate 1 as `reference_only`. Do not create an active practice or publish adapters.

把第 1 个 candidate 保留为 `reference_only`。不要创建 active practice，也不要 publish adapters。
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
