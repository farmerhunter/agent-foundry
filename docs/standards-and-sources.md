# Standards and Sources

This repository intentionally follows common agent-instruction conventions where they are useful, while keeping canonical practices vendor-neutral.

## Adopted Conventions

### `SKILL.md` Skill Folders

Used by Codex/OpenAI-style skills and also aligned with the broader Agent Skills pattern:

```text
skill-name/
  SKILL.md
  references/
  scripts/
  assets/
```

Use this format for Codex and Hermes adapters. Keep `SKILL.md` short and put detailed material under `references/`.

Relevant source:

- OpenAI skills catalog: https://github.com/openai/skills
- OpenAI Academy skills resource: https://academy.openai.com/public/resources/skills

### `AGENTS.md`

Use `AGENTS.md` as the repository-level instruction entry point for coding agents. This repository's `AGENTS.md` defines the canonical workflow and safety rules.

Relevant source:

- AGENTS.md convention: https://agents.md/

### Claude Code Project Instructions

Claude Code commonly uses `CLAUDE.md`, project memory, and slash commands. This repository keeps Claude-specific output under `adapters/claude-code/`.

Relevant sources:

- Claude Code memory: https://docs.anthropic.com/en/docs/claude-code/memory
- Claude Code slash commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands

### ChatGPT Projects / Custom GPTs

ChatGPT adapters use short custom/project instructions plus knowledge files. The instructions act as a dispatcher; detailed workflows and principles live in `adapters/chatgpt/knowledge/`.

### DeepSeek / MiniMax

DeepSeek, MiniMax, and similar providers are treated as underlying model providers, not direct programming-agent adapters in this repository. Use them through a coding agent that has its own adapter.

## Policy for Borrowing External Skills

External skills may be used as references for:

- workflow structure;
- trigger descriptions;
- progressive disclosure;
- adapter packaging;
- scripts or schemas, after review.

External skills should not be imported directly into active adapters without:

1. provenance capture;
2. license review;
3. security review;
4. dedupe against canonical practices;
5. human approval.
