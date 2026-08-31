# Practices and Skills: A User Guide

Agent Foundry helps an agent reuse good engineering judgment without making every
task begin with an entire process manual. Its practices explain reusable rules;
its skills help the agent choose and carry out the right kind of work. Neither
replaces your instructions, your repository's rules, or the permissions of the
tools that actually perform actions.

This guide connects everyday use with the reasons behind the system. Start with
an application below, then follow the concepts you need. You do not need to learn
practice IDs before using Agent Foundry.

**Delivery status:** this is the #574 candidate guide. The focused collaboration
refactor and its loading behavior remain proposed until the approved canonical
changes, generated output and selected installed targets are read back. Existing
onboarding, distribution and runtime capabilities retain their own documented
limits. This guide does not announce activation or a release.

**中文导读：** practice 保存可复用的判断，skill 帮助 agent 找到合适的工作方式。
目标不是让每个任务都走完整流程，而是在需要时读对规则、遵守已有授权，并交付
可验证的结果。安装了 skill，不代表所有项目已经启用本地协作或自动调度。

## Start with what you want to do

| Your goal | A useful request | What to expect | Read next |
| --- | --- | --- | --- |
| Use engineering guidance in a normal task | “Review this PR for regressions.” | Relevant review guidance, findings and evidence; no automatic new role or scheduler. | [Ordinary Work](#ordinary-work-from-request-to-result) |
| Adopt bounded collaboration in a project | “开启多agent协作：先检查这个项目的准备状态。” | Project-specific preflight and a truthful plan or hold; not automatic activation. | [First use](#prepare-a-project-for-bounded-collaboration) |
| Hand a defined task to another role | “Send this bounded review to the existing Reviewer.” | A specific recipient, scope, evidence and an actual dispatch receipt or explicit unavailability. | [Role support](#use-role-support-only-when-it-helps) |
| Reuse a lesson | “Harvest the lessons from this issue.” | A deduplicated review list, not immediately active policy. | [Learning](#turn-experience-into-maintained-guidance) |
| Recover or update | “Check whether my installed skills match the selected Vault.” | A read-only comparison and an exact proposed update or recovery path. | [Recovery](#recover-without-inventing-state) |

### Use the foundation without adopting everything

You can use a skill in an ordinary repository without creating a SQLite ledger,
starting permanent roles, importing an optional pack or changing branch policy.
For example, an architecture review needs the proposed boundary and relevant
code, not a new project scheduler. A translation unrelated to engineering should
not activate collaboration merely because it is requested inside a coding app.

Tell the agent the result you want and the boundaries that matter. “Fix the
incorrect empty-state label; preserve behavior and add a regression test” is more
useful than asking it to follow every available practice. The agent should select
guidance that helps the result and identify any missing authority before an
affected action, while continuing work that is already authorized.

### Prepare a project for bounded collaboration

Multi-agent collaboration is the capability to share work among agents. Bounded
collaboration is the controlled operating model: each Work has an objective,
owner, limits, evidence and a terminal handoff. Adoption is project-specific and
forward-only; historical issues and worktrees do not have to be migrated or
cleaned up before new work can use that model.

First-use preparation starts by inspecting the project binding and its actual
coordination state. A repository document saying “use two roles” is not evidence
that native roles or a scheduler exist. Where the owner-composed onboarding path
is available, its public preflight is read-only. Missing or ambiguous ownership
must produce a hold with a next action, not an invented success receipt.

The normal durable native roles are Coordinator and Durable Architect. Native
creation or reuse is a separately bounded operation, not an effect of reading
this guide. A successful initialization needs the corresponding owner readbacks;
a plan alone does not establish readiness. See the
[onboarding workflow](../workflows/onboard-bounded-collaboration.md) for the exact
supported interface in your selected Core version.

If preflight reports `owner_unavailable`, do not borrow another project's ledger,
create roles speculatively or repeatedly rerun the same check. Establish which
owner prerequisite is missing and use the authorized setup path. This condition
does not prevent ordinary GitHub-based issue and PR work. Likewise, guidance
installation is not project onboarding, and same-machine evidence is not proof
of a cross-device handoff.

### Use role support only when it helps

A request to review code and a request to dispatch a Reviewer are different.
The first asks for a result; the second asks for a collaboration operation.
Agent Collaboration owns the delivery lifecycle and durable handoff. Role
Automation Planner owns the bounded dispatch or automation plan when it is
explicitly requested or required by the accepted Work.

For a narrow handoff, pass the objective, authority, target revision, relevant
evidence, expected response and next owner. Do not copy an entire conversation or
load two complete overlapping manuals. Reuse an appropriate existing role when
available; report the mechanism actually used. A prompt printed in chat is not a
successful dispatch, and sending a task is not evidence that it has completed.

Recurring automation needs recurring intent. A one-time review request should
not create a heartbeat or schedule. An automation helps deliver work; it does not
grant new authority, supersede the issue or keep a blocked operation retrying.
If the necessary dispatch capability is absent, a clearly labelled portable
prompt can be a fallback. It must not be presented as a native operation.

### Turn experience into maintained guidance

A useful lesson begins as evidence, not as a new rule. The Harvester identifies
the evidence window, separates project-specific decisions from reusable
judgment, searches existing practices and proposes a merge where possible.
External skills are also review inputs, not trusted executable instructions.

The review list explains the actual content change, affected canonical records,
lifecycle, adapter impact and any installed-target impact. Material changes need
the applicable approval before becoming active. Approval of a direction is not
approval of unseen rules that govern future agent behavior. Once an exact list
is approved, complete its disclosed chain without asking again for unchanged
mechanical steps. Return for a new decision only if scope, risk, content or
targets materially change.

Keep raw prompts, transcripts, credentials and private payloads out of reusable
records. Concise, non-sensitive usage evidence can help maintenance; collecting
a telemetry quota is not a prerequisite for delivering an accepted improvement.
See [harvest practices](../workflows/harvest-practices.md).

## Understand the source-to-use model

The key distinction is between where a rule is maintained, where it is packaged,
and what can actually authorize an action.

| Layer | Owns | Does not prove |
| --- | --- | --- |
| Core | Shared workflows, schemas, publisher/install tooling, profiles and documentation. | That a particular Vault or runtime is current. |
| Selected User Vault | Canonical practice and asset records, indexes and approved lifecycle state. | That a downstream copy has been published or installed. |
| Practice | A reusable judgment with rationale, applicability and boundaries. | Permission for every operation it describes. |
| Asset / skill | A user-facing workflow, responsibility, trigger and references to its rules. | A second source of policy or a native runtime capability. |
| Capability pack | A reviewed distribution grouping or snapshot. | A live upstream authority, automatic import approval or successful upgrade. |
| Generated adapter | A target-specific projection of accepted source content. | That the user's tool is currently reading it. |
| Installed files | Managed copies in a selected runtime environment. | Project onboarding, execution permission or cross-device readiness. |
| Execution owners | The actual repository, ledger, scheduler, tool and user permissions for an operation. | Authority inferred from a title, summary or copied receipt. |

Resolve the selected Vault before canonical work. Do not edit a generated skill
to fix a source rule: the next publish can overwrite that edit and other runtimes
would still disagree. Change the reviewed source, regenerate, then verify the
selected installed copy. If local runtime changes are intentional, preserve and
classify them before choosing whether to incorporate or replace them.

Packs are optional distribution units, not the organizing principle for all
refactoring. A universal foundation and optional multi-agent content can remain
separate without making Core a third knowledge pack. Existing-user improvements
need not wait for pack importer or upgrade work. Current pack preview and apply
limits are documented in [usage](usage.md#capability-pack-safety); an old exported
pack is not automatically equivalent to today's canonical Vault.

## Ordinary Work: from request to result

A Work is a bounded delivery unit, not necessarily a new issue, branch, role or
conversation. The point is to make the intended result and responsibility clear
enough to complete and verify it. For ordinary work, a short contract can freeze:

- the outcome and its meaningful public behavior;
- one owner, allowed changes and explicit exclusions;
- the branch/workspace strategy appropriate to the repository;
- representative verification, completion evidence and the next owner;
- real residual risks or prerequisites, where present.

Add detail when a named risk requires it. A database migration needs failure and
recovery detail that a wording correction does not. Do not make an ordinary
patch wait for an exhaustive file inventory, a full role chain or a formal
decision about every hypothetical failure.

Start from current instructions and durable issue/PR state. Implement and verify
the authorized change, then hand off evidence tied to the candidate revision.
For a low-risk bounded change, one independent Reviewer can perform the focused
checks. Add a distinct Tester when it can observe a different boundary, such as
real persistence, a browser, a second device or a live external environment.
Separate role names alone do not create independent evidence.

A useful review finding identifies the concrete error prevented, its consequence,
the relevant requirement or Hard Boundary and the cheapest sufficient proof or
repair. Naming preferences, an unrelated cleanup and speculative hardening are
not automatically blockers. Conversely, reduced process must never downgrade
data loss, unauthorized external mutation, privacy/security, credentials or
forged authority into cosmetic residuals.

Unpublished mechanical bring-up corrections may fix syntax, imports or test
collection when behavior, dependencies, assertions, scope and evidence meaning
remain unchanged. They may not hide tests with skips, weaken assertions or
substitute a different environment. A semantic repair changes the contract or
behavior and needs consolidated review. After a second substantive failure,
rebaseline the approach rather than layering another patch contract. This rule
does not retroactively authorize operational repair or make a live mutation
“mechanical.”

Completion means the agreed result is proven on the agreed surface. A passing
unit test does not demonstrate runtime installation; a published PR is not a
merge; a merge is not a release. The final handoff says what changed, how it was
verified, what remains and who can take the next action. Use
[the collaboration workflow](multi-agent-collaboration.md) for detailed handoff
and review conventions rather than duplicating them in every request.

## Roles and ownership without unnecessary threads

Coordinator keeps objective, dependencies and handoffs coherent. Architect owns
material architectural choices and unresolved semantic boundaries. Implementer
produces the change; Reviewer independently evaluates it; Tester supplies any
distinct required evidence. Human decisions cover actual product choices and
protected operations, not every agent correction. Harvester proposes reusable
lessons after the work provides evidence.

Durable roles provide continuity; Work-scoped roles provide focused execution.
The Coordinator plus Durable Architect onboarding budget is not a global cap of
two threads. A Work may require other roles. Equally, mentioning “review” does
not require creating a persistent Reviewer. Choose the least coordination that
provides the needed evidence and respects the contract.

RoleHub is an optional logical, read-only directory or front door. It is not a
native thread, scheduler, controller, telemetry store or readiness prerequisite.
A RoleHub-titled conversation does not acquire authority because of its name.
Role conversation continuity and refresh are also separate from permission to
run the next operation: a successor needs fresh durable anchors, not just a
summary claiming that everything was approved.

## Workspace and Epic strategy

Isolation protects a concrete writer and change, rather than creating worktrees
for their own sake. A read-only review can inspect the current checkout. A
serial, low-risk task can use a task branch when repository policy allows it and
there is no overlapping Epic work. Writable concurrent work, protected-boundary
work and Epic children normally need an isolated task workspace. One writable
Work has one owner and one writer binding.

For multi-agent features, child branches normally integrate through a non-main
Epic branch. Keep that integration checkout for coordination, integration and
readback, not competing edits. A current `main` and an older feature integration
may contain different accepted capabilities; select a coherent base explicitly
rather than silently substituting one for the other.

Adaptive isolation is adopted for future Work in a bounded-collaboration project;
it is not an instruction to clean every historical branch or to impose the policy
on unrelated repositories. On interruption, verify the real path, branch, HEAD,
dirty state and owner. A stale conversation title is not a writer lease.

At the end, record whether a workspace is retained, reclaimable, held or
quarantined. Cleanup is a separate destructive operation: inspect tracked,
untracked and relevant ignored content, ownership and recovery before removing
an exact authorized target. Preserve uncertain work. Do not use force, wildcard
deletion or a guessed reconstruction to make an untidy inventory look complete.

## Permission and meaningful Human decisions

Establish permission from the latest applicable user instruction, repository
policy and Work contract before the operation. A skill explains a workflow; it
does not expand that permission. Actual explicit holds remain binding. If rules
conflict, stop the affected transition and resolve the conflict, while continuing
unaffected authorized work when possible.

Verified commits, task-branch pushes and PR updates are ordinary execution steps
inside an authorized repository workflow. A validated child merge into a
non-main integration branch or a child issue closure can be delegated by its
contract. That delegation is not permission for every repository, final main
integration or Epic closure.

Preserve explicit boundaries for destructive actions, migrations, privacy or
security changes, credentials, external effects, live/runtime changes and final
integration or release where the contract requires them. Do not ask the Human to
debug a test failure or decide every wording improvement merely because a review
found work remaining. Explain the actual decision: what changes, why it matters,
what has been checked, the remaining risk and what approval would authorize.

For canonical self-updates, show the exact review list and installed impact
before activation. A selected personal Vault may authorize automatic final merge
after an approved list and successful checks. That is a local policy, not a
permission to copy into public guidance or apply to Core `main`.

## Progressive loading: enough guidance, at the right time

Discovery and reference selection solve different problems. Discovery metadata
helps the host or model choose a skill. The selected SKILL body then tells the
agent which guidance is necessary for this task. A concise description should
name its positive scope and important exclusions; a description cut off before
the exclusions can trigger an unnecessary chain of skills.

The #574 candidate publisher marks routed assets as `intent` and unchanged
assets as `legacy`. These labels expose the instruction-selection path; they
are not runtime switches or a new scheduler. The proposed collaboration path
uses a compact entrypoint and coherent
conditional references. Ordinary delivery should not read cleanup, onboarding,
automation and migration procedures unless those operations are actually in
scope. A narrow dispatch should not read every lifecycle rule a second time.
Detailed rationale remains accessible, rather than being deleted to achieve a
smaller number.

Reference availability is not unconditional required reading. Once a relevant
reference is selected, read enough of its complete rule and context to apply it
faithfully, including applicable exceptions and recovery. Related-practice links
are navigation, not permission to invent an automatic transitive full-bundle
requirement. Mandatory safety must remain available before the effect it guards.

An uncertain route needs a visible fallback. Report the ambiguity and consult the
relevant existing guidance; do not silently claim precise intent selection, load
every available skill or escalate permissions. Compatibility for unchanged
assets must remain explicit. These are proposed source and projection behaviors
until their candidate checks and installed readbacks complete.

Measure the same task before and after: discovery description, entrypoint,
required direct and transitive references, and repeated exposure during a
handoff. Report both total exposure and unique content so duplicated files cannot
masquerade as a reduction. Static bytes describe instruction volume, not model
token consumption, latency or quality. Prompt text cannot guarantee host loading
behavior or remove history already present in a conversation.

The [Agent Skills specification](https://agentskills.io/specification) distinguishes
discovery metadata, the activated body and on-demand resources. Agent Foundry
uses that distinction without introducing a mandatory loader service or treating
documentation as a runtime enforcement mechanism.

## Recover without inventing state

### Resume an interrupted Work

Re-read the latest request and the small set of durable records governing the
next action. Confirm the current revision, evidence, owner and whether an
operation is running, finished or unknown. Do not repeat a mutation solely because
its response was lost; inspect its actual receipt or result first. A dispatch
timeout is not proof that the recipient stopped.

If the only missing evidence requires another device, service or operator, record
one concrete resume condition and preserve the Work. Repeating same-host fixtures
does not close that evidence gap. Safe independent work can continue without
redefining the blocked capability as complete.

### Restore guidance after an update

Before changing managed runtime files, identify the exact source revision, target
map and previous known-good material. Preview the operation and distinguish
managed files from user-owned additions. Validate restoration on temporary
managed targets before relying on it for the real update. A backup that has not
been shown to reconstruct the intended previous state is not a demonstrated
recovery path.

Restore the approved managed guidance and configuration with the supported
operation, then read back versions and references. Do not delete unrelated files
to make the target resemble a generated directory. Keep the same selected
generated root throughout publish, validation, install and status checks; using
different defaults can make a correct candidate appear installed when it is not.

Content rollback cannot undo actions an agent already performed, restore deleted
external data or erase instructions already read into a conversation. Those are
separate recovery problems with their own authority and evidence. The #574
delivery receipt must identify the tested restoration method and selected targets
before this candidate can claim reversible installed delivery.

## A connected example: fix one bug, keep one lesson

Suppose a repository's export dialog displays the wrong message when no rows are
selected. You request a fix with a regression test and authorize its normal PR
workflow. The Coordinator binds one Work: correct the message without changing
export semantics, use a task workspace, test the empty selection and a normal
selection, and hand off to a Reviewer.

The Implementer reads the ordinary delivery guidance. It does not initialize a
scheduler, call an Architect for a local string decision or load the worktree
destruction procedure. If test collection initially fails because of the
documented project environment, it fixes the unpublished invocation without
weakening the tests. A request to change export behavior instead would be a
semantic change, not the same mechanical correction.

An independent Reviewer checks the diff and both representative cases. The
handoff links the exact PR and concise issue evidence rather than duplicating a
full report. An authorized child merge can proceed into the Epic integration
branch; final main integration follows the repository's own permission rule.
The completed Work retains a clear workspace disposition, with cleanup handled
only when its safety and authorization requirements are met.

Later, you ask to harvest the lesson. The Harvester finds that testing a user-facing
path is already covered and proposes a small strengthening only if the case adds
new reusable judgment. The approved canonical change is published and installed
through reviewed managed targets. This final step improves future guidance; it
does not reopen the bug, create a new scheduler or make the original test prove
every runtime. One real task connects delivery, roles, isolation, review,
permission and learning without requiring all procedures at every step.

## Reference and troubleshooting

Run commands from the intended Core checkout. The examples below are read-only
inspection or preview; replace placeholders with the selected roots. Check your
installed version's help rather than guessing unsupported flags.

```sh
python3 scripts/foundry_config.py status
python3 scripts/operation_context.py harvest --cwd . --core-root <core> --vault-root <vault>
python3 scripts/publish_adapters.py --core-root <core> --vault-root <vault> --output-root <generated>
python3 scripts/check_adapter_quality.py --core-root <core> --vault-root <vault> --surface selected-output --generated-root <generated>
python3 scripts/install_foundry.py --core-root <core> --vault-root <vault> --adapter-root <generated>
python3 scripts/sync_status.py --core-root <core> --vault-root <vault> --adapter-root <generated>
```

Publishing and installing are distinct operations. The corresponding `--apply`
options write their declared surfaces; use them only under the reviewed scope.
Do not paste an apply example into an environment whose selected roots and local
changes have not been checked. See [deployment](deployment.md) for the supported
setup, update and target-specific instructions.

| Symptom | What it does and does not mean | Safe next step |
| --- | --- | --- |
| A skill was selected for an unrelated task. | Discovery or description may be too broad; it does not authorize the skill's actions. | State the non-trigger, inspect the canonical asset and propose a scoped correction. |
| A short task loads many long references. | Entrypoint or applicability may be overbroad; moving files alone will not solve it. | Compare the required content for that task and fix its canonical ownership/routing. |
| Generated and installed versions differ. | Publication is not installation. | Inspect the selected source/root and managed update preview; preserve local edits. |
| A reference is missing. | The intended guidance is not reachable. | Stop the affected action and restore the accepted version or repair the approved projection. |
| Onboarding is unavailable. | The owner path did not establish readiness; a skill install is not a project binding. | Read the named missing prerequisite; do not invent or borrow authority. |
| A read-only SQLite check touches a sidecar. | Read-only business operations do not necessarily imply byte-identical filesystem state. | Report the actual boundary; do not infer corruption or claim zero file mutation without evidence. |
| Another role is not responding. | A missing response does not prove completion or cancellation. | Inspect the live task or durable receipt before reassigning or retrying. |
| A reviewer asks for unrelated hardening. | More possible tests do not automatically create a requirement. | Ask which concrete defect and agreed invariant need the cheapest closing proof. |
| A second substantive repair is needed. | The current approach or scope may be wrong. | Rebaseline; preserve Hard Boundaries instead of weakening acceptance. |

Practice IDs help maintainers locate authority; they need not lead the user
journey. COLLAB-001 covers workflow permission, COLLAB-009 Work contracts,
COLLAB-011 Epic integration, COLLAB-013 edit/cleanup safety and COLLAB-017
onboarding. Architecture and Harvest keep their own semantic responsibilities.
Use the selected Vault indexes to find the actual accepted versions.

## Why these choices, and what remains separate

The design favors one owner for each rule, clear applicability and sufficient
context rather than a target file count. The content organization takes a
coherent-topic lens from [OASIS DITA](https://docs.oasis-open.org/dita/dita/v1.3/os/part2-tech-content/archSpec/base/topicdefined.html),
without adopting XML or a new registry. The guide uses user tasks and explanations
as complementary views, following [Diataxis](https://diataxis.fr/how-to-use-diataxis/),
not as duplicated policy sets.

Focused reversible delivery follows [DORA's small-batch principle](https://dora.dev/capabilities/working-in-small-batches/).
It does not impose a numerical shrinkage target or make a telemetry sample a
release gate. [Context engineering guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
supports selecting useful information instead of accumulating edge-case rules;
the actual required-content checks still come from this project's semantics and
observed publisher behavior.

Evolution anchors: [#560](https://github.com/farmerhunter/agent-foundry/issues/560)
records complexity and review lessons; [#568](https://github.com/farmerhunter/agent-foundry/issues/568)
tracks adaptive isolation; [#571](https://github.com/farmerhunter/agent-foundry/issues/571)
refines the repair budget; [#574](https://github.com/farmerhunter/agent-foundry/issues/574)
owns content, lean adapters and this guide. These links explain history, not
permission to replay old execution contracts.

Pack distribution/upgrade remains [#579](https://github.com/farmerhunter/agent-foundry/issues/579).
Cross-device deployment evidence remains separate from guidance delivery.
Proposed content, installed files, active project authority and final release
must each be described at the level actually verified.
