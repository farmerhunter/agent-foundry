# Adapter Quality Checklist

Use this checklist before publishing or installing adapters.

## Universal

- Adapter outputs listed in `adapters/adapter_profiles.yaml` exist.
- Short command vocabulary from the adapter profile is present in adapter output.
- Included active/revised canonical practice IDs are visible, either directly or through an explicit range such as `ARCH-001 through ARCH-006`.
- Published asset IDs are visible for audit.
- Candidate/proposed/deprecated/retired content is not published into default adapters.
- Runtime deployment rules preserve managed blocks, ownership markers, and local manifest boundaries.

## Codex

- Skills have concise triggers in `SKILL.md`.
- Detailed behavior is placed in references when it would bloat the skill body.
- Canonical IDs and asset IDs remain discoverable from the skill folder.

## Claude Code

- `CLAUDE.md` is a dispatcher and durable-rule surface, not a dump of every reference.
- Workflow-specific details live in command files or referenced project files.
- Managed runtime install uses `~/.claude/agent-foundry/` plus a managed import block.

## Hermes

- Keep higher fidelity than compact prompt-only tools because Hermes may operate in a freer style.
- Preserve operational references similarly to Codex.
- Do not disable Hermes native memory, autonomous skill creation, or local self-improvement.

## ChatGPT

- Keep custom instructions short.
- Put full workflow/schema/practice material in knowledge files.
- Manual import steps must be explicit because ChatGPT has no stable local runtime directory.
