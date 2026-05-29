# Harvest Practices

Canonical source: `workflows/harvest-practices.md`

Use when the user says `harvest practices` or `做一次 harvest practice`.

When harvesting from another project, that project is evidence source only. Locate Agent Foundry before proposing canonical changes. Use `AGENT_FOUNDRY_HOME`, then `~/.agent-foundry/config.yaml`, then the current directory only if it contains canonical markers such as `indexes/practice_index.yaml`, `indexes/asset_index.yaml`, and `workflows/harvest-practices.md`.

Route:

```text
session reconstruction
  -> candidate extraction
  -> classification
  -> dedupe against index
  -> decision
  -> human review
  -> approved canonical update
  -> adapter update
  -> report
```

Keep candidates only if they are reusable, actionable, specific, evidence-backed, and likely to change future agent behavior.

Present a concise review list. For each candidate show title, action, reason, canonical files affected, and adapters affected after approval.

After approval:

```text
merge/create/supersede
  -> promote approved practice to active when applicable
  -> update index
  -> publish relevant adapters
  -> report changed files
```

Before the final report, do a lightweight missed-activation self-check. Record or ask a local agent to record missed evidence only when there is a concrete missed moment and a specific practice ID: the user identified a violation, review found a specific missed trigger, or the agent can name the practice ID, trigger, and risk clearly. Do not record vague self-scoring.

Runtime publishing safety:

- Treat agent runtimes as shared user-owned environments.
- Use managed blocks/imports for central files and ownership markers for generated skill directories.
- Refuse to overwrite unmanaged runtime paths by default.
- Use dry-runs, backups, and explicit human approval before adopting existing runtime paths.
- Keep portable adapter intent separate from machine-local deployment state.
- Store adapter profiles and runtime templates in the repo; store enabled targets, detected paths, and adoption decisions in gitignored local manifests.
- Exclude machine-local runtime manifests from portable snapshots by default.
