#!/usr/bin/env python3
"""Regression fixture for split Core/Vault adapter quality checks."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from foundry_config import CONFIG_PATH, parse_config


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "scripts" / "check_adapter_quality.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"


def configured_vault_root() -> Path:
    data = parse_config(CONFIG_PATH)
    vault_root = data.get("vault_root", "")
    if isinstance(vault_root, str) and vault_root:
        return Path(vault_root).expanduser().resolve()
    raise RuntimeError("configured vault_root missing")


def digest_tree(path: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = str(file_path.relative_to(path))
        digests[rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return digests


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def expect(name: str, result: subprocess.CompletedProcess[str], should_pass: bool, expected_text: str = "") -> list[str]:
    output = result.stdout + result.stderr
    if (result.returncode == 0) == should_pass and (not expected_text or expected_text in output):
        print(f"{name}: ok")
        return []
    return [
        f"{name}: expected {'pass' if should_pass else 'failure'}"
        + (f" containing {expected_text!r}" if expected_text else "")
        + f", got exit {result.returncode}\n{output.strip()}"
    ]


def promote_asset_collab_002(vault_root: Path) -> None:
    index = vault_root / "indexes" / "asset_index.yaml"
    index_text = index.read_text(encoding="utf-8")
    index_text = index_text.replace(
        "  - id: ASSET-COLLAB-002\n"
        "    title: Role Dispatch and Automation Planner\n"
        "    path: assets/skills/ASSET-COLLAB-002-role-automation-planner.asset.yaml\n"
        "    asset_type: skill\n"
        "    status: proposed\n",
        "  - id: ASSET-COLLAB-002\n"
        "    title: Role Dispatch and Automation Planner\n"
        "    path: assets/skills/ASSET-COLLAB-002-role-automation-planner.asset.yaml\n"
        "    asset_type: skill\n"
        "    status: active\n",
    )
    index_text = index_text.replace(
        "    canonical_practices: [META-004, META-005, COLLAB-001, COLLAB-002, COLLAB-003, COLLAB-004, COLLAB-008, COLLAB-009, COLLAB-010, COLLAB-011, COLLAB-012, COLLAB-014, GOV-002, GOV-004, GOV-005, GOV-006, RUNTIME-001, RUNTIME-003]\n"
        "    published_to: []\n",
        "    canonical_practices: [META-004, META-005, COLLAB-001, COLLAB-002, COLLAB-003, COLLAB-004, COLLAB-008, COLLAB-009, COLLAB-010, COLLAB-011, COLLAB-012, COLLAB-014, GOV-002, GOV-004, GOV-005, GOV-006, RUNTIME-001, RUNTIME-003]\n"
        "    published_to: [codex, claude-code, hermes, chatgpt]\n",
    )
    index.write_text(index_text, encoding="utf-8")

    asset = vault_root / "assets" / "skills" / "ASSET-COLLAB-002-role-automation-planner.asset.yaml"
    asset_text = asset.read_text(encoding="utf-8")
    asset_text = asset_text.replace("status: proposed\n", "status: active\n", 1)
    asset_text = asset_text.replace("published_to: []\n", "published_to: [codex, claude-code, hermes, chatgpt]\n", 1)
    asset.write_text(asset_text, encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    real_vault = configured_vault_root()
    adapters_before = digest_tree(ROOT / "adapters")

    with tempfile.TemporaryDirectory(prefix="agent-foundry-adapter-quality-") as tmp:
        base = Path(tmp)
        temp_vault = base / "vault"
        generated = base / "generated-adapters"
        missing_generated = base / "missing-generated"
        shutil.copytree(real_vault, temp_vault)
        promote_asset_collab_002(temp_vault)

        core_quality = run(
            [
                str(QUALITY),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--surface",
                "core",
            ]
        )
        errors.extend(expect("core-surface-promoted-asset", core_quality, True, "core surface"))

        missing_publish = run(
            [
                str(QUALITY),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--surface",
                "selected-output",
                "--generated-root",
                str(missing_generated),
            ]
        )
        errors.extend(expect("selected-output-missing-publish", missing_publish, False, "Missing publish step"))

        unsafe_quality = run(
            [
                str(QUALITY),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--surface",
                "selected-output",
                "--generated-root",
                str(ROOT / "adapters"),
            ]
        )
        errors.extend(expect("selected-output-unsafe-core-root", unsafe_quality, False, "Unsafe Core overwrite attempt"))

        publish = run(
            [
                str(PUBLISH),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--output-root",
                str(generated),
                "--apply",
            ]
        )
        errors.extend(expect("publish-promoted-asset", publish, True, "Adapter publish wrote"))

        selected_quality = run(
            [
                str(QUALITY),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--surface",
                "selected-output",
                "--generated-root",
                str(generated),
            ]
        )
        errors.extend(expect("selected-output-promoted-asset", selected_quality, True, "selected-output surface"))
        generated_text = "\n".join(path.read_text(encoding="utf-8") for path in generated.rglob("*") if path.is_file())
        if "ASSET-COLLAB-002" not in generated_text:
            errors.append("selected-output-promoted-asset: generated output missing ASSET-COLLAB-002")

        unsafe_publish = run(
            [
                str(PUBLISH),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(temp_vault),
                "--output-root",
                str(ROOT / "adapters"),
                "--apply",
            ]
        )
        errors.extend(expect("publish-refuses-core-overwrite", unsafe_publish, False, "Refusing to overwrite Core adapter templates"))

    if digest_tree(ROOT / "adapters") != adapters_before:
        errors.append("core-adapters-mutated: regression fixture changed tracked Core adapters")

    if errors:
        print("Adapter quality split fixture failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Adapter quality split fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
