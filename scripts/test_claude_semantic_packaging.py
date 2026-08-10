#!/usr/bin/env python3
"""Regression coverage for Claude target-local semantic reference packaging."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import sync_adapters
from foundry_config import CONFIG_PATH, parse_config


ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
QUALITY = ROOT / "scripts" / "check_adapter_quality.py"
SYNC = ROOT / "scripts" / "sync_adapters.py"


def configured_vault_root() -> Path:
    data = parse_config(CONFIG_PATH)
    vault_root = data.get("vault_root", "")
    if isinstance(vault_root, str) and vault_root:
        return Path(vault_root).expanduser().resolve()
    raise RuntimeError("configured vault_root missing")


def digest_tree(path: Path) -> dict[str, str]:
    return {
        str(file_path.relative_to(path)): hashlib.sha256(file_path.read_bytes()).hexdigest()
        for file_path in sorted(candidate for candidate in path.rglob("*") if candidate.is_file())
    }


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def main() -> int:
    vault_root = configured_vault_root()
    vault_before = digest_tree(vault_root)
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="agent-foundry-claude-semantic-") as tmp:
        base = Path(tmp)
        generated = base / "generated"
        runtime = base / "runtime" / "claude"

        publish = run(
            [
                str(PUBLISH),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault_root),
                "--output-root",
                str(generated),
                "--apply",
            ]
        )
        if publish.returncode != 0:
            errors.append(f"publish failed:\n{output(publish)}")

        quality = run(
            [
                str(QUALITY),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault_root),
                "--surface",
                "selected-output",
                "--generated-root",
                str(generated),
            ]
        )
        if quality.returncode != 0:
            errors.append(f"selected-output quality failed:\n{output(quality)}")

        router = generated / "claude-code" / "CLAUDE.md"
        semantic = generated / "semantic-reachability-manifest.yaml"
        router_text = router.read_text(encoding="utf-8") if router.exists() else ""
        semantic_text = semantic.read_text(encoding="utf-8") if semantic.exists() else ""
        for practice_id in ["ARCH-001", "ARCH-006", "ARCH-010", "ARCH-011"]:
            installed = f"references/architecture-design/{practice_id}.md"
            generated_path = f"claude-code/references/architecture-design/{practice_id}.md"
            if installed not in router_text or generated_path in router_text:
                errors.append(f"Claude router lacks target-local locator for {practice_id}")
            if f"installed_path: {installed}" not in semantic_text:
                errors.append(f"semantic manifest lacks installed_path for {practice_id}")

        dry_run = run(
            [
                str(SYNC),
                "--target",
                "claude-code",
                "--adapter-root",
                str(generated),
                "--dest",
                str(runtime),
                "--dry-run",
            ]
        )
        if dry_run.returncode != 0:
            errors.append(f"Claude dry-run failed:\n{output(dry_run)}")
        if "agent-foundry/references/architecture-design/ARCH-001.md" not in output(dry_run):
            errors.append("Claude dry-run omitted ARCH-001 target-local reference copy")
        if runtime.exists():
            errors.append("Claude dry-run wrote to isolated runtime root")
        if str(sync_adapters.DEFAULT_DESTS["claude-code"]) in output(dry_run):
            errors.append("Claude dry-run used live runtime instead of isolated destination")

        missing_reference_plan = [
            ("copy", generated / "claude-code" / "CLAUDE.md", runtime / "agent-foundry" / "CLAUDE.md")
        ]
        try:
            sync_adapters.validate_claude_reference_plan(generated, runtime, missing_reference_plan)
        except SystemExit as error:
            if "omits declared reference copies" not in str(error):
                errors.append(f"Claude packaging negative control failed unexpectedly: {error}")
        else:
            errors.append("Claude packaging negative control did not fail closed")

        runtime.mkdir(parents=True)
        user_claude = runtime / "CLAUDE.md"
        user_claude.write_text("# User Claude instructions\n", encoding="utf-8")
        apply = run(
            [
                str(SYNC),
                "--target",
                "claude-code",
                "--adapter-root",
                str(generated),
                "--dest",
                str(runtime),
                "--apply",
            ]
        )
        if apply.returncode != 0:
            errors.append(f"Claude isolated apply failed:\n{output(apply)}")
        if str(sync_adapters.DEFAULT_DESTS["claude-code"]) in output(apply):
            errors.append("Claude isolated apply used a live runtime destination")
        backups = list(runtime.glob("CLAUDE.md.bak.*"))
        if not backups:
            errors.append("Claude isolated apply did not preserve managed-block backup behavior")
        if not (runtime / "commands" / "agent-foundry" / "README.md").is_file():
            errors.append("Claude isolated apply omitted commands packaging")
        for practice_id in ["ARCH-001", "ARCH-006", "ARCH-010", "ARCH-011"]:
            reference = runtime / "agent-foundry" / "references" / "architecture-design" / f"{practice_id}.md"
            if not reference.is_file():
                errors.append(f"Claude isolated apply omitted {practice_id} reference")
                continue
            route = next(
                (
                    item
                    for item in sync_adapters.semantic_manifest_routes(semantic)
                    if item.get("target") == "claude-code" and item.get("practice_id") == practice_id
                ),
                {},
            )
            text = reference.read_text(encoding="utf-8")
            if practice_id not in text or route.get("source_sha256", "") not in text:
                errors.append(f"Claude isolated apply lost provenance for {practice_id}")

    if digest_tree(vault_root) != vault_before:
        errors.append("selected Vault changed during Claude semantic packaging test")

    if errors:
        print("Claude semantic packaging tests failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Claude semantic packaging tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
