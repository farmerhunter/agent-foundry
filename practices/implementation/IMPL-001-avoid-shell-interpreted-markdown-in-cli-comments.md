---
id: IMPL-001
title: Avoid shell-interpreted Markdown in CLI comments
domain: implementation
type: anti-pattern
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [cli, github, markdown, shell-quoting]
aliases:
  - use body-file for gh comments
  - avoid backticks in double-quoted shell bodies
  - IMPL-001
related: [COLLAB-002]
applies_when:
  - posting GitHub comments through gh
  - passing Markdown through a shell command
  - comment text contains backticks, dollar signs, or command examples
review_required: false
provenance: "Harvested from 2026AgentApp issue comment quoting failure."
---

## Principle

Do not pass Markdown containing shell-significant characters directly inside double-quoted CLI arguments.

## Rationale

Backticks, dollar signs, and substitutions can be interpreted by the shell before the CLI receives the text. This can execute unintended commands, corrupt comments, and produce misleading local errors.

## Guidance

For `gh issue comment`, `gh pr comment`, or similar commands, write complex Markdown to a temporary file and use `--body-file`, or use a safely quoted here-doc that prevents interpolation. Prefer this whenever the body includes backticks, code fences, `$`, or command examples.

## Use This When

- Posting completion notes with command examples.
- Closing issues with Markdown summaries.
- Generating comments from scripts.

## Watch Out For

- Avoid `--body "ran \`npm test\`"` because the shell can execute the backticked text.
- Do not hide command-substitution errors if the remote mutation still partially succeeds.

## Example

Instead of `gh issue comment 21 --body "Ran \`python script.py\`"`, create a body file and run `gh issue comment 21 --body-file /tmp/comment.md`.

## Related Practices

- [[COLLAB-002]]
