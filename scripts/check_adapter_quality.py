#!/usr/bin/env python3
"""Adapter quality checks for Agent Foundry.

This script is intentionally dependency-free. It checks adapter profiles against
generated adapter outputs and verifies that key triggers, canonical IDs, and
asset IDs are visible for audit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "adapters" / "adapter_profiles.yaml"
ACTIVE_STATUSES = {"active", "revised"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    return [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]


def parse_profiles() -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = {}
    current: str | None = None
    section: str | None = None
    current_vocab: str | None = None
    in_adapters = False

    for raw in read(PROFILE).splitlines():
        line = raw.rstrip()
        if line == "adapters:":
            in_adapters = True
            continue
        if not in_adapters:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip().removesuffix(":")
            profiles[current] = {
                "outputs": [],
                "included_domains": [],
                "command_phrases": [],
                "direct_programming_agent": False,
            }
            section = None
            current_vocab = None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("direct_programming_agent:"):
            profiles[current]["direct_programming_agent"] = stripped.endswith("true")
        elif stripped.startswith("included_domains:"):
            profiles[current]["included_domains"] = inline_list(stripped.split(":", 1)[1])
        elif stripped == "outputs:":
            section = "outputs"
        elif stripped == "command_vocabulary:":
            section = "command_vocabulary"
        elif section == "outputs" and stripped.startswith("- "):
            profiles[current]["outputs"].append(stripped[2:].strip().strip('"'))
        elif section == "command_vocabulary" and re.match(r"^[A-Za-z_]+:", stripped):
            current_vocab = stripped.split(":", 1)[0]
            phrases = inline_list(stripped.split(":", 1)[1])
            profiles[current]["command_phrases"].extend(phrases)
        elif section == "command_vocabulary" and current_vocab and stripped.startswith("- "):
            profiles[current]["command_phrases"].append(stripped[2:].strip().strip('"'))
    return profiles


def parse_index_entries(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in read(path).splitlines():
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def adapter_files(outputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for output in outputs:
        path = ROOT / output
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
    return files


def output_text(outputs: list[str]) -> str:
    chunks: list[str] = []
    for path in adapter_files(outputs):
        if path.name == ".agent-foundry-managed":
            continue
        chunks.append(read(path))
    return "\n".join(chunks)


def id_visible(identifier: str, text: str) -> bool:
    if identifier in text:
        return True
    match = re.match(r"^([A-Z]+)-(\d{3})$", identifier)
    if not match:
        return False
    prefix, number = match.group(1), int(match.group(2))
    range_pattern = re.compile(
        rf"{prefix}-(\d{{3}})\s*(?:through|to|[-–])\s*{prefix}-(\d{{3}})",
        re.IGNORECASE,
    )
    for start, end in range_pattern.findall(text):
        if int(start) <= number <= int(end):
            return True
    return False


def active_practices_by_domain() -> dict[str, list[str]]:
    by_domain: dict[str, list[str]] = {}
    for entry in parse_index_entries(ROOT / "indexes" / "practice_index.yaml"):
        if entry.get("status") not in ACTIVE_STATUSES:
            continue
        by_domain.setdefault(entry.get("domain", ""), []).append(entry["id"])
    return by_domain


def active_assets_by_adapter() -> dict[str, list[str]]:
    by_adapter: dict[str, list[str]] = {}
    for entry in parse_index_entries(ROOT / "indexes" / "asset_index.yaml"):
        if entry.get("status") not in ACTIVE_STATUSES:
            continue
        published = inline_list(entry.get("published_to", ""))
        for adapter in published:
            by_adapter.setdefault(adapter, []).append(entry["id"])
    return by_adapter


def main() -> int:
    errors: list[str] = []
    profiles = parse_profiles()
    practices_by_domain = active_practices_by_domain()
    assets_by_adapter = active_assets_by_adapter()

    for name, profile in profiles.items():
        if name == "deepseek":
            continue
        outputs = list(profile["outputs"])
        for output in outputs:
            if not (ROOT / output).exists():
                errors.append(f"{name}: profile output missing: {output}")

        text = output_text(outputs)
        if profile.get("direct_programming_agent") and not text.strip():
            errors.append(f"{name}: direct programming adapter has no output text")

        for phrase in profile.get("command_phrases", []):
            if "<" in phrase:
                phrase = phrase.split("<", 1)[0].strip()
            if phrase and phrase not in text:
                errors.append(f"{name}: command phrase missing from outputs: {phrase}")

        for domain in profile.get("included_domains", []):
            for pid in practices_by_domain.get(domain, []):
                if not id_visible(pid, text):
                    errors.append(f"{name}: included active practice not visible in adapter outputs: {pid}")

        for aid in assets_by_adapter.get(name, []):
            if aid not in text:
                errors.append(f"{name}: published active asset ID not visible in adapter outputs: {aid}")

        if name == "chatgpt" and "knowledge/" not in "\n".join(outputs):
            errors.append("chatgpt: full fidelity adapter should include knowledge files")
        if name == "hermes" and "Do not disable Hermes native memory" not in text:
            errors.append("hermes: native memory/self-growth guardrail missing")

    if errors:
        print("Adapter quality check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Adapter quality check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
