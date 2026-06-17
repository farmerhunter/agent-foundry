#!/usr/bin/env python3
"""Regression tests for disable/retire pack lifecycle behavior."""

from __future__ import annotations

import hashlib
import shutil
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


def apply_pack(vault: Path, pack: Path) -> subprocess.CompletedProcess[str]:
    return run([str(APPLY), str(pack), "--core-root", str(ROOT), "--vault-root", str(vault), "--apply"])


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


def add_metadata_section(vault: Path, lines: list[str]) -> None:
    index = vault / "packs" / "deployed-pack-index.yaml"
    text = index.read_text(encoding="utf-8")
    marker = "    records:\n"
    index.write_text(
        text.replace(marker, "\n".join([*lines, "    records:", ""]), 1),
        encoding="utf-8",
    )


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


def copy_optional_variant(base: Path, name: str, replacements: dict[str, str]) -> Path:
    target = base / name
    shutil.copytree(OPTIONAL_PACK, target)
    manifest = target / "manifest.yaml"
    text = manifest.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    manifest.write_text(text, encoding="utf-8")
    return target


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


def add_deployed_pack_contract(vault: Path, source_authority: str) -> None:
    add_metadata_section(
        vault,
        [
            "    pack_contract:",
            "      promised_use_case: lifecycle fixture",
            "      deployment_role: optional user-selected capability",
            f"      source_authority_after_deployment: {source_authority}",
            "      non_authority_boundaries: [generated adapters are downstream only, runtime installs are downstream only]",
        ],
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
        repeat_metadata_before = digest(vault / "packs" / "deployed-pack-index.yaml")
        errors.extend(expect("apply-optional-repeat", apply_optional(vault), True, "pack metadata already present"))
        repeat_metadata_after = digest(vault / "packs" / "deployed-pack-index.yaml")
        if repeat_metadata_after != repeat_metadata_before:
            errors.append("apply-optional-repeat: same-version same-hash metadata changed")

        same_version_mismatch = copy_optional_variant(
            base,
            "same-version-mismatch-pack",
            {"title: Optional Multi-Agent Collaboration Pack": "title: Optional Multi-Agent Collaboration Pack Changed"},
        )
        errors.extend(
            expect(
                "apply-same-version-hash-mismatch",
                apply_pack(vault, same_version_mismatch),
                False,
                "different manifest_sha256",
            )
        )
        if digest(vault / "packs" / "deployed-pack-index.yaml") != repeat_metadata_before:
            errors.append("apply-same-version-hash-mismatch: metadata changed after refusal")

        newer_version = copy_optional_variant(
            base,
            "newer-version-pack",
            {"version: 0.2.0": "version: 0.3.0"},
        )
        errors.extend(
            expect(
                "apply-newer-version-requires-update-flow",
                apply_pack(vault, newer_version),
                False,
                "blocking record outcome update",
            )
        )
        if digest(vault / "packs" / "deployed-pack-index.yaml") != repeat_metadata_before:
            errors.append("apply-newer-version-requires-update-flow: metadata changed after refusal")

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
        errors.extend(expect("disable-dry-run-rollback-guidance", dry_disable, True, "rollback:"))
        errors.extend(expect("disable-dry-run-defer-guidance", dry_disable, True, "defer:"))
        if digest(metadata) != metadata_before:
            errors.append("disable-dry-run: metadata changed")

        dry_retire = lifecycle(vault, "retire", apply=False)
        errors.extend(expect("retire-dry-run", dry_retire, True, "writes: none"))
        errors.extend(expect("retire-dry-run-reports-records", dry_retire, True, "COLLAB-PACK-001 practice -> archived"))

        activate_plan = lifecycle(vault, "activate", apply=False)
        errors.extend(expect("activate-review-only", activate_plan, False, "status: review_required"))
        errors.extend(expect("activate-writes-none", activate_plan, False, "writes: none"))
        activate_apply = lifecycle(vault, "activate", apply=True)
        errors.extend(expect("activate-apply-refused", activate_apply, False, "cannot be applied"))

        exportable_plan = lifecycle(vault, "exportable", apply=False)
        errors.extend(expect("exportable-review-only", exportable_plan, False, "target_state: exportable"))
        errors.extend(expect("exportable-no-runtime-authority", exportable_plan, False, "runtime_followup:"))

        deprecate_plan = lifecycle(vault, "deprecate", apply=False)
        errors.extend(expect("deprecate-review-only", deprecate_plan, False, "target_state: deprecated"))
        errors.extend(expect("deprecate-reports-records", deprecate_plan, False, "ASSET-COLLAB-PACK-001 asset"))

        split_plan = lifecycle(vault, "split", apply=False)
        errors.extend(expect("split-review-only", split_plan, False, "before-after membership diff"))
        merge_plan = lifecycle(vault, "merge", apply=False)
        errors.extend(expect("merge-review-only", merge_plan, False, "split/merge requires"))

        metadata_with_valid_contract = metadata.read_text(encoding="utf-8")
        add_deployed_pack_contract(vault, "runtime generated adapter authority")
        unsafe_lifecycle_metadata = lifecycle(vault, "disable", apply=False)
        errors.extend(
            expect(
                "disable-unsafe-deployed-metadata-fails",
                unsafe_lifecycle_metadata,
                False,
                "must not claim runtime/generated/Core/pack authority",
            )
        )
        metadata.write_text(metadata_with_valid_contract, encoding="utf-8")

        add_metadata_section(
            vault,
            [
                "    lifecycle_transition:",
                "      evidence: /Users/example/private/raw-session.log",
            ],
        )
        private_metadata = lifecycle(vault, "disable", apply=False)
        errors.extend(expect("disable-local-private-metadata-fails", private_metadata, False, "local-private reference"))
        metadata.write_text(metadata_with_valid_contract, encoding="utf-8")

        add_metadata_section(
            vault,
            [
                "    lifecycle_transition:",
                "      notes: memory-system generated authority with destructive delete records",
            ],
        )
        unsafe_claim = lifecycle(vault, "disable", apply=False)
        errors.extend(expect("disable-memory-destructive-claim-fails", unsafe_claim, False, "unsafe lifecycle claim"))
        metadata.write_text(metadata_with_valid_contract, encoding="utf-8")

        missing_hash_text = "\n".join(
            line
            for line in metadata_with_valid_contract.splitlines()
            if not line.strip().startswith(("imported_sha256:", "deployed_sha256:"))
        ) + "\n"
        metadata.write_text(missing_hash_text, encoding="utf-8")
        missing_hash = lifecycle(vault, "disable", apply=False)
        errors.extend(expect("disable-missing-record-hash-fails", missing_hash, False, "missing deployed/imported hash"))
        metadata.write_text(metadata_with_valid_contract, encoding="utf-8")

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

        wrong_path_vault = base / "wrong-path-vault"
        errors.extend(expect("init-wrong-path-vault", init_blank(wrong_path_vault), True, "Blank Vault initialized"))
        errors.extend(expect("deploy-wrong-path-bootstrap", deploy_bootstrap(wrong_path_vault), True, "selected Vault validated"))
        errors.extend(expect("apply-wrong-path-optional", apply_optional(wrong_path_vault), True, "metadata: written"))
        wrong_user = wrong_path_vault / "practices" / "user" / "USER-LOCAL-001.md"
        write(
            wrong_user,
            "---\nid: USER-LOCAL-001\ntitle: Local User Record\ndomain: user\nstatus: active\n---\n\nUnrelated.\n",
        )
        wrong_user_before = digest(wrong_user)
        wrong_metadata = wrong_path_vault / "packs" / "deployed-pack-index.yaml"
        wrong_metadata.write_text(
            wrong_metadata.read_text(encoding="utf-8").replace(
                "path: practices/agent-collaboration/COLLAB-PACK-001-review-handoff.md",
                "path: practices/user/USER-LOCAL-001.md",
            ),
            encoding="utf-8",
        )
        wrong_path = lifecycle(wrong_path_vault, "retire", apply=True)
        errors.extend(expect("retire-refuses-wrong-path", wrong_path, False, "metadata path points to record id USER-LOCAL-001"))
        if digest(wrong_user) != wrong_user_before:
            errors.append("retire-refuses-wrong-path: unrelated user record changed")
        original_pack_record = (
            wrong_path_vault
            / "practices"
            / "agent-collaboration"
            / "COLLAB-PACK-001-review-handoff.md"
        )
        if "status: candidate" not in original_pack_record.read_text(encoding="utf-8"):
            errors.append("retire-refuses-wrong-path: original pack record changed")

        partial_vault = base / "partial-vault"
        errors.extend(expect("init-partial-vault", init_blank(partial_vault), True, "Blank Vault initialized"))
        errors.extend(expect("deploy-partial-bootstrap", deploy_bootstrap(partial_vault), True, "selected Vault validated"))
        errors.extend(expect("apply-partial-optional", apply_optional(partial_vault), True, "metadata: written"))
        partial_practice = partial_vault / "practices" / "agent-collaboration" / "COLLAB-PACK-001-review-handoff.md"
        partial_asset = partial_vault / "assets" / "skills" / "ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml"
        partial_metadata = partial_vault / "packs" / "deployed-pack-index.yaml"
        before_partial = {
            "practice": digest(partial_practice),
            "asset": digest(partial_asset),
            "practice_index": digest(partial_vault / "indexes" / "practice_index.yaml"),
            "asset_index": digest(partial_vault / "indexes" / "asset_index.yaml"),
            "metadata": digest(partial_metadata),
        }
        asset_index = partial_vault / "indexes" / "asset_index.yaml"
        other_asset = partial_vault / "assets" / "skills" / "ASSET-OTHER-001.yaml"
        write(
            other_asset,
            "\n".join(
                [
                    "id: ASSET-OTHER-001",
                    "title: Other Asset",
                    "asset_type: skill",
                    "status: candidate",
                    "purpose: Fixture.",
                    "responsibility: Fixture.",
                    "non_responsibility: Fixture.",
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
        )
        asset_index.write_text(
            asset_index.read_text(encoding="utf-8").replace(
                "path: assets/skills/ASSET-COLLAB-PACK-001-review-handoff-helper.asset.yaml",
                "path: assets/skills/ASSET-OTHER-001.yaml",
            ),
            encoding="utf-8",
        )
        expected_asset_index_after_tamper = digest(asset_index)
        partial = lifecycle(partial_vault, "retire", apply=True)
        errors.extend(expect("retire-refuses-partial-write", partial, False, "index entry missing or path mismatch"))
        if digest(partial_practice) != before_partial["practice"]:
            errors.append("retire-refuses-partial-write: practice changed before failure")
        if digest(partial_asset) != before_partial["asset"]:
            errors.append("retire-refuses-partial-write: asset changed before failure")
        if digest(partial_vault / "indexes" / "practice_index.yaml") != before_partial["practice_index"]:
            errors.append("retire-refuses-partial-write: practice index changed before failure")
        if digest(asset_index) != expected_asset_index_after_tamper:
            errors.append("retire-refuses-partial-write: asset index changed after preflight failure")
        if digest(partial_metadata) != before_partial["metadata"]:
            errors.append("retire-refuses-partial-write: metadata changed before failure")

    if errors:
        print("Capability pack lifecycle test failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack lifecycle test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
