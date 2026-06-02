# Architecture Principles

Canonical IDs: ARCH-001, ARCH-002, ARCH-003, ARCH-004, ARCH-005, ARCH-006, ARCH-007, ARCH-008, DEBUG-001

## ARCH-001 Boundaries Before Tools

Define durable state or outcomes, stable responsibilities, change points, and ownership boundaries before choosing or centering tools. Tools implement boundaries; they should not become accidental domain concepts. If the design is mostly a current tool pipeline, run a boundary rewrite and substitution test: separate stable responsibilities from mechanisms, replace plausible tools or workflows, and keep the architecture shape only if core responsibilities remain stable.

## ARCH-002 Separate Independent Axes Of Change

When two concepts can vary independently, model them independently. Look for dimensions such as source, transport, domain model, storage backend, presentation mode, and lifecycle state.

## ARCH-003 Unify Protocol, Preserve Semantics

Use a common envelope for identity, source, status, timestamps, and lifecycle. Preserve meaningful payload differences with typed payloads or discriminated unions.

## ARCH-004 Model Inevitable Failures As State

Failures expected to happen should be domain state, not only exceptions. Make adapters translate external failures into explicit statuses. When those failures will be diagnosed across sessions or agents, define stable diagnostic reasons or a failure taxonomy too.

## ARCH-005 UI Consumes Domain Summaries

The domain layer should produce display-ready summaries. UI should handle layout, interaction, and presentation, not core business derivation.

## ARCH-006 MVP Validates The Main Path

The MVP should validate the main system path and key boundaries, not every plausible future capability.

## ARCH-007 Maintain Design Docs As Context Contracts

Maintain the smallest design docs that preserve engineering context and user-facing runtime experience for future agents. Update them when domain models, boundaries, contracts, operations, rollout phase state, or user flows change; do not document every local implementation detail.

## ARCH-008 Bridge Architecture To Code With A Reviewed Implementation Plan

Between architecture docs and code, insert a concrete implementation plan with a detail gradient: current phase gets file structure, data flow with error branches, IPC contracts, and acceptance criteria; future phases get directional goals only. Review the plan adversarially to catch boundary violations, missing files, and protocol gaps before implementation.

For fragile integrations, parser-heavy flows, local automation, or user-assisted capture, add serviceability acceptance criteria: trace id, stable failure reasons, default diagnostic metadata, raw data exclusions, explicit debug artifact, and how an agent can turn the artifact into a fixture or failing test.

## DEBUG-001 Design Diagnostics As Agent-Actionable Reproduction Artifacts

Diagnostics should let a coding agent identify the failing boundary, reconstruct the minimum input, add a failing test, and verify the fix. Default to metadata-first traces and bounded snippets. Export raw text, screenshots, DOM, credentials, cookies, or storage only by explicit user action. Keep business outputs separate from diagnostics side channels.
