#!/usr/bin/env python3
"""Run local split-root validation fixtures."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_foundry_roots.py"
INIT = ROOT / "scripts" / "init_vault.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
MIGRATE = ROOT / "scripts" / "migrate_deployment.py"


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


def run_publish(core_root: Path, vault_root: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PUBLISH),
            "--core-root",
            str(core_root),
            "--vault-root",
            str(vault_root),
            "--output-root",
            str(output_root),
            "--apply",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_plan(core_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(MIGRATE),
            "plan",
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
    result = subprocess.run(
        [sys.executable, str(INIT), str(path), "--core-root", str(ROOT), "--apply"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)


def make_maintainer_like_vault(path: Path) -> None:
    make_blank_vault(path)
    write(
        path / "practices" / "meta" / "META-001-test-maintainer-like-practice.md",
        "\n".join(
            [
                "---",
                "id: META-001",
                "title: Test maintainer-like practice",
                "domain: meta",
                "type: principle",
                "status: active",
                "version: 1",
                "created: 2026-06-09",
                "updated: 2026-06-09",
                "tags: [test]",
                "aliases: [META-001]",
                "---",
                "",
                "## Principle",
                "",
                "Use the selected populated Vault records.",
                "",
            ]
        ),
    )
    write(
        path / "indexes" / "practice_index.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-09",
                "",
                "domains:",
                "  meta:",
                "    description: Test domain.",
                "",
                "practices:",
                "  - id: META-001",
                "    title: Test maintainer-like practice",
                "    path: practices/meta/META-001-test-maintainer-like-practice.md",
                "    domain: meta",
                "    type: principle",
                "    status: active",
                "",
            ]
        ),
    )


def make_custom_vault(path: Path) -> None:
    make_blank_vault(path)
    write(
        path / "practices" / "custom" / "CUST-001-custom-practice.md",
        "\n".join(
            [
                "---",
                "id: CUST-001",
                "title: Custom practice",
                "domain: meta",
                "type: principle",
                "status: active",
                "version: 1",
                "created: 2026-06-09",
                "updated: 2026-06-09",
                "tags: [custom]",
                "aliases: [CUST-001]",
                "---",
                "",
                "## Principle",
                "",
                "Use only the selected Vault records.",
                "",
            ]
        ),
    )
    write(
        path / "indexes" / "practice_index.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-09",
                "",
                "domains:",
                "  meta:",
                "    description: Custom test domain.",
                "",
                "practices:",
                "  - id: CUST-001",
                "    title: Custom practice",
                "    path: practices/custom/CUST-001-custom-practice.md",
                "    domain: meta",
                "    type: principle",
                "    status: active",
                "",
            ]
        ),
    )


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

        errors.extend(expect("clean-core-same-root", run_check(ROOT, ROOT), False, "vault marker missing"))
        errors.extend(expect("clean-core-same-root-plan", run_plan(ROOT, ROOT), False, "mode: unknown"))

        blank = base / "blank-vault"
        make_blank_vault(blank)
        errors.extend(expect("blank-vault", run_check(ROOT, blank), True))
        errors.extend(expect("blank-vault-plan", run_plan(ROOT, blank), True, "mode: split"))

        current_user_like = base / "current-user-like-vault"
        make_maintainer_like_vault(current_user_like)
        errors.extend(expect("current-user-like-vault", run_check(ROOT, current_user_like), True))

        missing = base / "missing-vault"
        make_blank_vault(missing)
        (missing / "indexes" / "asset_index.yaml").unlink()
        errors.extend(expect("missing-vault", run_check(ROOT, missing), False, "vault marker missing"))
        errors.extend(expect("missing-vault-plan", run_plan(ROOT, base / "absent-vault"), False, "mode: missing_vault"))
        errors.extend(expect("missing-core-plan", run_plan(base / "absent-core", blank), False, "mode: missing_core"))

        corrupt = base / "corrupt-vault"
        make_blank_vault(corrupt)
        write(corrupt / "indexes" / "practice_index.yaml", "schema_version: 1\nupdated: 2026-06-09\n")
        errors.extend(expect("corrupt-vault", run_check(ROOT, corrupt), False, "index missing required list: practices"))
        errors.extend(expect("corrupt-vault-plan", run_plan(ROOT, corrupt), False, "mode: unknown"))

        mismatched = base / "mismatched-vault"
        make_blank_vault(mismatched)
        marker = mismatched / ".agent-foundry-vault.yaml"
        marker.write_text(marker.read_text(encoding="utf-8").replace("layout_version: 1", "layout_version: 99"), encoding="utf-8")
        errors.extend(expect("mismatched-vault", run_check(ROOT, mismatched), False, "layout compatibility failed"))
        errors.extend(expect("mismatched-vault-plan", run_plan(ROOT, mismatched), False, "safe_apply_candidate: no"))

        blank_publish = run_publish(ROOT, blank, base / "blank-adapters")
        errors.extend(expect("blank-publish", blank_publish, True, "Nothing to publish"))

        current_user_publish = run_publish(ROOT, current_user_like, base / "current-user-adapters")
        errors.extend(expect("current-user-like-publish", current_user_publish, True, "Adapter publish wrote"))
        if not (base / "current-user-adapters" / "adapter-publish-manifest.yaml").exists():
            errors.append("current-user-like-publish: manifest was not written")

        custom = base / "custom-vault"
        custom_output = base / "custom-adapters"
        make_custom_vault(custom)
        custom_publish = run_publish(ROOT, custom, custom_output)
        errors.extend(expect("custom-vault-publish", custom_publish, True, "Adapter publish wrote"))
        output_text = "\n".join(path.read_text(encoding="utf-8") for path in custom_output.rglob("*") if path.is_file())
        if "CUST-001" not in output_text:
            errors.append("custom-vault-publish: selected custom practice ID missing from output")
        if "META-001" in output_text:
            errors.append("custom-vault-publish: maintainer practice ID leaked into output")

    if errors:
        print("Split-root fixture tests failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Split-root fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
