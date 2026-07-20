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
    "trae": HOME / ".trae-cn" / "skills",
}

MANAGED_MARKER = ".agent-foundry-managed"
CLAUDE_INCLUDE_START = "<!-- AGENT-FOUNDRY-START -->"
CLAUDE_INCLUDE_END = "<!-- AGENT-FOUNDRY-END -->"
Action = Literal["copy", "upsert-managed-block"]


def copytree_contents(src: Path, dest: Path, apply: bool) -> list[tuple[Action, Path, Path]]:
    copied = planned_tree_copies(src, dest)
    if apply:
        apply_copy_actions(copied)
    return copied


def planned_tree_copies(src: Path, dest: Path) -> list[tuple[Action, Path, Path]]:
    if not src.exists():
        raise SystemExit(f"Adapter source missing: {src}")
    copied: list[tuple[Action, Path, Path]] = []
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        target = dest / rel
        copied.append(("copy", path, target))
    return copied


def apply_copy_actions(copied: list[tuple[Action, Path, Path]]) -> None:
    for _, source, target in copied:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def semantic_manifest_routes(path: Path) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_routes = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("routes:"):
            in_routes = line.split(":", 1)[1].strip() != "[]"
            continue
        if in_routes and line and not line.startswith(" "):
            break
        if not in_routes:
            continue
        stripped = line.strip()
        if stripped.startswith("- target:"):
            if current:
                routes.append(current)
            current = {"target": stripped.split(":", 1)[1].strip().strip('"').strip("'")}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key] = value.strip().strip('"').strip("'")
    if current:
        routes.append(current)
    return routes


def safe_relative_path(value: str) -> Path | None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        return None
    return path


def claude_reference_actions(adapter_root: Path, dest: Path) -> list[tuple[Action, Path, Path]]:
    manifest = adapter_root / "semantic-reachability-manifest.yaml"
    if not manifest.is_file():
        return []

    routes = [route for route in semantic_manifest_routes(manifest) if route.get("target") == "claude-code"]
    actions: list[tuple[Action, Path, Path]] = []
    router = adapter_root / "claude-code" / "CLAUDE.md"
    router_text = router.read_text(encoding="utf-8") if router.is_file() else ""
    for route in routes:
        installed = safe_relative_path(route.get("installed_path", ""))
        target_path = safe_relative_path(route.get("target_path", ""))
        if installed is None or not str(installed).startswith("references/"):
            raise SystemExit(
                "Claude semantic packaging requires a target-local installed_path under references/: "
                f"{route.get('practice_id', '<unknown>')}"
            )
        if target_path is None or target_path != Path("claude-code") / installed:
            raise SystemExit(
                "Claude semantic packaging requires target_path to match the generated reference source: "
                f"{route.get('practice_id', '<unknown>')}"
            )
        source = adapter_root / target_path
        if not source.is_file():
            raise SystemExit(
                "Claude semantic packaging source reference is missing: "
                f"{route.get('target_path', '<unknown>')}"
            )
        text = source.read_text(encoding="utf-8")
        if route.get("practice_id", "") not in text or route.get("source_sha256", "") not in text:
            raise SystemExit(
                "Claude semantic packaging source reference lacks declared provenance: "
                f"{route.get('practice_id', '<unknown>')}"
            )
        if route.get("practice_id", "") not in router_text or str(installed) not in router_text:
            raise SystemExit(
                "Claude semantic router does not declare a readable target-local reference: "
                f"{route.get('practice_id', '<unknown>')}"
            )
        actions.append(("copy", source, dest / "agent-foundry" / installed))
    return actions


def validate_claude_reference_plan(
    adapter_root: Path, dest: Path, copied: list[tuple[Action, Path, Path]]
) -> None:
    expected = claude_reference_actions(adapter_root, dest)
    planned = {(action, source.resolve(), target.resolve()) for action, source, target in copied}
    missing = [
        target
        for action, source, target in expected
        if (action, source.resolve(), target.resolve()) not in planned
    ]
    if missing:
        raise SystemExit(
            "Claude semantic packaging plan omits declared reference copies: "
            + ", ".join(str(path) for path in missing)
        )


def log_adoption(path: Path, action: str) -> None:
    log_path = ROOT / "sync" / "local" / "adoption-log.yaml"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    entry = f"- timestamp: {timestamp}\n  path: {path}\n  action: {action}\n"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        if "adoptions:" not in existing:
            existing = "adoptions:\n" + existing
        log_path.write_text(existing.rstrip("\n") + "\n" + entry, encoding="utf-8")
    else:
        log_path.write_text("adoptions:\n" + entry, encoding="utf-8")


def ensure_managed_dir(dest: Path, apply: bool, adopt: bool) -> None:
    marker = dest / MANAGED_MARKER
    existed = dest.exists()
    was_unmanaged = existed and not marker.exists()
    if dest.exists() and not marker.exists() and not adopt:
        raise SystemExit(
            f"Refusing to overwrite unmanaged directory: {dest}\n"
            f"Use --adopt to manage this directory with Agent Foundry."
        )
    if apply:
        dest.mkdir(parents=True, exist_ok=True)
        marker.write_text("managed-by: agent-foundry\n", encoding="utf-8")
        if was_unmanaged:
            log_adoption(dest, "adopt")
        elif not existed:
            log_adoption(dest, "create")


def copy_skill_dirs(src: Path, dest: Path, apply: bool, adopt: bool) -> list[tuple[Action, Path, Path]]:
    if not src.exists():
        raise SystemExit(f"Adapter source missing: {src}")
    copied: list[tuple[Action, Path, Path]] = []
    for skill_dir in sorted(path for path in src.iterdir() if path.is_dir()):
        target_dir = dest / skill_dir.name
        ensure_managed_dir(target_dir, apply, adopt)
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


def upsert_managed_block(source: Path, path: Path, block: str, apply: bool, backup: bool) -> list[tuple[Action, Path, Path]]:
    copied = [("upsert-managed-block", source, path)]
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


def sync_codex(adapter_root: Path, dest: Path, apply: bool, adopt: bool) -> list[tuple[Action, Path, Path]]:
    src = adapter_root / "codex" / "skills"
    return copy_skill_dirs(src, dest, apply, adopt)


def sync_hermes(adapter_root: Path, dest: Path, apply: bool, adopt: bool) -> list[tuple[Action, Path, Path]]:
    src = adapter_root / "hermes" / "skills"
    return copy_skill_dirs(src, dest, apply, adopt)


def sync_trae(adapter_root: Path, dest: Path, apply: bool, adopt: bool) -> list[tuple[Action, Path, Path]]:
    src = adapter_root / "trae" / "skills"
    return copy_skill_dirs(src, dest, apply, adopt)


def sync_claude(adapter_root: Path, dest: Path, apply: bool, backup: bool) -> list[tuple[Action, Path, Path]]:
    copied: list[tuple[Action, Path, Path]] = []
    src_root = adapter_root / "claude-code"

    claude_md = src_root / "CLAUDE.md"
    if not claude_md.exists():
        raise SystemExit(f"Adapter source missing: {claude_md}")
    managed_claude = dest / "agent-foundry" / "CLAUDE.md"
    reference_actions = claude_reference_actions(adapter_root, dest)
    validate_claude_reference_plan(adapter_root, dest, [("copy", claude_md, managed_claude), *reference_actions])
    copied.append(("copy", claude_md, managed_claude))
    if apply:
        managed_claude.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(claude_md, managed_claude)

    user_claude = dest / "CLAUDE.md"
    copied.extend(upsert_managed_block(claude_md, user_claude, managed_block(managed_claude), apply, backup))

    commands_src = src_root / "commands"
    commands_dest = dest / "commands" / "agent-foundry"
    copied.extend(copytree_contents(commands_src, commands_dest, apply))
    copied.extend(reference_actions)
    if apply:
        apply_copy_actions(reference_actions)
    return copied


def sync_chatgpt(adapter_root: Path, dest: Path | None, apply: bool) -> list[tuple[Action, Path, Path]]:
    src = adapter_root / "chatgpt"
    if not src.exists():
        raise SystemExit(f"Adapter source missing: {src}")
    print("ChatGPT has no managed local runtime. Import these generated files manually:")
    print(f"- {src / 'custom-instructions.md'}")
    print(f"- {src / 'knowledge'}")
    if dest is not None:
        print(f"manual target destination ignored: {dest}")
    if apply and dest is not None:
        raise SystemExit("Refusing managed ChatGPT runtime write; ChatGPT remains manual-import only.")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Agent Foundry adapters.")
    parser.add_argument(
        "--target",
        choices=["all", "codex", "claude-code", "hermes", "trae", "chatgpt"],
        default="all",
    )
    parser.add_argument("--dest", help="Override destination for a single target.")
    parser.add_argument("--apply", action="store_true", help="Actually copy files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies only.")
    parser.add_argument("--adopt", action="store_true", help="Adopt unmanaged skill directories into Agent Foundry management.")
    parser.add_argument("--force", action="store_true", dest="adopt", help=argparse.SUPPRESS)
    parser.add_argument("--no-backup", action="store_true", help="Do not back up CLAUDE.md before editing its managed block.")
    parser.add_argument("--adapter-root", default="", help="Adapter output root to install from. Defaults to <core>/adapters.")
    args = parser.parse_args()

    apply = bool(args.apply)
    if args.dry_run:
        apply = False

    targets = ["codex", "claude-code", "hermes", "trae", "chatgpt"] if args.target == "all" else [args.target]
    if args.dest and len(targets) != 1:
        raise SystemExit("--dest can only be used with a single --target")

    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else ROOT / "adapters"
    all_copied: list[tuple[Action, Path, Path]] = []
    for target in targets:
        dest = Path(args.dest).expanduser() if args.dest else DEFAULT_DESTS.get(target)
        if target == "codex":
            all_copied.extend(sync_codex(adapter_root, dest, apply, args.adopt))
        elif target == "claude-code":
            all_copied.extend(sync_claude(adapter_root, dest, apply, not args.no_backup))
        elif target == "hermes":
            all_copied.extend(sync_hermes(adapter_root, dest, apply, args.adopt))
        elif target == "trae":
            all_copied.extend(sync_trae(adapter_root, dest, apply, args.adopt))
        elif target == "chatgpt":
            all_copied.extend(sync_chatgpt(adapter_root, Path(args.dest).expanduser() if args.dest else None, apply))

    for action, src, dest in all_copied:
        mode = action if apply else f"would {action}"
        try:
            src_label = src.relative_to(ROOT)
        except ValueError:
            src_label = src
        print(f"{mode}: {src_label} -> {dest}")
    if not all_copied:
        print("No files copied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
