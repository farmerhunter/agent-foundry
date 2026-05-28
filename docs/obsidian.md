# Using Agent Foundry with Obsidian

Agent Foundry is structured as an Obsidian-compatible vault. Open the repository root directly in Obsidian to browse practices and visualize relationships.

## Setup

1. Install [Obsidian](https://obsidian.md/).
2. Open the Agent Foundry repository root as a vault.
3. (Optional) Install community plugin **Dataview** for querying practices.

## What Works Out of the Box

- **YAML frontmatter** — Every practice has `id`, `domain`, `type`, `status`, `tags`, `aliases`, `related`.
- **Aliases** — Each practice lists its stable ID as an alias (e.g., `ARCH-001`). Type `[[ARCH-001]]` to link.
- **Wikilinks** — The "Related Practices" section at the bottom of each file uses `[[ID]]` links. These populate the Graph view and backlink panel.
- **Tags** — Frontmatter `tags` are recognized by Obsidian's tag pane.

## Hub Note

Open **[[Agent Foundry]]** for a dashboard with Dataview queries.

## Graph View Tips

1. Open **Graph view** (`Ctrl/Cmd + G`).
2. Enable **Tags** in graph settings to color nodes by domain.
3. Orphan nodes (unlinked notes) may indicate missing `related` entries.

## Single Source of Truth

The canonical indexes are `indexes/practice_index.yaml` and `indexes/asset_index.yaml`.

Do **not** create duplicate Markdown index files. If you need an index in Markdown form, generate it from the YAML (e.g., via a script), do not maintain it by hand.

## Dataview Queries

### Practices by domain
```dataview
TABLE type, status, tags
FROM "practices"
WHERE domain = "architecture"
SORT id ASC
```

### Practices needing review
```dataview
TABLE domain, type, review_required
FROM "practices"
WHERE review_required = true
```

## Recommended Settings

- **Files and links → New link format**: `Shortest path when possible`
- **Files and links → Use Wikilinks**: enabled
- **Editor → Properties in document**: visible

## Keeping Sync Safe

The `.obsidian/` directory is gitignored. Personal Obsidian settings stay local.
