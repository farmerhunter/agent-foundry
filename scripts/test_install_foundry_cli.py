#!/usr/bin/env python3
"""CLI contract tests for bounded Agent Foundry target selection."""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import install_foundry


def repeated_target_checks() -> list[str]:
    errors: list[str] = []
    cases = {
        "same": ["--target", "codex", "--target", "codex"],
        "different": ["--target", "codex", "--target", "claude-code"],
        "equals": ["--target=codex", "--target=trae"],
    }
    for name, argv in cases.items():
        stderr = io.StringIO()
        with (
            patch.object(install_foundry, "configured_roots") as configured_roots,
            patch.object(install_foundry, "fresh_install") as fresh_install,
            patch.object(install_foundry, "install") as install,
            contextlib.redirect_stderr(stderr),
        ):
            try:
                install_foundry.main(argv)
                errors.append(f"repeated-target-{name}: repeated target was accepted")
            except SystemExit as exc:
                if exc.code != 2:
                    errors.append(f"repeated-target-{name}: expected exit 2, got {exc.code}")
            output = stderr.getvalue()
            for expected in [
                "--target may be supplied only once for one target",
                "omit --target to process all enabled targets",
            ]:
                if expected not in output:
                    errors.append(f"repeated-target-{name}: missing error guidance {expected!r}")
            if configured_roots.called or fresh_install.called or install.called:
                errors.append(f"repeated-target-{name}: installer setup or execution ran before rejection")
        if not any(error.startswith(f"repeated-target-{name}:") for error in errors):
            print(f"repeated-target-{name}: ok")
    return errors


def main_selection_checks(base: Path) -> list[str]:
    errors: list[str] = []
    core = base / "core"
    vault = base / "vault"
    adapter = base / "generated"
    for name, argv, expected_target in [
        ("omitted", ["--adapter-root", str(adapter)], ""),
        ("single", ["--adapter-root", str(adapter), "--target", "codex"], "codex"),
        ("single-equals", ["--adapter-root", str(adapter), "--target=claude-code"], "claude-code"),
    ]:
        with (
            patch.object(install_foundry, "configured_roots", return_value=(core, vault)),
            patch.object(install_foundry, "install", return_value=0) as install,
        ):
            code = install_foundry.main(argv)
            if code != 0:
                errors.append(f"target-main-{name}: expected exit 0, got {code}")
                continue
            if install.call_args.kwargs["target"] != expected_target:
                errors.append(
                    f"target-main-{name}: expected target {expected_target!r}, "
                    f"got {install.call_args.kwargs['target']!r}"
                )
            else:
                print(f"target-main-{name}: ok")
    return errors


def manifest_selection_checks(base: Path) -> list[str]:
    errors: list[str] = []
    base.mkdir(parents=True, exist_ok=True)
    manifest = base / "runtime_manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "targets:",
                "  codex:",
                "    status: enabled",
                f"    install_path: {base / 'runtime' / 'codex'}",
                "  claude-code:",
                "    status: enabled",
                f"    install_path: {base / 'runtime' / 'claude'}",
                "  trae:",
                "    status: enabled",
                f"    install_path: {base / 'runtime' / 'trae'}",
                "  hermes:",
                "    status: disabled",
                f"    install_path: {base / 'runtime' / 'hermes'}",
                "  chatgpt:",
                "    status: manual",
                '    install_path: ""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    def exercise(target: str) -> list[str]:
        commands: list[list[str]] = []

        def record(command: list[str], execute: bool) -> int:
            commands.append(command)
            return 0

        with (
            patch.object(install_foundry, "print_operation_context"),
            patch.object(install_foundry, "check_adapter_root_guard", return_value=0),
            patch.object(install_foundry, "read_manifest", return_value=manifest.read_text(encoding="utf-8").splitlines()),
            patch.object(install_foundry, "install_launchers") as install_launchers,
            patch.object(install_foundry, "write_receipt") as write_receipt,
            patch.object(install_foundry, "run", side_effect=record),
        ):
            code = install_foundry.install(
                core_root=base / "core",
                vault_root=base / "vault",
                adapter_root=base / "generated",
                apply=False,
                target=target,
                skip_check=True,
            )
        if code != 0:
            errors.append(f"manifest-selection-{target or 'all'}: expected exit 0, got {code}")
        if install_launchers.call_args.kwargs != {"apply": False}:
            errors.append(f"manifest-selection-{target or 'all'}: launcher dry-run was not isolated")
        if write_receipt.called:
            errors.append(f"manifest-selection-{target or 'all'}: dry-run wrote a receipt")
        return [command[command.index("--target") + 1] for command in commands if "--target" in command]

    all_selected = exercise("")
    if all_selected != ["codex", "claude-code", "trae"]:
        errors.append(f"manifest-selection-all: expected enabled targets only, got {all_selected!r}")
    else:
        print("manifest-selection-all-enabled: ok")
    single_selected = exercise("claude-code")
    if single_selected != ["claude-code"]:
        errors.append(f"manifest-selection-single: expected claude-code only, got {single_selected!r}")
    else:
        print("manifest-selection-single: ok")
    return errors


def main() -> int:
    errors = repeated_target_checks()
    with tempfile.TemporaryDirectory(prefix="agent-foundry-install-cli-") as raw:
        base = Path(raw)
        errors.extend(main_selection_checks(base / "main"))
        errors.extend(manifest_selection_checks(base / "manifest"))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Install Foundry CLI tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
