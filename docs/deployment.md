# Deployment

Agent Foundry is local-first. The repository is the canonical workspace; installed agent runtime files are downstream copies.

```text
Agent Foundry repo
  -> generated adapters
  -> installed runtime copies
  -> real agent usage
  -> usage evidence back into Agent Foundry
```

## Boundaries

- `practices/`, `assets/`, `indexes/`, `usage/`: canonical vault.
- `workflows/`, `schemas/`, `scripts/`, `templates/`: Foundry system.
- `adapters/`: generated or maintained adapter outputs.
- Installed runtime locations: downstream copies, not source of truth.

## Codex

Adapter source:

```text
adapters/codex/skills/
```

Typical install target:

```text
~/.codex/skills/
```

Install with dry run:

```bash
python3 scripts/sync_adapters.py --target codex --dry-run
```

Apply:

```bash
python3 scripts/sync_adapters.py --target codex --apply
```

## Claude Code

Adapter source:

```text
adapters/claude-code/CLAUDE.md
adapters/claude-code/commands/
```

Runtime target:

```text
~/.claude/agent-foundry/CLAUDE.md
~/.claude/commands/agent-foundry/
~/.claude/CLAUDE.md
```

`~/.claude/CLAUDE.md` is a shared user-level instruction file. Agent Foundry must not replace the whole file. The sync script writes the generated instructions into `~/.claude/agent-foundry/CLAUDE.md` and inserts or updates only a small managed import block in `~/.claude/CLAUDE.md`:

```text
<!-- AGENT-FOUNDRY-START -->
# Agent Foundry managed instructions
@/Users/<user>/.claude/agent-foundry/CLAUDE.md
<!-- AGENT-FOUNDRY-END -->
```

Before editing an existing `~/.claude/CLAUDE.md`, the script creates a timestamped backup unless `--no-backup` is passed.

Dry run:

```bash
python3 scripts/sync_adapters.py --target claude-code --dry-run
```

## Hermes

Adapter source:

```text
adapters/hermes/skills/
```

Install into your Hermes custom skills directory. Do not disable Hermes native memory, autonomous skill creation, or local self-improvement. Agent Foundry governs durable cross-agent outputs; Hermes native growth remains an upstream candidate source.

Dry run:

```bash
python3 scripts/sync_adapters.py --target hermes --dry-run
```

## Runtime Collision Policy

Adapters are deployment artifacts, not canonical practice records. Runtime sync should preserve user and tool-owned files.

- Central files such as `~/.claude/CLAUDE.md` use managed blocks or imports, not full replacement.
- Skill directories use `.agent-foundry-managed` markers.
- If a Codex or Hermes target skill directory already exists without the marker, sync refuses to overwrite it by default.
- Use `--force` only after confirming the existing directory should become Agent Foundry managed.
- ChatGPT remains manually mediated because it has no stable local runtime directory.

## ChatGPT

Adapter source:

```text
adapters/chatgpt/custom-instructions.md
adapters/chatgpt/knowledge/
```

ChatGPT does not have a local file runtime in the same way. Use these files as Project instructions / Custom GPT instructions and uploaded knowledge files.

Recommended:

1. Put `custom-instructions.md` into project/custom GPT instructions.
2. Upload files under `knowledge/`.
3. Re-upload after adapter updates.

## Safety

- Run `python3 scripts/check_consistency.py` before installing.
- Use `--dry-run` first.
- Treat Agent Foundry managed runtime files as replaceable copies.
- Treat unmarked runtime files as user/tool-owned until explicitly adopted.
- Keep Agent Foundry repo as source of truth.
