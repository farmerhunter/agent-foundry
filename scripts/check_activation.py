#!/usr/bin/env python3
"""Check practice activation metadata and adapter preflight coverage."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from foundry_config import CONFIG_PATH, parse_config


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}
ALLOWED_TIERS = {
    "always_preflight",
    "task_router",
    "workflow_embedded",
    "review_only",
    "reference_only",
}


def configured_vault_root() -> Path:
    data = parse_config(CONFIG_PATH)
    vault_root = data.get("vault_root", "")
    if isinstance(vault_root, str) and vault_root:
        return Path(vault_root).expanduser().resolve()
    return ROOT


VAULT_ROOT = configured_vault_root()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> dict[str, str]:
    text = read(path)
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def parse_profiles() -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = {}
    current: str | None = None
    section: str | None = None
    in_adapters = False

    for raw in read(ROOT / "adapters" / "adapter_profiles.yaml").splitlines():
        line = raw.rstrip()
        if line == "adapters:":
            in_adapters = True
            continue
        if not in_adapters:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip().removesuffix(":")
            profiles[current] = {"outputs": [], "direct_programming_agent": False}
            section = None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("direct_programming_agent:"):
            profiles[current]["direct_programming_agent"] = stripped.endswith("true")
        elif stripped == "outputs:":
            section = "outputs"
        elif re.match(r"^[A-Za-z_]+:", stripped):
            section = None
        elif section == "outputs" and stripped.startswith("- "):
            profiles[current]["outputs"].append(stripped[2:].strip().strip('"'))
    return profiles


def adapter_files(outputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for output in outputs:
        path = ROOT / output
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
    return files


def adapter_text(outputs: list[str]) -> str:
    chunks: list[str] = []
    for path in adapter_files(outputs):
        if path.name == ".agent-foundry-managed":
            continue
        chunks.append(read(path))
    return "\n".join(chunks)


def activation_section(text: str) -> str:
    match = re.search(r"^## Activation\n+(.*?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def compact_preflight_section(text: str) -> str:
    match = re.search(r"^## Compact Preflight\n+(.*?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def activation_field(section: str, name: str) -> str:
    pattern = re.compile(rf"^- {re.escape(name)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(section)
    return match.group(1).strip() if match else ""


def practice_entries() -> list[tuple[Path, dict[str, str], str]]:
    entries: list[tuple[Path, dict[str, str], str]] = []
    for path in sorted((VAULT_ROOT / "practices").glob("*/*.md")):
        text = read(path)
        entries.append((path, frontmatter(path), text))
    return entries


def main() -> int:
    errors: list[str] = []
    always_preflight: list[str] = []
    inactive_with_preflight: list[str] = []

    for path, fm, text in practice_entries():
        pid = fm.get("id", path.name)
        status = fm.get("status", "")
        section = activation_section(text)
        if not section:
            continue

        tier = activation_field(section, "Tier")
        if not tier:
            errors.append(f"{pid}: Activation missing Tier")
            continue
        if tier not in ALLOWED_TIERS:
            errors.append(f"{pid}: invalid Activation Tier: {tier}")
        for required in ["Phases", "Signals", "Evidence"]:
            if not activation_field(section, required):
                errors.append(f"{pid}: Activation missing {required}")

        if tier == "always_preflight":
            if status in ACTIVE_STATUSES:
                always_preflight.append(pid)
            else:
                inactive_with_preflight.append(pid)

    for pid in inactive_with_preflight:
        errors.append(f"{pid}: inactive practice must not be always_preflight")

    profiles = parse_profiles()
    for name, profile in profiles.items():
        if not profile.get("direct_programming_agent"):
            continue
        text = adapter_text(list(profile["outputs"]))
        preflight = compact_preflight_section(text)
        if not preflight:
            errors.append(f"{name}: missing compact preflight kernel")
        for pid in always_preflight:
            if pid not in preflight:
                errors.append(f"{name}: always_preflight practice missing from compact preflight: {pid}")

    if errors:
        print("Activation check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Activation check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
