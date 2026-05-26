#!/usr/bin/env python3
"""Sync Agent Foundry adapters into local agent runtime directories.

Default is dry-run. Use --apply to write files.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()


DEFAULT_DESTS = {
    "codex": HOME / ".codex" / "skills",
    "claude-code": HOME / ".claude",
    "hermes": HOME / ".hermes" / "skills",
}

MANAGED_MARKER = ".agent-foundry-managed"
CLAUDE_INCLUDE_START = "<!-- AGENT-FOUNDRY-START -->"
CLAUDE_INCLUDE_END = "<!-- AGENT-FOUNDRY-END -->"
Action = Literal["copy", "upsert-managed-block"]


def copytree_contents(src: Path, dest: Path, apply: bool) -> list[tuple[Action, Path, Path]]:
    copied: list[tuple[Action, Path, Path]] = []
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        target = dest / rel
        copied.append(("copy", path, target))
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return copied


def ensure_managed_dir(dest: Path, apply: bool, force: bool) -> None:
    marker = dest / MANAGED_MARKER
    if dest.exists() and not marker.exists() and not force:
        raise SystemExit(
            f"Refusing to overwrite unmanaged directory: {dest}\n"
            f"Use --force only after confirming this directory should be managed by Agent Foundry."
        )
    if apply:
        dest.mkdir(parents=True, exist_ok=True)
        marker.write_text("managed-by: agent-foundry\n", encoding="utf-8")


def copy_skill_dirs(src: Path, dest: Path, apply: bool, force: bool) -> list[tuple[Action, Path, Path]]:
    copied: list[tuple[Action, Path, Path]] = []
    for skill_dir in sorted(path for path in src.iterdir() if path.is_dir()):
        target_dir = dest / skill_dir.name
        ensure_managed_dir(target_dir, apply, force)
        copied.extend(copytree_contents(skill_dir, target_dir, apply))
    return copied


def backup_file(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup)
    return backup


def managed_block(import_path: Path) -> str:
    return "\n".join(
        [
            CLAUDE_INCLUDE_START,
            "# Agent Foundry managed instructions",
            f"@{import_path}",
            CLAUDE_INCLUDE_END,
            "",
        ]
    )


def upsert_managed_block(path: Path, block: str, apply: bool, backup: bool) -> list[tuple[Action, Path, Path]]:
    copied = [("upsert-managed-block", ROOT / "adapters" / "claude-code" / "CLAUDE.md", path)]
    if not apply:
        return copied

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if backup and path.exists():
        backup_file(path)

    if CLAUDE_INCLUDE_START in existing and CLAUDE_INCLUDE_END in existing:
        before, rest = existing.split(CLAUDE_INCLUDE_START, 1)
        _, after = rest.split(CLAUDE_INCLUDE_END, 1)
        updated = before.rstrip() + "\n\n" + block + after.lstrip()
    else:
        updated = existing.rstrip() + "\n\n" + block if existing.strip() else block

    path.write_text(updated, encoding="utf-8")
    return copied


def sync_codex(dest: Path, apply: bool, force: bool) -> list[tuple[Action, Path, Path]]:
    src = ROOT / "adapters" / "codex" / "skills"
    return copy_skill_dirs(src, dest, apply, force)


def sync_hermes(dest: Path, apply: bool, force: bool) -> list[tuple[Action, Path, Path]]:
    src = ROOT / "adapters" / "hermes" / "skills"
    return copy_skill_dirs(src, dest, apply, force)


def sync_claude(dest: Path, apply: bool, backup: bool) -> list[tuple[Action, Path, Path]]:
    copied: list[tuple[Action, Path, Path]] = []
    src_root = ROOT / "adapters" / "claude-code"

    claude_md = src_root / "CLAUDE.md"
    managed_claude = dest / "agent-foundry" / "CLAUDE.md"
    copied.append(("copy", claude_md, managed_claude))
    if apply:
        managed_claude.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(claude_md, managed_claude)

    user_claude = dest / "CLAUDE.md"
    copied.extend(upsert_managed_block(user_claude, managed_block(managed_claude), apply, backup))

    commands_src = src_root / "commands"
    commands_dest = dest / "commands" / "agent-foundry"
    copied.extend(copytree_contents(commands_src, commands_dest, apply))
    return copied


def sync_chatgpt(dest: Path | None, apply: bool) -> list[tuple[Action, Path, Path]]:
    src = ROOT / "adapters" / "chatgpt"
    if dest is None:
        print("ChatGPT has no default local runtime. Use these files manually:")
        print(f"- {src / 'custom-instructions.md'}")
        print(f"- {src / 'knowledge'}")
        return []
    return copytree_contents(src, dest, apply)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Agent Foundry adapters.")
    parser.add_argument(
        "--target",
        choices=["all", "codex", "claude-code", "hermes", "chatgpt"],
        default="all",
    )
    parser.add_argument("--dest", help="Override destination for a single target.")
    parser.add_argument("--apply", action="store_true", help="Actually copy files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies only.")
    parser.add_argument("--force", action="store_true", help="Overwrite unmanaged skill directories.")
    parser.add_argument("--no-backup", action="store_true", help="Do not back up CLAUDE.md before editing its managed block.")
    args = parser.parse_args()

    apply = bool(args.apply)
    if args.dry_run:
        apply = False

    targets = ["codex", "claude-code", "hermes", "chatgpt"] if args.target == "all" else [args.target]
    if args.dest and len(targets) != 1:
        raise SystemExit("--dest can only be used with a single --target")

    all_copied: list[tuple[Action, Path, Path]] = []
    for target in targets:
        dest = Path(args.dest).expanduser() if args.dest else DEFAULT_DESTS.get(target)
        if target == "codex":
            all_copied.extend(sync_codex(dest, apply, args.force))
        elif target == "claude-code":
            all_copied.extend(sync_claude(dest, apply, not args.no_backup))
        elif target == "hermes":
            all_copied.extend(sync_hermes(dest, apply, args.force))
        elif target == "chatgpt":
            all_copied.extend(sync_chatgpt(Path(args.dest).expanduser() if args.dest else None, apply))

    for action, src, dest in all_copied:
        mode = action if apply else f"would {action}"
        print(f"{mode}: {src.relative_to(ROOT)} -> {dest}")
    if not all_copied:
        print("No files copied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
