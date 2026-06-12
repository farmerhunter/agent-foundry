---
id: RUNTIME-002
title: Separate portable adapter intent from machine-local deployment state
domain: runtime
type: principle
status: active
version: 2
created: 2026-05-26
updated: 2026-06-11
tags: [runtime, deployment, manifest, offline-sync, portability]
aliases:
  - RUNTIME-002
  - runtime manifest is machine-local
  - keep local deployment state out of git
  - portable snapshots exclude local runtime state
  - runtime tools are machine-local installs
related: [RUNTIME-001, META-001, GOV-007]
applies_when:
  - designing runtime manifests
  - syncing Agent Foundry across machines
  - exporting portable snapshots
  - installing adapters on a new machine
  - installing generated runtime tools from canonical asset payloads
review_required: false
provenance: "Harvested from the runtime manifest redesign on 2026-05-26, where a tracked manifest risked syncing one machine's enabled targets and paths to other machines."
---

## Principle

Separate portable adapter intent from machine-local deployment state. Track adapter profiles and runtime templates in the repository, but keep enabled targets, detected paths, and adoption decisions in gitignored local manifests; portable snapshots must exclude machine-local runtime state by default.

## Rationale

Adapter profiles answer "how should this type of agent be supported?" Runtime manifests answer "where should this machine install Agent Foundry now?" These are different facts. If a local manifest is tracked or included in portable snapshots, one machine's installed agents, paths, and adoption decisions can leak into another machine and cause wrong or unsafe deployments.

## Guidance

Use repository-tracked files for portable intent:

- adapter profiles;
- runtime manifest templates;
- schemas, workflows, and install scripts.

Use gitignored local files for machine-specific state:

- enabled or disabled targets;
- detected runtime paths;
- local adoption decisions;
- machine-specific install notes.
- installed runtime tool copies and receipts derived from canonical asset payloads.

Portable snapshots should include runtime templates but exclude local runtime manifests. New machines should initialize a local manifest from the template, detect available runtimes, and require review before enabling targets.

When canonical assets contain executable payloads, keep the portable source and policy in the selected Vault, but put executable copies, wrappers, chmod state, dependency probes, and install receipts in machine-local runtime/tool state. Another machine should recreate those runtime copies through refresh/install from its selected Vault rather than inheriting paths or execution state from the original machine.

## Watch Out For

Do not confuse a conservative template with a detected local state. Templates should be safe defaults. Local manifests may enable targets, but that choice belongs to the current machine only.

## Example

Track `runtime/templates/runtime_manifest.template.yaml` in git with local targets disabled by default. Keep `runtime/local/runtime_manifest.yaml` ignored by git, and exclude it from portable snapshots. On a new machine, run `runtime_manifest.py init`, then detect, enable, configure, review, and install.

For a helper-script asset, the Vault may store the accepted source payload, while `~/.agent-foundry/runtime/tools/...` stores the executable installed copy and receipt for the current machine.

## Related Practices

- [[RUNTIME-001]]
- [[META-001]]
- [[GOV-007]]
