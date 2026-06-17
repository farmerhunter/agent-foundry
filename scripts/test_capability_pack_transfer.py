#!/usr/bin/env python3
"""Regression tests for privacy-safe capability pack transfer planning."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
TRANSFER = ROOT / "scripts" / "plan_capability_pack_transfer.py"


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def practice_text(item_id: str) -> str:
    return "\n".join(
        [
            "---",
            f'id: "{item_id}"',
            f'title: "{item_id}"',
            'domain: "meta"',
            'status: "candidate"',
            "---",
            "",
            "Sanitized practice fixture.",
            "",
        ]
    )


def write_pack(
    base: Path,
    name: str,
    *,
    private_text: str = "",
    executable: bool = False,
    import_action: str = "stage_only",
    destination_layer: str = "import_staging_reference",
) -> Path:
    pack = base / name
    record = pack / "records" / "TRANSFER-001.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(practice_text("TRANSFER-001") + private_text, encoding="utf-8")
    payload_lines: list[str] = ["executable_payloads: []"]
    if executable:
        helper = pack / "payloads" / "helper.py"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text("print('must not execute')\n", encoding="utf-8")
        payload_lines = [
            "executable_payloads:",
            "  - id: helper",
            "    title: helper",
            "    lifecycle_status: candidate",
            "    path: payloads/helper.py",
            f"    source_sha256: \"{sha256(helper)}\"",
            "    interpreter: python3",
            "    execute_from_pack: false",
            "    install_boundary: managed_runtime_copy_required",
            "    permissions: [filesystem-read]",
            "    dependencies: []",
            "    runtime_impact: test",
        ]
    manifest_lines = [
        "manifest_schema_version: 1",
        f"pack_id: pack.transfer.{name}",
        f"title: Transfer {name}",
        "description: Transfer planner fixture.",
        "lifecycle_status: candidate",
        "version: 0.1.0",
        "exported_at: 2026-06-17",
        "distribution_type: optional_capability",
        "source_provenance: public test fixture",
        "maintainer_contact: test",
        "license: test",
        "sensitivity: public",
        "review_state: reviewed",
        "export_policy:",
        "  exportability: review_required",
        "  privacy_class: sanitized",
        "  excluded_material: [private evidence, raw logs, session transcripts, runtime receipts]",
        "  review_required: true",
        "runtime_projection:",
        "  downstream_only: true",
        "  generated_adapter_intent: review_required",
        "  runtime_install: review_required",
        "  authority: downstream_only",
        "compatibility:",
        "  core_schema_version_min: 1",
        "  core_schema_version_max: 1",
        "  vault_layout_versions: [1]",
        "  requires_bootstrap_pack: false",
        "included_records:",
        "  - id: TRANSFER-001",
        "    kind: practice",
        "    lifecycle_status: candidate",
        "    path: records/TRANSFER-001.md",
        "    source_version: 1",
        f"    content_sha256: \"{sha256(record)}\"",
        f"    destination_layer: {destination_layer}",
        "    membership_role: optional_member",
        "    activation_default: manual_review",
        f"    import_action: {import_action}",
        "",
        *payload_lines,
        "",
        "conflict_policy:",
        "  id_collision: fail_closed",
        "  same_version_hash_mismatch: fail_closed",
        "  newer_version_update: reviewed_diff_required",
        "  local_edit_behavior: preserve_vault_and_propose_merge",
        "  rollback_notes: discard staged transfer material",
        "",
        "integrity:",
        "  digest_algorithm: sha256",
        "  manifest_paths_are_relative: true",
        "  private_vault_content: excluded",
        "",
    ]
    (pack / "manifest.yaml").write_text("\n".join(manifest_lines), encoding="utf-8")
    return pack


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"])


def transfer(pack: Path, vault: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run([str(TRANSFER), str(pack), "--core-root", str(ROOT), "--vault-root", str(vault), *extra])


def write_conflicting_vault_record(vault: Path, pack: Path) -> None:
    record = vault / "practices" / "meta" / "TRANSFER-001.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(practice_text("TRANSFER-001") + "\nLocal selected Vault edit.\n", encoding="utf-8")
    index = vault / "indexes" / "practice_index.yaml"
    index.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "practices:",
                "  - id: TRANSFER-001",
                "    title: TRANSFER-001",
                "    domain: meta",
                "    status: candidate",
                "    path: practices/meta/TRANSFER-001.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-17",
                "deployed_packs:",
                "  - pack_id: pack.transfer.conflict",
                "    version: 0.1.0",
                "    source:",
                f"      manifest_sha256: {sha256(pack / 'manifest.yaml')}",
                "    records:",
                "      - id: TRANSFER-001",
                "        kind: practice",
                "        path: practices/meta/TRANSFER-001.md",
                f"        deployed_sha256: {'0' * 64}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-pack-transfer-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))

        clean_pack = write_pack(base, "clean")
        clean_preview = transfer(clean_pack, vault, "--action", "import-preview", "--import-state", "preview")
        errors.extend(expect("transfer-clean-preview", clean_preview, True, "status: review_required"))
        errors.extend(expect("transfer-clean-writes-none", clean_preview, True, "writes: none"))
        errors.extend(expect("transfer-clean-diff-before-write", clean_preview, True, "diff_before_write:"))
        errors.extend(expect("transfer-clean-no-silent-activation", clean_preview, True, "existing practice/asset review gates"))

        dry_run = transfer(clean_pack, vault, "--action", "import-dry-run", "--import-state", "dry-run")
        errors.extend(expect("transfer-dry-run", dry_run, True, "import_state: dry-run"))

        conflict_pack = write_pack(
            base,
            "conflict",
            import_action="create_or_review_update",
            destination_layer="canonical_vault_record",
        )
        write_conflicting_vault_record(vault, conflict_pack)
        conflict = transfer(conflict_pack, vault, "--action", "import-dry-run", "--import-state", "dry-run")
        errors.extend(expect("transfer-local-edit-conflict-requires-merge", conflict, True, "merge_required"))
        errors.extend(expect("transfer-local-edit-conflict-writes-none", conflict, True, "writes: none"))

        accepted = transfer(clean_pack, vault, "--action", "import-preview", "--import-state", "accepted")
        errors.extend(expect("transfer-accepted-still-review-gated", accepted, False, "accepted import state still requires"))

        private_pack = write_pack(base, "private", private_text="Evidence: /Users/example/private/raw-session.log\n")
        private_preview = transfer(private_pack, vault)
        errors.extend(expect("transfer-private-reference-blocked", private_preview, False, "private/local reference"))
        errors.extend(expect("transfer-private-writes-none", private_preview, False, "writes: none"))

        private_path_pack = write_pack(base, "private-path")
        local_dir = private_path_pack / "runtime" / "local"
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "runtime_manifest.yaml").write_text("targets: []\n", encoding="utf-8")
        private_path = transfer(private_path_pack, vault)
        errors.extend(expect("transfer-private-path-blocked", private_path, False, "private/local path"))

        executable_pack = write_pack(base, "executable", executable=True)
        executable_preview = transfer(executable_pack, vault)
        errors.extend(expect("transfer-executable-blocked", executable_preview, False, "cannot install or execute during transfer"))

        no_export_policy = write_pack(base, "no-export-policy")
        manifest = no_export_policy / "manifest.yaml"
        manifest.write_text(
            "\n".join(line for line in manifest.read_text(encoding="utf-8").splitlines() if "export_policy" not in line and "exportability:" not in line and "privacy_class:" not in line and "excluded_material:" not in line and "review_required:" not in line),
            encoding="utf-8",
        )
        no_policy = transfer(no_export_policy, vault)
        errors.extend(expect("transfer-export-policy-required", no_policy, False, "export_policy is required"))

    if errors:
        print("Capability pack transfer test failed:")
        for error in errors:
            print(error)
        return 1
    print("Capability pack transfer test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
