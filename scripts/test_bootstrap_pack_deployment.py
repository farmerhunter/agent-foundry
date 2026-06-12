#!/usr/bin/env python3
"""Regression fixture for blank Vault to bootstrap pack deployment."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_foundry_roots.py"
DEPLOY = ROOT / "scripts" / "deploy_capability_pack.py"
INIT = ROOT / "scripts" / "init_vault.py"
INSTALL = ROOT / "scripts" / "install_foundry.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
OPTIONAL_PACK = ROOT / "fixtures" / "capability-packs" / "optional-multi-agent"


def run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
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


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"])


def deploy_bootstrap(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(DEPLOY),
            str(BOOTSTRAP_PACK),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault_root),
            "--apply",
        ]
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-bootstrap-deploy-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        generated = base / "generated-adapters"

        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))
        blank_practice_index = (vault / "indexes" / "practice_index.yaml").read_text(encoding="utf-8")
        blank_asset_index = (vault / "indexes" / "asset_index.yaml").read_text(encoding="utf-8")
        if "practices: []" not in blank_practice_index:
            errors.append("init-blank-vault: practice index was not blank")
        if "assets: []" not in blank_asset_index:
            errors.append("init-blank-vault: asset index was not blank")

        fresh_vault = base / "fresh-vault"
        fresh_generated = base / "fresh-generated-adapters"
        fake_home = base / "home"
        fake_home.mkdir()
        fresh_env = os.environ.copy()
        fresh_env["HOME"] = str(fake_home)
        fresh = run(
            [
                str(INSTALL),
                "--fresh-install",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(fresh_vault),
                "--generated-root",
                str(fresh_generated),
                "--apply",
                "--skip-check",
            ],
            env=fresh_env,
        )
        errors.extend(expect("fresh-install-report", fresh, True, "Agent Foundry setup/status report"))
        for expected in [
            "deployed_pack: pack.bootstrap.minimal",
            f"generated_output: ready path={fresh_generated.resolve()}",
            "- chatgpt: manual import required",
            "receipt: missing",
            "first_usable_command: python3 scripts/sync_status.py",
            "chatgpt_manual_import: explicit",
        ]:
            errors.extend(expect(f"fresh-install-report-{expected}", fresh, True, expected))
        if not (fresh_generated / "adapter-publish-manifest.yaml").exists():
            errors.append("fresh-install-report: generated adapter manifest missing")
        locator = fake_home / ".agent-foundry" / "config.yaml"
        if not locator.exists():
            errors.append("fresh-install-report: temp HOME locator was not written")
        elif str(fresh_vault.resolve()) not in locator.read_text(encoding="utf-8"):
            errors.append("fresh-install-report: temp HOME locator did not select fresh Vault")
        for runtime_path in [
            fake_home / ".codex" / "skills",
            fake_home / ".claude",
            fake_home / ".hermes" / "skills",
        ]:
            if runtime_path.exists():
                errors.append(f"fresh-install-report: runtime dry-run unexpectedly wrote {runtime_path}")

        optional_result = run(
            [
                str(DEPLOY),
                str(OPTIONAL_PACK),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--apply",
            ]
        )
        errors.extend(expect("optional-pack-refused", optional_result, False, "only mandatory_bootstrap packs are supported"))

        deploy_result = deploy_bootstrap(vault)
        errors.extend(expect("deploy-bootstrap", deploy_result, True, "added: 24"))
        errors.extend(expect("deploy-bootstrap-validates", deploy_result, True, "selected Vault validated"))
        for expected in [
            vault / "practices" / "meta" / "BOOT-001-bootstrap-orientation.md",
            vault / "practices" / "meta" / "META-001-canonical-practices-source-of-truth.md",
            vault / "practices" / "runtime" / "RUNTIME-001-treat-agent-runtimes-as-shared-environments.md",
            vault / "assets" / "skills" / "ASSET-BOOT-001-bootstrap-status.asset.yaml",
            vault / "assets" / "skills" / "ASSET-META-001-practice-harvester.asset.yaml",
        ]:
            if not expected.exists():
                errors.append(f"deploy-bootstrap: expected Vault record missing: {expected}")
            else:
                text = expected.read_text(encoding="utf-8")
                for marker in [
                    "provenance: \"Deployed from capability pack pack.bootstrap.minimal version 0.2.0",
                    "pack_membership",
                    "pack.bootstrap.minimal",
                    "pack_source_version: \"0.2.0\"",
                ]:
                    if marker not in text:
                        errors.append(f"deploy-bootstrap: {expected} missing deployment metadata marker {marker}")

        check = run([str(CHECK), "--core-root", str(ROOT), "--vault-root", str(vault)])
        errors.extend(expect("check-bootstrap-vault", check, True, "Foundry root validation passed."))

        publish = run(
            [
                str(PUBLISH),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--output-root",
                str(generated),
                "--apply",
            ]
        )
        errors.extend(expect("publish-bootstrap-vault", publish, True, "Active practices selected: 22"))
        errors.extend(expect("publish-bootstrap-skill", publish, True, "Active assets selected: 2"))
        generated_text = "\n".join(path.read_text(encoding="utf-8") for path in generated.rglob("*") if path.is_file())
        for expected in ["BOOT-001", "META-001", "ASSET-BOOT-001", "ASSET-META-001", "Generated from the selected Agent Foundry Vault."]:
            if expected not in generated_text:
                errors.append(f"publish-bootstrap-vault: generated output missing {expected}")

        rerun = deploy_bootstrap(vault)
        errors.extend(expect("deploy-bootstrap-rerun-skip", rerun, True, "skipped: 24"))
        errors.extend(expect("deploy-bootstrap-rerun-no-add", rerun, True, "added: 0"))

        record = vault / "practices" / "meta" / "BOOT-001-bootstrap-orientation.md"
        record.write_text(record.read_text(encoding="utf-8") + "\nLocal edit fixture.\n", encoding="utf-8")
        conflict = deploy_bootstrap(vault)
        errors.extend(expect("deploy-bootstrap-conflict", conflict, False, "local Vault record differs from pack content"))
        errors.extend(expect("deploy-bootstrap-conflict-summary", conflict, False, "conflicts: 1"))

    if errors:
        print("Bootstrap pack deployment fixture failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Bootstrap pack deployment fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
