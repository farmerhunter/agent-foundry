---
id: GOV-007
title: Classify package layers before making them active sources
domain: governance
type: principle
status: active
version: 2
created: 2026-06-11
updated: 2026-07-07
tags: [governance, packages, imports, source-of-truth, capability-packs]
aliases:
  - GOV-007
  - classify package layers before import
  - packs are not automatically truth sources
  - do not create a third authority
  - Capability Pack impact check
  - release gate checks capability pack impact
related: [GOV-001, GOV-005, GOV-006, RUNTIME-001, META-004]
applies_when:
  - adding packages, packs, plugins, bundles, snapshots, registries, import formats, or exported archives
  - deciding whether packaged content should become canonical records, runtime dependencies, or generated output
  - importing reusable capability from another project or runtime
  - designing bootstrap packs or optional capability packs
review_required: false
provenance: "Harvested from AF5 capability-pack boundary discussion on 2026-06-11. Revised after Agent Foundry v1.1 release readiness on 2026-07-07, where starter capability packs needed an explicit release-gate impact decision, version updates, and manifest hash verification instead of being treated as incidental docs or generated output."
---

## Principle

Before a package, pack, plugin, bundle, snapshot, or registry is wired into workflows, classify its authority layer. Decide whether it is an export snapshot, import staging artifact, canonical record, generated output, runtime dependency, live upstream authority, or local evidence source.

## Rationale

Packaged content is easy to mistake for a new source of truth. A package can contain valuable practices, assets, scripts, docs, and examples, but that does not mean the package should remain an active runtime authority after import. Without an explicit layer decision, systems drift into three competing truths: the original source project, the imported user records, and the package copy.

## Guidance

Classify package-like artifacts before allowing them to affect canonical records or runtime behavior:

- `source evidence`: original project, runtime folder, external repo, or session material that produced the content.
- `export snapshot`: immutable or versioned package content prepared for review, transfer, or installation.
- `import staging`: reviewed inbox where provenance, license, security, and conflicts are checked.
- `canonical record`: the user's accepted practice, asset, index, or policy after import.
- `generated output`: adapter, runtime skill, helper copy, or derived file generated from canonical records.
- `runtime dependency`: installed executable or external tool needed to run the generated capability.
- `live authority`: an upstream dependency that the system consults at runtime; use only when the lifecycle, versioning, trust, and offline behavior are intentionally designed.

For local-first systems, prefer snapshot import followed by canonical ownership transfer. Keep provenance and upstream version metadata so later update checks can produce diffs, but do not let the imported pack remain a hidden runtime truth source unless that live-dependency model is an explicit design decision.

For a release that changes user-facing workflows, starter behavior, imported/reusable capabilities, or canonical practice guidance, include an explicit Capability Pack impact check before tagging the release. The check should decide one of:

```text
CP impact: none
CP impact: update required
CP impact: deferred with linked issue
```

When an update is required, verify the pack version, member records, catalog metadata, changelog, and manifest hash together. Do not assume a release note, README change, generated adapter update, or runtime publish automatically updates the official pack. Conversely, do not update a pack only because a release is being tagged; update it only when the pack's selected-user value, packaged records, or safe-use guidance actually changed.

## Use This When

- A system introduces capability packs, starter packs, templates, plugin bundles, import archives, or marketplace concepts.
- A project-local helper or document set is being promoted into a reusable capability.
- A package contains executable scripts as well as docs or records.
- A user asks whether imported content should live in Core, a user vault, a pack repository, runtime directories, or the source project.
- A release gate must decide whether official starter packs, optional packs, or transfer packages need version/hash updates.

## Watch Out For

- Do not treat "included in a pack" as the same thing as "canonical after import."
- Do not make user-vault records depend on ad hoc Core code that was not part of a reviewed platform capability.
- Do not execute pack-contained scripts merely because the pack was downloaded or staged.
- Do not let marketplace or registry vocabulary imply a live dependency model before update, trust, conflict, and offline rules exist.
- Do not copy project-local defaults into global package defaults without separating examples from reusable behavior.
- Do not tag a release that changes pack-relevant behavior without recording a `CP impact` decision and verifying affected manifest hashes.
- Do not let generated/runtime publish status substitute for official pack catalog or manifest updates.

## Example

The Tiny IPA role-generic GitHub helpers are strong evidence for a future multi-agent workflow capability pack. The helper scripts, docs, and examples should first be packaged as a reviewed snapshot. After import, the selected User Vault should own the canonical asset record and payload; runtime tools should be generated or installed from that accepted record. The pack snapshot should not remain an independent runtime source of truth.

In Agent Foundry v1.1, collaboration readiness and documentation changes affected the official starter packs. The release gate therefore added a Capability Pack impact check, updated `pack.bootstrap.minimal` and `pack.multi-agent.optional`, and verified catalog manifest hashes before `v1.1.0` was tagged.

## Activation

- Tier: task_router
- Phases: architecture_design, import_design, onboarding_design, package_review, release_readiness, before_runtime_install
- Signals: pack, plugin, bundle, marketplace, import, export, snapshot, starter content, bootstrap content, helper scripts inside package content, release tag, GitHub Release, starter pack update
- Evidence: design or review identifies each package-like artifact as evidence, snapshot, staging, canonical, generated, runtime dependency, or live authority; release readiness records `CP impact` and affected pack versions/hashes when relevant

## Related Practices

- [[GOV-001]]
- [[GOV-005]]
- [[GOV-006]]
- [[RUNTIME-001]]
- [[META-004]]
