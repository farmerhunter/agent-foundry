---
id: IMPL-001
title: Avoid shell-interpreted Markdown in CLI comments
domain: implementation
type: anti-pattern
status: active
version: 2
created: 2026-05-26
updated: 2026-07-06
tags: [cli, github, markdown, shell-quoting, comments, body-file]
aliases:
  - IMPL-001
  - use body-file for gh comments
  - avoid backticks in double-quoted shell bodies
  - use uppercase form flags for gh api body files
related: [COLLAB-002]
applies_when:
  - posting GitHub comments through gh
  - passing Markdown through a shell command
  - comment text contains backticks, dollar signs, or command examples
review_required: false
provenance: "Harvested from 2026AgentApp issue comment quoting failure. Revised on 2026-07-06 after Agent Foundry AF15 HDC comments were accidentally posted as literal temporary-file paths because `gh api -f body=@file` was used instead of a file-reading form."
---

## Principle

Do not pass Markdown containing shell-significant characters directly inside double-quoted CLI arguments.

## Rationale

Backticks, dollar signs, and substitutions can be interpreted by the shell before the CLI receives the text. This can execute unintended commands, corrupt comments, and produce misleading local errors.

## Guidance

For `gh issue comment`, `gh pr comment`, or similar commands, write complex Markdown to a temporary file and use `--body-file`, or use a safely quoted here-doc that prevents interpolation. Prefer this whenever the body includes backticks, code fences, `$`, or command examples.

For lower-level GitHub API calls, verify whether the CLI flag reads a file or sends a literal string. In `gh api`, use a file-reading form such as `-F body=@/path/to/comment.md` when the endpoint expects a text body. Do not assume `-f body=@/path/to/comment.md` behaves like `--body-file`; in affected `gh` versions it can send the literal `@/path/to/comment.md` string and create a durable placeholder comment.

After posting important GitHub comments through a nonstandard API path, read back the first line or comment URL before continuing. If a placeholder or malformed body was posted, patch the comment immediately with the correct file-reading form and record the correction.

## Use This When

- Posting completion notes with command examples.
- Closing issues with Markdown summaries.
- Generating comments from scripts.

## Watch Out For

- Avoid `--body "ran \`npm test\`"` because the shell can execute the backticked text.
- Do not hide command-substitution errors if the remote mutation still partially succeeds.
- Do not treat all `gh` file flags as interchangeable. `gh issue comment --body-file`, `gh pr comment --body-file`, and `gh api -F body=@file` are different interfaces.
- Do not leave a literal temp-path placeholder in a durable issue or PR comment after discovering the upload form was wrong.

## Example

Instead of `gh issue comment 21 --body "Ran \`python script.py\`"`, create a body file and run `gh issue comment 21 --body-file /tmp/comment.md`.

For REST endpoints that do not expose `--body-file`, prefer:

```bash
gh api repos/OWNER/REPO/issues/123/comments -F body=@/tmp/comment.md
```

Avoid:

```bash
gh api repos/OWNER/REPO/issues/123/comments -f body=@/tmp/comment.md
```

unless a current `gh` help/readback check proves that flag reads the file for that endpoint.

## Related Practices

- [[COLLAB-002]]
