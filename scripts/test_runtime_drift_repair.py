#!/usr/bin/env python3
"""Runtime drift and selected-output receipt repair policy tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import sync_status
from adapter_install_receipt import write_receipt


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_core(root: Path) -> Path:
    core = root / "core"
    write(
        core / "runtime" / "local" / "runtime_manifest.yaml",
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
    return vault


def make_generated(root: Path) -> Path:
    generated = root / "generated"
    write(generated / "adapter-publish-manifest.yaml", "active_assets:\n  - ASSET-COLLAB-002\n")
    write(generated / "codex" / "skills" / "example" / "SKILL.md", "codex skill\n")
    write(generated / "chatgpt" / "custom-instructions.md", "manual import\n")
    return generated


def assert_contains(text: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet in text, f"missing {snippet!r} in:\n{text}"


def with_fake_root(core: Path, func) -> None:
    original = sync_status.ROOT
    try:
        sync_status.ROOT = core
        func()
    finally:
        sync_status.ROOT = original


def assert_missing_receipt_guidance(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)

    def check() -> None:
        report = sync_status.setup_report(core, vault, generated, base / "missing-receipt.json")
        assert_contains(
            report,
            (
                "receipt: missing",
                "run runtime install only after generated output dry-run/review; receipt is currently missing",
                "- codex: skipped status=disabled",
                "- chatgpt: manual import required",
            ),
        )

    with_fake_root(core, check)


def assert_generated_output_drift_guidance(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)
    runtime = base / "runtime" / "codex"
    receipt = base / "receipt.json"
    write(runtime / "example" / "SKILL.md", "codex skill\n")
    write_receipt(
        core_root=core,
        vault_root=vault,
        adapter_root=generated,
        installed_targets={"codex": runtime},
        receipt_path=receipt,
    )
    write(generated / "adapter-publish-manifest.yaml", "active_assets:\n  - ASSET-CHANGED-001\n")

    def check() -> None:
        report = sync_status.setup_report(core, vault, generated, receipt)
        assert_contains(
            report,
            (
                "receipt: selected-output-drift",
                "receipt detail: changed adapter_manifest",
                "review selected-output drift, regenerate generated output if needed, then dry-run runtime install before apply",
            ),
        )

    with_fake_root(core, check)


def assert_stale_runtime_file_guidance(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)
    runtime = base / "runtime" / "codex"
    receipt = base / "receipt.json"
    write(runtime / "example" / "SKILL.md", "codex skill\n")
    write_receipt(
        core_root=core,
        vault_root=vault,
        adapter_root=generated,
        installed_targets={"codex": runtime},
        receipt_path=receipt,
    )
    write(runtime / "example" / "SKILL.md", "stale runtime copy\n")

    def check() -> None:
        report = sync_status.setup_report(core, vault, generated, receipt)
        assert_contains(
            report,
            (
                "receipt: selected-output-drift",
                "receipt target: codex selected-output-drift checked=1 problems=1",
                "receipt detail: changed codex:",
                "review selected-output drift, regenerate generated output if needed, then dry-run runtime install before apply",
            ),
        )

    with_fake_root(core, check)


def assert_unknown_receipt_guidance(base: Path) -> None:
    core = make_core(base)
    vault = make_vault(base)
    generated = make_generated(base)
    receipt = base / "receipt.json"
    write(
        receipt,
        "{\n"
        '  "schema_version": 1,\n'
        f'  "adapter_root": "{generated}",\n'
        '  "installed_files": []\n'
        "}\n",
    )

    def check() -> None:
        report = sync_status.setup_report(core, vault, generated, receipt)
        assert_contains(
            report,
            (
                "receipt: selected-output-unknown",
                "receipt detail: receipt has no installed files",
                "repair or recreate runtime install receipt only through reviewed install apply after generated output is ready",
            ),
        )

    with_fake_root(core, check)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-runtime-drift.") as raw:
        base = Path(raw)
        assert_missing_receipt_guidance(base / "missing-receipt")
        assert_generated_output_drift_guidance(base / "generated-output-drift")
        assert_stale_runtime_file_guidance(base / "runtime-file-drift")
        assert_unknown_receipt_guidance(base / "unknown-receipt")
    print("Runtime drift and receipt repair policy tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
