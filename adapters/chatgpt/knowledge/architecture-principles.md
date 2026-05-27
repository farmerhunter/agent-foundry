# Architecture Principles

Canonical IDs: ARCH-001, ARCH-002, ARCH-003, ARCH-004, ARCH-005, ARCH-006, ARCH-007

## ARCH-001 Boundaries Before Tools

Define system boundaries and change ownership before choosing or centering tools. Tools implement boundaries; they should not become accidental domain concepts.

## ARCH-002 Separate Independent Axes Of Change

When two concepts can vary independently, model them independently. Look for dimensions such as source, transport, domain model, storage backend, presentation mode, and lifecycle state.

## ARCH-003 Unify Protocol, Preserve Semantics

Use a common envelope for identity, source, status, timestamps, and lifecycle. Preserve meaningful payload differences with typed payloads or discriminated unions.

## ARCH-004 Model Inevitable Failures As State

Failures expected to happen should be domain state, not only exceptions. Make adapters translate external failures into explicit statuses.

## ARCH-005 UI Consumes Domain Summaries

The domain layer should produce display-ready summaries. UI should handle layout, interaction, and presentation, not core business derivation.

## ARCH-006 MVP Validates The Main Path

The MVP should validate the main system path and key boundaries, not every plausible future capability.

## ARCH-007 Maintain Design Docs As Context Contracts

Maintain the smallest design docs that preserve engineering context and user-facing runtime experience for future agents. Update them when domain models, boundaries, contracts, operations, or user flows change; do not document every local implementation detail.
