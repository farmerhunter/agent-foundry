# Roadmap Milestone AF-14

Status: planning document
Updated: 2026-07-03
Scope: Tester role, test planning, test evidence, automation execution workflow, and readiness pilot for Agent Foundry V1.x maintenance.

## Goal

AF-14 makes testing a first-class collaboration workflow.

The user value is not simply adding more tests. The value is that a user can see, before accepting work, what risks were considered, which evidence type covers each risk, why the test plan is enough for the change, and what remains for human trial or later follow-up.

## Source Inputs

- tiny-ipa #230 records concrete readiness blockers where a future Tester role would have helped.
- AF-14 design must also use independent web research into mature testing frameworks and patterns. tiny-ipa #230 is evidence, not the whole design.

Research areas for Architect review include:

- test pyramid and test-size thinking;
- Testing Trophy and confidence-focused coverage;
- Playwright-style resilient browser/E2E testing;
- pytest fixtures and parametrization;
- QA/tester workflow patterns that separate test planning from implementation and final acceptance.

## Role Boundary

Tester should help design and execute testing evidence. Tester should not replace:

- Architect ownership of product semantics and acceptance contracts;
- Implementer ownership of production changes;
- Reviewer ownership of independent findings-first acceptance review;
- Human ownership of subjective trial and high-risk approvals.

If Tester writes test code, the issue must explicitly scope that as test-harness or evidence work.

## Branch Policy

AF-14 is V1.x maintenance.

- Integration branch: `codex/af14-tester-role-testing`.
- Child branches should target that AF14 integration branch unless explicitly scoped as a small direct V1.x maintenance PR.
- Final AF14 integration to `main` remains a later reviewed and human-gated decision.
- V2 remains on `codex/v2-local-first-orchestration` and is not started by AF-14.

## Milestone Sequence

| Milestone | GitHub records | Purpose | Status |
| --- | --- | --- | --- |
| AF-14 Epic | #302 | Coordinate Tester role and test planning workflow. | Active |
| AF-14 A Tester role and workflow gates | #303 | Define role boundaries, routing gates, test evidence taxonomy, and research-backed design. | Done |
| AF-14 B Testing Contract and evidence taxonomy | #304 | Define test plan/test matrix fields and evidence categories. | Done |
| AF-14 C Scheduler and Project workflow support | #305 | Decide `needs:tester`, Project Owner Role=Tester, and Execution Contract validation shape. | Done |
| AF-14 D Workflow docs and templates | #306 | Implement accepted docs and templates. | Active; Implementer |
| AF-14 E Helper validation and fixtures | #307 | Implement accepted helper/schema/test validation. | Active; Implementer |
| AF-14 F Readiness and pilot review | #308 | Run bounded pilot and readiness review. | Dependency-gated |

## Non-Goals

- Do not start V2 #293.
- Do not implement memory-system work.
- Do not publish generated Skills or adapters.
- Do not mutate live Vault, runtime, generated, or private state.
- Do not treat Tester output as final Reviewer or Human acceptance.
