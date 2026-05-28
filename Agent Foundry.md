---
id: foundry-hub
title: Agent Foundry Hub
domain: meta
type: hub
status: active
tags: [hub, index, obsidian]
aliases:
  - Foundry Hub
  - Agent Foundry
---

# Agent Foundry

Canonical source of truth: `indexes/practice_index.yaml` and `indexes/asset_index.yaml`.

## Quick Navigation

- **Practices**: `practices/` — canonical rules by domain
- **Assets**: `assets/` — reusable skills, subagents, automations
- **Indexes**: `indexes/` — canonical registry files (YAML)
- **Adapters**: `adapters/` — agent-specific published outputs

## Practice Registry

```dataview
TABLE domain, type, status, tags
FROM "practices"
SORT domain ASC, id ASC
```

## Active Principles

```dataview
TABLE domain, title, tags
FROM "practices"
WHERE type = "principle" AND status = "active"
SORT domain ASC, id ASC
```

## Recently Updated

```dataview
TABLE updated, domain, type
FROM "practices"
SORT updated DESC
LIMIT 10
```

## Graph View

Open **Graph view** to see practice relationships via `[[ID]]` wikilinks.
