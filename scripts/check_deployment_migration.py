#!/usr/bin/env python3
"""Run read-only Agent Foundry deployment migration verification checks."""

from __future__ import annotations

import argparse

from deployment_checks import (
    git_lines,
    locator_lines,
    publish_dry_run_lines,
    report_header,
    resolve_roots,
    root_validation_lines,
    runtime_lines,
    stale_reference_lines,
    stop_lines,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an Agent Foundry deployment without applying changes.")
    parser.add_argument("--core-root", default="", help="Agent Foundry Core root. Defaults to this checkout.")
    parser.add_argument("--vault-root", default="", help="Selected User Vault root. Defaults to locator vault_root.")
    args = parser.parse_args()

    core_root, vault_root = resolve_roots(args.core_root, args.vault_root)
    stops: list[str] = []
    lines = report_header("Agent Foundry Deployment Migration Check")
    for section, section_stops in [
        git_lines("Core", core_root),
        git_lines("Vault", vault_root),
        locator_lines(core_root, vault_root),
        root_validation_lines(core_root, vault_root),
        publish_dry_run_lines(core_root, vault_root),
        runtime_lines(core_root),
        stale_reference_lines(core_root, vault_root),
    ]:
        lines.extend(section)
        lines.append("")
        stops.extend(section_stops)
    lines.extend(stop_lines(stops))
    print("\n".join(lines))
    return 1 if stops else 0


if __name__ == "__main__":
    raise SystemExit(main())

