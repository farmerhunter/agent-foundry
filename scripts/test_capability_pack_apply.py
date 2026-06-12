#!/usr/bin/env python3
"""Regression tests for reviewed capability pack apply behavior."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_capability_pack.py"
DEPLOY = ROOT / "scripts" / "deploy_capability_pack.py"
INIT = ROOT / "scripts" / "init_vault.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
STATUS = ROOT / "scripts" / "sync_status.py"
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


def practice_text(item_id: str, domain: str = "meta") -> str:
    return "\n".join(
        [
            "---",
            f'id: "{item_id}"',
            f'title: "{item_id}"',
            f'domain: "{domain}"',
            'status: "candidate"',
            "---",
            "",
            "Apply fixture practice.",
            "",
        ]
    )


def write_apply_pack(
    base: Path,
    name: str = "apply-pack",
    pack_id: str = "pack.probe.apply",
    item_id: str = "APPLY-001",
    domain: str = "meta",
) -> Path:
    pack = base / name
    record = pack / "records" / f"{item_id}.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(practice_text(item_id, domain=domain), encoding="utf-8")
    (pack / "manifest.yaml").write_text(
        "\n".join(
            [
                "manifest_schema_version: 1",
                f"pack_id: {pack_id}",
                "title: Apply Probe Pack",
                "description: Probe pack for apply regression tests.",
                "lifecycle_status: reviewed",
                "version: 0.1.0",
                "exported_at: 2026-06-12",
                "distribution_type: optional_capability",
                "source_provenance: test fixture",
                "maintainer_contact: test",
                "license: test",
                "sensitivity: public",
                "review_state: reviewed",
                "",
                "compatibility:",
                "  core_schema_version_min: 1",
                "  core_schema_version_max: 1",
                "  vault_layout_versions: [1]",
                "  requires_bootstrap_pack: false",
                "",
                "included_records:",
                f"  - id: {item_id}",
                "    kind: practice",
                "    lifecycle_status: candidate",
                f"    path: records/{item_id}.md",
                "    source_version: 1",
                f"    content_sha256: \"{sha256(record)}\"",
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
                "  rollback_notes: test",
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


def write_conflicting_metadata(vault: Path) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-12",
                "deployed_packs:",
                "  - pack_id: pack.probe.apply",
                "    version: \"0.1.0\"",
                "    source:",
                f"      manifest_sha256: {'0' * 64}",
                "    records: []",
                "",
            ]
        ),
        encoding="utf-8",
    )


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


def apply_pack(pack_root: Path, vault_root: Path, apply: bool) -> subprocess.CompletedProcess[str]:
    args = [str(APPLY), str(pack_root), "--core-root", str(ROOT), "--vault-root", str(vault_root)]
    if apply:
        args.append("--apply")
    return run(args)


def publish_adapters(vault_root: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(PUBLISH),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault_root),
            "--output-root",
            str(output_root),
            "--apply",
        ]
    )


def status_report(vault_root: Path, output_root: Path, receipt_path: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(STATUS),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault_root),
            "--adapter-root",
            str(output_root),
            "--receipt-path",
            str(receipt_path),
        ]
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-pack-apply-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        pack = write_apply_pack(base)

        errors.extend(expect("init-blank-vault", init_blank(vault), True, "Blank Vault initialized and validated."))

        dry_run = apply_pack(pack, vault, apply=False)
        errors.extend(expect("apply-dry-run", dry_run, True, "Dry-run only"))
        if (vault / "practices" / "meta" / "APPLY-001.md").exists():
            errors.append("apply-dry-run: practice record was written")
        if (vault / "packs" / "deployed-pack-index.yaml").exists():
            errors.append("apply-dry-run: deployed pack metadata was written")

        applied = apply_pack(pack, vault, apply=True)
        errors.extend(expect("apply-writes-records", applied, True, "metadata: written"))
        practice_path = vault / "practices" / "meta" / "APPLY-001.md"
        metadata_path = vault / "packs" / "deployed-pack-index.yaml"
        if not practice_path.exists():
            errors.append("apply-writes-records: practice record missing")
        if "APPLY-001" not in (vault / "indexes" / "practice_index.yaml").read_text(encoding="utf-8"):
            errors.append("apply-writes-records: practice index missing APPLY-001")
        if not metadata_path.exists() or "pack.probe.apply" not in metadata_path.read_text(encoding="utf-8"):
            errors.append("apply-writes-records: pack metadata missing")

        reapplied = apply_pack(pack, vault, apply=True)
        errors.extend(expect("apply-idempotent-same-metadata", reapplied, True, "pack metadata already present"))

        conflict_vault = base / "conflict-vault"
        errors.extend(
            expect("init-conflict-vault", init_blank(conflict_vault), True, "Blank Vault initialized and validated.")
        )
        write_conflicting_metadata(conflict_vault)
        conflict = apply_pack(pack, conflict_vault, apply=True)
        errors.extend(expect("apply-refuses-metadata-conflict", conflict, False, "different manifest_sha256"))
        if (conflict_vault / "practices" / "meta" / "APPLY-001.md").exists():
            errors.append("apply-refuses-metadata-conflict: practice was written before metadata refusal")

        unsafe_vault = base / "unsafe-vault"
        unsafe_pack = write_apply_pack(
            base,
            name="unsafe-domain-pack",
            pack_id="pack.probe.unsafe-domain",
            item_id="UNSAFE-APPLY-001",
            domain="../outside",
        )
        errors.extend(expect("init-unsafe-vault", init_blank(unsafe_vault), True, "Blank Vault initialized and validated."))
        unsafe = apply_pack(unsafe_pack, unsafe_vault, apply=True)
        errors.extend(expect("apply-refuses-unsafe-domain", unsafe, False, "safe single path segment"))
        if any(path.name == "UNSAFE-APPLY-001.md" for path in unsafe_vault.rglob("*")):
            errors.append("apply-refuses-unsafe-domain: unsafe destination was written")

        errors.extend(expect("deploy-bootstrap", deploy_bootstrap(vault), True, "selected Vault validated"))
        optional = apply_pack(OPTIONAL_PACK, vault, apply=True)
        errors.extend(expect("apply-optional-multi-agent", optional, True, "metadata: written"))
        optional_practice = vault / "practices" / "agent-collaboration" / "COLLAB-PACK-001-review-handoff.md"
        optional_asset = vault / "assets" / "skills" / "ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml"
        if not optional_practice.exists():
            errors.append("apply-optional-multi-agent: candidate practice missing")
        if not optional_asset.exists():
            errors.append("apply-optional-multi-agent: candidate asset missing")
        vault_text = "\n".join(path.read_text(encoding="utf-8") for path in vault.rglob("*") if path.is_file())
        for expected in ["pack.multi-agent.optional", "COLLAB-PACK-001", "ASSET-COLLAB-PACK-001"]:
            if expected not in vault_text:
                errors.append(f"apply-optional-multi-agent: Vault missing {expected}")
        if "review_handoff_summary.py" in vault_text:
            errors.append("apply-optional-multi-agent: deferred helper payload leaked into Vault records")

        generated = base / "generated-after-optional"
        published = publish_adapters(vault, generated)
        errors.extend(expect("publish-after-optional", published, True, "Adapter publish wrote"))
        generated_text = "\n".join(path.read_text(encoding="utf-8") for path in generated.rglob("*") if path.is_file())
        for candidate_id in ["COLLAB-PACK-001", "ASSET-COLLAB-PACK-001"]:
            if candidate_id in generated_text:
                errors.append(f"publish-after-optional: candidate record leaked into generated output: {candidate_id}")

        status = status_report(vault, generated, base / "missing-receipt.json")
        errors.extend(expect("status-reports-optional-pack", status, True, "pack.multi-agent.optional"))
        errors.extend(expect("status-reports-bootstrap-pack", status, True, "pack.bootstrap.minimal"))

    if errors:
        print("Capability pack apply test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack apply test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
