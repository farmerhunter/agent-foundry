---
id: TEST-001
title: Render-verify format conversions
domain: testing
type: checklist
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [documents, conversion, rendering, verification]
aliases:
  - TEST-001
  - verify generated documents visually
  - conversion requires render checks
related: []
applies_when:
  - converting Markdown, SVG, DOCX, PDF, images, or presentations
  - generating deliverables with non-ASCII text
  - preparing user-facing document artifacts
review_required: false
provenance: "Harvested from 2026AgentApp technical document and SVG-to-PNG conversion work."
---

## Principle

Generated or converted document artifacts must be checked by rendered output, not only by command success.

## Rationale

Format conversion can succeed while silently breaking layout, fonts, encoding, images, or non-ASCII text. Rendered inspection catches failures that structural file checks miss.

## Guidance

After conversion, verify source-to-output structure and rendered appearance. Check headings, tables, images, code blocks, list counts, font consistency, encoding, and representative text. For documents with Chinese or other non-ASCII text, inspect the rendered artifact or exported image to confirm characters display correctly.

## Use This When

- Converting Markdown to DOCX, PDF, or HTML.
- Inserting SVGs into Word or presentation files.
- Producing competition, client, or publication deliverables.

## Watch Out For

- Do not treat "file generated" as "file correct".
- Do not assume fonts available on the development machine exist in the review environment.

## Example

When regenerating a technical document, compare Markdown counts for headings, images, lists, tables, and code blocks against the DOCX, then inspect rendered pages or image exports for Chinese text and layout quality.

## Activation

- Tier: always_preflight
- Phases: verification, final_report
- Signals: converting Markdown, SVG, DOCX, PDF, images, slides, spreadsheets, or other user-facing artifacts; producing rendered output with non-ASCII text
- Evidence: final report names the rendered artifact inspected or the fallback verification used
