#!/usr/bin/env python3
"""Regression tests for Agent Foundry runtime helper launchers."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from install_helper_launchers import install_launchers


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def expect(name: str, condition: bool, detail: str) -> list[str]:
    if condition:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-helper-launcher-") as raw:
        base = Path(raw)
        home = base / "home"
        core = base / "core"
        non_core = base / "product"
        helper = core / "scripts" / "github_collaboration_helper.py"
        launcher_dir = home / ".agent-foundry" / "bin"
        config = home / ".agent-foundry" / "config.yaml"
        write(
            helper,
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import sys",
                    "print('helper-cwd=' + __import__('os').getcwd())",
                    "print('helper-args=' + ' '.join(sys.argv[1:]))",
                ]
            )
            + "\n",
        )
        write(
            config,
            "\n".join(
                [
                    "schema_version: 1",
                    f"repo_root: \"{core}\"",
                    f"core_root: \"{core}\"",
                    f"vault_root: \"{base / 'vault'}\"",
                ]
            )
            + "\n",
        )
        non_core.mkdir()

        install_launchers(bin_dir=launcher_dir, apply=True)
        launcher = launcher_dir / "agent-foundry-github-collab"
        env = os.environ.copy()
        env["HOME"] = str(home)
        result = run([str(launcher), "--json", "activation-report"], cwd=non_core, env=env)
        output = result.stdout + result.stderr
        errors.extend(expect("launcher-executable", os.access(launcher, os.X_OK), str(launcher)))
        errors.extend(expect("launcher-non-core-cwd", result.returncode == 0, output))
        errors.extend(expect("launcher-forwards-args", "helper-args=--json activation-report" in output, output))
        expected_cwd = str(non_core.resolve())
        errors.extend(expect("launcher-preserves-cwd", f"helper-cwd={expected_cwd}" in output, output))

        missing_env = env.copy()
        missing_env["AGENT_FOUNDRY_CONFIG"] = str(base / "missing.yaml")
        missing = run([str(launcher), "repo-resolve"], cwd=non_core, env=missing_env)
        missing_output = missing.stdout + missing.stderr
        errors.extend(expect("launcher-missing-config-fails", missing.returncode != 0, missing_output))
        errors.extend(expect("launcher-missing-config-message", "foundry_config_missing" in missing_output, missing_output))

    if errors:
        print("Helper launcher tests failed:")
        for error in errors:
            print(error)
        return 1
    print("Helper launcher tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
