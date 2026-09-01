#!/usr/bin/env python3
"""Regression tests for capability pack update comparison."""

from __future__ import annotations

import hashlib
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_capability_pack.py"
COMPARE = ROOT / "scripts" / "compare_capability_pack_update.py"
DEPLOY = ROOT / "scripts" / "deploy_capability_pack.py"
UPDATE = ROOT / "scripts" / "update_capability_pack.py"
INIT = ROOT / "scripts" / "init_vault.py"
BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
OPTIONAL_PACK = ROOT / "fixtures" / "capability-packs" / "optional-multi-agent"


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


def practice_text(item_id: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f'id: "{item_id}"',
            f'title: "{item_id}"',
            'domain: "meta"',
            'status: "candidate"',
            "---",
            "",
            body,
            "",
        ]
    )


def write_pack(
    base: Path,
    name: str,
    version: str,
    body: str,
    *,
    include_source_provenance: bool = True,
    schema_version: str = "1",
    core_min: str = "1",
    core_max: str = "1",
    include_payload: bool = False,
) -> Path:
    pack = base / name
    record = pack / "records" / "UPDATE-001.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(practice_text("UPDATE-001", body), encoding="utf-8")
    payload = pack / "payloads" / "helper.py"
    if include_payload:
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text("print('do not execute')\n", encoding="utf-8")
    lines = [
        f"manifest_schema_version: {schema_version}",
        "pack_id: pack.probe.update",
        "title: Update Probe Pack",
        "description: Probe pack for update comparison tests.",
        "lifecycle_status: reviewed",
        f"version: {version}",
        "exported_at: 2026-06-12",
        "distribution_type: optional_capability",
        "maintainer_contact: test",
        "license: test",
        "sensitivity: public",
        "review_state: reviewed",
        "",
        "compatibility:",
        f"  core_schema_version_min: {core_min}",
        f"  core_schema_version_max: {core_max}",
        "  vault_layout_versions: [1]",
        "  requires_bootstrap_pack: false",
        "",
        "included_records:",
        "  - id: UPDATE-001",
        "    kind: practice",
        "    lifecycle_status: candidate",
        "    path: records/UPDATE-001.md",
        "    source_version: 1",
        f"    content_sha256: \"{sha256(record)}\"",
        "    destination_layer: canonical_vault_record",
        "    membership_role: optional_member",
        "    activation_default: manual_review",
        "    import_action: create_or_review_update",
        "",
        "executable_payloads:",
    ]
    if include_source_provenance:
        lines.insert(8, "source_provenance: test fixture")
    if include_payload:
        lines.extend(
            [
                "  - id: helper.update",
                "    title: Update Helper",
                "    lifecycle_status: candidate",
                "    path: payloads/helper.py",
                f"    source_sha256: \"{sha256(payload)}\"",
                "    interpreter: python3",
                "    execute_from_pack: false",
                "    install_boundary: managed_runtime_copy_required",
                "    permissions: [filesystem-read]",
                "    dependencies: []",
                "    runtime_impact: test",
            ]
        )
    else:
        lines[-1] = "executable_payloads: []"
    lines.extend(
        [
            "",
            "conflict_policy:",
            "  id_collision: fail_closed",
            "  same_version_hash_mismatch: fail_closed",
            "  newer_version_update: reviewed_diff_required",
            "  local_edit_behavior: preserve_vault_and_propose_merge",
            "  rollback_notes: test",
            "",
            "integrity:",
            "  digest_algorithm: sha256",
            "  manifest_paths_are_relative: true",
            "  private_vault_content: excluded",
            "",
        ]
    )
    (pack / "manifest.yaml").write_text("\n".join(lines), encoding="utf-8")
    return pack


def write_legacy_optional_pack(base: Path) -> Path:
    pack = base / "optional-0.4.0"
    practice = pack / "records" / "practices" / "COLLAB-PACK-001-review-handoff.md"
    asset = pack / "records" / "assets" / "ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml"
    practice.parent.mkdir(parents=True, exist_ok=True)
    asset.parent.mkdir(parents=True, exist_ok=True)
    practice.write_text(
        "\n".join(
            [
                "---",
                "id: COLLAB-PACK-001",
                "title: Legacy review handoff",
                "domain: agent-collaboration",
                "status: candidate",
                "version: 6",
                "---",
                "",
                "Legacy optional-pack candidate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    asset.write_text(
        "\n".join(
            [
                "id: ASSET-COLLAB-PACK-001",
                "title: Legacy review handoff helper",
                "asset_type: skill",
                "status: candidate",
                "version: 6",
                "purpose: Legacy candidate fixture.",
                "responsibility: Legacy candidate fixture.",
                "non_responsibility: Does not own current collaboration guidance.",
                "inputs: []",
                "process: []",
                "outputs: []",
                "canonical_practices: []",
                "published_to: []",
                "usage_triggers: []",
                "success_criteria: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack / "manifest.yaml").write_text(
        "\n".join(
            [
                "manifest_schema_version: 1",
                "pack_id: pack.multi-agent.optional",
                "title: Optional Multi-Agent Collaboration Pack",
                "description: Legacy two-candidate optional pack fixture.",
                "lifecycle_status: reviewed",
                "version: 0.4.0",
                "exported_at: 2026-07-10",
                "distribution_type: optional_capability",
                "source_provenance: Agent Foundry legacy public fixture",
                "maintainer_contact: test",
                "license: test",
                "sensitivity: public",
                "review_state: reviewed",
                "",
                "compatibility:",
                "  core_schema_version_min: 1",
                "  core_schema_version_max: 1",
                "  vault_layout_versions: [1]",
                "  requires_bootstrap_pack: true",
                "",
                "included_records:",
                "  - id: COLLAB-PACK-001",
                "    kind: practice",
                "    lifecycle_status: candidate",
                "    path: records/practices/COLLAB-PACK-001-review-handoff.md",
                "    source_version: 6",
                f'    content_sha256: "{sha256(practice)}"',
                "    destination_layer: canonical_vault_record",
                "    membership_role: optional_member",
                "    activation_default: manual_review",
                "    import_action: create_or_review_update",
                "  - id: ASSET-COLLAB-PACK-001",
                "    kind: asset",
                "    lifecycle_status: candidate",
                "    path: records/assets/ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml",
                "    source_version: 6",
                f'    content_sha256: "{sha256(asset)}"',
                "    destination_layer: canonical_vault_record",
                "    membership_role: optional_member",
                "    activation_default: manual_review",
                "    import_action: create_or_review_update",
                "",
                "executable_payloads: []",
                "",
                "conflict_policy:",
                "  id_collision: fail_closed",
                "  same_version_hash_mismatch: fail_closed",
                "  newer_version_update: reviewed_diff_required",
                "  local_edit_behavior: preserve_vault_and_propose_merge",
                "  rollback_notes: preserve legacy candidates",
                "",
                "integrity:",
                "  digest_algorithm: sha256",
                "  manifest_paths_are_relative: true",
                "  private_vault_content: excluded",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return pack


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


def apply_pack(pack_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(APPLY), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root), "--apply"])


def compare_pack(pack_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(COMPARE), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root)])


def update_pack(
    pack_root: Path,
    vault_root: Path,
    *,
    apply: bool = False,
    backup_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [str(UPDATE), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root)]
    if backup_root is not None:
        args.extend(["--backup-root", str(backup_root)])
    if apply:
        args.append("--apply")
    return run(args)


def restore_pack(backup_root: Path, vault_root: Path, *, apply: bool = False) -> subprocess.CompletedProcess[str]:
    args = [str(UPDATE), "--restore", str(backup_root), "--vault-root", str(vault_root)]
    if apply:
        args.append("--apply")
    return run(args)


def add_deployed_pack_contract(vault_root: Path, source_authority: str) -> None:
    index = vault_root / "packs" / "deployed-pack-index.yaml"
    text = index.read_text(encoding="utf-8")
    marker = "    records:\n"
    index.write_text(
        text.replace(
            marker,
            "\n".join(
                [
                    "    pack_contract:",
                    "      promised_use_case: update comparison fixture",
                    "      deployment_role: optional user-selected capability",
                    f"      source_authority_after_deployment: {source_authority}",
                    "      non_authority_boundaries: [generated adapters are downstream only, runtime installs are downstream only]",
                    "    records:",
                    "",
                ]
            ),
            1,
        ),
        encoding="utf-8",
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-pack-update-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        v1 = write_pack(base, "pack-v1", "0.1.0", "Version one.")
        v1_same_version_changed = write_pack(base, "pack-v1-changed", "0.1.0", "Version one changed.")
        v2 = write_pack(base, "pack-v2", "0.2.0", "Version two.")
        v2_payload = write_pack(base, "pack-v2-payload", "0.2.0", "Version two.", include_payload=True)
        missing_provenance = write_pack(
            base,
            "pack-missing-provenance",
            "0.2.0",
            "Version two.",
            include_source_provenance=False,
        )
        incompatible = write_pack(base, "pack-incompatible", "0.2.0", "Version two.", schema_version="999")
        incompatible_core = write_pack(base, "pack-incompatible-core", "0.2.0", "Version two.", core_min="2", core_max="3")

        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))
        errors.extend(expect("apply-v1", apply_pack(v1, vault), True, "metadata: written"))
        index_after_apply = (vault / "packs" / "deployed-pack-index.yaml").read_text(encoding="utf-8")
        errors.extend(expect("compare-unchanged", compare_pack(v1, vault), True, "status: unchanged"))
        add_deployed_pack_contract(vault, "selected User Vault records")
        errors.extend(expect("compare-advanced-deployed-metadata", compare_pack(v1, vault), True, "status: unchanged"))
        (vault / "packs" / "deployed-pack-index.yaml").write_text(index_after_apply, encoding="utf-8")
        add_deployed_pack_contract(vault, "runtime generated adapter authority")
        errors.extend(
            expect(
                "compare-unsafe-deployed-metadata-fails",
                compare_pack(v1, vault),
                False,
                "must not claim runtime/generated/Core/pack authority",
            )
        )
        (vault / "packs" / "deployed-pack-index.yaml").write_text(index_after_apply, encoding="utf-8")
        errors.extend(expect("compare-same-version-mismatch", compare_pack(v1_same_version_changed, vault), False, "same pack id and version"))
        errors.extend(expect("compare-clean-update", compare_pack(v2, vault), True, "status: clean_update_available"))
        errors.extend(expect("compare-clean-update-count", compare_pack(v2, vault), True, "clean_update: 1"))

        target = vault / "practices" / "meta" / "UPDATE-001.md"
        backup = base / "backup-v1-v2"
        errors.extend(expect("update-dry-run", update_pack(v2, vault), True, "status: update_ready"))
        if backup.exists():
            errors.append("update-dry-run: backup was created")
        errors.extend(
            expect(
                "update-apply",
                update_pack(v2, vault, apply=True, backup_root=backup),
                True,
                "status: updated",
            )
        )
        receipt = backup / "receipt.json"
        if not receipt.exists():
            errors.append("update-apply: backup receipt missing")
        if stat.S_IMODE(backup.stat().st_mode) != 0o700:
            errors.append("update-apply: backup root is not mode 0700")
        if receipt.exists() and stat.S_IMODE(receipt.stat().st_mode) != 0o600:
            errors.append("update-apply: backup receipt is not mode 0600")
        if "Version two." not in target.read_text(encoding="utf-8"):
            errors.append("update-apply: record content did not update")
        errors.extend(expect("restore-dry-run", restore_pack(backup, vault), True, "status: restore_ready"))
        errors.extend(expect("restore-apply", restore_pack(backup, vault, apply=True), True, "status: restored"))
        if (vault / "packs" / "deployed-pack-index.yaml").read_text(encoding="utf-8") != index_after_apply:
            errors.append("restore-apply: deployed pack metadata did not return to its exact preimage")
        if "Version one." not in target.read_text(encoding="utf-8"):
            errors.append("restore-apply: record content did not return to its preimage")
        if not backup.exists():
            errors.append("restore-apply: backup was not retained")

        target.write_text(target.read_text(encoding="utf-8") + "\nLocal edit.\n", encoding="utf-8")
        local_edit_preimages = (sha256(target), sha256(vault / "packs" / "deployed-pack-index.yaml"))
        errors.extend(expect("compare-local-edit-merge", compare_pack(v2, vault), True, "status: merge_required"))
        errors.extend(expect("compare-local-edit-count", compare_pack(v2, vault), True, "merge_required: 1"))
        errors.extend(expect("update-local-edit-holds", update_pack(v2, vault), False, "status: merge_required"))
        if local_edit_preimages != (sha256(target), sha256(vault / "packs" / "deployed-pack-index.yaml")):
            errors.append("update-local-edit-holds: files changed despite HOLD")

        errors.extend(expect("compare-missing-provenance", compare_pack(missing_provenance, vault), False, "source_provenance"))
        errors.extend(expect("compare-incompatible-schema", compare_pack(incompatible, vault), False, "manifest_schema_version"))
        errors.extend(expect("compare-incompatible-core", compare_pack(incompatible_core, vault), False, "Core schema version"))
        errors.extend(expect("compare-blocked-payload", compare_pack(v2_payload, vault), False, "blocked_executable_install: 1"))
        errors.extend(
            expect(
                "compare-blocked-payload-status",
                compare_pack(v2_payload, vault),
                False,
                "status: blocked_executable_install",
            )
        )

        legacy_vault = base / "legacy-vault"
        legacy_pack = write_legacy_optional_pack(base)
        errors.extend(expect("legacy-init", init_blank(legacy_vault), True, "Blank Vault initialized"))
        errors.extend(expect("legacy-bootstrap", deploy_bootstrap(legacy_vault), True, "selected Vault validated"))
        errors.extend(expect("legacy-apply-0.4", apply_pack(legacy_pack, legacy_vault), True, "metadata: written"))
        legacy_practice = legacy_vault / "practices" / "agent-collaboration" / "COLLAB-PACK-001-review-handoff.md"
        legacy_asset = legacy_vault / "assets" / "skills" / "ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml"
        legacy_hashes = (sha256(legacy_practice), sha256(legacy_asset))
        legacy_backup = base / "legacy-upgrade-backup"
        errors.extend(expect("legacy-update-preview", update_pack(OPTIONAL_PACK, legacy_vault), True, "from_version: 0.4.0"))
        errors.extend(
            expect(
                "legacy-update-apply",
                update_pack(OPTIONAL_PACK, legacy_vault, apply=True, backup_root=legacy_backup),
                True,
                "to_version: 0.5.0",
            )
        )
        current_practice = legacy_vault / "practices" / "agent-collaboration" / "COLLAB-001-issue-code-work-uses-prs.md"
        current_asset = legacy_vault / "assets" / "skills" / "ASSET-COLLAB-001-agent-collaboration.asset.yaml"
        if "status: proposed" not in current_practice.read_text(encoding="utf-8"):
            errors.append("legacy-update-apply: current practice was not proposed")
        if "status: proposed" not in current_asset.read_text(encoding="utf-8"):
            errors.append("legacy-update-apply: current asset was not proposed")
        if legacy_hashes != (sha256(legacy_practice), sha256(legacy_asset)):
            errors.append("legacy-update-apply: legacy candidate evidence changed")
        errors.extend(expect("legacy-restore", restore_pack(legacy_backup, legacy_vault, apply=True), True, "status: restored"))
        if current_practice.exists() or current_asset.exists():
            errors.append("legacy-restore: new 0.5.0 members remain after restore")
        if legacy_hashes != (sha256(legacy_practice), sha256(legacy_asset)):
            errors.append("legacy-restore: legacy candidate evidence changed")
        drift_backup = base / "legacy-drift-backup"
        errors.extend(
            expect(
                "legacy-drift-update",
                update_pack(OPTIONAL_PACK, legacy_vault, apply=True, backup_root=drift_backup),
                True,
                "status: updated",
            )
        )
        current_practice.write_text(current_practice.read_text(encoding="utf-8") + "\nAdopter edit after update.\n", encoding="utf-8")
        drift_state = (sha256(current_practice), sha256(legacy_vault / "packs" / "deployed-pack-index.yaml"))
        errors.extend(
            expect(
                "legacy-drift-restore-blocked",
                restore_pack(drift_backup, legacy_vault, apply=True),
                False,
                "status: restore_blocked",
            )
        )
        if drift_state != (sha256(current_practice), sha256(legacy_vault / "packs" / "deployed-pack-index.yaml")):
            errors.append("legacy-drift-restore-blocked: restore partially wrote before HOLD")

    if errors:
        print("Capability pack update test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack update test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
