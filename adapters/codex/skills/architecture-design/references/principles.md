# Architecture Principles

Canonical IDs: ARCH-001, ARCH-002, ARCH-003, ARCH-004, ARCH-005, ARCH-006, ARCH-007

1. **Boundaries before tools**: Define system boundaries and change ownership before centering technical choices.
2. **Separate independent axes of change**: If two concepts vary independently, model them independently.
3. **Unify protocol, preserve semantics**: Share envelope and lifecycle, but keep meaningful payload differences.
4. **Model inevitable failures as state**: Expected external failures should become explicit domain status.
5. **UI consumes domain summaries**: Domain derives meaning; UI presents it.
6. **MVP validates the main path**: First version proves the core loop and key boundaries, not every future capability.
7. **Design docs are context contracts**: Maintain the smallest docs that preserve boundaries, decisions, contracts, operations, and user-facing runtime flows for future agents; keep rollout phase state current.
