# Architecture Principles

Canonical IDs: ARCH-001, ARCH-002, ARCH-003, ARCH-004, ARCH-005, ARCH-006, ARCH-007, ARCH-008, DEBUG-001

1. **Boundaries before tools**: Define durable state or outcomes, stable responsibilities, change points, and ownership boundaries before centering technical choices. If the design is mostly a current tool pipeline, run a boundary rewrite and substitution test.
2. **Separate independent axes of change**: If two concepts vary independently, model them independently.
3. **Unify protocol, preserve semantics**: Share envelope and lifecycle, but keep meaningful payload differences.
4. **Model inevitable failures as state**: Expected external failures should become explicit domain status. When the failure will be diagnosed across sessions or agents, define stable diagnostic reasons or taxonomy as well.
5. **UI consumes domain summaries**: Domain derives meaning; UI presents it.
6. **MVP validates the main path**: First version proves the core loop and key boundaries, not every future capability.
7. **Design docs are context contracts**: Maintain the smallest docs that preserve boundaries, decisions, contracts, operations, and user-facing runtime flows for future agents; keep rollout phase state current.
8. **Implementation plans bridge architecture to code**: For the current phase, specify file structure, data flow with error branches, IPC/contracts, and acceptance criteria; review the plan before coding.
9. **Diagnostics are reproduction artifacts**: For fragile integrations, parser/capture/import flows, and local automation, diagnostics should let an agent identify the failing boundary, create a fixture or failing test, and verify the fix. Default to metadata traces; export raw data only by explicit user action.
