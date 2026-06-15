#!/usr/bin/env python3
"""Second-machine onboarding and restore fixtures for AF7 capability hardening."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import foundry_config
import install_foundry
import runtime_manifest
from sync_status import setup_report


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_core(root: Path) -> Path:
    core = root / "second-machine-core"
    write(
        core / "runtime" / "templates" / "runtime_manifest.template.yaml",
        "\n".join(
            [
                "schema_version: 1",
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
    vault = root / "selected-vault"
    write(vault / ".agent-foundry-vault.yaml", "layout_version: 1\n")
    write(vault / "indexes" / "practice_index.yaml", "practices: []\n")
    write(vault / "indexes" / "asset_index.yaml", "assets: []\n")
    write(vault / "usage" / "usage-aggregate.yaml", "aggregates: []\n")
    return vault


def make_generated(root: Path) -> Path:
    generated = root / "generated-adapters"
    write(generated / "adapter-publish-manifest.yaml", "active_practices: []\nactive_assets: []\n")
    write(generated / "codex" / "skills" / "example" / "SKILL.md", "# Example\n")
    write(generated / "chatgpt" / "custom-instructions.md", "# ChatGPT\n")
    return generated


def capture_stdout(func, *args, **kwargs) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = func(*args, **kwargs)
    return code, output.getvalue()


def assert_contains(text: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet in text, f"missing {snippet!r} in:\n{text}"


def assert_locator_round_trip(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    config = base / "machine-home" / ".agent-foundry" / "config.yaml"
    foundry_config.write_config(config, core, core, vault)
    parsed = foundry_config.parse_config(config)
    assert parsed["repo_root"] == str(core.resolve())
    assert parsed["core_root"] == str(core.resolve())
    assert parsed["vault_root"] == str(vault.resolve())
    assert config.exists()


def assert_runtime_manifest_init_uses_temp_paths(base: Path) -> None:
    template = base / "runtime" / "templates" / "runtime_manifest.template.yaml"
    local = base / "runtime" / "local" / "runtime_manifest.yaml"
    repo_local = Path(__file__).resolve().parents[1] / "runtime" / "local" / "runtime_manifest.yaml"
    before = repo_local.read_bytes() if repo_local.exists() else None
    write(
        template,
        "\n".join(
            [
                "updated: 2026-06-15",
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
    original_local = runtime_manifest.LOCAL_MANIFEST
    original_template = runtime_manifest.TEMPLATE_MANIFEST
    try:
        runtime_manifest.LOCAL_MANIFEST = local
        runtime_manifest.TEMPLATE_MANIFEST = template
        runtime_manifest.ensure_local_manifest()
        lines = runtime_manifest.status_lines()
        assert local.exists()
        assert_contains("\n".join(lines), ("codex: status=disabled", "chatgpt: status=manual"))
    finally:
        runtime_manifest.LOCAL_MANIFEST = original_local
        runtime_manifest.TEMPLATE_MANIFEST = original_template
    after = repo_local.read_bytes() if repo_local.exists() else None
    assert after == before


def assert_fresh_install_dry_run_is_status_only(base: Path) -> None:
    core = make_core(base)
    vault = base / "new-selected-vault"
    generated = base / "restored-generated-output"
    args = SimpleNamespace(
        core_root=str(core),
        vault_root=str(vault),
        adapter_root=str(generated),
        bootstrap_pack=str(base / "bootstrap-pack"),
        apply=False,
        runtime_apply=False,
        force=False,
        no_write_locator=True,
        target="",
        skip_check=True,
    )
    code, output = capture_stdout(install_foundry.fresh_install, args)
    assert code == 0
    assert_contains(
        output,
        (
            "Dry-run only.",
            "Agent Foundry setup/status report",
            "generated_output: missing",
            "status-only: no files were written by this report",
            "select or initialize a Vault before harvesting, refreshing, or applying packs",
            "treat ChatGPT as manual import unless a future managed target is explicitly implemented",
        ),
    )
    assert not vault.exists()
    assert not generated.exists()


def assert_cross_machine_receipt_reports_drift(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)
    receipt = base / "adapter-install-receipt.json"
    old_machine_dest = base / "old-machine-home" / ".codex" / "skills" / "example" / "SKILL.md"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "installed_at": "2026-06-15T00:00:00+00:00",
                "core_root": str(base / "old-core"),
                "vault_root": str(vault),
                "adapter_root": str(generated),
                "installed_targets": ["codex"],
                "installed_files": [
                    {
                        "target": "codex",
                        "source": "codex/skills/example/SKILL.md",
                        "destination": str(old_machine_dest),
                        "sha256": "0" * 64,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report = setup_report(core, vault, generated, receipt)
    assert_contains(
        report,
        (
            "receipt: selected-output-drift",
            "receipt target: codex selected-output-drift checked=1 problems=1",
            "receipt detail: missing codex:",
            "status-only: no files were written by this report",
        ),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-second-machine.") as raw:
        base = Path(raw)
        assert_locator_round_trip(base / "locator")
        assert_runtime_manifest_init_uses_temp_paths(base / "runtime-manifest")
        assert_fresh_install_dry_run_is_status_only(base / "fresh-install")
        assert_cross_machine_receipt_reports_drift(base / "cross-machine")
    print("Second-machine onboarding and restore tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
