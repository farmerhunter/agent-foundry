# Roadmap Milestones AF-7 Through AF-12

This file contains detailed milestone plans moved out of `docs/roadmap.md` to keep the main roadmap readable.

Return to the main roadmap: ../roadmap.md

### AF-7 / M7: Runtime Adapter Framework And Trae Support

Goal: make Agent Foundry adapter publishing runtime-aware and support Trae CN through a verified global Skill path that keeps the user's day-to-day Trae setup simple.

AF-7 is adapter and runtime UX work. It does not start memory-system design or implementation. See `docs/runtime-adapter-framework-and-trae.md` for the current design.

Design areas:

- **Runtime adapter framework**
  - Define a portable adapter model between canonical practices/assets and runtime-specific outputs.
  - Track source canonical ids, versions, generator versions, target runtime, activation scope, human gates, and managed-file ownership.
  - Make generated output and installed runtime state comparable through status, dry-run, diff, and apply flows.

- **Trae CN global-first UX**
  - Publish Trae global Skills under `~/.trae-cn/skills` as the preferred reusable setup path.
  - Keep `.agents/skills` as a portable shared-skill option where compatible.
  - Use project overlays only when behavior is genuinely project-specific.
  - Do not write Trae private application state without a supported public import/export contract and explicit human approval.

- **Multi-agent role projection**
  - Project Architect, Implementer, Reviewer, Verifier, and Harvester behavior into Trae Skills or role instructions usable by SOLO Agent.
  - Keep canonical multi-agent assets runtime-neutral where possible.
  - Add Trae-specific wrappers only for activation, install path, UI wording, or future public Trae schemas.

- **Canonical update compatibility**
  - Ensure future canonical asset updates can refresh Trae outputs without forking practice logic.
  - Detect fresh, stale, drifted, unmanaged, missing, blocked, and unknown runtime states before writes.
  - Preserve fail-closed behavior for malformed or ambiguous metadata.

- **Long-running use and sync UX**
  - Show whether canonical records, generated adapters, installed Trae files, and project overlays are fresh.
  - Provide repair actions in user terms: pull, publish adapters, dry-run install, apply install, manual import, or reopen Trae.

Current GitHub records:

| Record | Purpose | Status |
| --- | --- | --- |
| #134 | AF-7 Epic for runtime adapter framework and Trae support. | In Progress |
| #135 | Historical baseline batch PR. This merged design, implementation, live Trae apply, and first validation before the child-issue plan was reconstructed. Do not use it as the AF-7 planning model. | Merged |
| #136 | Evidence issue for real Trae global Skill discovery, role UX, project instruction interaction, and project-overlay need. | Done |
| #138 | Corrective planning issue to reconstruct the AF-7 child issue plan and governance record. | Done |
| #139 | Review issue for auditing the merged #135 baseline scope and residual risks. | Done |
| #140 | Accepted decision for the Trae user-facing role invocation and project-overlay contract. | Done |
| #141 | Task issue for runtime adapter profile and selected-output contract hardening. | Done |
| #142 | Task issue for Trae sync, refresh, and repair UX validation. | Done |
| #143 | Task issue for project-overlay compatibility and multi-agent coordination scenarios. | Done |
| #145 | Task issue for Trae SOLO mode and role automation planning output. | Done |
| #147 | Task issue for idle/resume Skill rehydration and collaboration transition gates. | Done |
| #150 | Follow-up issue for explicit Trae publication intent on `ASSET-COLLAB-001`. | Done |
| #144 | Final AF-7 acceptance gate and Epic readiness review. | Review |

Child issue dependency order:

1. #138 repairs the Epic planning surface and records the governance correction.
2. #139 audits the already-merged #135 baseline before downstream hardening.
3. #136 supplies Trae runtime and UX evidence; #140 accepted the user-facing contract decision.
4. #141 follows #139 for adapter contract hardening.
5. #142 and #143 follow #136 plus #140 for sync/repair UX and project-overlay/multi-agent scenarios.
6. #145 follows #140 and #143 if Trae SOLO is accepted as the complex multi-role orchestration path.
7. #147 follows the observed #145/#146 collaboration-state drift and hardens idle/resume rehydration plus `needs:*` transition gates before final readiness review.
8. #150 resolves the non-blocking Trae publication-intent residual from #147.
9. #144 reviews #136 and #138 through #143 plus #145, #147, and #150 before any AF-7 completion or Epic closure decision.

Acceptance criteria:

- Trae is represented as a target runtime in profiles, docs, validation, and status.
- A generated Trae global Skill can be dry-run, installed, detected, refreshed, and repaired.
- Existing multi-agent assets can project into Trae without duplicating canonical logic.
- Project overlays remain optional and separated from global setup.
- Runtime status distinguishes canonical, generated, installed, project, unmanaged, stale, and conflict states.
- #134 drives AF-7 runtime adapter framework and Trae support through child issues #136, #138 through #145, #147, and #150.
- Existing former-AF7 capability-hardening records are renumbered to AF-8 and held until AF-7 completes.
- No additional AF-7 implementation work starts from the Epic or the historical baseline PR alone; every new implementation, evidence, decision, or review step must enter through a scoped child issue.
- No memory-system directories, schemas, storage, MCP tools, or design work are introduced.

### AF-8 / M8: Capability System Hardening

Goal: harden the AF-6 capability system under realistic long-running, multi-user, multi-machine, multi-runtime, drift, restore, parser/schema, lifecycle, and scheduler-state scenarios.

AF-8 is capability-system work. It does not start memory-system design or implementation. Existing GitHub records #119 through #127 were originally created as AF-7 work and are held as AF-8 records after the AF-7 Trae/runtime adapter reorder.

Hardening areas:

- **Scenario matrix and acceptance gates**
  - Build a concrete scenario matrix for Core, selected Vault, generated output, runtime installs, local config, and Project scheduler state.
  - Classify each scenario by expected status, allowed reads, allowed writes, forbidden writes, failure mode, and repair hint.

- **Multi-user and multi-machine operation**
  - Validate one Core with one Vault, switched Vaults, multiple Core checkouts, separate users, moved Core paths, moved generated roots, missing Vaults, and stale receipts.
  - Keep live runtime and private Vault mutation behind explicit authorization; use temp fixtures for validation.

- **Long-running agent sync and activation UX**
  - Validate the experience where agents start after remote Core progress, stale generated output, stale installed runtime files, or selected-output receipt drift.
  - Make repo freshness, generated-output freshness, runtime install freshness, and manual-target freshness visible as separate states.
  - Ensure users can tell whether practices and assets are actually effective in Codex, Claude Code, Hermes, ChatGPT/manual import, and future runtime targets.

- **Runtime drift and manual target policy**
  - Distinguish selected-output receipt authority from Core reference diagnostics.
  - Keep disabled/manual targets from producing false failure signals.
  - Keep ChatGPT explicit as manual import unless a future managed target is deliberately designed.

- **Pack metadata, lifecycle, and rollback robustness**
  - Validate parser/schema behavior, duplicate keys, reordered fields, malformed metadata, same-version hash mismatch, local edits, disable/retire, generated-output exclusion, and partial-write preflight.
  - Preserve the rule that malformed or ambiguous metadata fails closed before writes.

- **Installer and first-run UX**
  - Audit the actual command path from Core checkout through Vault selection, bootstrap pack deployment, generated output publish, status, dry-run install, reviewed apply, and repair.
  - Make failure states actionable without silently inferring private Vault or runtime paths.

Acceptance criteria:

- #119 through #127 or their successors cover practical boundary scenarios and are synchronized in the GitHub Project as AF-8 records.
- Status/install/publish/lifecycle flows distinguish Core, Vault, Generated, Runtime, Local Private, manual target, and Project scheduler state.
- Temp-root tests or evidence cover stale runtime after remote update, stale generated output after Core/Vault change, second-machine onboarding, receipt drift, manual ChatGPT boundary, and lifecycle rollback behavior.
- Repair guidance is explicit and safe: fetch/pull, publish generated output, dry-run install, reviewed apply, manual import, or route to human review.
- No memory-system directories, schemas, storage, MCP tools, or design work are introduced.

### AF-9 / M9: Advanced Capability Pack Discovery and Lifecycle

Goal: improve whether Agent Foundry can recognize, maintain, and export higher-level capability packs that emerge from repeated work after the basic AF-6 pack lifecycle exists.

This is intentionally later than repository hygiene, productization, physical split migration, current-user deployment and upgrade migration, onboarding, lifecycle completion, runtime adapter framework work, and capability-system hardening. Do not use this milestone to delay AF-1 through AF-8. AF-6 owns the complete install experience, basic pack status/plan/apply/update/disable lifecycle, and first optional multi-agent collaboration pack deployment path. AF-7 makes adapters runtime-aware and adds Trae support. AF-8 hardens the actual capability system in realistic user/runtime scenarios. AF-9 is for automatic discovery, advanced lifecycle optimization, export polish, and maintenance of emergent packs.

Capability packs are not the same as individual assets. A future capability pack may bundle practices, assets, workflows, templates, adapter snippets, examples, configuration profiles, dependency metadata, and export/install behavior around a recurring user goal such as multi-agent collaboration or technical documentation writing.

Epics:

- **Capability candidate detection**
  - Define when repeated practice/asset/workflow co-activation suggests an emergent capability.
  - Let agents propose capability candidates during harvest, asset discovery, or lifecycle review.
  - Avoid requiring humans to predefine all future capability categories.

- **Capability pack schema evolution**
  - Extend the AF-5 manifest only when usage proves more fields are needed.
  - Keep schema changes compatible with deployed Vault records and pack membership metadata.

- **Review and activation lifecycle**
  - Define states such as detected, candidate, proposed, active, deprecated, split, and merged.
  - Preserve human review before an emergent capability becomes active or exportable.
  - Define how capability boundaries are revised when usage evidence shows a pack is too broad, too narrow, or overlapping.

- **Export and install model**
  - Define how an approved capability pack can be exported, installed, or reused without carrying this user's private vault content.
  - Reuse Core/Vault split, generated artifact policy, adapter publishing, and runtime install safeguards.

Acceptance criteria:

- Capability packs are modeled as emergent, reviewable bundles rather than human-predeclared categories.
- Agents can propose capability candidates from evidence, but cannot activate or publish them without review.
- Exportable packs do not include local-private evidence, personal vault content, or future architecture concepts as current substrate.
- The design proves at least one existing capability cluster could be packaged without weakening Core/Vault boundaries.

### AF-10 / M10: Coordinator Workflow Optimization

Goal: use AF9's real multi-thread execution evidence to make Coordinator-driven role orchestration measurable, cheaper, and safer before memory-system planning expands the workflow surface.

AF-10 is not memory-system design. It is a workflow maturity stage for the collaboration substrate itself: Coordinator authority, role dispatch, rehydration packets, GitHub label/Project synchronization, Human Decision Contracts, closure gates, late correction handling, and token overhead modeling.

AF-10 should not be completed as a paper exercise. It is intentionally split around a real AF11 pilot:

1. **AF10-A: Foundation and instrumentation**
   - Define Coordinator workflow optimization scope and success criteria.
   - Add the workflow telemetry and Epic ledger model.
   - Define compact rehydration packet fields and authority-source rules.
   - Define initial single-thread versus multi-thread routing guidance.
   - Do enough implementation to collect consistent data during the AF11 pilot.

2. **AF11 interleaved pilot**
   - Run the Tiny IPA GitHub collaboration workflow helper migration as a narrow, telemetry-enabled pilot.
   - Use the pilot to collect real evidence about handoff cost, rehydration duplication, Project/GitHub state sync, HDC overhead, and user-facing workflow helper value.
   - Keep the pilot small enough that it tests the workflow substrate without becoming an uncontrolled migration.

3. **AF10-B: Analysis, optimization, and closeout**
   - Analyze AF11 pilot telemetry and compare it against AF9 historical evidence.
   - Decide which optimizations are policy-only, which need Skill updates, and which need helper/tool implementation.
   - Update `agent-collaboration`, role automation guidance, callback templates, HDC templates, and Project sync rules as needed.
   - Apply concrete token optimization rules: single-session serial work for low-risk tasks, compact packets before full rehydration, explicit authority-source lists, batch checkpoints only by contract, bundled human gates, and separate role dispatch only when independence or risk justifies the cost.
   - Close AF10 only after the optimized workflow model has been exercised and reviewed.

Evidence baseline:

- #158 records Coordinator authority, flow-level coherence responsibilities, and AF9 workflow lessons.
- #170 through #180 record the AF9 advanced capability-pack Epic flow, including role handoffs, PRs, reviews, human gates, readiness review, and Epic closure handling.
- #188 records the late AF9 correction that reopened closure because user-facing Skill packaging was missing.
- #189 records the initial token-overhead model for multi-thread role orchestration.

Epics:

- **Scope and success criteria**
  - Define AF10 as Coordinator workflow operating-model hardening, not just token telemetry.
  - Name success measures for efficiency, correctness, recovery, traceability, and human-gate clarity.
  - Define which parts must be proven before AF11 pilot starts and which must wait for pilot evidence.

- **Workflow cost model and telemetry**
  - Estimate token and coordination overhead from repeated role rehydration, callbacks, GitHub comments, label changes, Project readbacks, and correction cycles.
  - Add a lightweight `context_cost_estimate` section to role callbacks where useful.
  - Maintain an Epic-level `workflow_cost_ledger` for transitions, rehydrates, human gates, Project sync passes, correction cycles, and overhead class.

- **Coordinator state digest**
  - Define a compact durable state packet that downstream role threads can trust for pickup.
  - Separate must-read authority sources from reusable summaries.
  - Reduce repeated full-context rehydration without weakening review gates.

- **Role dispatch and ownership policy**
  - Clarify when to use multi-thread orchestration, single-thread serial execution, batch checkpoints, or human gates.
  - Keep `needs:*` labels as transition requests backed by durable evidence.
  - Avoid creating role churn when the next action is mechanical state repair or low-risk batch review.

- **Coordinator authority and routing contract**
  - Define when Coordinator schedules, records, blocks, repairs state, or routes work to Architect, Implementer, Reviewer, Harvester, or Human.
  - Preserve the AF9 decision not to introduce `needs:coordinator` until a later explicit decision changes it.
  - Define the durable alternative to `needs:coordinator`: issue comments, Project Owner Role, Roadmap Status, HDCs, dispatch evidence, and Coordinator state digests.
  - Clarify when Coordinator may perform mechanical Project/label repair versus when Architect or Human judgment is required.

- **GitHub and Project synchronization robustness**
  - Define when full Project field readback is required and when issue labels/comments are sufficient.
  - Document serial retry behavior for fragile Project GraphQL updates.
  - Preserve coherence between issue state, labels, Project Status, Roadmap Status, Owner Role, milestone, and roadmap docs.

- **Closure and final-user gate discipline**
  - Require final-user/adopter-facing capability, usage, trial, verification, exclusions, residual risks, and next-gate output before milestone or Epic closure.
  - Treat late closure corrections as high-value workflow evidence, not merely process failure.
  - Keep fresh readiness review and fresh Human Decision Contract required after a reopened closure gate.

- **Operational safety and permission model**
  - Classify GitHub label mutation, issue closure, PR merge, Project field sync, runtime/global config writes, Vault/private-state writes, generated adapter updates, memory-system actions, and destructive operations.
  - Define which actions are normal workflow after a valid issue contract and verification, which require Architect acceptance, and which require explicit Human approval.
  - Keep runtime/global/Vault/private/memory boundary checks visible in role handoffs, HDCs, and closure gates.
  - Preserve dry-run or report-only behavior for helper migrations until permission gates are reviewed.

- **Process harvesting and Skill update loop**
  - Decide which AF10 workflow lessons become durable practices, which become Skill or adapter updates, and which remain incident notes.
  - Define when to update `agent-collaboration`, `role-automation-planner`, callback templates, HDC templates, and generated role Skills.
  - Avoid repeating the same workflow debates in every Epic by harvesting accepted collaboration patterns after review.
  - Keep practice harvesting distinct from memory-system work.

- **Post-pilot optimization**
  - Use AF11 pilot telemetry to classify overhead as necessary review cost, avoidable duplication, state-sync cost, human-gate cost, or correction-value cost.
  - Define compact handoff patterns that reduce repeated context without hiding authority sources.
  - Decide when Coordinator should batch handoffs, keep work in one thread, require independent review, or route to human.
  - Measure optimization impact with before/after transition counts, compact-versus-full rehydrate counts, duplicated-context levels, correction cycles, human-gate turns, and observed goal-token counters when available.
  - Keep ledger estimates separate from observed goal-token counters; use observed counters to calibrate estimate bands rather than treating either as billing-grade accounting.
  - Update collaboration practices and generated Skills only after the pilot evidence supports the change.

Acceptance criteria:

- AF10 has a durable model comparing multi-thread role orchestration with single-thread serial workflow.
- Coordinator callbacks or Epic records include a reusable telemetry shape for workflow overhead.
- Rehydration packet guidance distinguishes mandatory authority reads from compact state summaries.
- Role routing policy explains when multi-thread orchestration is worth its overhead.
- Coordinator routing contract is accepted without introducing `needs:coordinator`.
- Project/label/state synchronization rules are clear enough to prevent stale readiness gates.
- Permission model classifies GitHub state mutation, issue closure, PR merge, Project sync, runtime/global config, Vault/private-state, generated adapter, memory-system, and destructive boundaries.
- AF11 pilot telemetry is reviewed and used before AF10 final policy/tooling changes are accepted.
- AF10 has a harvest/update path for collaboration practices, `agent-collaboration`, `role-automation-planner`, callback templates, HDC templates, and generated role Skills where appropriate.
- Collaboration Skill or role automation guidance is updated with accepted AF10 patterns where appropriate.
- MS-01 remains on a separate milestone axis, but MS-01 execution waits for accepted AF10 workflow optimization evidence or an explicit human waiver.

### AF-11 / M11: GitHub Collaboration Helper Migration

Goal: reserve a future Agent Foundry stage for migrating the GitHub-based collaboration workflow helper incubated in Tiny IPA into Agent Foundry, after AF10-A clarifies Coordinator workflow cost, routing, durable-state requirements, and handoff discipline.

AF-11 is intentionally interleaved into AF10: it starts only after AF10 foundation and instrumentation exist, then feeds evidence back into AF10-B analysis and optimization. It should not import project-local Tiny IPA assumptions, branch conventions, cache paths, Project ids, or mutating behavior without review.

Expected scope:

- Identify the reusable portion of the Tiny IPA GitHub collaboration helper.
- Separate generic GitHub workflow behavior from Tiny IPA project-local defaults.
- Decide whether the helper becomes a practice, asset, capability pack member, adapter-facing Skill entry point, or Core script.
- Define user-facing workflows for issue triage, role handoff, PR review, Project sync, Human Decision Contracts, and closure gates.
- Preserve Agent Foundry's Core/Vault/Generated/Runtime/Local Private boundaries.
- Reuse AF10 workflow telemetry and routing guidance instead of adding another unmeasured orchestration layer.
- Produce telemetry that AF10-B can use to optimize collaboration policy and implementation.

Non-scope:

- No direct migration of Tiny IPA private state, cache paths, project-local ids, or repository-specific defaults.
- No automatic GitHub mutation behavior without reviewed dry-run and permission gates.
- No memory-system design or implementation.
- No runtime/global config mutation unless a later scoped issue explicitly authorizes it.

Acceptance criteria:

- The helper's reusable behavior is documented separately from Tiny IPA-specific behavior.
- The migration target is chosen: practice, asset, capability pack member, adapter-facing Skill, Core script, or explicit rejection/defer.
- User-facing workflow entry points are named before implementation.
- GitHub mutation permissions, dry-run behavior, review gates, and rollback or no-write modes are explicit.
- AF10 cost/rehydration/routing findings are applied to avoid unnecessary role-thread overhead.

### AF-12 / M12: End-to-End UX, Documentation, And Core Starter Packs

Goal: make the accepted Core capabilities understandable and usable from a final-user point of view before the first public V1 release.

AF-12 covered onboarding, daily operation, capability-pack UX, runtime/generated adapter status, GitHub collaboration helper adopter UX, documentation information architecture, first-party Core starter packs, and final walkthrough evidence. It did not authorize memory-system work.

Accepted V1-facing outputs:

- README first-value onboarding path and documentation tiering.
- Ordinary-user usage and command guidance.
- Complete/power-user reference navigation.
- Capability-pack state taxonomy, normal-user consumption contract, power-user maintenance contract, candidate discovery review-list workflow, Core-hosted official catalog model, and readiness walkthrough.
- Corrected first-party starter pack set:
  - `pack.bootstrap.minimal` as mandatory/bootstrap baseline with source-of-truth, architecture-boundary, Generated/Runtime downstream, and Local Private exclusion guidance.
  - `pack.multi-agent.optional` as the only standalone optional first-party Core starter pack.
  - No standalone `pack.architecture-boundary-review.starter` in the current-stage official set.

Acceptance criteria:

- Users can understand the Core/Vault/Generated/Runtime/Local Private model without reading internal planning history.
- Starter packs are discoverable with simple user-value descriptions.
- Raw scripts remain implementation/debug substrate rather than the primary user interface.
- Final release notes can point to README, usage, commands, deployment, catalog docs, and readiness evidence.
- No memory-system directories, schemas, storage, MCP tools, or automatic memory writing are introduced.

### AF-13: External Skills Import And Reference Workflow

Goal: support the independent external-skills use case before the public `v1.0.0` release.

This work is tracked as GitHub milestone `AF-13: External Skills Import and Reference Workflow` with Epic #286 and child issues #276 through #281.

Current scheduler state: the human hold is lifted, #276 is accepted as the completed planning/decomposition record, and #277 is the active next issue.

Why it is an independent AF milestone:

- Agent Foundry already exposes `import skill <source>` to users.
- External skills, prompt packs, articles, repos, and local skill folders can be valuable, but they are reviewed inputs rather than authorities.
- Users need a clear review result: discard, reference-only, defer, merge into existing, propose practice, propose asset, or publish after approval.
- Reference-only material must be searchable or manually useful without becoming active practice/asset authority or adapter output.

Planned issue sequence:

1. #276 plan end-to-end import, reference, and user-facing workflow hardening.
2. #277 define outcome taxonomy and reference-only contract.
3. #278 harden import workflow and review packet template.
4. #279 add user-facing import/reference workflow docs.
5. #280 add fixture-backed validation for import outcomes.
6. #281 run final readiness walkthrough for the import/reference workflow.

Acceptance criteria:

- External-skill import has a complete lifecycle from source review through approval, canonicalization, adapter publish, and verification.
- User-facing docs explain when to import, what the report means, what approval changes, and what remains blocked.
- Script-bearing or unsafe external material remains inert unless explicitly reviewed and approved.
- Fixture coverage proves safe public skill, local folder, script-bearing skill, duplicate practice, reference-only material, unknown/unsafe license, and prompt-injection cases.
- No real external skill import, external script execution, Vault/private/runtime/generated mutation, generated adapter publish, capability-pack operation, or memory-system work occurs without a later reviewed issue and explicit authorization where required.
