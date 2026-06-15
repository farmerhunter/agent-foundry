#!/usr/bin/env python3
"""Smoke tests for selected-output adapter install receipts."""

from __future__ import annotations

import tempfile
from pathlib import Path

from adapter_install_receipt import read_receipt, receipt_status, receipt_target_statuses, write_receipt


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-receipt-test.") as raw:
        root = Path(raw)
        core = root / "core"
        vault = root / "vault"
        adapter = root / "generated"
        codex_dest = root / "runtime" / "codex"
        hermes_dest = root / "runtime" / "hermes"
        receipt = root / "receipt.yaml"
        for repo in (core, vault):
            (repo / ".git").mkdir(parents=True)

        write(adapter / "adapter-publish-manifest.yaml", "active_assets:\n  - ASSET-COLLAB-002\n")
        write(adapter / "codex" / "skills" / "role-automation-planner" / "SKILL.md", "codex skill\n")
        write(adapter / "hermes" / "skills" / "role-automation-planner" / "SKILL.md", "hermes skill\n")
        write(codex_dest / "role-automation-planner" / "SKILL.md", "codex skill\n")
        write(hermes_dest / "role-automation-planner" / "SKILL.md", "hermes skill\n")

        write_receipt(
            core_root=core,
            vault_root=vault,
            adapter_root=adapter,
            installed_targets={"codex": codex_dest, "hermes": hermes_dest},
            receipt_path=receipt,
        )

        loaded = read_receipt(receipt)
        assert loaded is not None
        state, problems = receipt_status(loaded)
        assert state == "selected-output-in-sync", (state, problems)
        targets = receipt_target_statuses(loaded)
        assert targets["codex"][0] == "selected-output-in-sync"
        assert targets["hermes"][0] == "selected-output-in-sync"

        write(adapter / "adapter-publish-manifest.yaml", "active_assets:\n  - ASSET-CHANGED-001\n")
        state, problems = receipt_status(loaded)
        assert state == "selected-output-drift"
        assert any("changed adapter_manifest" in problem for problem in problems)
        write(adapter / "adapter-publish-manifest.yaml", "active_assets:\n  - ASSET-COLLAB-002\n")

        write(codex_dest / "role-automation-planner" / "SKILL.md", "changed\n")
        state, problems = receipt_status(loaded)
        assert state == "selected-output-drift"
        assert any("changed" in problem for problem in problems)
        targets = receipt_target_statuses(loaded)
        assert targets["codex"][0] == "selected-output-drift"
        assert targets["hermes"][0] == "selected-output-in-sync"

    print("Adapter install receipt tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
