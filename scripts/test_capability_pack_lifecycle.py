#!/usr/bin/env python3
"""Regression tests for disable/retire pack lifecycle behavior."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
DEPLOY = ROOT / "scripts" / "deploy_capability_pack.py"
APPLY = ROOT / "scripts" / "apply_capability_pack.py"
LIFECYCLE = ROOT / "scripts" / "manage_capability_pack_lifecycle.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
STATUS = ROOT / "scripts" / "sync_status.py"
BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
OPTIONAL_PACK = ROOT / "fixtures" / "capability-packs" / "optional-multi-agent"
OPTIONAL_ID = "pack.multi-agent.optional"


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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_blank(vault: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault), "--core-root", str(ROOT), "--apply"])


def deploy_bootstrap(vault: Path) -> subprocess.CompletedProcess[str]:
    return run([str(DEPLOY), str(BOOTSTRAP_PACK), "--core-root", str(ROOT), "--vault-root", str(vault), "--apply"])


def apply_optional(vault: Path) -> subprocess.CompletedProcess[str]:
    return run([str(APPLY), str(OPTIONAL_PACK), "--core-root", str(ROOT), "--vault-root", str(vault), "--apply"])


def lifecycle(vault: Path, action: str, apply: bool) -> subprocess.CompletedProcess[str]:
    args = [
        str(LIFECYCLE),
        "--core-root",
        str(ROOT),
        "--vault-root",
        str(vault),
        "--pack-id",
        OPTIONAL_ID,
        "--action",
        action,
    ]
    if apply:
        args.append("--apply")
    return run(args)


def publish(vault: Path, generated: Path) -> subprocess.CompletedProcess[str]:
    return run(
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


def status(vault: Path, generated: Path, receipt: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(STATUS),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(generated),
            "--receipt-path",
            str(receipt),
        ]
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-pack-lifecycle-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        generated = base / "generated"
        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))
        errors.extend(expect("deploy-bootstrap", deploy_bootstrap(vault), True, "selected Vault validated"))
        errors.extend(expect("apply-optional", apply_optional(vault), True, "metadata: written"))

        user_record = vault / "practices" / "user" / "USER-LOCAL-001.md"
        write(
            user_record,
            "\n".join(
                [
                    "---",
                    "id: USER-LOCAL-001",
                    "title: Local User Record",
                    "domain: user",
                    "status: active",
                    "---",
                    "",
                    "Unrelated user record.",
                    "",
                ]
            ),
        )
        user_before = digest(user_record)
        practice = vault / "practices" / "agent-collaboration" / "COLLAB-PACK-001-review-handoff.md"
        asset = vault / "assets" / "skills" / "ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml"
        metadata = vault / "packs" / "deployed-pack-index.yaml"
        metadata_before = digest(metadata)

        dry_disable = lifecycle(vault, "disable", apply=False)
        errors.extend(expect("disable-dry-run", dry_disable, True, "writes: none"))
        if digest(metadata) != metadata_before:
            errors.append("disable-dry-run: metadata changed")

        apply_disable = lifecycle(vault, "disable", apply=True)
        errors.extend(expect("disable-apply", apply_disable, True, "writes: applied"))
        metadata_text = metadata.read_text(encoding="utf-8")
        if "lifecycle_status: disabled" not in metadata_text:
            errors.append("disable-apply: metadata missing disabled lifecycle")
        if "status: candidate" not in practice.read_text(encoding="utf-8"):
            errors.append("disable-apply: practice status changed during metadata-only disable")
        if "status: candidate" not in asset.read_text(encoding="utf-8"):
            errors.append("disable-apply: asset status changed during metadata-only disable")

        apply_retire = lifecycle(vault, "retire", apply=True)
        errors.extend(expect("retire-apply", apply_retire, True, "runtime_cleanup:"))
        if "status: archived" not in practice.read_text(encoding="utf-8"):
            errors.append("retire-apply: practice was not archived")
        if "status: retired" not in asset.read_text(encoding="utf-8"):
            errors.append("retire-apply: asset was not retired")
        if "    status: archived" not in (vault / "indexes" / "practice_index.yaml").read_text(encoding="utf-8"):
            errors.append("retire-apply: practice index status was not archived")
        if "    status: retired" not in (vault / "indexes" / "asset_index.yaml").read_text(encoding="utf-8"):
            errors.append("retire-apply: asset index status was not retired")
        retired_metadata = metadata.read_text(encoding="utf-8")
        for expected in ["lifecycle_status: retired", "current_state: archived", "current_state: retired"]:
            if expected not in retired_metadata:
                errors.append(f"retire-apply: metadata missing {expected}")
        if digest(user_record) != user_before:
            errors.append("retire-apply: unrelated user record changed")

        errors.extend(expect("publish-after-retire", publish(vault, generated), True, "Adapter publish wrote"))
        generated_text = "\n".join(path.read_text(encoding="utf-8") for path in generated.rglob("*") if path.is_file())
        for retired_id in ["COLLAB-PACK-001", "ASSET-COLLAB-PACK-001"]:
            if retired_id in generated_text:
                errors.append(f"publish-after-retire: retired candidate leaked into generated output: {retired_id}")
        restore_status = status(vault, generated, base / "missing-receipt.json")
        for expected in [
            "root_validation: passed",
            "generated_output: ready",
            "receipt: missing",
            "chatgpt_manual_import: explicit",
            "status-only: no files were written by this report",
        ]:
            errors.extend(expect(f"restore-status-{expected}", restore_status, True, expected))

    if errors:
        print("Capability pack lifecycle test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack lifecycle test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
