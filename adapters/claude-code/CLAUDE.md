# Claude Code Instructions

This project contains Agent Foundry, the user's canonical agent capability system.

Published assets include ASSET-META-001 Practice Harvester, ASSET-ARCH-001 Architecture Design, ASSET-COLLAB-001 Agent Collaboration, and ASSET-IMPL-001 Provider Integration Playbook.

## Request Routing (META-008)

Before acting on a request, classify user intent:

- If the user asks to **execute a repeatable workflow** (harvest, design architecture, collaborate on a PR), match the request to an asset trigger and invoke the asset. During execution, reference the canonical practices the asset lists.
- If the user asks to **apply a constraint or change behavior** ("stop doing X", "always do Y"), match the request to a canonical practice and apply its Principle and Guidance. Do not invoke an asset for a one-off behavioral correction.
- If the user asks to **update or govern agent knowledge**, invoke the Practice Harvester asset (ASSET-META-001, META-001 through META-013, GOV-001 through GOV-006, RUNTIME-001 through RUNTIME-004).

Assets perform work; practices govern rules. Do not conflate them.

## Compact Preflight

Before substantial changes, check:

- Duplicate or derived truth source? Apply GOV-001.
- New machinery, layer, script, workflow, or integration? Apply GOV-002 and ARCH-001.
- Transient memory or chat summary used as fact? Apply GOV-003.
- Writing into user-owned runtime or agent configuration? Apply GOV-004 and RUNTIME-001.
- Syncing, publishing, or installing adapters? Apply RUNTIME-003.
- Producing rendered or converted output? Apply TEST-001.
- Producing packaged desktop/runtime artifacts? Apply TEST-003.
- Building a background, tray, menu bar, or ambient app? Apply PROD-001.
- Designing diagnostics for a fragile integration, parser, capture, import, or local automation flow? Apply DEBUG-001.

## Practice Harvesting

Short commands:

- `harvest practices` / `做一次 harvest practice`
- `discover assets` / `harvest skills` / `harvest assets` / `发现可打包资产`
- `import skill <source>` / `导入这个 skill <source>`
- `publish practices` / `发布 practices`
- `review practices` / `检查 skill rot`
- `review assets` / `检查 asset rot`
- `refresh practices and assets` / `刷新practices和assets`

When asked to refresh, read `workflows/refresh.md` and follow the steps: git pull, conditionally regenerate adapters if canonical files changed, then install to local runtimes.

When asked to harvest, persist, deduplicate, merge, or publish reusable lessons:

1. Locate Agent Foundry Core and Vault. Prefer explicit roots when available, then `AGENT_FOUNDRY_CORE` plus `AGENT_FOUNDRY_VAULT` after commands support them, then `~/.agent-foundry/config.yaml`, then `AGENT_FOUNDRY_HOME` as same-root compatibility, then the current directory only if it validates as the required Core and Vault context. The current project is evidence source, not canonical destination.
2. Read `workflows/harvest-practices.md`.
3. Read `schemas/practice-entry.schema.yaml`.
4. Run the current capability check; do not use future architecture concepts as current writable substrate.
5. Route artifacts before abstracting practices.
6. Apply the generalization gate before drafting practice candidates.
7. Search `indexes/practice_index.yaml`.
8. Present a concise review list before mutation, including rejected-as-practice items, canonical impact, adapter impact, and runtime/global instruction impact when relevant.
9. Treat approval as scoped to the listed items only; broad phrases such as "continue", "approved", or "do the whole chain" do not permit skipping unshown harvest steps.
10. After approval, continue through the listed canonical changes, checks, PR/traceability, merge/apply, and adapter/runtime publish automatically unless the diff departs from the approved list, checks fail, risk increases, or a new unlisted runtime/global target appears.
11. Update canonical practice entries under `practices/` first.
12. Do not publish `candidate` or `proposed` entries into adapters without human approval.

When asked to discover reusable assets or harvest skills, read `workflows/discover-assets.md`, search `indexes/asset_index.yaml`, present asset candidates, and after approval create or extend assets and publish relevant adapters. For whole-session or phase-level skill harvests, set an explicit evidence window that includes earlier phases, linked issues, PRs, and commits rather than only the latest discussion topic.

When an active asset is used, record concise non-sensitive usage evidence automatically, preferably with `scripts/record_asset_usage.py`.

## Cross-Project Governance

Apply GOV-001 through GOV-006 across all projects, not only inside Agent Foundry:

- GOV-001: protect canonical source of truth; derived views, generated files, caches, summaries, and compatibility artifacts must not become second hand-maintained truth sources.
- GOV-002: prefer the smallest maintainable mechanism; avoid adding scripts, layers, files, automations, or abstractions before ownership, validation, and failure modes are clear.
- GOV-003: treat transient context as evidence; memory, chat history, rollout summaries, and temporary notes must be verified against project-owned durable records.
- GOV-004: preserve maintainability and runtime capability; do not degrade native agent memory, skills, project instructions, self-improvement, or user-owned runtime configuration.
- GOV-005: do not use future architecture concepts, directories, schemas, categories, or workflows as if they already exist.
- GOV-006: explicitly mark current, candidate, proposed, future, deprecated, or unknown capability state when it affects action.

Treat memory, session summaries, and activity logs as evidence only. Durable rules and assets belong in Agent Foundry canonical records.

Do not suppress native agent memory or self-improvement features when available. Treat native learning outputs as candidates for Agent Foundry when they should become durable or cross-agent.

When publishing adapters into local runtimes, apply RUNTIME-001: treat agent runtime directories as shared user-owned environments. Use managed blocks, namespaced files, ownership markers, backups, dry-runs, and explicit adoption for unmanaged runtime paths. Never overwrite unmanaged runtime files by default.

Apply RUNTIME-002 when working with deployment manifests or offline sync: adapter profiles and runtime templates are portable repository content, while enabled targets, detected runtime paths, and adoption decisions belong in gitignored local manifests. Portable snapshots exclude machine-local runtime state by default.

Apply RUNTIME-003 after every sync or refresh operation: report the exact commit hash, unpushed commit count, adapters regenerated, runtime updates applied, and the exact next action required. Never report "done" when unpushed commits remain or runtime state is ambiguous.

Apply META-009 when publishing adapters: adapter quality must be executable and must verify the exact contract surface it claims to protect, including trigger vocabulary, Compact Preflight sections, canonical IDs, published asset IDs, target conventions, and target-specific fidelity, not only generated file existence or broad text matches.

Apply META-010 when reviewing assets: use lifecycle state, usage evidence, overlap, canonical coverage, stale triggers, and published targets before recommending keep, revise, deprecate, archive, split, or merge.

Apply META-011 through META-013 during harvest: route artifacts before abstracting practices, treat user method corrections as process evidence before domain content, require insights to pass a generalization gate before they become practice candidates, and do not convert approval of a direction into approval to bypass an unshown review list.

Apply RUNTIME-004 when recording or reviewing usage evidence: raw logs stay local under `usage/local/`; shared review uses sanitized aggregate rows in `usage/usage-aggregate.yaml`; missed activation and other review-only signals must not inflate shared usage counts.

## External Skills

When asked to borrow or evaluate external skills, read `workflows/import-external-skills.md`. Capture provenance, review security and license concerns, deduplicate, and ask before activation.

## GitHub And Multi-Agent Collaboration

Use the Agent Collaboration asset ASSET-COLLAB-001 for GitHub issue, PR, GitHub Project/Epic scheduling, multi-agent sync, CLI comment, document conversion, and resume workflows. It applies canonical collaboration practices COLLAB-001 through COLLAB-012 and COLLAB-014:

- When turning a roadmap stage or milestone into GitHub work, create or update issues with Stage, Epic, Owner Role, Risk, Depends On, Roadmap Status, labels, and durable issue bodies before releasing tasks.
- Distinguish GitHub built-in `Status` from custom `Roadmap Status`; use labels and durable comments as the agent inbox surface.
- For work already authorized through an issue, branch, and PR workflow, create verified task commits, push the task branch, and open or update the PR without a separate commit-permission round trip.
- Direct commits to `main`, PR merges, issue closure, force pushes, resets, deletions, data migrations, and privacy/security boundary changes still require explicit authorization.
- Before moving an issue to review or closing it, comment with completion scope, linked PR or commit, verification method, verification results, and residual risks.
- If the user has authorized auto-merge, merge validated PRs by default unless review, hold, or risk conditions require confirmation.
- In multi-agent repositories, fetch or pull before issue work and verify remote sync when another machine may have pushed.
- Do not infer that the session is ending after compaction, interruption, or finishing one subtask; continue from the latest user request.
- When completing a task list from another agent, verify each item against the original list — not against implementation signals like tests passing or build succeeding.
- In a new multi-agent repository, Architect should bootstrap or locate the repo-local workflow contract and apply an issue role-fit gate before handing issues to Implementers.
- Use GitHub Project status for human-visible state and `needs:*` labels plus comments as the agent inbox/message layer; keep built-in Status, Roadmap Status, issue state, labels, comments, and session-role-task binding semantically coherent.
- Ready issues should carry an Execution Contract with branch strategy, base branch, PR target, dependencies, role fit, current owner role, Architect-owned decisions, Implementer boundary, completion handoff, reviewer target, merge rule, and verification; completion handoff controls when Architect review is requested.
- Before moving work into an Implementer inbox, classify role fit; split mixed work or constrain Implementers to evidence, preliminary classification, implementation, or verification when final taxonomy, architecture, policy, harvest, privacy, or security decisions remain Architect-owned.
- If an Implementer evidence pass exposes taxonomy, architecture, privacy, or policy questions, route to Architect review before releasing downstream batches.
- If Architect-owned decisions remain after evidence or preliminary classification, the producing agent moves the issue to Review and keeps it open rather than closing it.
- `Ready + needs:implementer` may be an ordered queue; related low-risk child issues in the same Epic integration branch default to dependency-gated batch execution/review, and obey `Depends on` gates before starting code.
- `Ready` is pickup state, `Review` is validation state, and `Done` requires acceptance or closure; do not leave one status surface saying `Ready` while another says `Done`. `needs:*` labels route roles, not necessarily different sessions.
- Prefer Epic integration branches for multi-agent feature work; direct-to-main and stacked PRs are explicit alternatives with narrower use.
- When work moves to Review, name the reviewer target: current-session structured self-review, user, separate Reviewer agent, CI/automation, or batch/Epic checkpoint. If the same session switches from producing role to reviewing role, mark structured self-review and residual risks instead of implying independent review.
- When review requests changes, leave detailed PR feedback and a linked issue handoff before routing back to Implementer; an open child PR is not automatically an Architect review request, so prefer batch or Epic checkpoint review for related low-risk issues unless completion handoff, reviewer target, high-risk trigger, failed verification, or the checkpoint itself requires review.
- For complex handoffs, preserve knowledge state before action planning: context, research output, frameworks, decisions, rejected options, user corrections, current capability boundary, unresolved questions, and next actions.

For GitHub comments containing Markdown with backticks, dollar signs, or command examples, apply IMPL-001: use `--body-file` or another safely quoted path instead of shell-interpreted inline strings.

For converted document deliverables, apply TEST-001: verify rendered output, font/encoding behavior, images, and source-to-output structure rather than relying only on command success.

Apply TEST-002 when a system connects independently-tested modules through glue code: test the connecting pipeline — especially error paths — not only the endpoints. Adapter tests + ViewModel tests passing does not prove the full pipeline works. Verify that error paths preserve provider identity and status propagation through the connecting transformation.

Apply TEST-003 when producing packaged runtime artifacts: open the generated artifact in the target shell and verify user-visible installer contents, app/file icons, tray or menu behavior, startup/login item behavior, permissions, and quit path. Build success is not runtime success.

Apply PROD-001 for background, tray, menu bar, daemon-like, or ambient apps: expose install, open, settings, startup, identity, and explicit quit affordances where users already interact with the app. Do not rely on Activity Monitor, terminal commands, or hidden OS knowledge for lifecycle control.

## Provider Integration

Use the Provider Integration Playbook asset ASSET-IMPL-001 when adding or reviewing provider/API adapters. It applies GOV-002, ARCH-001 through ARCH-005, ARCH-007 through ARCH-009, IMPL-002, TEST-002, COLLAB-006, DEBUG-001, and DEBUG-002:

- Verify official API or user-mediated source behavior before building adapter code; defer unverified providers.
- Write a structured provider candidate review covering provider_id, source, quota_model, refresh semantics, credentials, payload, failure states, UI actions, diagnostics, risks, and decision.
- Write adapter tests first for success and failure paths.
- Route config and dashboard behavior through ViewModels or explicit contracts, not scattered JSX provider branches.
- Add pipeline tests for provider_id preservation, error status propagation, null-safety, and provider isolation.
- When debugging endpoint, auth, region, credential, quota model, external behavior, or user-facing text failures, first name the failed assumption and search its blast radius across code, UI, tests, and docs.
- Update implementation plan, design decisions, and interaction contracts, then verify completion against the original task list.

## Architecture Design

Use canonical architecture practices ARCH-001 through ARCH-009, and DEBUG-001 when architecture work includes serviceability/debug artifact design:

- Boundaries before tools; if a design is mostly a current tool pipeline, run a boundary rewrite and substitution test.
- Separate independent axes of change.
- For mixed or maturing systems, inventory current layers before designing target movement; classify paths, modules, records, generated outputs, runtime state, private state, and proposed design evidence by ownership and change behavior.
- Mark ambiguous areas as `Mixed` or `Needs Architect Classification` instead of forcing premature final taxonomy.
- Unify protocol while preserving semantics.
- Model inevitable failures as state.
- Let UI consume domain summaries.
- Scope MVP around the main path.
- Maintain design docs as lightweight context contracts for boundaries, decisions, contracts, operations, and user-facing runtime flows; mark rollout phases as implemented baseline, future work, rejected, or non-goal when state changes; name durable interaction contract docs after the contract they preserve, not the temporary review that discovered it.
- Bridge architecture to code with a reviewed implementation plan: insert a concrete plan (file structure, data flow, IPC contracts, acceptance criteria) between architecture docs and code, review it adversarially, and fix gaps before implementation.
- Introduce interaction ViewModels for cross-state UI contracts: when UI action availability depends on multiple domain or workflow states, make actions and card variants explicit in a small testable ViewModel before escalating to larger frontend frameworks.
- For fragile integrations, parser/capture/import flows, and local automation, design diagnostics as agent-actionable reproduction artifacts: trace the flow, define stable failure reasons, avoid default raw-data persistence, and provide a debug bundle path to fixtures/tests.

## Implementation

Apply IMPL-002 and IMPL-003:

- Before building any integration that depends on third-party behavior (APIs, web scraping, browser automation, file formats, SDKs), run a minimal disposable experiment to verify the external system actually behaves as assumed. Do not build adapter code on unverified premises.
- Never run stealth, anti-detection, or automation-bypass experiments against production services without the user's explicit command and approval. The user must specify the exact experiment, understand and accept the risks, and set a clear stop condition. If a probe fails, stop — do not iterate through different evasion techniques unless the user issues a new explicit command.

## Debugging And Serviceability

Apply DEBUG-001 when a user-facing tool needs diagnostics for failures that may return to an agent for repair:

- Prefer metadata-first traces with `trace_id`, component, action, status, stable reason, and bounded metadata.
- Keep raw text, screenshots, DOM, credentials, cookies, localStorage, and sessionStorage out of default logs.
- Provide explicit debug bundles with environment, trace, parser/importer diagnostics, and raw input only by explicit user choice.
- For parser/importer failures, preserve the normal business API and add a diagnostics side-channel that can become fixture tests.
