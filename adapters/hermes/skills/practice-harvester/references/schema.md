# Practice Schema Reference

Canonical source: `schemas/practice-entry.schema.yaml`

Required frontmatter:

```yaml
id:
title:
domain:
type:
status:
version:
created:
updated:
tags:
```

Recommended frontmatter:

```yaml
aliases:
related:
supersedes:
superseded_by:
applies_when:
review_required:
provenance:
```

Required sections:

- `Principle`
- `Rationale`
- `Guidance`

Only `active` and `revised` entries are published into default adapters.

