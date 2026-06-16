#!/usr/bin/env python3
"""Regression tests for runtime manifest template upgrades."""

from __future__ import annotations

import tempfile
from pathlib import Path

import runtime_manifest


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-runtime-manifest.") as raw:
        base = Path(raw)
        local = base / "runtime" / "local" / "runtime_manifest.yaml"
        template = base / "runtime" / "templates" / "runtime_manifest.template.yaml"
        write(
            local,
            "\n".join(
                [
                    "schema_version: 1",
                    "updated: 2026-06-01",
                    "",
                    "targets:",
                    "  codex:",
                    "    status: disabled",
                    "    install_path: ~/.codex/skills",
                    "    ownership_mode: managed-directories",
                    "",
                ]
            ),
        )
        write(
            template,
            "\n".join(
                [
                    "schema_version: 1",
                    "updated: 2026-06-15",
                    "",
                    "targets:",
                    "  codex:",
                    "    status: disabled",
                    "    install_path: ~/.codex/skills",
                    "    ownership_mode: managed-directories",
                    "  trae:",
                    "    status: disabled",
                    "    install_path: ~/.trae-cn/skills",
                    "    ownership_mode: managed-directories",
                    "",
                ]
            ),
        )

        original_local = runtime_manifest.LOCAL_MANIFEST
        original_template = runtime_manifest.TEMPLATE_MANIFEST
        try:
            runtime_manifest.LOCAL_MANIFEST = local
            runtime_manifest.TEMPLATE_MANIFEST = template
            before = local.read_text(encoding="utf-8")

            targets = runtime_manifest.parse_targets(runtime_manifest.read_manifest())
            assert "trae" in targets, targets
            assert local.read_text(encoding="utf-8") == before

            runtime_manifest.set_target_status("trae", "enabled")
            written = local.read_text(encoding="utf-8")
            assert "  trae:" in written, written
            assert "    status: enabled" in written, written
        finally:
            runtime_manifest.LOCAL_MANIFEST = original_local
            runtime_manifest.TEMPLATE_MANIFEST = original_template

    print("Runtime manifest tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
