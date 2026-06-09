#!/usr/bin/env python3
"""Run local split-root validation fixtures."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_foundry_roots.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_check(core_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK),
            "--core-root",
            str(core_root),
            "--vault-root",
            str(vault_root),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_blank_vault(path: Path) -> None:
    write(
        path / "indexes" / "practice_index.yaml",
        "schema_version: 1\nupdated: 2026-06-09\n\ndomains: {}\n\npractices: []\n",
    )
    write(
        path / "indexes" / "asset_index.yaml",
        "schema_version: 1\nupdated: 2026-06-09\n\nasset_types: {}\n\nassets: []\n",
    )
    write(path / "usage" / "usage-aggregate.yaml", "schema_version: 1\nupdated: 2026-06-09\n\naggregates: []\n")
    (path / "practices").mkdir(parents=True, exist_ok=True)
    (path / "assets").mkdir(parents=True, exist_ok=True)


def make_maintainer_like_vault(path: Path) -> None:
    for name in ["indexes", "practices", "assets", "usage"]:
        source = ROOT / name
        target = path / name
        if source.is_dir():
            shutil.copytree(source, target)


def expect(name: str, result: subprocess.CompletedProcess[str], should_pass: bool, expected_text: str = "") -> list[str]:
    passed = result.returncode == 0
    if passed == should_pass and (not expected_text or expected_text in (result.stdout + result.stderr)):
        print(f"{name}: ok")
        return []
    output = (result.stdout + result.stderr).strip()
    return [
        f"{name}: expected {'pass' if should_pass else 'failure'}"
        + (f" containing {expected_text!r}" if expected_text else "")
        + f", got exit {result.returncode}\n{output}"
    ]


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-root-fixtures-") as tmp:
        base = Path(tmp)

        errors.extend(expect("same-root", run_check(ROOT, ROOT), True))

        blank = base / "blank-vault"
        make_blank_vault(blank)
        errors.extend(expect("blank-vault", run_check(ROOT, blank), True))

        maintainer_like = base / "maintainer-like-vault"
        make_maintainer_like_vault(maintainer_like)
        errors.extend(expect("maintainer-like-vault", run_check(ROOT, maintainer_like), True))

        missing = base / "missing-vault"
        make_blank_vault(missing)
        (missing / "indexes" / "asset_index.yaml").unlink()
        errors.extend(expect("missing-vault", run_check(ROOT, missing), False, "vault marker missing"))

        corrupt = base / "corrupt-vault"
        make_blank_vault(corrupt)
        write(corrupt / "indexes" / "practice_index.yaml", "schema_version: 1\nupdated: 2026-06-09\n")
        errors.extend(expect("corrupt-vault", run_check(ROOT, corrupt), False, "index missing required list: practices"))

    if errors:
        print("Split-root fixture tests failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Split-root fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
