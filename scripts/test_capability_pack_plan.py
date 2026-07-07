#!/usr/bin/env python3
"""Regression tests for read-only capability pack planning."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import deploy_capability_pack as deploy_parser
import plan_capability_pack as planner


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts" / "deploy_capability_pack.py"
INIT = ROOT / "scripts" / "init_vault.py"
PLAN = ROOT / "scripts" / "plan_capability_pack.py"
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


def practice_text(item_id: str, filename: str = "", domain: str = "meta") -> str:
    return "\n".join(
        [
            "---",
            f'id: "{item_id}"',
            f'title: "{filename or item_id}"',
            f'domain: "{domain}"',
            'status: "candidate"',
            "---",
            "",
            "Fixture practice.",
            "",
        ]
    )


def asset_text(item_id: str, asset_type: str = "skill") -> str:
    return "\n".join(
        [
            f"id: {item_id}",
            f"title: {item_id}",
            "status: candidate",
            f"asset_type: {asset_type}",
            "",
        ]
    )


def write_probe_pack(
    base: Path,
    name: str,
    records: list[dict[str, str]],
    payloads: list[dict[str, str]] | None = None,
    *,
    manifest_schema_version: str = "1",
    include_source_provenance: bool = True,
    include_conflict_policy: bool = True,
    include_integrity: bool = True,
    core_schema_min: str = "1",
    core_schema_max: str = "1",
    advanced_metadata: list[str] | None = None,
) -> Path:
    pack = base / name
    pack.mkdir(parents=True, exist_ok=True)
    lines = [
        f"manifest_schema_version: {manifest_schema_version}",
        f"pack_id: pack.probe.{name}",
        f"title: Probe Pack {name}",
        "description: Probe pack for planner regression tests.",
        "lifecycle_status: candidate",
        "version: 0.1.0",
        "exported_at: 2026-06-12",
        "distribution_type: optional_capability",
        "maintainer_contact: test",
        "license: test",
        "sensitivity: public",
        "review_state: unreviewed",
        "",
        "compatibility:",
        f"  core_schema_version_min: {core_schema_min}",
        f"  core_schema_version_max: {core_schema_max}",
        "  vault_layout_versions: [1]",
        "  requires_bootstrap_pack: false",
        "",
        "included_records:",
    ]
    if include_source_provenance:
        lines.insert(8, "source_provenance: test fixture")
    if advanced_metadata:
        compatibility_index = lines.index("compatibility:")
        lines[compatibility_index:compatibility_index] = ["", *advanced_metadata, ""]
    for record in records:
        kind = record.get("kind", "practice")
        lines.extend(
            [
                f"  - id: {record['id']}",
                f"    kind: {kind}",
                "    lifecycle_status: candidate",
            ]
        )
        if "path" in record:
            lines.append(f"    path: {record['path']}")
        lines.extend(
            [
                "    source_version: 1",
                f"    content_sha256: \"{record['sha']}\"",
                "    destination_layer: canonical_vault_record",
                "    membership_role: optional_member",
                "    activation_default: manual_review",
                "    import_action: create_or_review_update",
            ]
        )
    lines.append("")
    lines.append("executable_payloads:")
    for payload in payloads or []:
        lines.extend(
            [
                f"  - id: {payload['id']}",
                f"    title: {payload['id']}",
                "    lifecycle_status: candidate",
                f"    path: {payload['path']}",
                f"    source_sha256: \"{payload['sha']}\"",
                "    interpreter: python3",
                "    execute_from_pack: false",
                "    install_boundary: managed_runtime_copy_required",
                "    permissions: [filesystem-read]",
                "    dependencies: []",
                "    runtime_impact: test",
            ]
        )
    if not payloads:
        lines[-1] = "executable_payloads: []"
    if include_conflict_policy:
        lines.extend(
            [
                "",
                "conflict_policy:",
                "  id_collision: fail_closed",
                "  same_version_hash_mismatch: fail_closed",
                "  newer_version_update: reviewed_diff_required",
                "  local_edit_behavior: preserve_vault_and_propose_merge",
                "  rollback_notes: test",
            ]
        )
    if include_integrity:
        lines.extend(
            [
                "",
                "integrity:",
                "  digest_algorithm: sha256",
                "  manifest_paths_are_relative: true",
                "  private_vault_content: excluded",
            ]
        )
    (pack / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pack


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"])


def plan_pack(pack_root: Path, vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(PLAN), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root)])


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


def write_deployed_index(vault: Path, pack_id: str, version: str, manifest_hash: str, record_id: str, record_hash: str) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-12",
                "deployed_packs:",
                f"  - pack_id: {pack_id}",
                f"    version: {version}",
                "    source:",
                f"      manifest_sha256: {manifest_hash}",
                "    records:",
                f"      - id: {record_id}",
                f"        deployed_sha256: {record_hash}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_reordered_deployed_index(
    vault: Path, pack_id: str, version: str, manifest_hash: str, record_id: str, record_hash: str
) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-12",
                "deployed_packs:",
                f"  - title: Reordered {pack_id}",
                f"    pack_id: \"{pack_id}\"",
                "    source:",
                "      kind: local_path",
                f"      manifest_sha256: \"{manifest_hash}\"",
                f"    version: \"{version}\"",
                "    records:",
                f"      - kind: practice",
                f"        path: practices/meta/BOOT-001-bootstrap-orientation.md",
                f"        deployed_sha256: \"{record_hash}\"",
                f"        id: \"{record_id}\"",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_advanced_deployed_index(
    vault: Path, pack_id: str, version: str, manifest_hash: str, record_id: str, record_hash: str
) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-12",
                "deployed_packs:",
                f"  - pack_id: {pack_id}",
                f"    version: {version}",
                "    source:",
                f"      manifest_sha256: {manifest_hash}",
                "    pack_contract:",
                "      promised_use_case: reviewed deployed metadata fixture",
                "      deployment_role: optional user-selected capability",
                "      source_authority_after_deployment: selected User Vault records",
                "      non_authority_boundaries: [generated adapters are downstream only, runtime installs are downstream only]",
                "    records:",
                f"      - id: {record_id}",
                f"        deployed_sha256: {record_hash}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_malformed_deployed_index(vault: Path) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "schema_version: 1\nupdated: 2026-06-12\ndeployed_packs:\n  - pack_id: pack.bootstrap.minimal\n   version: 0.2.0\n",
        encoding="utf-8",
    )


def parser_contract_errors(base: Path) -> list[str]:
    errors: list[str] = []
    valid = deploy_parser.parse_simple_yaml(
        "\n".join(
            [
                'title: "Quoted title"',
                "compatibility:",
                "  vault_layout_versions: [1, 2]",
                "deployed_packs:",
                '  - title: "Reordered pack"',
                '    version: "0.1.0"',
                "    pack_id: pack.reordered",
                "    source:",
                '      manifest_sha256: "' + ("a" * 64) + '"',
                "    records:",
                "      - deployed_sha256: " + ("b" * 64),
                "        id: RECORD-001",
                "",
            ]
        )
    )
    if valid.get("title") != "Quoted title":
        errors.append("parser quoted scalar contract failed")
    compatibility = valid.get("compatibility", {})
    if not isinstance(compatibility, dict) or compatibility.get("vault_layout_versions") != ["1", "2"]:
        errors.append("parser inline list contract failed")
    packs = valid.get("deployed_packs", [])
    if not isinstance(packs, list) or not isinstance(packs[0], dict) or packs[0].get("pack_id") != "pack.reordered":
        errors.append("parser reordered sequence mapping contract failed")

    invalid_cases = [
        ("duplicate-key", "pack_id: one\npack_id: two\n", "duplicate mapping key"),
        ("odd-indent", "deployed_packs:\n  - pack_id: one\n   version: 1\n", "unsupported odd indentation"),
        ("malformed-nesting", "deployed_packs:\n  - pack_id: one\n      version: 1\n", "unexpected"),
    ]
    for name, text, expected in invalid_cases:
        try:
            deploy_parser.parse_simple_yaml(text)
        except ValueError as exc:
            if expected not in str(exc):
                errors.append(f"{name}: expected error containing {expected!r}, got {exc}")
        else:
            errors.append(f"{name}: parser accepted malformed metadata")

    vault = base / "parser-vault"
    write_reordered_deployed_index(vault, "pack.reordered", "0.1.0", "a" * 64, "RECORD-001", "b" * 64)
    records, metadata_errors = planner.deployed_pack_records(vault, "pack.reordered")
    if metadata_errors or records.get("RECORD-001", {}).get("deployed_sha256") != "b" * 64:
        errors.append(f"deployed index reordered parse failed: {metadata_errors} {records}")

    write_deployed_index(vault, "pack.reordered", "0.1.0", "not-a-sha", "RECORD-001", "b" * 64)
    records, metadata_errors = planner.deployed_pack_records(vault, "pack.reordered")
    if records or "source.manifest_sha256 must be sha256" not in "; ".join(metadata_errors):
        errors.append(f"deployed index invalid manifest hash did not fail closed: {metadata_errors} {records}")

    deployed_index = vault / "packs" / "deployed-pack-index.yaml"
    deployed_index.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "deployed_packs:",
                "  - pack_id: pack.reordered",
                "    source:",
                '      manifest_sha256: "' + ("a" * 64) + '"',
                "    records: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    records, metadata_errors = planner.deployed_pack_records(vault, "pack.reordered")
    if records or "missing version" not in "; ".join(metadata_errors):
        errors.append(f"deployed index missing version did not fail closed: {metadata_errors} {records}")

    deployed_index.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "deployed_packs:",
                "  - pack_id: pack.reordered",
                '    version: "0.1.0"',
                "    records: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    records, metadata_errors = planner.deployed_pack_records(vault, "pack.reordered")
    if records or "missing source" not in "; ".join(metadata_errors):
        errors.append(f"deployed index missing source did not fail closed: {metadata_errors} {records}")

    deployed_index.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "deployed_packs:",
                "  - pack_id: pack.reordered",
                '    version: "0.1.0"',
                "    source: local_path",
                "    records: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    records, metadata_errors = planner.deployed_pack_records(vault, "pack.reordered")
    if records or "source must be a mapping" not in "; ".join(metadata_errors):
        errors.append(f"deployed index scalar source did not fail closed: {metadata_errors} {records}")
    return errors


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-pack-plan-") as tmp:
        base = Path(tmp)
        errors.extend(parser_contract_errors(base))
        vault = base / "vault"
        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))

        bootstrap_plan = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(expect("plan-bootstrap-add", bootstrap_plan, True, "add: 25"))
        errors.extend(expect("plan-bootstrap-no-writes", bootstrap_plan, True, "writes: none"))

        optional_without_bootstrap = plan_pack(OPTIONAL_PACK, vault)
        errors.extend(
            expect(
                "plan-optional-requires-bootstrap",
                optional_without_bootstrap,
                False,
                "pack requires bootstrap pack",
            )
        )

        errors.extend(expect("deploy-bootstrap", deploy_bootstrap(vault), True, "selected Vault validated"))

        bootstrap_after_deploy = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(expect("plan-bootstrap-skip-after-deploy", bootstrap_after_deploy, True, "skip: 25"))

        optional_after_bootstrap = plan_pack(OPTIONAL_PACK, vault)
        errors.extend(expect("plan-optional-adds-records", optional_after_bootstrap, True, "add: 2"))
        errors.extend(expect("plan-optional-no-executable-block", optional_after_bootstrap, True, "blocked_executable_install: 0"))

        advanced_record = base / "advanced-metadata" / "records" / "ADV.md"
        advanced_record.parent.mkdir(parents=True, exist_ok=True)
        advanced_record.write_text(practice_text("ADV-001"), encoding="utf-8")
        advanced_pack = write_probe_pack(
            base,
            "advanced-metadata",
            [{"id": "ADV-001", "path": "records/ADV.md", "sha": sha256(advanced_record)}],
            advanced_metadata=[
                "pack_contract:",
                "  promised_use_case: reviewed optional capability fixture",
                "  deployment_role: optional user-selected capability",
                "  source_authority_after_deployment: selected User Vault records",
                "  non_authority_boundaries: [generated adapters are downstream only, runtime installs are downstream only]",
                "export_policy:",
                "  exportability: review_required",
                "  privacy_class: sanitized",
                "  excluded_material: [private evidence, raw logs]",
                "  review_required: true",
                "runtime_projection:",
                "  downstream_only: true",
                "  generated_adapter_intent: generated_adapter_projection",
                "  runtime_install: review_required",
                "  authority: downstream_only",
                "lifecycle_policy:",
                "  split_behavior: review_required",
                "  merge_behavior: review_required",
                "  deprecation_behavior: review_required",
                "  update_behavior: reviewed_diff_required",
                "candidate_provenance:",
                "  review_only: true",
                "  candidate_ids: [candidate.probe.advanced]",
                "  canonical: false",
                "  activation_input: false",
                "  export_input: false",
            ],
        )
        advanced_metadata = plan_pack(advanced_pack, vault)
        errors.extend(expect("plan-advanced-metadata-valid", advanced_metadata, True, "add: 1"))

        bad_authority_record = base / "bad-advanced-authority" / "records" / "BAD.md"
        bad_authority_record.parent.mkdir(parents=True, exist_ok=True)
        bad_authority_record.write_text(practice_text("BAD-AUTH-001"), encoding="utf-8")
        bad_authority_pack = write_probe_pack(
            base,
            "bad-advanced-authority",
            [{"id": "BAD-AUTH-001", "path": "records/BAD.md", "sha": sha256(bad_authority_record)}],
            advanced_metadata=[
                "pack_contract:",
                "  promised_use_case: unsafe authority fixture",
                "  deployment_role: optional user-selected capability",
                "  source_authority_after_deployment: runtime generated adapter is canonical authority",
                "  non_authority_boundaries: [generated adapters are downstream only, runtime installs are downstream only]",
            ],
        )
        bad_authority = plan_pack(bad_authority_pack, vault)
        errors.extend(
            expect(
                "plan-advanced-runtime-authority-fails-closed",
                bad_authority,
                False,
                "must not claim runtime/generated/Core/pack authority",
            )
        )

        bad_evidence_record = base / "bad-advanced-evidence" / "records" / "BAD.md"
        bad_evidence_record.parent.mkdir(parents=True, exist_ok=True)
        bad_evidence_record.write_text(practice_text("BAD-EVIDENCE-001"), encoding="utf-8")
        bad_evidence_pack = write_probe_pack(
            base,
            "bad-advanced-evidence",
            [{"id": "BAD-EVIDENCE-001", "path": "records/BAD.md", "sha": sha256(bad_evidence_record)}],
            advanced_metadata=[
                "evidence_sources:",
                "  - /Users/example/private/raw-session.log",
            ],
        )
        bad_evidence = plan_pack(bad_evidence_pack, vault)
        errors.extend(
            expect(
                "plan-private-evidence-fails-closed",
                bad_evidence,
                False,
                "private/local evidence reference",
            )
        )

        candidate_manifest = base / "candidate-schema-as-pack" / "manifest.yaml"
        candidate_manifest.parent.mkdir(parents=True, exist_ok=True)
        candidate_manifest.write_text(
            "\n".join(
                [
                    "candidate_schema_version: 1",
                    "candidate_id: candidate.probe.review-only",
                    "proposed_pack_id: pack.probe.review-only",
                    "title: Review-only candidate",
                    "outcome: candidate",
                    "confidence: medium",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        candidate_as_manifest = plan_pack(candidate_manifest.parent, vault)
        errors.extend(
            expect(
                "plan-candidate-schema-review-only",
                candidate_as_manifest,
                False,
                "candidate schema records are review-only",
            )
        )

        hybrid_record = base / "hybrid-candidate-manifest" / "records" / "HYBRID.md"
        hybrid_record.parent.mkdir(parents=True, exist_ok=True)
        hybrid_record.write_text(practice_text("HYBRID-001"), encoding="utf-8")
        hybrid_pack = write_probe_pack(
            base,
            "hybrid-candidate-manifest",
            [{"id": "HYBRID-001", "path": "records/HYBRID.md", "sha": sha256(hybrid_record)}],
        )
        hybrid_manifest = hybrid_pack / "manifest.yaml"
        hybrid_manifest.write_text(
            "candidate_schema_version: 1\n" + hybrid_manifest.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        hybrid_candidate_as_manifest = plan_pack(hybrid_pack, vault)
        errors.extend(
            expect(
                "plan-hybrid-candidate-manifest-review-only",
                hybrid_candidate_as_manifest,
                False,
                "candidate schema records are review-only",
            )
        )

        write_deployed_index(
            vault,
            "pack.multi-agent.optional",
            "0.3.2",
            "0" * 64,
            "COLLAB-PACK-001",
            "",
        )
        mismatch = plan_pack(OPTIONAL_PACK, vault)
        errors.extend(expect("plan-same-version-hash-mismatch", mismatch, False, "different manifest_sha256"))

        target = vault / "practices" / "meta" / "BOOT-001-bootstrap-orientation.md"
        current_hash = sha256(target)
        write_deployed_index(
            vault,
            "pack.bootstrap.minimal",
            "0.2.1",
            sha256(BOOTSTRAP_PACK / "manifest.yaml"),
            "BOOT-001",
            current_hash,
        )
        target.write_text(target.read_text(encoding="utf-8") + "\nLocal user edit fixture.\n", encoding="utf-8")
        local_edit = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(expect("plan-local-edit-merge-required", local_edit, True, "merge_required: 1"))

        target.write_text(target.read_text(encoding="utf-8").replace("\nLocal user edit fixture.\n", ""), encoding="utf-8")
        write_reordered_deployed_index(
            vault,
            "pack.bootstrap.minimal",
            "0.2.1",
            sha256(BOOTSTRAP_PACK / "manifest.yaml"),
            "BOOT-001",
            sha256(target),
        )
        reordered = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(expect("plan-reordered-metadata-parses", reordered, True, "skip: 25"))

        write_advanced_deployed_index(
            vault,
            "pack.bootstrap.minimal",
            "0.2.1",
            sha256(BOOTSTRAP_PACK / "manifest.yaml"),
            "BOOT-001",
            sha256(target),
        )
        advanced_deployed_index = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(expect("plan-advanced-deployed-index-parses", advanced_deployed_index, True, "skip: 25"))

        write_malformed_deployed_index(vault)
        malformed_metadata = plan_pack(BOOTSTRAP_PACK, vault)
        errors.extend(
            expect(
                "plan-malformed-deployed-index-fails-closed",
                malformed_metadata,
                False,
                "deployed-pack-index.yaml parse error",
            )
        )
        (vault / "packs" / "deployed-pack-index.yaml").unlink()

        missing_pack = write_probe_pack(
            base,
            "missing-path",
            [{"id": "MISSING-PATH-001", "sha": "0" * 64}],
        )
        missing_path = plan_pack(missing_pack, vault)
        errors.extend(expect("plan-missing-path-fails-closed", missing_path, False, "missing path"))

        outside = base / "outside.md"
        outside.write_text(practice_text("OUTSIDE-001"), encoding="utf-8")
        traversal_pack = write_probe_pack(
            base,
            "path-traversal",
            [{"id": "OUTSIDE-001", "path": "../outside.md", "sha": sha256(outside)}],
        )
        traversal = plan_pack(traversal_pack, vault)
        errors.extend(expect("plan-path-traversal-fails-closed", traversal, False, "path escapes pack root"))

        mismatch_file = base / "id-mismatch" / "records" / "WRONG.md"
        mismatch_file.parent.mkdir(parents=True, exist_ok=True)
        mismatch_file.write_text(practice_text("RIGHT-001"), encoding="utf-8")
        mismatch_pack = write_probe_pack(
            base,
            "id-mismatch",
            [{"id": "WRONG-001", "path": "records/WRONG.md", "sha": sha256(mismatch_file)}],
        )
        mismatch_id = plan_pack(mismatch_pack, vault)
        errors.extend(expect("plan-id-mismatch-fails-closed", mismatch_id, False, "does not match source metadata id"))

        duplicate_a = base / "duplicate-destination" / "a" / "DUP.md"
        duplicate_b = base / "duplicate-destination" / "b" / "DUP.md"
        duplicate_a.parent.mkdir(parents=True, exist_ok=True)
        duplicate_b.parent.mkdir(parents=True, exist_ok=True)
        duplicate_a.write_text(practice_text("DUP-001", "Duplicate A"), encoding="utf-8")
        duplicate_b.write_text(practice_text("DUP-002", "Duplicate B"), encoding="utf-8")
        duplicate_pack = write_probe_pack(
            base,
            "duplicate-destination",
            [
                {"id": "DUP-001", "path": "a/DUP.md", "sha": sha256(duplicate_a)},
                {"id": "DUP-002", "path": "b/DUP.md", "sha": sha256(duplicate_b)},
            ],
        )
        duplicate_destination = plan_pack(duplicate_pack, vault)
        errors.extend(
            expect(
                "plan-duplicate-destination-fails-closed",
                duplicate_destination,
                False,
                "duplicate planned destination",
            )
        )

        payload_outside = base / "outside_payload.py"
        payload_outside.write_text("print('do not execute')\n", encoding="utf-8")
        payload_record = base / "payload-traversal" / "records" / "PAYLOAD.md"
        payload_record.parent.mkdir(parents=True, exist_ok=True)
        payload_record.write_text(practice_text("PAYLOAD-001"), encoding="utf-8")
        payload_pack = write_probe_pack(
            base,
            "payload-traversal",
            [{"id": "PAYLOAD-001", "path": "records/PAYLOAD.md", "sha": sha256(payload_record)}],
            [{"id": "helper.outside", "path": "../outside_payload.py", "sha": sha256(payload_outside)}],
        )
        payload_traversal = plan_pack(payload_pack, vault)
        errors.extend(expect("plan-payload-traversal-fails-closed", payload_traversal, False, "path escapes pack root"))

        provenance_record = base / "missing-provenance" / "records" / "PROV.md"
        provenance_record.parent.mkdir(parents=True, exist_ok=True)
        provenance_record.write_text(practice_text("PROV-001"), encoding="utf-8")
        missing_provenance_pack = write_probe_pack(
            base,
            "missing-provenance",
            [{"id": "PROV-001", "path": "records/PROV.md", "sha": sha256(provenance_record)}],
            include_source_provenance=False,
        )
        missing_provenance = plan_pack(missing_provenance_pack, vault)
        errors.extend(
            expect(
                "plan-missing-provenance-fails-closed",
                missing_provenance,
                False,
                "manifest missing source_provenance",
            )
        )

        schema_record = base / "schema-version" / "records" / "SCHEMA.md"
        schema_record.parent.mkdir(parents=True, exist_ok=True)
        schema_record.write_text(practice_text("SCHEMA-001"), encoding="utf-8")
        schema_pack = write_probe_pack(
            base,
            "schema-version",
            [{"id": "SCHEMA-001", "path": "records/SCHEMA.md", "sha": sha256(schema_record)}],
            manifest_schema_version="999",
        )
        schema_version = plan_pack(schema_pack, vault)
        errors.extend(
            expect(
                "plan-unsupported-schema-version-fails-closed",
                schema_version,
                False,
                "unsupported manifest_schema_version",
            )
        )

        conflict_record = base / "missing-conflict-policy" / "records" / "CONFLICT.md"
        conflict_record.parent.mkdir(parents=True, exist_ok=True)
        conflict_record.write_text(practice_text("CONFLICT-001"), encoding="utf-8")
        conflict_pack = write_probe_pack(
            base,
            "missing-conflict-policy",
            [{"id": "CONFLICT-001", "path": "records/CONFLICT.md", "sha": sha256(conflict_record)}],
            include_conflict_policy=False,
        )
        missing_conflict = plan_pack(conflict_pack, vault)
        errors.extend(
            expect(
                "plan-missing-conflict-policy-fails-closed",
                missing_conflict,
                False,
                "conflict_policy missing",
            )
        )

        integrity_record = base / "missing-integrity" / "records" / "INTEGRITY.md"
        integrity_record.parent.mkdir(parents=True, exist_ok=True)
        integrity_record.write_text(practice_text("INTEGRITY-001"), encoding="utf-8")
        integrity_pack = write_probe_pack(
            base,
            "missing-integrity",
            [{"id": "INTEGRITY-001", "path": "records/INTEGRITY.md", "sha": sha256(integrity_record)}],
            include_integrity=False,
        )
        missing_integrity = plan_pack(integrity_pack, vault)
        errors.extend(expect("plan-missing-integrity-fails-closed", missing_integrity, False, "integrity missing"))

        core_schema_record = base / "core-schema-range" / "records" / "CORE.md"
        core_schema_record.parent.mkdir(parents=True, exist_ok=True)
        core_schema_record.write_text(practice_text("CORE-SCHEMA-001"), encoding="utf-8")
        core_schema_pack = write_probe_pack(
            base,
            "core-schema-range",
            [{"id": "CORE-SCHEMA-001", "path": "records/CORE.md", "sha": sha256(core_schema_record)}],
            core_schema_min="2",
            core_schema_max="3",
        )
        core_schema_range = plan_pack(core_schema_pack, vault)
        errors.extend(
            expect(
                "plan-core-schema-range-fails-closed",
                core_schema_range,
                False,
                "pack does not support Core schema version",
            )
        )

        unsafe_domain_file = base / "unsafe-domain" / "records" / "UNSAFE.md"
        unsafe_domain_file.parent.mkdir(parents=True, exist_ok=True)
        unsafe_domain_file.write_text(practice_text("UNSAFE-DOMAIN-001", domain="../outside"), encoding="utf-8")
        unsafe_domain_pack = write_probe_pack(
            base,
            "unsafe-domain",
            [{"id": "UNSAFE-DOMAIN-001", "path": "records/UNSAFE.md", "sha": sha256(unsafe_domain_file)}],
        )
        unsafe_domain = plan_pack(unsafe_domain_pack, vault)
        errors.extend(expect("plan-unsafe-domain-fails-closed", unsafe_domain, False, "safe single path segment"))

        unsafe_asset_file = base / "unsafe-asset-type" / "records" / "UNSAFE.asset.yaml"
        unsafe_asset_file.parent.mkdir(parents=True, exist_ok=True)
        unsafe_asset_file.write_text(asset_text("UNSAFE-ASSET-001", asset_type="../outside"), encoding="utf-8")
        unsafe_asset_pack = write_probe_pack(
            base,
            "unsafe-asset-type",
            [
                {
                    "id": "UNSAFE-ASSET-001",
                    "kind": "asset",
                    "path": "records/UNSAFE.asset.yaml",
                    "sha": sha256(unsafe_asset_file),
                }
            ],
        )
        unsafe_asset_type = plan_pack(unsafe_asset_pack, vault)
        errors.extend(expect("plan-unsafe-asset-type-fails-closed", unsafe_asset_type, False, "safe single path segment"))

    if errors:
        print("Capability pack plan test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack plan test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
