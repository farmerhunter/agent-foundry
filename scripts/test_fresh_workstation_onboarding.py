#!/usr/bin/env python3
"""Run the representative fresh-workstation journey in temporary roots only."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def run(core: Path, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        cwd=core,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require(name: str, result: subprocess.CompletedProcess[str], success: bool, text: str) -> None:
    output = result.stdout + result.stderr
    if (result.returncode == 0) != success or text not in output:
        raise AssertionError(
            f"{name}: expected {'success' if success else 'failure'} containing {text!r}; "
            f"exit={result.returncode}\n{output}"
        )
    print(f"{name}: ok")


def value(output: str, field: str) -> str:
    prefix = f"{field}: "
    return next((line[len(prefix) :] for line in output.splitlines() if line.startswith(prefix)), "")


def main() -> int:
    deployment = (SOURCE_ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
    readme = (SOURCE_ROOT / "README.md").read_text(encoding="utf-8")
    for required in [
        "scripts/deploy_capability_pack.py fixtures/capability-packs/bootstrap-minimal",
        "scripts/plan_capability_pack.py fixtures/capability-packs/optional-multi-agent",
        "--pack-id pack.multi-agent.optional --action activate",
        "--surface selected-output --generated-root <generated-root>",
        "--restore-backup <activation-backup-root>",
    ]:
        if required not in deployment:
            raise AssertionError(f"canonical runbook missing exercised interface: {required}")
    if "docs/deployment.md#fresh-install" not in readme:
        raise AssertionError("README does not strongly link the canonical Fresh Install runbook")
    with tempfile.TemporaryDirectory(prefix="agent-foundry-fresh-workstation-") as temporary:
        root = Path(temporary)
        core = root / "core"
        home = root / "home"
        vault = root / "vault"
        generated = root / "generated"
        runtime = root / "runtime" / "codex-skills"
        backup = root / "private-backups" / "optional-activation"
        home.mkdir(mode=0o700)
        (root / "private-backups").mkdir(mode=0o700)
        shutil.copytree(
            SOURCE_ROOT,
            core,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "runtime/local", "sync/local"),
        )

        init = run(core, home, "scripts/init_vault.py", str(vault), "--core-root", str(core), "--apply")
        require("blank-vault", init, True, "Blank Vault initialized and validated.")
        locator = run(
            core,
            home,
            "scripts/foundry_config.py",
            "write",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
        )
        require("locator-write", locator, True, "wrote foundry locator")
        locator_status = run(core, home, "scripts/foundry_config.py", "status")
        require("locator-readback", locator_status, True, "validation: passed")

        bootstrap = core / "fixtures" / "capability-packs" / "bootstrap-minimal"
        bootstrap_preview = run(
            core,
            home,
            "scripts/deploy_capability_pack.py",
            str(bootstrap),
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
        )
        require("bootstrap-preview", bootstrap_preview, True, "Dry-run only")
        bootstrap_apply = run(
            core,
            home,
            "scripts/deploy_capability_pack.py",
            str(bootstrap),
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--apply",
        )
        require("bootstrap-apply", bootstrap_apply, True, "selected Vault validated")

        optional = core / "fixtures" / "capability-packs" / "optional-multi-agent"
        optional_preview = run(
            core,
            home,
            "scripts/plan_capability_pack.py",
            str(optional),
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
        )
        require("optional-preview", optional_preview, True, "fail: 0")
        optional_apply = run(
            core,
            home,
            "scripts/apply_capability_pack.py",
            str(optional),
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--apply",
        )
        require("optional-import", optional_apply, True, "metadata: written")

        lifecycle_args = (
            "scripts/manage_capability_pack_lifecycle.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--pack-id",
            "pack.multi-agent.optional",
            "--action",
            "activate",
        )
        activation_preview = run(core, home, *lifecycle_args)
        require("activation-preview", activation_preview, True, "status: ready_for_review")
        token = value(activation_preview.stdout, "review_token")
        if len(token) != 64:
            raise AssertionError("activation-preview: missing exact review token")
        activation_apply = run(
            core,
            home,
            *lifecycle_args,
            "--review-token",
            token,
            "--backup-root",
            str(backup),
            "--apply",
        )
        require("activation-apply", activation_apply, True, "status: activated")
        require("activation-readback", activation_apply, True, "readback: passed")

        publish_preview = run(
            core,
            home,
            "scripts/publish_adapters.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--output-root",
            str(generated),
        )
        require("publish-preview", publish_preview, True, "Adapter publish planned")
        publish_apply = run(
            core,
            home,
            "scripts/publish_adapters.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--output-root",
            str(generated),
            "--apply",
        )
        require("publish-apply", publish_apply, True, "Adapter publish wrote")
        quality = run(
            core,
            home,
            "scripts/check_adapter_quality.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--surface",
            "selected-output",
            "--generated-root",
            str(generated),
        )
        require("selected-output-quality", quality, True, "Adapter quality check passed")

        manifest_init = run(core, home, "scripts/runtime_manifest.py", "init")
        require("runtime-manifest-init", manifest_init, True, "initialized local runtime manifest")
        configure = run(core, home, "scripts/runtime_manifest.py", "configure", "codex", "--path", str(runtime))
        require("runtime-configure", configure, True, "")
        enable = run(core, home, "scripts/runtime_manifest.py", "enable", "codex")
        require("runtime-enable", enable, True, "")
        runtime_detect = run(core, home, "scripts/runtime_manifest.py", "detect")
        require("runtime-detect", runtime_detect, True, "codex: not found")

        install_args = (
            "scripts/install_foundry.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(generated),
            "--target",
            "codex",
            "--skip-check",
        )
        install_preview = run(core, home, *install_args)
        require("runtime-install-preview", install_preview, True, "## codex: dry-run")
        install_apply = run(core, home, *install_args, "--apply")
        require("runtime-install-apply", install_apply, True, "## codex: apply")
        receipt = core / "runtime" / "local" / "adapter-install-receipt.yaml"
        status = run(
            core,
            home,
            "scripts/sync_status.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(generated),
            "--receipt-path",
            str(receipt),
        )
        require("final-status-roots", status, True, "root_validation: passed")
        require("final-status-generated", status, True, "generated_output: ready")
        require("final-status-runtime", status, True, "selected-output-in-sync")

        managed_markers = list(runtime.glob("*/.agent-foundry-managed"))
        if not managed_markers or not backup.is_dir() or not receipt.is_file():
            raise AssertionError("layer readback: missing managed marker, activation backup, or runtime receipt")
        generated_file = next(path for path in generated.rglob("*") if path.is_file())
        installed_file = next(path for path in runtime.rglob("*") if path.is_file() and path.name != ".agent-foundry-managed")
        if generated_file.is_relative_to(vault) or installed_file.is_relative_to(generated):
            raise AssertionError("layer readback: source/generated/runtime roots were conflated")

        installed_file.write_text(installed_file.read_text(encoding="utf-8") + "\nlocal drift\n", encoding="utf-8")
        drift_status = run(
            core,
            home,
            "scripts/sync_status.py",
            "--core-root",
            str(core),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(generated),
            "--receipt-path",
            str(receipt),
        )
        require("runtime-drift-readback", drift_status, True, "selected-output-drift")

        unmanaged = root / "runtime" / "unmanaged-codex"
        unmanaged_skill = unmanaged / "agent-collaboration"
        unmanaged_skill.mkdir(parents=True)
        (unmanaged_skill / "user-file.txt").write_text("user owned\n", encoding="utf-8")
        configure_unmanaged = run(
            core, home, "scripts/runtime_manifest.py", "configure", "codex", "--path", str(unmanaged)
        )
        require("unmanaged-configure", configure_unmanaged, True, "")
        unmanaged_apply = run(core, home, *install_args, "--apply")
        require("unmanaged-runtime-hold", unmanaged_apply, False, "Refusing to overwrite unmanaged directory")
        if (unmanaged / ".agent-foundry-managed").exists():
            raise AssertionError("unmanaged-runtime-hold: target was adopted")

    print("Fresh-workstation onboarding E2E passed; temporary roots cleaned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
