---
id: META-009
title: Make adapter fidelity executable
domain: meta
type: principle
status: active
version: 2
created: 2026-05-27
updated: 2026-05-28
tags: [adapters, fidelity, verification, testing, publishing]
aliases:
  - META-009
  - test adapter meaning, not only adapter existence
  - executable adapter quality
  - adapter fidelity check
related: [META-001, META-002, META-008, RUNTIME-003]
applies_when:
  - publishing canonical practices into agent-specific adapters
  - reviewing whether adapters preserve canonical intent
  - adding support for a new agent runtime
  - changing adapter generation or adapter quality checks
review_required: false
provenance: "Harvested from the adapter quality work on 2026-05-27, where file-existence checks were insufficient to prove that Codex, Claude Code, Hermes, and ChatGPT adapters preserved canonical practice semantics."
---

## Principle

Adapter fidelity must be executable. Do not treat an adapter as correct just because the target file exists or was regenerated. The publish path must include checks that the adapter still carries the canonical semantics needed by that agent.

## Rationale

Agent adapters are lossy by default: each runtime has different instruction surfaces, length tolerance, trigger behavior, and deployment mechanics. A concise adapter can accidentally drop important constraints, while a full-fidelity adapter can become too long for the target agent to follow well. If quality remains a manual impression, drift appears only when a later agent fails to apply the intended rule.

Executable checks turn adapter quality into a repeatable gate. They do not replace human review, but they catch obvious loss of meaning, missing triggers, missing asset IDs, and target-specific requirements before runtime publishing.

## Guidance

When publishing or reviewing adapters:

1. Maintain an adapter quality checklist for each supported target.
2. Check more than file existence:
   - user-facing trigger phrases are present
   - active canonical practice IDs required by the adapter profile are represented
   - published asset IDs are represented
   - target-specific conventions are followed
   - high-fidelity targets retain enough detail to act correctly
3. Run the executable adapter quality check before claiming adapters are publishable.
4. Treat failed quality checks as adapter drift, not as cosmetic formatting issues.
5. Update the check when adding a new adapter target or changing a target's expected instruction surface.

Checks must verify the exact contract surface they claim to protect. If the requirement is "practice appears in Compact Preflight", the check must inspect the Compact Preflight section, not the entire adapter file. If the requirement is "runtime managed block is intact", the check must inspect the managed block, not only the target file's existence.

## Watch Out For

Do not let the check become a brittle text snapshot. It should verify durable meaning signals such as IDs, trigger vocabulary, ownership markers, and required target conventions. Exact wording may vary across adapters.

Do not assume all agents need identical output. Fidelity means preserving the canonical behavior in the form the target agent can actually use.

Do not accept a loose proxy when the contract surface is narrower. Broad text search can hide missing behavior when the same ID appears in references, examples, or unrelated sections.

## Related Practices

- [[META-001]]
- [[META-002]]
- [[META-008]]
- [[RUNTIME-003]]
