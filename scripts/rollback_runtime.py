#!/usr/bin/env python3
"""Rollback Agent Foundry managed runtime changes.

Provides safe recovery paths for:
- Restoring ~/.claude/CLAUDE.md from backups
- Removing managed skill directories
- Removing managed include blocks
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


HOME = Path.home()
CLAUDE_MD = HOME / ".claude" / "CLAUDE.md"
CLAUDE_BACKUP_GLOB = "CLAUDE.md.bak.*"
MANAGED_MARKER = ".agent-foundry-managed"
CLAUDE_INCLUDE_START = "<!-- AGENT-FOUNDRY-START -->"
CLAUDE_INCLUDE_END = "<!-- AGENT-FOUNDRY-END -->"

SKILL_ROOTS = {
    "codex": HOME / ".codex" / "skills",
    "hermes": HOME / ".hermes" / "skills",
}


def list_claude_backups() -> list[Path]:
    if not CLAUDE_MD.parent.exists():
        return []
    return sorted(CLAUDE_MD.parent.glob(CLAUDE_BACKUP_GLOB))


def restore_claude(backup_path: Path | None, dry_run: bool) -> None:
    if backup_path is None:
        backups = list_claude_backups()
        if not backups:
            raise SystemExit("No backups found in ~/.claude/")
        backup_path = backups[-1]

    if not backup_path.exists():
        raise SystemExit(f"Backup not found: {backup_path}")

    print(f"{'Would restore' if dry_run else 'Restoring'} {CLAUDE_MD}")
    print(f"  from: {backup_path}")
    if not dry_run:
        CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, CLAUDE_MD)
        print("Restored.")


def remove_managed_block(dry_run: bool) -> None:
    print(f"{'Would remove' if dry_run else 'Removing'} managed block from {CLAUDE_MD}")
    if not CLAUDE_MD.exists():
        print("File does not exist. Nothing to do.")
        return

    text = CLAUDE_MD.read_text(encoding="utf-8")
    if CLAUDE_INCLUDE_START not in text:
        print("No managed block found. Nothing to do.")
        return

    if not dry_run:
        start = text.find(CLAUDE_INCLUDE_START)
        end = text.find(CLAUDE_INCLUDE_END)
        if start == -1 or end == -1 or end < start:
            raise SystemExit("Managed block is malformed. Aborting.")
        before = text[:start].rstrip()
        after = text[end + len(CLAUDE_INCLUDE_END) :].lstrip()
        updated = ""
        if before and after:
            updated = before + "\n\n" + after
        elif before:
            updated = before
        elif after:
            updated = after
        CLAUDE_MD.write_text(updated.strip() + "\n" if updated.strip() else "\n", encoding="utf-8")
        print("Managed block removed.")


def remove_skill(target: str, name: str, dry_run: bool, force: bool) -> None:
    root = SKILL_ROOTS.get(target)
    if not root:
        raise SystemExit(f"Unknown target: {target}")

    skill_dir = root / name
    marker = skill_dir / MANAGED_MARKER

    if not skill_dir.exists():
        raise SystemExit(f"Skill directory not found: {skill_dir}")

    if not marker.exists() and not force:
        raise SystemExit(
            f"Refusing to remove unmanaged directory: {skill_dir}\n"
            f"Use --force only if you are certain this directory should be removed."
        )

    print(f"{'Would remove' if dry_run else 'Removing'} {skill_dir}")
    if not dry_run:
        shutil.rmtree(skill_dir)
        print("Removed.")


def show_status() -> None:
    print("## Claude Code")
    if CLAUDE_MD.exists():
        text = CLAUDE_MD.read_text(encoding="utf-8")
        has_block = CLAUDE_INCLUDE_START in text
        print(f"  {CLAUDE_MD}: managed block present = {has_block}")
        backups = list_claude_backups()
        print(f"  Backups: {len(backups)}")
        for b in backups:
            print(f"    - {b.name}")
    else:
        print(f"  {CLAUDE_MD}: does not exist")

    print("\n## Codex")
    codex_root = SKILL_ROOTS["codex"]
    if codex_root.exists():
        for path in sorted(codex_root.iterdir()):
            if path.is_dir():
                marker = path / MANAGED_MARKER
                print(f"  {path.name}: managed = {marker.exists()}")
    else:
        print(f"  {codex_root}: does not exist")

    print("\n## Hermes")
    hermes_root = SKILL_ROOTS["hermes"]
    if hermes_root.exists():
        for path in sorted(hermes_root.iterdir()):
            if path.is_dir():
                marker = path / MANAGED_MARKER
                print(f"  {path.name}: managed = {marker.exists()}")
    else:
        print(f"  {hermes_root}: does not exist")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback Agent Foundry runtime changes.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show managed runtime state and available backups")

    list_backups = sub.add_parser("list-backups", help="List available backups")
    list_backups.add_argument("--target", default="claude", choices=["claude"])

    restore = sub.add_parser("restore-claude", help="Restore ~/.claude/CLAUDE.md from backup")
    restore.add_argument("--backup", help="Specific backup path. Uses latest if omitted.")
    restore.add_argument("--dry-run", action="store_true", help="Show what would be done.")

    rm_block = sub.add_parser("remove-block", help="Remove managed include block from ~/.claude/CLAUDE.md")
    rm_block.add_argument("--target", default="claude-code", choices=["claude-code"])
    rm_block.add_argument("--dry-run", action="store_true")

    rm_skill = sub.add_parser("remove-skill", help="Remove a managed skill directory")
    rm_skill.add_argument("name", help="Skill directory name")
    rm_skill.add_argument("--target", required=True, choices=["codex", "hermes"])
    rm_skill.add_argument("--dry-run", action="store_true")
    rm_skill.add_argument("--force", action="store_true", help="Remove even if not managed by Agent Foundry")

    args = parser.parse_args()

    if args.command == "status":
        show_status()
    elif args.command == "list-backups":
        backups = list_claude_backups()
        if not backups:
            print("No backups found.")
        else:
            for b in backups:
                print(b)
    elif args.command == "restore-claude":
        restore_claude(Path(args.backup) if args.backup else None, args.dry_run)
    elif args.command == "remove-block":
        remove_managed_block(args.dry_run)
    elif args.command == "remove-skill":
        remove_skill(args.target, args.name, args.dry_run, args.force)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
