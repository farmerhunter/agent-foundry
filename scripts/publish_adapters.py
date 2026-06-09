#!/usr/bin/env python3
"""Publish adapter outputs from a selected Agent Foundry Vault."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from check_foundry_roots import validate
from foundry_config import ROOT


ACTIVE_STATUSES = {"active", "revised"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def simple_yaml_entries(index_text: str, list_key: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_list = False
    for line in index_text.splitlines():
        if line.startswith(f"{list_key}:"):
            rest = line.split(":", 1)[1].strip()
            if rest == "[]":
                return []
            in_list = True
            continue
        if in_list and line and not line.startswith(" "):
            in_list = False
        if not in_list:
            continue
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip().strip('"')}
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def active_entries(vault_root: Path, index_rel: str, list_key: str) -> list[dict[str, str]]:
    entries = simple_yaml_entries(read(vault_root / index_rel), list_key)
    return [entry for entry in entries if entry.get("status") in ACTIVE_STATUSES]


def inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    return [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]


def parse_profiles(core_root: Path) -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = {}
    current: str | None = None
    section: str | None = None
    in_adapters = False
    profile_text = read(core_root / "adapters" / "adapter_profiles.yaml")

    for raw in profile_text.splitlines():
        line = raw.rstrip()
        if line == "adapters:":
            in_adapters = True
            continue
        if not in_adapters:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip().removesuffix(":")
            profiles[current] = {
                "target": current,
                "direct_programming_agent": False,
                "outputs": [],
                "included_domains": [],
                "command_phrases": [],
            }
            section = None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("target:"):
            profiles[current]["target"] = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.startswith("direct_programming_agent:"):
            profiles[current]["direct_programming_agent"] = stripped.endswith("true")
        elif stripped.startswith("included_domains:"):
            profiles[current]["included_domains"] = inline_list(stripped.split(":", 1)[1])
        elif stripped == "outputs:":
            section = "outputs"
        elif stripped == "command_vocabulary:":
            section = "command_vocabulary"
        elif stripped.startswith("transform_policy:") or stripped.startswith("supports:"):
            section = None
        elif section == "outputs" and stripped.startswith("- "):
            profiles[current]["outputs"].append(stripped[2:].strip().strip('"'))
        elif section == "command_vocabulary" and ":" in stripped:
            profiles[current]["command_phrases"].extend(inline_list(stripped.split(":", 1)[1]))
    return profiles


def manifest_text(active_practices: list[dict[str, str]], active_assets: list[dict[str, str]]) -> str:
    lines = [
        "schema_version: 1",
        f"updated: {date.today().isoformat()}",
        "source: selected_vault",
        "private_paths_recorded: false",
        "",
    ]
    if active_practices:
        lines.append("active_practices:")
        for entry in active_practices:
            lines.append(f"  - {entry['id']}")
    else:
        lines.append("active_practices: []")
    lines.append("")
    if active_assets:
        lines.append("active_assets:")
        for entry in active_assets:
            lines.append(f"  - {entry['id']}")
    else:
        lines.append("active_assets: []")
    lines.append("")
    return "\n".join(lines)


def write_manifest(output_root: Path, text: str, apply: bool) -> None:
    path = output_root / "adapter-publish-manifest.yaml"
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        output_root.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def adapter_body(
    adapter_id: str,
    profile: dict[str, object],
    active_practices: list[dict[str, str]],
    active_assets: list[dict[str, str]],
) -> str:
    practice_ids = [entry["id"] for entry in active_practices]
    asset_ids = [entry["id"] for entry in active_assets]
    phrases = [phrase.split("<", 1)[0].strip() for phrase in profile.get("command_phrases", []) if phrase]
    lines = [
        f"# Agent Foundry Adapter: {adapter_id}",
        "",
        f"Target: {profile.get('target', adapter_id)}",
        "Generated from the selected Agent Foundry Vault.",
        "",
        "This AF-3 transitional output intentionally includes only selected active/revised canonical IDs,",
        "adapter command vocabulary, and audit metadata. It does not copy maintainer adapter content,",
        "private paths, raw usage evidence, or future memory-system paths.",
        "",
        "## Active Practices",
    ]
    lines.extend(f"- {pid}" for pid in practice_ids)
    lines.extend(["", "## Active Assets"])
    lines.extend(f"- {aid}" for aid in asset_ids)
    lines.extend(["", "## Command Vocabulary"])
    lines.extend(f"- {phrase}" for phrase in phrases if phrase)
    lines.extend(["", "## Boundary"])
    lines.append("Full semantic regeneration from canonical sections is future generator work.")
    lines.append("")
    return "\n".join(lines)


def output_file(output_root: Path, output: str) -> Path:
    rel = Path(output)
    if rel.parts and rel.parts[0] == "adapters":
        rel = Path(*rel.parts[1:])
    if output.endswith("/") or rel.suffix == "":
        return output_root / rel / "README.md"
    return output_root / rel


def write_adapter_outputs(
    core_root: Path,
    output_root: Path,
    active_practices: list[dict[str, str]],
    active_assets: list[dict[str, str]],
    apply: bool,
) -> list[Path]:
    profiles = parse_profiles(core_root)
    written: list[Path] = []
    for adapter_id, profile in profiles.items():
        if not profile.get("direct_programming_agent"):
            continue
        outputs = list(profile.get("outputs", []))
        if not outputs:
            continue
        text = adapter_body(adapter_id, profile, active_practices, active_assets)
        for output in outputs:
            target = output_file(output_root, str(output))
            written.append(target)
            print(f"{'write' if apply else 'would write'}: {target}")
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
    return written


def publish(core_root: Path, vault_root: Path, output_root: Path, apply: bool) -> int:
    errors = validate(core_root, vault_root)
    if errors:
        print("Adapter publish failed root validation:")
        for error in errors:
            print(f"- {error}")
        return 1

    active_practices = active_entries(vault_root, "indexes/practice_index.yaml", "practices")
    active_assets = active_entries(vault_root, "indexes/asset_index.yaml", "assets")
    if not active_practices and not active_assets:
        print("Selected Vault has no active or revised practices/assets. Nothing to publish.")
        write_manifest(output_root, manifest_text(active_practices, active_assets), apply)
        return 0

    if not (core_root / "adapters" / "adapter_profiles.yaml").exists():
        print(f"Core adapter profile missing: {core_root / 'adapters' / 'adapter_profiles.yaml'}")
        return 1

    if (core_root / "adapters").resolve() == output_root.resolve() and apply:
        print("Refusing to overwrite Core adapter templates in place. Pass --output-root for generated outputs.")
        return 1

    written = write_adapter_outputs(core_root, output_root, active_practices, active_assets, apply)
    write_manifest(output_root, manifest_text(active_practices, active_assets), apply)
    print(f"Adapter publish {'wrote' if apply else 'planned'} {len(written)} files.")
    print(f"Active practices selected: {len(active_practices)}")
    print(f"Active assets selected: {len(active_assets)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish adapters from a selected Agent Foundry Vault.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", default=str(ROOT), help="Selected Agent Foundry Vault root.")
    parser.add_argument("--output-root", default="", help="Adapter output directory. Defaults to <core-root>/adapters.")
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else core_root / "adapters"
    return publish(core_root, vault_root, output_root, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
