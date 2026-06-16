#!/usr/bin/env python3
"""Executable AF8 scenario matrix for capability-system ownership boundaries."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import sync_status
from adapter_install_receipt import receipt_status
from sync_status import generated_output_status, runtime_drift_status, setup_report


@dataclass(frozen=True)
class Scenario:
    name: str
    setup: str
    expected_status: str
    allowed_reads: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    forbidden_writes: tuple[str, ...]
    failure_mode: str
    recovery_hint: str
    gap_type: str


SCENARIOS = [
    Scenario(
        name="one-core-one-selected-vault",
        setup="single Core checkout, selected Vault, generated output present, no runtime receipt yet",
        expected_status="generated_output ready; receipt missing; ChatGPT manual import explicit",
        allowed_reads=("Core", "selected Vault", "generated output", "runtime manifest", "install receipt"),
        allowed_writes=(),
        forbidden_writes=("Core", "selected Vault", "generated output", "runtime files"),
        failure_mode="status-only report must not imply runtime freshness before install receipt exists",
        recovery_hint="review generated output, then run runtime install only through approved apply path",
        gap_type="test-only",
    ),
    Scenario(
        name="one-core-switched-selected-vault",
        setup="same Core checkout points to a different selected Vault and output root",
        expected_status="ownership distinguishes Core, Vault, generated output, and local config",
        allowed_reads=("Core", "new selected Vault", "new generated output", "local config"),
        allowed_writes=(),
        forbidden_writes=("previous Vault", "runtime files"),
        failure_mode="agent could apply stale generated output from the previous Vault",
        recovery_hint="regenerate selected Vault adapter output before runtime refresh",
        gap_type="implementation-needed",
    ),
    Scenario(
        name="two-core-checkouts-one-vault",
        setup="two Core worktrees share one selected Vault",
        expected_status="Core path is diagnostic and Vault remains canonical for practice/asset records",
        allowed_reads=("both Core checkouts", "selected Vault"),
        allowed_writes=(),
        forbidden_writes=("runtime files", "other Core checkout"),
        failure_mode="receipt or config references moved/alternate Core checkout",
        recovery_hint="use explicit core-root/vault-root and refresh generated output from intended checkout",
        gap_type="evidence-only",
    ),
    Scenario(
        name="two-users-separate-vaults-output",
        setup="two users have separate Vaults and generated output roots",
        expected_status="private paths stay local and generated output roots are not shared implicitly",
        allowed_reads=("current user's Core", "current user's Vault", "current user's generated output"),
        allowed_writes=(),
        forbidden_writes=("other user's Vault", "other user's runtime files"),
        failure_mode="shared repo state appears to authorize private runtime mutation",
        recovery_hint="treat private config and runtime receipt as machine-local",
        gap_type="evidence-only",
    ),
    Scenario(
        name="moved-core-path-existing-runtime-receipt",
        setup="runtime receipt points to an older Core path after checkout move",
        expected_status="receipt adapter_root remains selected-output authority; Core reference is secondary",
        allowed_reads=("current Core", "receipt adapter_root", "runtime files"),
        allowed_writes=(),
        forbidden_writes=("runtime files", "old Core path"),
        failure_mode="status compares against wrong Core adapter templates as if authoritative",
        recovery_hint="publish selected output and reinstall through approved path when Core path changes",
        gap_type="implementation-needed",
    ),
    Scenario(
        name="moved-generated-output-stale-receipt",
        setup="receipt points to generated output path that has moved or disappeared",
        expected_status="selected-output unknown or drift, with safe repair guidance",
        allowed_reads=("Core", "Vault", "receipt"),
        allowed_writes=(),
        forbidden_writes=("runtime files", "generated output"),
        failure_mode="runtime appears fresh although selected generated output is unavailable",
        recovery_hint="regenerate selected Vault adapter output, dry-run install, then apply",
        gap_type="test-only",
    ),
    Scenario(
        name="disabled-runtime-target-stale-installed-files",
        setup="runtime target is disabled but stale installed files still exist",
        expected_status="target skipped because disabled; stale installed files are not overwritten",
        allowed_reads=("runtime manifest", "receipt"),
        allowed_writes=(),
        forbidden_writes=("disabled target install path",),
        failure_mode="disabled target is silently refreshed",
        recovery_hint="enable target explicitly before planning or applying runtime install",
        gap_type="implementation-needed",
    ),
    Scenario(
        name="manual-chatgpt-target-generated-files-present",
        setup="ChatGPT generated files exist but no stable local runtime target exists",
        expected_status="manual import required and explicit",
        allowed_reads=("generated ChatGPT files", "runtime manifest"),
        allowed_writes=(),
        forbidden_writes=("ChatGPT platform state", "runtime files"),
        failure_mode="status implies managed ChatGPT install",
        recovery_hint="manual import generated ChatGPT files when desired",
        gap_type="test-only",
    ),
    Scenario(
        name="missing-runtime-manifest",
        setup="Core checkout has no local runtime manifest",
        expected_status="template-read-only or no local runtime manifest; no local manifest is created by status",
        allowed_reads=("runtime manifest template",),
        allowed_writes=(),
        forbidden_writes=("runtime/local/runtime_manifest.yaml",),
        failure_mode="status command initializes private runtime config unexpectedly",
        recovery_hint="run runtime_manifest.py init only when the user wants local runtime config",
        gap_type="test-only",
    ),
    Scenario(
        name="selected-vault-unavailable",
        setup="configured selected Vault path is unavailable",
        expected_status="root validation reports missing Vault and blocks publish/install assumptions",
        allowed_reads=("Core", "local config"),
        allowed_writes=(),
        forbidden_writes=("Core", "generated output", "runtime files"),
        failure_mode="agent harvests, publishes, or installs without selected Vault",
        recovery_hint="select or initialize a Vault before harvesting, refreshing, or applying packs",
        gap_type="test-only",
    ),
    Scenario(
        name="pack-metadata-present-generated-output-absent",
        setup="Vault records deployed pack metadata but generated adapter output is absent",
        expected_status="deployed pack visible; generated_output missing; runtime install blocked",
        allowed_reads=("Core", "selected Vault", "runtime manifest"),
        allowed_writes=(),
        forbidden_writes=("runtime files",),
        failure_mode="pack deployment is mistaken for active runtime capability",
        recovery_hint="regenerate selected Vault adapter output before runtime install or refresh",
        gap_type="test-only",
    ),
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_core(root: Path, *, with_template: bool = True) -> Path:
    core = root / "core"
    if with_template:
        write(
            core / "runtime" / "templates" / "runtime_manifest.template.yaml",
            "\n".join(
                [
                    "targets:",
                    "  codex:",
                    "    status: disabled",
                    "    install_path: ~/.codex/skills",
                    "    ownership_mode: managed-directories",
                    "  chatgpt:",
                    "    status: manual",
                    '    install_path: ""',
                    "    ownership_mode: manual-import",
                    "",
                ]
            ),
        )
    return core


def make_vault(root: Path) -> Path:
    vault = root / "vault"
    (vault / "practices").mkdir(parents=True)
    write(
        vault / "packs" / "deployed-pack-index.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-15",
                "deployed_packs:",
                "  - pack_id: pack.bootstrap.minimal",
                '    version: "0.1.0"',
                "    lifecycle_status: deployed",
                "    distribution_type: mandatory_bootstrap",
                "    source:",
                "      kind: local_path",
                "",
            ]
        ),
    )
    return vault


def make_generated(root: Path, *, manifest: bool = True) -> Path:
    generated = root / "generated"
    write(generated / "codex" / "skills" / "example" / "SKILL.md", "# Example\n")
    write(generated / "chatgpt" / "instructions.md", "# ChatGPT\n")
    if manifest:
        write(generated / "adapter-publish-manifest.yaml", "active_practices: []\nactive_assets: []\n")
    return generated


def assert_contains(text: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet in text, f"missing {snippet!r} in:\n{text}"


def assert_matrix_contract() -> None:
    required_names = {
        "one-core-one-selected-vault",
        "one-core-switched-selected-vault",
        "two-core-checkouts-one-vault",
        "two-users-separate-vaults-output",
        "moved-core-path-existing-runtime-receipt",
        "moved-generated-output-stale-receipt",
        "disabled-runtime-target-stale-installed-files",
        "manual-chatgpt-target-generated-files-present",
        "missing-runtime-manifest",
        "selected-vault-unavailable",
        "pack-metadata-present-generated-output-absent",
    }
    names = {scenario.name for scenario in SCENARIOS}
    assert required_names == names, names
    for scenario in SCENARIOS:
        assert scenario.setup
        assert scenario.expected_status
        assert scenario.allowed_reads
        assert scenario.forbidden_writes
        assert scenario.failure_mode
        assert scenario.recovery_hint
        assert scenario.gap_type in {"evidence-only", "docs-only", "test-only", "implementation-needed"}
        assert not scenario.allowed_writes, f"{scenario.name} must remain status/evidence-only"


def assert_status_baseline(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)
    receipt = base / "missing-receipt.json"
    report = setup_report(core, vault, generated, receipt)
    assert_contains(
        report,
        (
            "generated_output: ready",
            "receipt: missing",
            "- chatgpt: manual import required",
            "chatgpt_manual_import: explicit",
            "status-only: no files were written by this report",
            "run runtime install only after generated output dry-run/review; receipt is currently missing",
        ),
    )


def assert_missing_vault_and_output(base: Path) -> None:
    core = make_core(base)
    missing_vault = base / "missing-vault"
    missing_generated = base / "missing-generated"
    report = setup_report(core, missing_vault, missing_generated, base / "missing-receipt.json")
    assert_contains(
        report,
        (
            "deployed_pack: none detected",
            "generated_output: missing",
            "select or initialize a Vault before harvesting, refreshing, or applying packs",
            "regenerate selected Vault adapter output before runtime install or refresh",
        ),
    )


def assert_pack_metadata_without_generated_output(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    report = setup_report(core, vault, base / "absent-generated", base / "missing-receipt.json")
    assert_contains(
        report,
        (
            "deployed_pack: pack.bootstrap.minimal",
            "generated_output: missing",
            "regenerate selected Vault adapter output before runtime install or refresh",
        ),
    )


def assert_missing_manifest_read_only(base: Path) -> None:
    core = make_core(base, with_template=False)
    original_root = sync_status.ROOT
    try:
        sync_status.ROOT = core
        assert runtime_drift_status(base / "missing-receipt.json") == "no local runtime manifest"
        assert not (core / "runtime" / "local" / "runtime_manifest.yaml").exists()
    finally:
        sync_status.ROOT = original_root


def assert_generated_output_states(base: Path) -> None:
    generated = make_generated(base / "present")
    assert generated_output_status(generated) == ("ready", 3)
    no_manifest = make_generated(base / "no-manifest", manifest=False)
    assert generated_output_status(no_manifest) == ("missing-manifest", 2)
    assert generated_output_status(base / "absent") == ("missing", 0)


def assert_stale_receipt_is_unknown(base: Path) -> None:
    receipt = {
        "schema_version": 1,
        "adapter_root": str(base / "moved-generated"),
        "installed_targets": ["codex"],
        "installed_files": [],
    }
    state, problems = receipt_status(receipt)
    assert state == "selected-output-unknown"
    assert problems == ["receipt has no installed files"]


def main() -> int:
    assert_matrix_contract()
    with tempfile.TemporaryDirectory(prefix="agent-foundry-af8-scenarios.") as raw:
        base = Path(raw)
        assert_status_baseline(base / "baseline")
        assert_missing_vault_and_output(base / "missing")
        assert_pack_metadata_without_generated_output(base / "pack-no-generated")
        assert_missing_manifest_read_only(base / "missing-manifest")
        assert_generated_output_states(base / "generated-states")
        assert_stale_receipt_is_unknown(base / "stale-receipt")
    print(f"AF8 capability scenario matrix tests passed ({len(SCENARIOS)} scenarios).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
