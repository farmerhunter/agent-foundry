#!/usr/bin/env python3
"""Regression fixture for blank Vault to bootstrap pack deployment."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import rollback_runtime
import runtime_manifest

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


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def exercise_restore_rollback_boundaries(base: Path, vault: Path) -> list[str]:
    errors: list[str] = []
    user_record = vault / "practices" / "user" / "USER-001-local-user-record.md"
    user_record.parent.mkdir(parents=True, exist_ok=True)
    user_record.write_text(
        "\n".join(
            [
                "---",
                'id: "USER-001"',
                'title: "Local user record fixture"',
                'status: "active"',
                "---",
                "",
                "This fixture must survive runtime disable and rollback simulation.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    before_vault = tree_digest(vault)

    original_manifest = runtime_manifest.LOCAL_MANIFEST
    temp_manifest = base / "runtime-local" / "runtime_manifest.yaml"
    runtime_manifest.LOCAL_MANIFEST = temp_manifest
    try:
        runtime_manifest.ensure_local_manifest()
        runtime_manifest.set_target_status("codex", "enabled")
        runtime_manifest.set_target_path("codex", str(base / "runtime" / "codex-skills"))
        runtime_manifest.set_target_status("codex", "disabled")
        targets = runtime_manifest.parse_targets(runtime_manifest.read_manifest())
        if targets.get("codex", {}).get("status") != "disabled":
            errors.append("runtime-disable: temp manifest did not disable codex")
        if not temp_manifest.exists():
            errors.append("runtime-disable: temp manifest missing")
    finally:
        runtime_manifest.LOCAL_MANIFEST = original_manifest

    fake_claude = base / "runtime" / "claude" / "CLAUDE.md"
    fake_claude.parent.mkdir(parents=True, exist_ok=True)
    fake_claude.write_text(
        "\n".join(
            [
                "User-owned Claude notes.",
                rollback_runtime.CLAUDE_INCLUDE_START,
                "# Agent Foundry managed instructions",
                "@managed/CLAUDE.md",
                rollback_runtime.CLAUDE_INCLUDE_END,
                "User-owned footer.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    codex_root = base / "runtime" / "codex-skills"
    managed_skill = codex_root / "pack-sourced-skill"
    unmanaged_skill = codex_root / "user-owned-skill"
    (managed_skill / ".agent-foundry-managed").parent.mkdir(parents=True, exist_ok=True)
    (managed_skill / ".agent-foundry-managed").write_text("managed-by: agent-foundry\n", encoding="utf-8")
    (managed_skill / "SKILL.md").write_text("managed runtime copy\n", encoding="utf-8")
    unmanaged_skill.mkdir(parents=True, exist_ok=True)
    (unmanaged_skill / "SKILL.md").write_text("user runtime copy\n", encoding="utf-8")

    original_claude = rollback_runtime.CLAUDE_MD
    original_roots = rollback_runtime.SKILL_ROOTS
    rollback_runtime.CLAUDE_MD = fake_claude
    rollback_runtime.SKILL_ROOTS = {"codex": codex_root, "hermes": base / "runtime" / "hermes-skills"}
    try:
        rollback_runtime.remove_skill("codex", "pack-sourced-skill", dry_run=True, force=False)
        if not managed_skill.exists():
            errors.append("rollback-dry-run: managed skill was removed during dry-run")
        rollback_runtime.remove_skill("codex", "pack-sourced-skill", dry_run=False, force=False)
        if managed_skill.exists():
            errors.append("rollback-managed-skill: managed skill still exists after removal")
        try:
            rollback_runtime.remove_skill("codex", "user-owned-skill", dry_run=False, force=False)
            errors.append("rollback-unmanaged-skill: unmanaged skill removal was not refused")
        except SystemExit as exc:
            if "Refusing to remove unmanaged directory" not in str(exc):
                errors.append(f"rollback-unmanaged-skill: unexpected refusal text {exc}")
        if not unmanaged_skill.exists():
            errors.append("rollback-unmanaged-skill: unmanaged skill was removed")

        rollback_runtime.remove_managed_block(dry_run=True)
        if rollback_runtime.CLAUDE_INCLUDE_START not in fake_claude.read_text(encoding="utf-8"):
            errors.append("rollback-block-dry-run: managed block was removed during dry-run")
        rollback_runtime.remove_managed_block(dry_run=False)
        claude_text = fake_claude.read_text(encoding="utf-8")
        if rollback_runtime.CLAUDE_INCLUDE_START in claude_text:
            errors.append("rollback-block: managed block remains after removal")
        for expected in ["User-owned Claude notes.", "User-owned footer."]:
            if expected not in claude_text:
                errors.append(f"rollback-block: user text missing after removal: {expected}")
    finally:
        rollback_runtime.CLAUDE_MD = original_claude
        rollback_runtime.SKILL_ROOTS = original_roots

    after_vault = tree_digest(vault)
    if before_vault != after_vault:
        errors.append("restore-rollback-boundary: runtime disable/rollback changed Vault records")
    return errors


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
        errors.extend(expect("deploy-bootstrap", deploy_result, True, "added: 25"))
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
        errors.extend(expect("publish-bootstrap-vault", publish, True, "Active practices selected: 23"))
        errors.extend(expect("publish-bootstrap-skill", publish, True, "Active assets selected: 2"))
        generated_text = "\n".join(path.read_text(encoding="utf-8") for path in generated.rglob("*") if path.is_file())
        for expected in ["BOOT-001", "META-001", "ASSET-BOOT-001", "ASSET-META-001", "Generated from the selected Agent Foundry Vault."]:
            if expected not in generated_text:
                errors.append(f"publish-bootstrap-vault: generated output missing {expected}")

        rerun = deploy_bootstrap(vault)
        errors.extend(expect("deploy-bootstrap-rerun-skip", rerun, True, "skipped: 25"))
        errors.extend(expect("deploy-bootstrap-rerun-no-add", rerun, True, "added: 0"))

        errors.extend(exercise_restore_rollback_boundaries(base, vault))

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
