#!/usr/bin/env python3
"""Regression tests for read-only install/status reporting."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sync_status import ROOT, default_adapter_root, deployed_packs, setup_report


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-sync-status.") as raw:
        base = Path(raw)
        vault = base / "vault"
        generated = base / "generated-adapters"
        receipt = base / "adapter-install-receipt.json"
        (vault / "practices").mkdir(parents=True)
        (generated / "codex" / "skills").mkdir(parents=True)
        write(generated / "adapter-publish-manifest.yaml", "active_assets: []\n")
        write(
            receipt,
            "{\n"
            '  "schema_version": 1,\n'
            f'  "adapter_root": "{generated}",\n'
            '  "installed_files": []\n'
            "}\n",
        )
        write(
            vault / "packs" / "deployed-pack-index.yaml",
            "\n".join(
                [
                    "schema_version: 1",
                    "updated: 2026-06-12",
                    "deployed_packs:",
                    "  - pack_id: pack.bootstrap.minimal",
                    '    title: "Bootstrap Pack"',
                    '    version: "0.1.0"',
                    "    lifecycle_status: deployed",
                    "    distribution_type: mandatory_bootstrap",
                    "    source:",
                    "      kind: local_path",
                    f'      locator: "{base / "pack"}"',
                    "      manifest_sha256: abc123",
                    "      reviewed_by: architect",
                    "    records: []",
                    "    executable_payloads: []",
                    "    decisions:",
                    "      conflict_policy: fail_closed",
                    "      notes: []",
                    "",
                ]
            ),
        )

        packs = deployed_packs(vault)
        assert packs == [
            "pack.bootstrap.minimal (version=0.1.0, status=deployed, type=mandatory_bootstrap, source=local_path)"
        ], packs
        assert default_adapter_root(ROOT, vault, receipt) == generated.resolve()

        missing_receipt = base / "missing-receipt.json"
        report = setup_report(ROOT, vault, generated, missing_receipt)
        expected = [
            "Agent Foundry setup/status report",
            "deployed_pack: pack.bootstrap.minimal",
            "deployed_packs:",
            "- pack.bootstrap.minimal (version=0.1.0, status=deployed, type=mandatory_bootstrap, source=local_path)",
            f"generated_output: ready path={generated} files=1",
            "receipt: missing",
            "- chatgpt: manual import required",
            "next_safe_actions:",
            "- status-only: no files were written by this report",
            "- run runtime install only after generated output dry-run/review; receipt is currently missing",
            "- treat ChatGPT as manual import unless a future managed target is explicitly implemented",
        ]
        for text in expected:
            assert text in report, text

    print("Sync status report tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
