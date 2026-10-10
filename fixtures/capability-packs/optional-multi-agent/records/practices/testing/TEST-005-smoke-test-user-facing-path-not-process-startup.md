---
id: TEST-005
title: Smoke test the user-facing path, not just process startup
domain: testing
type: checklist
status: active
version: 9
created: 2026-06-16
updated: 2026-08-26
tags: [testing, smoke-test, local-development, bootstrap, runtime, verification, frontend, walkthrough, activation, failure-domain, evidence-contract, independent-evidence]
aliases:
  - TEST-005
  - process startup is not user-facing readiness
  - health check is not business path verification
  - smoke test initialized state
  - smoke test target runtime activation
  - evidence environment must match the claim
  - collector expectation is not a product defect
related: [TEST-002, TEST-003, TEST-004, DEBUG-002, COLLAB-006, COLLAB-016, PROD-003, ARCH-009]
review_required: false
provenance: "Harvested from tiny-ipa local development verification on 2026-06-16, where uvicorn startup and /api/health passed but /api/today failed because the local SQLite database existed without schema/content bootstrap. Revised on 2026-06-23 after AF11 showed that Core helper implementation and local tests do not prove target runtime/thread activation. Revised on 2026-06-30 after tiny-ipa M11 Progress trial showed walkthroughs for workflow-heavy UI must verify metric scope and next-action affordances, not only text presence. Revised on 2026-07-04 after tiny-ipa M12/M13 readiness showed that route-mocked browser tests, real-backend/temp-DB browser tests, backend integration, and human trial prove different risks and must be named separately. Revised on 2026-07-06 after AF15 showed a collaboration readiness helper needs adopting-project dogfood evidence, not only fixture shape, before closure. v8 added claim-to-failure-domain matching and Collector-contract validation from Agent Foundry V2 development history and #556. v9 harvests independent-evidence routing from W10 M8-B/M8-C/M8-D dogfood recorded in Agent Foundry #567."
---

## Principle

Do not declare a local development environment or service ready from process startup alone. Verify the first user-facing workflow that depends on initialized state.

## Rationale

Many services can start successfully while their actual user path is unusable. A web server can bind a port, a health endpoint can return `200`, and a CLI can print `--version` even though required schema, seed data, migrations, content imports, cache directories, credentials, or runtime assets are missing.

The same applies to reusable agent capabilities. A script can exist in Core, an adapter can be generated, or a skill can be present in a source repository while the actual target runtime, new thread, or adopting project still cannot trigger it. The smoke path must exercise the environment where the user expects to use the capability.

This failure mode is common in local development setup because the machine often contains partial state: an empty SQLite file, stale local database, half-created cache, old `node_modules`, missing generated assets, or a previous server process. If verification stops at "process started", the next human action discovers the real failure.

The completion bar is not "the process is alive"; it is "the documented first-use path works."

## Guidance

When validating setup, startup, deployment, or a developer quick start:

1. Distinguish the evidence levels:
   - **Process startup**: the command starts and logs "ready".
   - **Health check**: a shallow endpoint or status command responds.
   - **User-facing path**: the first real workflow works with initialized state.
2. Identify bootstrap state before smoke testing:
   - database schema and migrations;
   - seed/import/content data;
   - generated static/runtime assets;
   - local config and environment variables;
   - caches or writable directories the app expects.
3. Run at least one real user-facing smoke test after startup:
   - API service: call an endpoint that reads/writes the domain model, not only `/health`;
   - frontend app: open the main page and verify it does not rely on a failing API path;
   - CLI tool: run a representative command, not only `--help` or `--version`;
   - desktop/local service: exercise the first screen or tray/menu action users will try.
   - agent runtime/helper capability: start or inspect the intended target runtime/thread/project and trigger the capability path, not only the Core script or source asset.
   - collaboration/readiness helper: run it against at least one realistic adopting project or repository slice, then inspect whether the user-facing layer names readiness, blockers, allowed next actions, forbidden actions, degraded sources, and telemetry separately from raw debug output.
4. If documenting setup, rerun the documented commands from a clean or intentionally half-clean state that matches a new developer machine.
5. In the final report, name exactly which level was verified: startup, health, or user-facing path. Do not let one imply the others.

For milestone readiness or workflow-heavy features, also name the evidence type:

- **Static or contract evidence** proves documented shape, schema, or policy.
- **Backend integration evidence** proves API/state behavior in a controlled runtime.
- **Route-mocked browser evidence** proves UI copy, rendering, and client transitions with controlled responses; it does not prove backend persistence or data isolation.
- **Real-backend/temp-DB browser evidence** proves an end-to-end state chain against realistic service boundaries; it still may not prove private production data or subjective UX acceptance.
- **Human trial** proves user-facing acceptability and can reveal semantic gaps that automated checks did not model.
- **Adopting-project dogfood** proves a helper, workflow, or skill output can be interpreted against a real repository or target project. It does not authorize mutation by itself; it proves the output helps the adopter decide the next safe action.

Do not report only "E2E passed" when the distinction matters. State which evidence type passed, which risk it covers, and what remains for another evidence layer or human judgment.

Match the evidence environment to the claim's operating environment and failure domain. A same-process fixture cannot prove process isolation, a same-host dual-root run cannot prove independent host or device failure domains, and a route mock cannot prove a live backend. When exact target evidence is unavailable, name the strongest evidence actually collected and the specific missing layer; do not upgrade the capability label.

Before interpreting a failed evidence run as a product defect, bind the Collector or harness expectations to the current authoritative public contract. Classify the failure as one of: product behavior, evidence-collector expectation, or external environment/binding. If the Collector expected an internal field, obsolete label, or noncanonical outcome, correct or hold the evidence mechanism without widening the product API merely to satisfy the Collector.

Apply the same distinction to role independence. A second agent repeating the same deterministic suite is not a second evidence layer. Let one independent Reviewer inspect the complete bounded diff and run focused deterministic verification when that covers the named risks. Add a separate Tester only when it exercises a materially different boundary, such as live provider or network behavior, real process and concurrency faults, persistence failure, cross-environment packaging, browser execution, security or privacy probes, or device and physical behavior. Name what the Tester observes that the Reviewer did not; otherwise keep the route lean.

Keep missing evidence explicit. `not_collected` means no measurement was obtained; `unavailable` or `not_exposed` means the producer was not trustworthy or accessible. Neither state may be rewritten as zero, a guessed score, or a stronger acceptance claim. Qualitative Human acceptance may be recorded as qualitative acceptance, but it does not create quantitative ratings that were never collected.

For local databases, treat "database file exists" as insufficient. Check that required tables and initial rows exist, or run the repository's import/migration command before declaring the app usable.

For workflow-heavy frontend features, add a browser-level walkthrough gate:

- drive the actual UI in a realistic desktop and, when relevant, mobile viewport;
- use seeded or mocked data that exercises the named scenario contract;
- verify visible text and enabled actions after each transition, not only network responses;
- when the scenario includes metrics, statuses, or summary cards, verify their visible scope and actionability: today versus all-time, current active state versus historical evidence, level-specific versus global, and whether the next action is present or intentionally absent;
- when a visible item implies an action owned elsewhere, verify the route or affordance to that owner screen instead of only asserting the label text;
- capture screenshots, traces, or step logs when they are useful for review;
- keep API-level tests as support evidence, not a substitute for the browser walkthrough when the feature's value is UX workflow clarity.

If browser automation is unavailable, record that as a blocker or residual risk and do not mark the workflow fully accepted. A route-mocked or API-only smoke may prove technical feasibility, but it does not prove that a user can complete the flow.

## Use This When

- A user asks how to start, install, deploy, or try a project locally.
- A service has a local database, migrations, seed data, generated content, cache, or runtime assets.
- A reusable helper, skill, adapter, or workflow is expected to work in another runtime, project, or new thread.
- A delivery plan is deciding whether an independent Tester adds a genuinely different observation boundary.
- A frontend immediately calls backend business endpoints on page load.
- A health endpoint is intentionally shallow.
- A bug report says "the app started, but the page/API errors".
- An agent is about to report success after seeing only server startup logs.

## Watch Out For

- Do not equate `Application startup complete`, `listening on port`, or `/health 200` with feature readiness.
- Do not ignore partial local state. Empty databases and stale generated files often satisfy file-existence checks while breaking business paths.
- Do not make smoke tests so broad that they become full regression suites. One representative user-facing path is enough for readiness evidence.
- Do not count a repeated command under a different agent role as independent evidence.
- Do not expand walkthroughs by page boundary alone. Exercise the related visible-item cluster that shares a user question, domain concept, state transition, or next-action loop, even when it crosses pages; leave unrelated same-page items to separate coverage.
- Do not silently repair local state without updating setup docs when the failure came from missing bootstrap instructions.
- Do not accept a workflow-heavy frontend feature from lint, typecheck, build, and endpoint tests alone.
- Do not accept a runtime/helper capability from Core implementation tests alone when the user-facing value depends on target runtime activation.
- Do not let route-mocked browser tests stand in for real-backend persistence, authentication, user isolation, backup/restore, or scheduler behavior.
- Do not let real-backend/temp-DB tests stand in for subjective human product acceptance when the issue is copy clarity, visible affordance, or option quality.
- Do not accept an audit/readiness helper only because its JSON schema is correct. If the value is decision support, verify that a realistic adopter can see what is ready, what blocks readiness, what can be handled through existing workflow, what needs a human gate, and what remains unsupported.
- Do not let a convenient substitute environment stand in for an independent failure domain required by the claim.
- Do not patch product behavior until the evidence harness expectation has been checked against the authoritative public contract.

## Example

In tiny-ipa, the backend started successfully:

```bash
uv run uvicorn app.main:app --reload --port 8010
```

The startup log showed the server was running, and `/api/health` returned `200`. But the frontend called `/api/today`, which failed with:

```text
sqlite3.OperationalError: no such table: settings
```

The local `backend/tiny_ipa.sqlite` file existed but was an empty SQLite database without schema or imported content. The correct setup path was:

```bash
uv sync --extra dev --locked
uv run python scripts/import_words.py --source ../content/core_300_words.json
uv run uvicorn app.main:app --reload --port 8010
```

The correct verification was not just startup. It included `/api/health` and `/api/today` returning `200`, proving both process readiness and the first business path.

In Agent Foundry AF15, fixture tests proved `collaboration-readiness` output shape, but closure required a dogfood trial against `tiny-ipa`. The useful evidence was not just that JSON parsed; it was that the report identified missing role labels, an issue without a next-owner label, optional Project v2 visibility, `mutation_performed:false`, and a user-facing action plan separating safe workflow actions from unsupported live repair/apply.

## Activation

- Tier: task_router
- Phases: setup, startup, verification, handoff, final_report
- Signals: local dev setup, first run, health endpoint success, server startup log, SQLite/Postgres migration, seed data, import script, generated assets, frontend workflow, Playwright walkthrough, user reports runtime 500 after startup
- Evidence: final report names the startup command, the bootstrap command if any, the user-facing smoke path exercised, the target runtime/thread/project when applicable, and for workflow features the browser walkthrough scenario, any metric/status scope and affordance assertions, or explicit blocker

## Related Practices

- [[TEST-002]] — test connecting pipeline behavior, especially where startup hides downstream failures
- [[TEST-003]] — packaged artifacts need target-shell runtime smoke tests
- [[TEST-004]] — verification should use project-local dependency environments
- [[DEBUG-002]] — treat the bug as evidence of a failed assumption and clear the blast radius
- [[COLLAB-006]] — verify completion against the original user-facing task, not incidental green signals
- [[COLLAB-016]] — stop substitute work when the only remaining proof needs a non-substitutable external prerequisite
- [[PROD-003]] — design frontend features from named user scenarios before implementation
- [[ARCH-009]] — keep cross-state UI action availability explicit and testable
