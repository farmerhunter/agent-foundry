# Memory-System Milestones

This file tracks memory-system planning outside the Agent Foundry AF maturity-stage sequence.

The MS axis exists because Agent Foundry stages continue to evolve. Memory-system planning should not be renumbered every time a new Agent Foundry workflow or migration stage is inserted.

Return to the main roadmap: ../roadmap.md

## MS-01: Memory-System Readiness Design

Goal: define memory as an adjacent future capability using evidence from Agent Foundry maturity work, without implementing storage yet.

MS-01 is a readiness design stage, not implementation. It does not authorize creating memory directories, schemas, MCP write tools, automatic memory writing, or storage. MS-01 execution should wait until AF10 workflow optimization evidence is accepted or explicitly waived by the user, because memory-system design will depend on the collaboration workflow substrate.

Readiness areas:

- **Memory record taxonomy**
  - Draft record types such as research memo, source digest, concept note, project fact, decision record, open question, profile update, practice candidate, and skill candidate.
  - Keep these as proposed until implementation.

- **Evidence and privacy model**
  - Decide raw evidence storage rules.
  - Decide whether raw ChatGPT exports ever enter Git.
  - Define encryption, local-only, shared aggregate, retention, and high-stakes metadata expectations.

- **Routing and save levels**
  - Define memory harvest routing separately from practice harvest.
  - Preserve levels such as raw only, summary, research/design preserved, candidate canonical records, and adapter/runtime impact.

- **Knowledge-to-practice promotion**
  - Define when knowledge remains reference material.
  - Define when knowledge can become a practice, asset, workflow, or adapter update.
  - Preserve rejected-as-practice reasoning.

- **MCP boundary**
  - Prefer read-only memory resources first.
  - Treat write operations as propose/validate/review/apply, not direct arbitrary writes.
  - Require proof that the write target is current capability.

Acceptance criteria:

- Memory-system design can be reviewed without creating future directories.
- Open questions remain visible.
- No automatic memory writing exists.
- Record types, evidence policy, routing levels, promotion rules, and MCP boundary are explicit enough to inform an implementation-home decision.
- Workflow-cost implications from AF10 are carried into the readiness design instead of being treated as unrelated process overhead.

## MS-02: Memory Implementation Home Decision

Goal: decide the implementation home for memory-system work using evidence from Agent Foundry maturity work and MS-01 readiness design.

MS-02 is a decision stage, not implementation. It does not authorize creating memory directories, schemas, MCP write tools, automatic memory writing, or storage.

Decision options:

- **In-repo extension**
  - Best if memory records are a natural extension of the User Vault and Core boundaries are clean.
  - Risk: repo grows too broad and mixes personal knowledge with product machinery.

- **Monorepo package**
  - Best if Core, Vault, adapters, and memory modules need shared scripts and schemas but independent packaging.
  - Risk: more tooling and release complexity.

- **Sibling repository**
  - Best if memory system should be a separate product or vault that depends on Agent Foundry governance.
  - Risk: cross-repo coordination and duplicated workflow code.

- **Forked experimental repository**
  - Best for fast exploration with permission to break structure.
  - Risk: useful work may be hard to merge back, and fork may drift from governance practices.

- **User-vault convention**
  - Best if memory should mostly be a directory/schema convention inside each user's vault.
  - Risk: weak product boundary if tooling remains implicit.

Decision criteria:

- Does memory need to be reusable by other users?
- Does it require raw/private evidence in the same Git repository?
- Does it share enough lifecycle machinery with practices/assets to justify one Core?
- Can generated outputs be reproduced cleanly?
- Can MCP and runtime adapters remain safe?
- Can a new user initialize a blank vault without personal content?

Acceptance criteria:

- Decision record names the chosen implementation home and rejected alternatives.
- Future implementation plan has file boundaries, data flow, validation, privacy policy, rollback path, and workflow-cost implications.
