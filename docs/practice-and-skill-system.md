# Practices 与 Skills 用户指南

中文（默认） | [English](practice-and-skill-system.en.md)

Agent Foundry 帮助 agent 复用可靠的工程判断，而不必在每次任务开始时读完整本流程手册。
Practice（实践规则）保存可复用的判断及其理由；skill（技能）帮助 agent 找到并执行
适合当前任务的工作方式。它们都不能替代你的指令、项目规则或实际执行工具的权限。

本指南从日常场景出发，解释如何使用这套系统，以及为什么这样设计。
你不必先记住 practice ID，也不必一次采用全部能力。

**交付状态：** 本文是 #574 的候选用户指南。本次协作规则重构及按需加载方式仍处于
提议阶段；只有获批的 canonical 内容、生成结果和选定安装目标经过实际核验后，
才能宣告相应交付完成。既有 onboarding、分发和 runtime 能力仍受各自文档中的
限制约束。本文不代表已启用新规则，也不是发布公告。

## 从你想做的事情开始

| 你的目标 | 可以这样提出请求 | 应得到什么 | 接着阅读 |
| --- | --- | --- | --- |
| 在普通任务中使用工程指导 | “检查这个 PR 是否引入回归。” | 相关审查规则、问题与证据；不会自动创建新角色或 scheduler。 | [完成一次普通 Work](#ordinary-work-from-request-to-result) |
| 在项目中采用有边界的多 agent 协作 | “开启多agent协作：先检查这个项目的准备状态。” | 针对该项目的 preflight，以及可信的计划或暂停原因；不会自动启用。 | [首次使用](#prepare-a-project-for-bounded-collaboration) |
| 将明确的任务交给其他角色 | “把这项范围明确的审查交给现有 Reviewer。” | 明确的接收者、范围、证据和实际派发回执；不可用时如实说明。 | [按需使用角色支持](#use-role-support-only-when-it-helps) |
| 复用一次工作的经验 | “Harvest 这个 issue 中的经验。” | 去重后的内容审阅清单，而不是立即生效的新政策。 | [沉淀经验](#turn-experience-into-maintained-guidance) |
| 检查更新或恢复状态 | “检查已安装 skills 是否与当前选定的 Vault 一致。” | 只读比较，以及明确的拟更新或恢复方案。 | [恢复与更新](#recover-without-inventing-state) |

### 使用基础能力，不必采用整套系统

在普通仓库中使用 skill，不要求创建 SQLite ledger、启动常驻角色、导入可选 pack，
也不要求改变分支策略。例如，架构审查需要了解方案边界和相关代码，不需要先建一个
项目 scheduler。与工程协作无关的翻译，也不应该仅因发生在编程工具中就触发协作流程。

请说明你想要的结果和重要限制。“修复错误的空状态提示，保持原有行为并补充回归测试”
比“遵循所有可用实践”更有帮助。Agent 应选择能促进交付的规则，在受影响的操作开始前
指出缺失的权限，同时继续完成不受影响、已经获准的工作。

<a id="prepare-a-project-for-bounded-collaboration"></a>

### 为项目准备有边界的多 agent 协作

多 agent 协作是一类分工能力；bounded collaboration 是采用这种能力后的运行方式：
每个 Work 都有目标、负责人、范围、验证证据和最终交接。采用是逐项目、面向未来的，
不要求先迁移所有历史 issue 或清理所有旧 worktree。

首次准备从检查项目绑定和真实协调状态开始。仓库文档写着“使用两个角色”，并不能
证明原生角色或 scheduler 已经存在。如果当前版本提供由实际责任组件组合的 onboarding
入口，其公开 preflight 是只读检查。归属缺失或不明确时，应给出 HOLD（暂停）
及下一步，而不能编造成功回执。

通常的常驻原生角色是 Coordinator 和 Durable Architect。创建或复用它们是需要
单独限定范围的操作，不是阅读本指南的自动结果。初始化成功需要相应责任组件的
状态回读；只有计划不足以证明已经就绪。当前 Core 版本支持的确切接口见
[onboarding workflow](../workflows/onboard-bounded-collaboration.md)。

如果 preflight 返回 `owner_unavailable`，不要借用其他项目的 ledger、试探性创建
角色，或反复重跑同一检查。应先确定缺失的责任组件或前置条件，再走获准的准备路径。
这不妨碍普通的 GitHub issue 和 PR 工作。同样，安装 skill 不等于完成项目 onboarding，
本机验证也不能证明跨设备交接成功。

<a id="use-role-support-only-when-it-helps"></a>

### 只在有帮助时使用角色支持

“审查这段代码”和“派发一位 Reviewer”不是同一请求。前者要求交付结果，后者还要求
执行协作操作。Agent Collaboration 负责交付生命周期和持久交接；只有明确请求，
或已接受的 Work 要求时，Role Automation Planner 才负责范围受控的角色派发或自动化计划。

一次小范围交接只需携带目标、权限、目标 revision、相关证据、预期回复和下一负责人。
不必复制整个对话，也不必重复加载两本大幅重叠的手册。有合适的现有角色就优先复用，
并说明实际使用了哪种派发机制。在聊天中打印一段提示词，不等于已经派发；
成功发送任务，也不等于任务已经完成。

周期性自动化必须来自周期性需求。一次审查请求不应该创建 heartbeat 或定时任务。
自动化只是帮助交付，不会增加权限、取代 issue，也不能让已暂停的操作持续重试。
缺少必要的派发能力时，可以提供明确标注的可移植提示词作为替代，
但不能把这种替代说成已执行的原生操作。

<a id="turn-experience-into-maintained-guidance"></a>

### 将经验变成可维护的指导

有价值的经验首先是证据，不是新规则。Harvester 确定证据范围，区分项目特定决定与
可复用判断，搜索现有 practices，并尽量合并到已有条目。外部 skills 也是待审阅材料，
不是可以直接信任并执行的指令。

审阅清单应解释实际内容变化、受影响的 canonical 记录、生命周期状态、adapter 影响，
以及可能涉及的安装目标。实质变化必须获得相应批准后才能成为 active。
认可一个方向，不等于批准尚未展示、以后将约束 agent 行为的规则。
精确清单一旦获批，就应完成其中已披露的处理链，不为未改变的机械步骤重复询问。
只有范围、风险、内容或目标发生实质变化时，才需要返回决策。

不要把原始 prompts、对话记录、credentials 或私密 payload 写进可复用规则。
简洁、非敏感的使用证据可以帮助维护；凑足 telemetry 样本数不是交付已接受改进的前提。
具体流程见 [harvest practices](../workflows/harvest-practices.md)。

## 理解从源内容到实际使用的关系

关键是区分三件事：规则在哪里维护、在哪里被打包，以及谁真正有权执行操作。

| 层次 | 负责什么 | 不能据此认定什么 |
| --- | --- | --- |
| Core | 共享 workflows、schemas、发布与安装工具、profiles 和文档。 | 不能证明某个 Vault 或 runtime 已是最新状态。 |
| 当前选定的 User Vault | Canonical practices、assets、索引和已批准的生命周期状态。 | 不能证明下游副本已发布或安装。 |
| Practice | 可复用的判断、理由、适用条件和边界。 | 不会授予它所描述的全部操作权限。 |
| Asset / skill | 面向用户的工作方式、职责、触发条件和规则引用。 | 不是第二套政策源，也不是原生 runtime 能力。 |
| Capability pack | 经审阅的分发组合或快照。 | 不是实时上游权威；不意味着自动批准导入或升级成功。 |
| Generated adapter | 将已接受源内容转换为目标工具格式的结果。 | 不能证明用户的工具正在读取这些文件。 |
| 已安装文件 | 选定 runtime 环境中的受管副本。 | 不等于项目 onboarding、执行授权或跨设备就绪。 |
| 实际执行责任方（execution owners） | 某次操作涉及的真实仓库、ledger、scheduler、工具和用户权限。 | 不能从角色名称、摘要或复制的回执推导权限。 |

处理 canonical 内容前，先确认当前选定的 Vault。不要靠直接编辑生成的 skill 来修正规则：
下次发布可能覆盖它，其他 runtime 的副本也仍然不同。应修改经过审阅的源内容，
重新生成，再核验选定的安装副本。如果 runtime 中存在用户有意保留的本地修改，
先保护并分类，再决定纳入还是替换。

Pack 是可选分发单元，不是所有重构的组织原则。通用基础与可选多 agent 内容可以分开，
不必把 Core 再定义成第三个知识 pack。现有用户的改进不必等待 pack 导入器或升级能力。
当前 pack 预览和应用限制见[使用说明](usage.md#capability-pack-safety)；
旧导出包不能自动视为等同于今天的 canonical Vault。

<a id="ordinary-work-from-request-to-result"></a>

## 完成一次普通 Work：从请求到结果

Work 是一次有边界的交付，不一定对应新 issue、新 branch、新角色或新对话。
其作用是把结果和责任说清楚，让工作能够完成并验证。普通任务用一份简短约定就可以明确：

- 交付结果，以及真正重要的对外行为；
- 唯一负责人、允许修改的范围和明确排除项；
- 适合当前仓库的 branch / workspace 策略；
- 有代表性的验证、完成证据和下一负责人；
- 如有实际剩余风险或前置条件，明确列出。

只有具体风险需要时才增加细节。数据库迁移需要说明失败与恢复方式，措辞修正则不需要
同等规格。不要让普通补丁等待穷尽式文件盘点、完整角色链，或对每一种假设故障作正式决定。

从当前指令和持久的 issue / PR 状态开始，实施并验证已授权的改动，再交接与候选 revision
对应的证据。对于低风险、范围明确的改动，一位独立 Reviewer 可以完成聚焦检查。
只有另一个 Tester 能观察不同边界，例如真实持久化、浏览器、第二台设备或真实外部环境时，
才增加该角色。仅仅换一个角色名不会产生独立证据。

有效的审查问题应说明：防止什么具体错误、后果是什么、对应哪个要求或 Hard Boundary，
以及最低成本的充分验证或修复方式。命名偏好、无关清理和假设性加固不会自动成为 blocker。
反过来，流程精简也不能把数据丢失、未授权外部修改、隐私或安全问题、credentials 风险、
伪造权限等不可降低的安全底线，当成可忽略的小问题。

在尚未发布的准备阶段，可以修正语法、import 或测试发现问题，前提是行为、依赖、断言、
范围和证据含义都不变。不能靠 skip 隐藏测试、削弱断言或换一个环境来掩盖失败。
改变合同或行为属于实质修复，需要合并审查。第二次实质性失败后，应重新确定目标、
范围和方案基线（rebaseline），而不是再叠加一份补丁合同。
这条规则不追溯授权 operational repair，也不会把真实环境修改变成“机械修正”。

完成意味着：在约定的对象和环境上，证明确实交付了约定结果。单元测试通过不证明
runtime 已安装；PR 已创建不等于已合并；合并也不等于 release。
最终交接应说明改了什么、如何验证、还剩什么、谁能进行下一步。
详细交接和审查约定见[协作工作流](multi-agent-collaboration.md)，不必在每次请求中复制全文。

## 角色与归属：不为分工制造多余线程

Coordinator 负责保持目标、依赖和交接一致；Architect 负责实质性架构选择和未解决的
语义边界；Implementer 产出改动；Reviewer 独立评估；Tester 提供另外确有必要的验证。
Human 决策针对真实产品选择和受保护操作，而不是 agent 的每次纠错。
Harvester 则从已经发生的工作证据中提出可复用经验。

常驻角色维持连续性，Work 级角色负责集中执行。Onboarding 中的 Coordinator 加
Durable Architect 预算不是全局“最多两个线程”的限制。具体 Work 可以需要其他角色；
同样，提到“review”也不意味着必须创建常驻 Reviewer。
在尊重合同的前提下，选择足以提供所需证据的最简协作方式。

RoleHub 是可选的逻辑只读目录或入口，不是原生线程、scheduler、controller、
telemetry store，也不是就绪前提。一个叫 RoleHub 的对话不会因名称而获得权限。
角色对话的延续与刷新，也不同于下一步操作授权：接任者需要核查最新持久依据，
不能只依赖“全部已获批”的摘要。

## Workspace 与 Epic 策略

隔离是为了保护明确的写入者和改动，而不是为了多建 worktree。
只读审查可以检查当前 checkout；仓库规则允许且没有重叠 Epic 工作时，
串行低风险任务可以使用 task branch。可写并发工作、涉及受保护边界的工作以及
Epic 子任务通常需要隔离的任务 workspace。每个可写 Work 只有一位负责人和一个写入绑定。

多 agent 功能的子分支通常先进入非 main 的 Epic integration branch。
该 integration checkout 用于协调、集成和回读，不供多个任务竞争编辑。
当前 `main` 和较旧的功能集成分支可能包含不同的已接受能力；
必须明确选择一致的 base，不能悄悄用一个替代另一个。

在采用 bounded collaboration 的项目中，adaptive isolation 面向未来的新 Work；
它不是清理所有历史分支的命令，也不应强加给无关仓库。
中断后先检查真实路径、branch、HEAD、未提交状态和负责人。
旧对话标题不等于当前写入权。

结束时说明 workspace 是保留、可回收、暂停还是隔离待查。
清理是单独的破坏性操作：移除精确获准的目标前，要检查 tracked、untracked、
相关 ignored 内容、归属和恢复方式。无法确定的工作应保留。
不要使用 force、通配符删除或猜测性重建，只为让盘点结果显得整洁。

## 权限与真正需要 Human 的决定

操作前，从最新适用的用户指令、仓库政策和 Work 合同确认权限。
Skill 解释流程，但不会扩大权限。明确的 HOLD 仍然有效。
规则冲突时，暂停受影响的步骤并解决冲突；可以继续不受影响、已经获准的工作。

在已授权的仓库工作流内，验证后的 commit、task-branch push 和 PR 更新属于正常执行步骤。
合同可以委托经验证的 child PR 合入非 main 集成分支，或关闭已接受的 child issue。
这种委托不等于对所有仓库、最终 main 集成或 Epic closure 的通用授权。

对于破坏性操作、迁移、隐私或安全变化、credentials、外部影响、真实环境或 runtime
修改，以及合同明确要求批准的最终集成或 release，应保留相应边界。
不要因为审查发现还有工作，就请 Human 调试测试失败或决定每一处措辞改进。
需要决策时，用人能理解的方式说清：改什么、为什么重要、检查了什么、剩余风险是什么、
批准后具体允许什么。

对于 canonical 自更新，启用前应展示精确审阅清单及安装影响。
选定的个人 Vault 可以有“内容清单已批准且检查通过后自动最终合并”的政策；
那是该 Vault 的本地政策，不能直接复制成公共指导，也不能套用到 Core `main`。

## 按需加载：在合适的时候读取足够的指导

发现 skill 和选择引用解决不同问题。Discovery metadata 帮助宿主或模型选择 skill；
被选中的 SKILL 正文再说明当前任务需要哪些指导。
简短描述仍应完整说明适用范围和重要排除项。如果描述在排除项之前被截断，
可能触发一串本不需要的 skills。

#574 的候选 publisher 将采用路由的 assets 标记为 `intent`，未改变的 assets 标记为
`legacy`。这些标签展示指令选择路径，不是 runtime 开关，也不是新 scheduler。
拟议的协作路径使用精简入口和语义完整的条件式引用。
普通交付不应读取清理、onboarding、自动化或迁移流程，除非这些操作确实属于当前范围；
小范围派发也不应再读一遍全部生命周期规则。详细理由仍可查阅，不是为了减少数字而删掉。

引用可访问，不等于必须无条件阅读。确定某条引用适用后，应充分阅读完整规则和必要上下文，
包括适用的例外和恢复要求，确保正确执行。Related-practice 链接用于导航，
不是自动递归加载整套库的依据。必要的安全规则必须在其保护的操作发生前可获得并被应用。

路由不确定时，必须明确显示 fallback：说明歧义，查阅相关既有指导，
不能默默宣称已精确识别 intent、加载全部 skills 或扩大权限。
未修改 assets 的兼容路径也应明确。本次源内容与生成行为，在候选检查和安装回读完成前，
仍应标为提议状态。

比较加载量时，应针对同一个任务统计修改前后的 discovery description、入口正文、
必需的直接和传递引用，以及交接中的重复内容。既报告总暴露量，也报告去重后的内容量，
避免把重复文件转移位置冒充精简。静态字节数描述的是指令体积，不是模型 token 消耗、
延迟或质量；提示词也不能保证宿主如何加载，或清除已经进入对话历史的上下文。

[Agent Skills specification](https://agentskills.io/specification) 区分发现用的 metadata、
激活后的正文和按需资源。Agent Foundry 采用这种区分，但不因此引入强制 loader 服务，
也不把文档当成 runtime 的强制执行机制。

<a id="recover-without-inventing-state"></a>

## 恢复工作：先核实状态，不凭空补全

### 继续被中断的 Work

重新读取最新请求，以及决定下一步的少量持久记录。确认当前 revision、证据、负责人，
并判断操作究竟仍在运行、已经结束，还是状态未知。
不要仅因响应丢失就重复执行修改；先检查真实回执或结果。
派发超时也不证明接收方已经停止。

如果唯一缺失的证据必须来自另一台设备、服务或操作者，就记录一个明确恢复条件并保留 Work。
重复本机 fixture 不能填补这个证据缺口。安全且独立的工作仍可继续，
但不能把受阻能力重新定义成已完成。

### 更新后恢复指导内容

修改受管 runtime 文件前，确认精确源 revision、目标映射和上一个已知正常版本。
先预览操作，区分受管文件与用户自行添加的内容。依赖恢复方案执行真实更新前，
应在临时受管目标上验证恢复。如果备份从未证明能重建预期旧状态，
就还不能说恢复路径已经验证。

用支持的操作恢复已批准的受管指导与配置，再回读版本和引用。
不要删除无关文件，只为让安装目录看起来与生成目录完全相同。
发布、验证、安装和状态检查必须使用同一个选定 generated root；
不同默认路径可能造成“候选正确，但实际并未安装”的误判。

内容 rollback 不能撤销 agent 已做过的操作、恢复已删除的外部数据，
也不能消除已经读入对话的指令。这些属于另外的恢复问题，有各自的权限和证据要求。
#574 要宣告可恢复的安装交付，回执必须先说明已测试的恢复方式和选定目标。

## 串起整个过程：修一个 bug，留下一个经验

假设某仓库的导出对话框，在未选择任何行时显示了错误提示。
你要求修正提示并补充回归测试，同时授权正常 PR 流程。
Coordinator 将其限定为一个 Work：不改变导出语义，使用任务 workspace，
验证空选择和正常选择，最后交给 Reviewer。

Implementer 阅读普通交付所需指导，不会初始化 scheduler、为一个局部字符串决定
请求 Architect，也不会加载 worktree 删除流程。
如果测试最初因为项目环境要求而无法发现用例，可以修正尚未发布的运行方式，
但不能削弱测试。反之，若要改变导出行为，就是实质变化，而不是同一类机械纠错。

独立 Reviewer 检查 diff 和两个代表性场景。交接链接精确 PR 和简洁的 issue 证据，
不重复完整报告。已授权的 child merge 可以进入 Epic integration branch；
最终进入 main 仍遵循仓库权限。完成时明确 workspace 的处置，
只有安全与授权要求都满足后才进行清理。

之后，你要求 harvest 经验。Harvester 发现“测试用户可见路径”已有规则覆盖，
只有本案例增加了新的可复用判断时，才提议小幅加强。
已批准的 canonical 改动随后通过审阅过的受管目标发布和安装。
这一步改善未来指导，不会重新打开原 bug、创建新 scheduler，
也不会让原测试突然证明所有 runtime 都可用。
这样，一个真实任务就串起交付、角色、隔离、审查、权限和经验沉淀，
而不要求每一步都运行全部流程。

## 命令参考与问题排查

从预期的 Core checkout 运行命令。以下示例仅作只读检查或预览；
请将占位符替换为当前选定路径，并先确认已安装版本的帮助说明，不要猜测未支持的 flags。

```sh
python3 scripts/foundry_config.py status
python3 scripts/operation_context.py harvest --cwd . --core-root <core> --vault-root <vault>
python3 scripts/publish_adapters.py --core-root <core> --vault-root <vault> --output-root <generated>
python3 scripts/check_adapter_quality.py --core-root <core> --vault-root <vault> --surface selected-output --generated-root <generated>
python3 scripts/install_foundry.py --core-root <core> --vault-root <vault> --adapter-root <generated>
python3 scripts/sync_status.py --core-root <core> --vault-root <vault> --adapter-root <generated>
```

发布与安装是两个不同操作。各自的 `--apply` 会写入它所声明的目标，
只能在已审阅范围内使用。尚未检查选定路径与本地修改时，不要直接粘贴 apply 示例。
支持的初始化、更新和目标工具专用说明见[部署文档](deployment.md)。

| 现象 | 能说明什么、不能说明什么 | 安全的下一步 |
| --- | --- | --- |
| 无关任务选中了某个 skill。 | 可能是 discovery 或描述过宽；不代表已授权该 skill 中的操作。 | 明确不适用条件，检查 canonical asset，并提出限定范围的修正。 |
| 很短的任务加载大量长引用。 | 入口或适用条件可能过宽；仅移动文件不会解决。 | 比较该任务真正必需的内容，修正规则归属和路由。 |
| Generated 与 installed 版本不同。 | 发布不等于安装。 | 检查选定源、路径和受管更新预览，保留本地改动。 |
| 引用缺失。 | 预期指导无法访问。 | 停止受影响操作，恢复已接受版本，或修复已批准的生成结果。 |
| Onboarding 不可用。 | 实际责任组件尚未建立就绪状态；安装 skill 不等于项目绑定。 | 查看明确指出的前置条件，不编造或借用权限。 |
| 只读 SQLite 检查触碰了 sidecar 文件。 | 业务只读不一定意味着文件系统字节完全不变。 | 如实说明实际边界；不能无证据推断损坏或声称零文件修改。 |
| 另一个角色没有响应。 | 没有响应不证明已完成或取消。 | 重新分配或重试前，检查实时任务或持久回执。 |
| Reviewer 要求无关加固。 | 还能增加测试，不等于产生了新需求。 | 问清具体缺陷、约定 invariant，以及最低成本的充分验证。 |
| 需要第二次实质修复。 | 当前方案或范围可能不合适。 | Rebaseline，保留 Hard Boundaries，不降低验收标准。 |

Practice ID 便于维护者定位权威记录，不必成为用户阅读的起点。
COLLAB-001 负责工作流权限，COLLAB-009 负责 Work 合同，COLLAB-011 负责 Epic 集成，
COLLAB-013 负责编辑与清理安全，COLLAB-017 负责 onboarding。
Architecture 和 Harvest 各自保留其语义职责。实际已接受版本以选定 Vault 的索引为准。

## 为什么这样设计，还有哪些事情独立推进

设计优先保证每条规则有明确归属、清晰适用条件和足够上下文，而不是追求文件数量指标。
内容组织借鉴 [OASIS DITA](https://docs.oasis-open.org/dita/dita/v1.3/os/part2-tech-content/archSpec/base/topicdefined.html)
按完整主题组织知识的思路，但不引入 XML 或新 registry。
本指南参考 [Diataxis](https://diataxis.fr/how-to-use-diataxis/)，
让任务说明与原理解释互补，而不是重复维护两套政策。

范围集中、可恢复的交付遵循 [DORA 小批量原则](https://dora.dev/capabilities/working-in-small-batches/)；
它不要求任意比例的体积缩减，也不把 telemetry 样本数设为 release gate。
[Context engineering 指导](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
支持选择有用信息，而不是不断堆积边界案例规则；实际必需内容仍须根据本项目语义
和已观察到的 publisher 行为验证。

演进记录：[#560](https://github.com/farmerhunter/agent-foundry/issues/560) 沉淀复杂度与审查经验；
[#568](https://github.com/farmerhunter/agent-foundry/issues/568) 跟踪 adaptive isolation；
[#571](https://github.com/farmerhunter/agent-foundry/issues/571) 完善修复预算；
[#574](https://github.com/farmerhunter/agent-foundry/issues/574) 负责内容重构、精简 adapters 和本指南。
这些链接解释历史，不授权重放旧执行合同。

Pack 分发与升级仍由 [#579](https://github.com/farmerhunter/agent-foundry/issues/579) 独立推进。
跨设备部署证据也与指导内容交付分开。
提议内容、已安装文件、项目已生效权限与最终 release，都必须按实际验证到的层次分别说明。
