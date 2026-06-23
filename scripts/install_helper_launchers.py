#!/usr/bin/env python3
"""Install stable Agent Foundry helper launchers.

Launchers are intentionally tiny runtime entry points. They locate the selected
Core through the machine-local Agent Foundry locator, then execute the canonical
helper script from that Core checkout. They do not copy helper implementations
into runtime state.
"""

from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path


DEFAULT_BIN_DIR = Path.home() / ".agent-foundry" / "bin"
GITHUB_COLLAB_LAUNCHER = "agent-foundry-github-collab"


def launcher_text() -> str:
    return '''#!/usr/bin/env python3
"""Runtime launcher for the Agent Foundry GitHub collaboration helper."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def parse_config(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        raise SystemExit(f"foundry_config_missing: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key.strip() in {"core_root", "repo_root", "vault_root"}:
            data[key.strip()] = value.strip().strip('"')
    return data


def main() -> int:
    config_path = Path(os.environ.get("AGENT_FOUNDRY_CONFIG", Path.home() / ".agent-foundry" / "config.yaml"))
    config = parse_config(config_path.expanduser())
    core_root_text = config.get("core_root") or config.get("repo_root")
    if not core_root_text:
        raise SystemExit(f"foundry_core_root_missing: {config_path}")
    core_root = Path(core_root_text).expanduser()
    helper = core_root / "scripts" / "github_collaboration_helper.py"
    if not helper.exists():
        raise SystemExit(f"foundry_helper_missing: {helper}")
    return subprocess.run([sys.executable, str(helper), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
'''


def install_launchers(*, bin_dir: Path = DEFAULT_BIN_DIR, apply: bool = False) -> list[Path]:
    launcher = bin_dir.expanduser() / GITHUB_COLLAB_LAUNCHER
    if not apply:
        print(f"would write launcher: {launcher}")
        return [launcher]
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(launcher_text(), encoding="utf-8")
    mode = launcher.stat().st_mode
    launcher.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote launcher: {launcher}")
    return [launcher]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent Foundry helper launchers.")
    parser.add_argument("--apply", action="store_true", help="Write launchers. Default is dry-run.")
    parser.add_argument("--bin-dir", default=str(DEFAULT_BIN_DIR), help="Launcher directory.")
    args = parser.parse_args()
    install_launchers(bin_dir=Path(args.bin_dir), apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
