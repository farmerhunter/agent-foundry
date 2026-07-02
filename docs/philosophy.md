# Agent Foundry 的哲学：从记忆到能力治理

这篇文章是围绕我的一个开源实验项目 [Agent Foundry](https://github.com/farmerhunter/agent-foundry) 写下的思考。

## 入坑

在Agentic coding的时代，每个半吊子vibe coder都在兴奋的熬红眼睛几天之后试图走向创造世界运行之道的道路。

我大概是从26年5月开始尝试vibe coding。严格说，我每天用光的那点 token 限额根本够不上tokenmaxxing，只是token all-in。但这段时间我确实开始用起来甚至沉迷于AI编程。这种“我不必会coding也能开发”的体验一方面很兴奋，另一方面也很不安。AI 确实能把产出速度拉得很高，一个小项目也可能很快达到每天几千行文档加代码的节奏。但越是这样，质量风险也越明显。尤其是能力不够稳定的模型或 agent，经常会在看似流畅的执行中犯一些很隐蔽的错误：理解边界不完整，修改范围失控，覆盖已有约定，或者在架构问题上过早收敛到一个漂亮但脆弱的方案。。然后被纠正，然后重复犯同样的错。。

在某一阶段，我甚至忍不住退回到一种更 old school 的工作方式：强流程、强设计文档、强计划。（20年的肌肉记忆。。）某种意义上，这和 vibe coding 的直觉是矛盾的。Vibe coding 强调放手，让系统快速探索；而我更习惯在复杂系统里先建立结构、接口、约束和验收标准。这个习惯大概来自长期企业级软件开发训练，也来自对工程质量的本能焦虑。

1. 当前 AI 的能力已经很强，但架构思考的稳定性还不够。它可以提出很好的抽象、很完整的列表、很像样的路线图；但它也可能遗漏生命周期、权限边界、运行时约束、source-of-truth 关系、演进成本和组织协作问题。
2. 确定性问题。AI编程thread无法可信赖的重复高质量输出，随运行时长退化问题严重。
3. 对经验知识固化能力的忧虑。我就算能调教出来一个满足我要求的agent，又如何保证能移植到别处呢？毕竟在当今百”模“大战的乱世，换模型/封号/狡兔三窟是常态。Codex、Claude Code、ChatGPT、Hermes、VPS 上的开发环境、各种编辑器和自动化工具会同时存在。经验如果只留在某一个 agent 的 memory 里，就会被平台锁住；如果只写在一个项目的 README 里，又很难迁移到下一个项目；如果只存在聊天记录里，下次上下文一压缩就消失了。
4. 成长路径问题。在使用AI的初期，以我个人有限的经验，有时还能帮它发现一些疏漏，对方向问题做纠偏。但这也反过来让我产生一个更强的愿望：我希望我的 AI 不只是每次被我纠正，而是能不断成长，自我反哺，越来越成熟，至少不要在相同类型的问题上反复犯同样的错。

我越来越强烈地感觉到，一个 agent 系统真正有价值的部分，不只是底层 LLM 有多聪明。LLM 的推理和生成能力当然重要，但如果每一次对话都像重新认识我、重新理解项目、重新犯一遍旧错误，那么这种智能就很难积累。除了模型本身，memory 很重要，harness 也很重要：前者决定系统能不能记住，后者决定系统能不能在真实工具、真实文件、真实权限和真实运行时里把事情做出来。

所以做这个项目，想解决的问题是：我和 agent 一起工作时产生的经验，怎样才能从一次性的对话里出来，变成跨 session、跨 agent、跨机器都能使用的能力？

## 做什么不重要，思考总结最重要

在使用 AI 工具完成一个具体任务时，真正值得被记住的东西，并不是所有上下文，也不是所有聊天记录，而是系统和人一起生成的 insight。

AI 工具有一种很特别的能力：它可以在任务过程中或任务之后，对自己的工作进行反思、归纳和解释。有时这种反思是我主动要求的，比如“这次 lesson learned 是什么”；有时是 agent 自己主动给出的总结。它会把散乱的事件组织成模式，把局部错误抽象成原则，把一次修正变成一个未来可复用的流程。

这件事很重要。因为过去很多经验之所以珍贵，是因为它们需要老手在大量重复实践中慢慢形成。一个有经验的工程师看到一个系统，会自然感到“这里边界不对”“这个自动化将来会失控”“这个文档会变成第二套 truth source”。这种判断往往不是某条明文规则，而是一种被很多失败和修正训练出来的直觉。

**【观点】：Vibe Coding不但生成软件输出物，也可以同时生成对过程的反思，进而生成见解（insight）。**

那么 AI 生成的 insight 和老手的经验是不是一回事？我觉得它们相似，但有可能存在质量差距。二者都是试图从具体情境里抽象出可迁移的判断，但老手的经验通常背后有长期失败、修正和责任感，而 AI 的 insight 很容易过早成形，看起来漂亮却证据不足。它需要经过人的审查和后续使用验证，才有资格从“一个有道理的总结”变成“我愿意让未来 agent 遵守的经验”。AI 让 insight 的生成速度变快了，但 insight 变多之后，真正稀缺的东西变成了治理。没有治理，insight 会堆积成噪音；有了治理，它才可能变成经验，进一步变成能力。

 **【观点】：不能简单用memory 保存所有内容，而是要治理内容，去芜存菁，才能找到 insight。**

 AI 直觉式的观察和思考要经过一个完整的治理流程来成熟，而不是直接进入长期规则，变成未经审查的规则记忆。

## 生成了 Memory，但不止于 Memory

我最开始想做的是 memory。更准确地说，是一种我能看见、能维护、能审查的 memory。我不希望重要经验只存在于某个产品的黑盒记忆里，也不希望每次换工具都重新训练一遍我的工作方式。

但做着做着，我发现 memory 只是起点。

这里有一个我很在意的哲学问题：记住一件事，和会做一件事，到底是什么关系？

我记得一件事和我会做一件事并不等同。一个 agent 记得“不要覆盖用户 runtime 文件”，并不等于它在真实部署运行时会 dry-run、会识别 managed block、会备份、会在不确定时停下来问我。它也可能在总结时说得很漂亮，执行时还是照样犯错。人也是这样。我可以记得“写代码前要先理解边界”，但这不代表我每次都会做到。

**【观点】：真正的能力不只是记忆，而是记忆在正确时机被唤起，并进入行动。它要和情境识别、操作流程、反馈机制、复盘习惯绑在一起。**

所以 memory 需要继续向前走。经验被记住之后，要被结构化成 practice；practice 要能约束一个 workflow；workflow 要能被打包成 asset；asset 要能进入不同 agent 的 runtime；使用之后还要留下 evidence；长期还要 review，避免 skill rot。

这就是我后来逐渐意识到的转变：Agent Foundry 不是单纯的 memory system，而是一个以 memory 为基础的 capability governance system。它关心的不只是“系统是否记得”，而是“系统能不能在合适的时机稳定地做对”。

## Memory、Capability 与 Harness

我现在会把 agent 系统粗略看成三部分：LLM、memory、harness。

LLM 提供推理和生成能力。Memory 保存长期上下文、偏好、经验和事实。Harness 则把 agent 接到真实世界里：文件系统、Git、browser、shell、CI、runtime install、权限边界、自动化任务。

Agent Foundry 不想替代 LLM，也不想变成一个通用 harness。它的边界更窄：它要治理经验如何从 memory 进入 capability，再通过 adapter 影响不同 harness 中的真实行为。

如果 memory 不能影响 execution，它只是笔记。如果 execution 不受 memory 约束，它只是自动化。真正的 agent capability 出现在两者连接之后：一个经验能被再次唤起，能进入具体工作流程，能被验证，能被复盘，也能在不合适时被撤回。

这也是为什么项目里会有 practices、assets、adapters、usage evidence、review workflow 这些概念。它们不是为了增加复杂度，而是因为单靠“记住”无法保证“做到”。Agent Foundry 的目标不是堆积记忆，而是**让记忆进入行为**。Practice 是被结构化的判断；asset 是可调用的工作方式；adapter 是进入具体 agent runtime 的表达；evidence 是能力是否真的被使用的回声。只有这些连起来，memory 才开始转化成 capability。

## 经验如何变成资产

Agent Foundry 里最核心的一条链路，是从真实工作经验到可复用能力的转化。

一次工作中出现的教训，先只是 candidate lesson。它需要经过 dedupe，判断是否已经被已有 practice 覆盖。如果确实有普遍性，才进入 canonical practice。Practice 不是一段感想，而是一个能改变未来 agent 行为的规则。多个 practices 可以被打包成 asset，比如 architecture-design、practice-harvester、agent-collaboration。Asset 再被转换成不同 agent 的 adapter，进入 Codex、Claude Code、Hermes 或 ChatGPT 的运行环境。最后，真实使用会产生 evidence，review 再根据 evidence 判断它是否有用、是否过时、是否应该修改。

这个闭环看起来比“写一条 memory”复杂，但有了它，你就能在辛苦工作一天后放心的说，今天我本人遇到的坑点和学到的正确做事方法都梳理了，记住了，下次可以直接避坑了。

**【观点】：AF帮助你构建个人能力资产，而非通用知识导入。**

不是那种商业意义上包装好的课程或 prompt，而是更细、更贴近工作现场的 judgment patterns、workflow habits、failure checks、collaboration rules。它们是我和 agent 一起工作时形成的操作性经验。

## 跨 Agent 和跨机器不是附加需求

一开始我以为跨 session 就够了。后来发现，跨 agent 和跨机器不是额外功能，而是这个时代使用 AI 工具的基本现实。

我会不断尝试新的 agent 系统。某个阶段 Codex 好用，另一个阶段 Claude Code 更适合某些任务，ChatGPT 适合讨论和整理，Hermes 可能有自己的 memory 和自成长能力。与此同时，本机和 VPS 也会并行开发。经验如果不能跨这些环境，就会反复碎片化。

**【观点】：必须把 权威知识（canonical source of truth） 和软件的 运行态表述（runtime adapter） 分开。**

Canonical records 应该是我真正批准、愿意长期维护的经验；adapter 只是针对某个 agent runtime 的表达。某个 runtime 文件可以被重新生成，可以被替换，但 canonical practice 不能因为某个工具的格式变化就丢失。

这个边界后来变得越来越重要。比如当前项目里，我们进一步拆出了 Foundry Core、Foundry Vault 和本机 locator。这样当我在另一个项目里说 “harvest practices” 时，那个项目只是 evidence source；Agent Foundry Vault 才是 canonical destination。这个设计不是形式主义，而是为了防止 agent 把经验写错地方。

## 走向无人驾驶之路

一个很自然、也很诱人的想法是：既然要做 capability governance system，那是不是把它 setup 好之后，就让它全自动运行？让 agent 自动总结 lesson，自动提升 practice，自动打包 asset，自动部署 adapter，自动根据 evidence 修正自己。这样看起来才像真正的自成长系统。

但这个想法越往下想，越需要谨慎。 Human-in-the-loop 不是安全口号，而是系统质量的一部分。起码在目前的AI编程使用经验来看，很多关键 insight 都不是 agent 自动想出来的，而是人和AI一起在真实使用中不断”磨“出来的。这些判断来很多自人的直觉、经验、焦虑和表达。它们不总是一下子说得很完整，但正是这些不完整的提醒，推动系统补上真正重要的边界。

与此同时，我也感受到，和优秀的 LLM 共事确实能学到东西。人在闭环中的价值不只是审批和纠错，也不是永远站在系统外面当裁判。更深一层的价值是：人和 AI 共同工作时，人的判断也会被反向训练。AI 能帮我把直觉展开，提出反例，整理结构，指出可能的实现路径；我提供方向、边界和责任判断，它提供推演、表达和结构化能力。这个过程中，我也会更清楚地理解自己为什么不放心、为什么坚持某个边界、为什么一个看似简单的自动化会引入维护风险。

**【观点】： Human-in-the-loop 不是简单地“人比 AI 更可靠”，而是一个双向成熟过程。**

Agent 通过人的审查避免把噪音变成规则，人也通过和高质量 agent 的协作，把原本模糊的工程直觉变成更可表达、更可复用的判断。Agent Foundry 想保留下来的，不只是 agent 的 lesson learned，也包括这种共同工作过程中逐渐成形的 judgment pattern。

也许终有一天，我能提出的意见会越来越少。这个过程有点像自动驾驶从 L2 到 L4 的演进：在早期，人必须持续盯着系统，因为系统随时可能在边界场景中做错；到了更高等级，人不再介入每一个动作，但系统仍然需要清晰的运行设计域、接管机制、责任边界和安全证明。Agent capability governance 也类似。目标不是永远手工审批每一条规则，而是在系统足够成熟之前，不假装它已经成熟。

因此，Agent Foundry 可以逐步提高自动化程度，但不应该从一开始就无人驾驶，而是走分级自治的路径。

## 一个 Meta Project

这个项目有一种很有趣的嵌套感。

我在用 agent 构建一个改善 agent 的系统。我从 agent 犯过的错误里提炼 practice，再让未来 agent 避免同类错误。我设计 memory system，而这个设计过程本身又被 memory system 记录和改进。我讨论 source of truth，而项目自身不断暴露新的 source-of-truth 问题。我设计 review workflow，而每一次 review 又反过来改进 workflow。

这不是简单的**自我指涉**，而是一种**自举**。Agent Foundry 一边被使用，一边学习如何更好地保存和部署使用中产生的经验。

这种 pattern 背后其实有一个更深的变化：AI 把“改进工作方式”这件事本身变成了日常工作的一部分。过去，流程改进、知识沉淀、规范建设往往需要专门的时间和组织推动；而现在，每一次与 agent 协作时，系统都有机会观察自己的失败、总结一次修正、生成一条候选 practice，并把它接回下一次执行。工作产物和工作方法之间的边界变得更薄了。

这也是 AI 赋能自举的地方。Agent 不只是执行任务，它也能帮助描述任务是如何被执行的；不只是生成代码或文档，它也能生成关于生成过程的反思；不只是使用已有规范，它也能在被审查后参与规范演进。也就是说，系统的能力不再只来自外部一次性设计，而是来自持续使用中的反馈回路。

但这种层层嵌套也会带来眩晕感。你一开始只是想修一个脚本，后来发现需要一条 practice；为了发布 practice，又需要 adapter；为了证明 adapter 有效，又需要 evidence；为了管理 evidence，又需要 review workflow；为了防止 review workflow 本身失控，又需要新的治理原则。系统像一面镜子照着另一面镜子，递归地展开，容易让人迷失在 meta 层里。

所以 Agent Foundry 必须保持一个很实际的约束：每一层 meta 设计，都要回到真实工作中的一个失败模式或能力缺口。不能因为“治理”本身很有趣，就把项目做成一个抽象的治理宇宙。它应该像工厂里的治具和量规：存在的意义不是展示复杂性，而是让下一次生产更稳定、更可复验、更少犯同样的错。

## 自我指涉的流程缺陷

Agent Foundry 的一个特殊风险，是 agent 会用正在被修改的流程来修改流程本身。

这不是普通的执行错误，而是一种自我指涉缺陷。比如，我要求 agent 走 harvest workflow 来修正 harvest workflow，agent 同时要理解用户授权、执行修改、维护 review gate、发布 adapter，还要判断自己是否已经遵守了刚刚被讨论的规则。所有这些判断都发生在同一个推理回路里。只靠 agent 说“我下次会记住”，并不能可靠地避免再次跳过流程。

这个问题在真实使用中已经出现过不止一次：用户说“批准”“继续”“做完整链路”，agent 就把它解释成可以直接修改 canonical practice、发布 runtime adapter，事后再补解释。这种行为表面上提高效率，实际上破坏了 Agent Foundry 最重要的治理边界：批准必须作用于已经列明的对象，而不是回头覆盖一个没有展示过的 review list。

更可靠的办法，是把自我更新拆成外化状态机：

```text
harvest report / review list
  -> explicit approval of listed items
  -> canonical mutation
  -> PR or equivalent review surface
  -> post-merge adapter/runtime publish
  -> final verification
```

这不是为了把流程变慢，而是为了避免最危险的压缩：把方向性授权当成流程豁免。尤其当修改对象是 harvest workflow、practice-harvester asset、adapter publish、runtime install、AGENTS 指令或其他会影响未来 agent 行为的规则时，系统必须先把 proposed change 外化成 review list。用户批准的是 list 里的 items，而不是 agent 心里推断出来的完整链路。

这也说明 human-in-the-loop 的意义不只是审批内容是否正确，还包括打断 agent 的自我合理化。一个 agent 可以很好地解释为什么它跳过了步骤，但解释不是治理。治理需要可检查的状态、可引用的 review surface、可回滚的 commit、以及发布前后的明确边界。

## 这是一个重复造轮子的故事吗？

我也受到了一些外部 memory system 的影响。比如 Garry Tan 的 GBrain 引起了我很大兴趣，我也是因此才决定做这个系统。而且我相信记忆系统结合harness必然是当今最火的发展方向，各种复杂度的此类系统会层出不穷。

表面上，这很容易沦为重复造轮子。市面上已经有 agent memory、skills、custom instructions、project knowledge、MCP、knowledge graph、vector database、prompt library、workflow automation。未来一定还会出现更成熟、更强大的系统。Agent memory 不是小功能，而是 agent 能不能长期变聪明的核心基础设施。那为什么还要自己做一遍？

我的想法是，外部系统可以启发我，未来也可能被接入或替换底层实现。但如果我不亲手经历一遍，就很难知道如何驱动智能体的能力成长。

**【观点】：Agent Foundry项目真正探索的不是一个具体工具，而是经验治理模型。**

经验治理模型回答的是：什么经验值得留下？什么只属于一次对话？谁有权把经验提升为规则？规则如何 dedupe、merge、supersede？经验如何从记忆变成能力？规则如何进入不同 agent runtime？规则被 miss 时如何记录？规则变旧、变泛、冲突时如何修正？什么是 canonical source of truth？什么只是 adapter、runtime copy、derived view？人的判断和 agent 的总结之间如何分工？

这些问题当然不是 Agent Foundry 独有。理想情况下，它们可以追溯到更底层的原理：认知科学、行为科学、知识管理、软件工程、组织学习、人机协作、系统安全。也正因为它们有底层共性，将来成熟系统完全可能提供一套很好的默认答案。

但在现阶段，如果直接依赖一个黑盒 memory 或 capability system（例如龙虾，Hermes），我很难去真正理解如何确保它记住的是事实、偏好、规则而非噪音；它如何决定一条经验应该长期保留；它如何避免一次性事件变成永久行为；它如何处理冲突和遗忘；它是否允许我审查和撤销；它如何跨 agent、跨机器迁移；它如何影响 native memory 和 runtime；它失效时能不能解释、修复和回滚。

换句话说，我还是希望搞懂治理memory的底层原理。

所以自己做一遍的价值不是为了永远使用自制系统，也不是为了拒绝外部系统。它的价值是通过真实使用，把经验治理模型长出来。它选择一个边界清晰的小闭环：足够简单可以被理解和维护；又足够完整，能暴露经验治理的核心问题。只有亲自经历 harvest、dedupe、approval、adapter、runtime sync、missed activation、review、skill rot、source-of-truth drift，才知道哪些问题是本质，哪些只是实现细节。

未来如果出现成熟的 agent memory system、capability marketplace、personal knowledge graph 或 team skill platform，我会乐于跳船。但前提是，我已经知道自己要保护什么边界，要追求什么行为，要如何判断一个系统是否可靠。


## 未来：走向缸中之脑？

我最终很关心的一个问题是：未来，每个人的思想、经验、技能，会不会被蒸馏成可以交流、交换，甚至买卖的能力资产？

我觉得方向上很可能会发生，但形态未被权威定义：Prompt 太表层了。怎样固化某个人或某个团队在长期工作中形成的 workflows、practices、judgment patterns、domain playbooks、evaluation checklists、tool-use habits、memory schemas 和 operating policies，是个课题也是个机会。

这些东西如果结构足够好，就不只是“别人写过的一段提示词”，而是可部署的能力包。一个优秀工程师、研究者、投资人、设计师、运营者的经验，可能被部分蒸馏成 agent 可以学习和执行的资产。**人与人之间交换的不只是知识，还有工作方式。**

当然，这也会带来新的问题。经验被商品化后，如何处理隐私和上下文？如何防止规则脱离原场景后误用？如何让使用者理解能力包背后的判断，而不只是盲目安装（我觉得当前那些Skill Marketplace的滥觞就有这个隐忧）？

这些问题现在还没有答案。Agent Foundry 只是我自己的一个小实验：先把我和 agent 一起工作中形成的经验，从易失的 conversation 中提取出来，变成可审查、可继承、可运行、可交换的能力资产。哪怕未来它被更好的系统取代，我也希望自己已经理解了其中最关键的东西。

## 参考

- [Vectorize: What Is GBrain? Garry Tan's AI Agent Memory System Explained](https://vectorize.io/articles/what-is-gbrain)
- [Agent Wars: GBrain, Long-term memory for AI agents](https://agent-wars.com/news/2026-04-11-gbrain-the-memex-built-for-people-who-think-for-a-living)
