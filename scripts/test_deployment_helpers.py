#!/usr/bin/env python3
"""Run focused fixtures for AF-4 deployment helper scripts."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from deployment_checks import runtime_lines, stale_reference_lines


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def alternate_core_runtime_fixture() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-alt-core-") as tmp:
        alt_core = Path(tmp)
        distinctive = alt_core / "runtime" / "local" / "runtime_manifest.yaml"
        current_manifest = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
        write(
            distinctive,
            "\n".join(
                [
                    "schema_version: 1",
                    "updated: 2026-06-10",
                    "",
                    "targets:",
                    "  codex:",
                    "    status: enabled",
                    f"    install_path: {alt_core}/af65-distinctive-codex-runtime",
                    "    ownership_mode: managed-directories",
                    "  chatgpt:",
                    "    status: manual",
                    "    install_path: ''",
                    "    ownership_mode: manual-import",
                    "",
                ]
            ),
        )
        runtime_report, runtime_stops = runtime_lines(alt_core)
        stale_report, _ = stale_reference_lines(alt_core, Path("/tmp/af65-vault"))
        runtime_text = "\n".join(runtime_report)
        stale_text = "\n".join(stale_report)
        if str(distinctive) not in runtime_text:
            errors.append("alternate-core-runtime: runtime report did not use alternate core manifest")
        if str(current_manifest) in runtime_text:
            errors.append("alternate-core-runtime: runtime report leaked current checkout manifest")
        if "af65-distinctive-codex-runtime" not in runtime_text:
            errors.append("alternate-core-runtime: distinctive runtime path missing from report")
        if str(distinctive) not in stale_text:
            errors.append("alternate-core-runtime: stale scan did not use alternate core manifest")
        if str(current_manifest) in stale_text:
            errors.append("alternate-core-runtime: stale scan leaked current checkout manifest")
        if not any("runtime target codex enabled but install path is missing" in stop for stop in runtime_stops):
            errors.append("alternate-core-runtime: missing distinctive runtime path did not fail closed")
    return errors


def main() -> int:
    errors = alternate_core_runtime_fixture()
    if errors:
        print("Deployment helper fixture tests failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Deployment helper fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
