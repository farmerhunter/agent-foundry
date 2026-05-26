# Import External Skills

Canonical source: `workflows/import-external-skills.md`

Use when the user says `import skill <source>` or `导入这个 skill <source>`.

External skills are reviewed inputs, not trusted source-of-truth content.

Steps:

1. Capture provenance.
2. Check license.
3. Review scripts and security risks.
4. Review quality and specificity.
5. Extract reusable candidates.
6. Deduplicate against canonical practices.
7. Present extracted candidates for human review.
8. After approval, canonicalize, promote to active when applicable, update the index, and publish relevant adapters.

Never execute external scripts or install dependencies without explicit approval.

