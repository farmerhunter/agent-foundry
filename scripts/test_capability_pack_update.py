#!/usr/bin/env python3
"""Regression tests for capability pack update comparison."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_capability_pack.py"
COMPARE = ROOT / "scripts" / "compare_capability_pack_update.py"
INIT = ROOT / "scripts" / "init_vault.py"


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


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"])


def apply_pack(pack_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(APPLY), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root), "--apply"])


def compare_pack(pack_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(COMPARE), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root)])


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
        target.write_text(target.read_text(encoding="utf-8") + "\nLocal edit.\n", encoding="utf-8")
        errors.extend(expect("compare-local-edit-merge", compare_pack(v2, vault), True, "status: merge_required"))
        errors.extend(expect("compare-local-edit-count", compare_pack(v2, vault), True, "merge_required: 1"))

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

    if errors:
        print("Capability pack update test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack update test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
