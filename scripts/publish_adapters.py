#!/usr/bin/env python3
"""Publish adapter outputs from a selected Agent Foundry Vault."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from check_foundry_roots import validate
from foundry_config import ROOT
from operation_context import configured_roots, print_operation_context


ACTIVE_STATUSES = {"active", "revised"}
SKILL_FOLDER_ADAPTERS = {"codex", "hermes", "trae"}
TRAE_COMPATIBLE_SKILL_ADAPTERS = {"codex", "hermes"}


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


def yaml_scalar(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def yaml_list(text: str, key: str) -> list[str]:
    lines = text.splitlines()
    values: list[str] = []
    in_list = False
    for line in lines:
        if line.startswith(f"{key}:"):
            rest = line.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                return inline_list(rest)
            in_list = True
            continue
        if in_list and line and not line.startswith(" "):
            break
        if in_list and line.strip().startswith("- "):
            values.append(line.strip()[2:].strip().strip('"').strip("'"))
    return values


def slug_from_asset(entry: dict[str, str]) -> str:
    path = Path(entry.get("path", ""))
    stem = path.name.removesuffix(".asset.yaml").removesuffix(".yaml")
    asset_id = entry.get("id", "")
    prefix = f"{asset_id}-"
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or re.sub(r"[^a-z0-9]+", "-", entry.get("title", asset_id).lower()).strip("-")


def skill_asset_records(vault_root: Path, active_assets: list[dict[str, str]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for entry in active_assets:
        rel = entry.get("path", "")
        if not rel:
            continue
        path = vault_root / rel
        if not path.exists():
            continue
        text = read(path)
        if yaml_scalar(text, "asset_type") != "skill":
            continue
        record = dict(entry)
        record.update(
            {
                "slug": slug_from_asset(entry),
                "source_path": rel,
                "asset_type": "skill",
                "title": yaml_scalar(text, "title") or entry.get("title", entry["id"]),
                "purpose": yaml_scalar(text, "purpose"),
                "responsibility": yaml_scalar(text, "responsibility"),
                "non_responsibility": yaml_scalar(text, "non_responsibility"),
                "usage_triggers": yaml_list(text, "usage_triggers"),
                "inputs": yaml_list(text, "inputs"),
                "process": yaml_list(text, "process"),
                "outputs": yaml_list(text, "outputs"),
                "success_criteria": yaml_list(text, "success_criteria"),
                "canonical_practices": yaml_list(text, "canonical_practices"),
                "published_to": yaml_list(text, "published_to") or inline_list(entry.get("published_to", "")),
            }
        )
        records.append(record)
    return records


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


def bullet_lines(values: object) -> list[str]:
    items = [str(value) for value in values] if isinstance(values, list) else []
    return [f"- {item}" for item in items] or ["- Not specified in canonical asset record."]


def generated_skill_body(record: dict[str, object]) -> str:
    slug = str(record["slug"])
    title = str(record.get("title") or record["id"])
    purpose = str(record.get("purpose") or "Generated Agent Foundry runtime skill.")
    triggers = record.get("usage_triggers", [])
    trigger_summary = ", ".join(str(item) for item in triggers[:4]) if isinstance(triggers, list) else ""
    description = purpose
    if trigger_summary:
        description = f"{purpose} Triggers: {trigger_summary}."
    if len(description) > 260:
        description = description[:257].rstrip() + "..."
    quoted_description = '"' + description.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = [
        "---",
        f"name: {slug}",
        f"description: {quoted_description}",
        "---",
        "",
        f"# {title}",
        "",
        "Generated transitional runtime skill from the selected Agent Foundry Vault.",
        f"Canonical source: `{record.get('source_path', '')}`.",
        f"Asset ID: `{record['id']}`.",
        "",
        "## Purpose",
        purpose,
        "",
        "## Trigger Guidance",
        *bullet_lines(triggers),
        "",
        "## Responsibility",
        str(record.get("responsibility") or "Not specified in canonical asset record."),
        "",
        "## Non-Responsibility",
        str(record.get("non_responsibility") or "Not specified in canonical asset record."),
        "",
        "## Required Or Optional Inputs",
        *bullet_lines(record.get("inputs", [])),
        "",
        "## Process",
        *bullet_lines(record.get("process", [])),
        "",
        "## Outputs",
        *bullet_lines(record.get("outputs", [])),
        "",
        "## Success Criteria",
        *bullet_lines(record.get("success_criteria", [])),
        "",
        "## Canonical Practices",
        *bullet_lines(record.get("canonical_practices", [])),
        "",
        "## Safety Boundaries",
        "- Treat the Vault YAML asset record as the source of truth.",
        "- Do not perform high-risk actions without explicit approval.",
        "- Do not mutate runtime, config, private remote, or canonical practice state unless the user explicitly approves that action.",
        "",
    ]
    return "\n".join(lines)


def write_generated_skill_outputs(
    output_root: Path,
    skill_assets: list[dict[str, object]],
    apply: bool,
) -> list[Path]:
    written: list[Path] = []
    for record in skill_assets:
        published_to = record.get("published_to", [])
        if not isinstance(published_to, list):
            continue
        for adapter_id in sorted(SKILL_FOLDER_ADAPTERS):
            if adapter_id not in published_to and not (
                adapter_id == "trae" and TRAE_COMPATIBLE_SKILL_ADAPTERS.intersection(published_to)
            ):
                continue
            target = output_root / adapter_id / "skills" / str(record["slug"]) / "SKILL.md"
            written.append(target)
            print(f"{'write' if apply else 'would write'}: {target}")
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(generated_skill_body(record), encoding="utf-8")
    return written


def publish(core_root: Path, vault_root: Path, output_root: Path, apply: bool) -> int:
    print_operation_context("publish", core_root=core_root, vault_root=vault_root, adapter_root=output_root)
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
    written.extend(write_generated_skill_outputs(output_root, skill_asset_records(vault_root, active_assets), apply))
    write_manifest(output_root, manifest_text(active_practices, active_assets), apply)
    print(f"Adapter publish {'wrote' if apply else 'planned'} {len(written)} files.")
    print(f"Active practices selected: {len(active_practices)}")
    print(f"Active assets selected: {len(active_assets)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish adapters from a selected Agent Foundry Vault.")
    parser.add_argument("--core-root", default="", help="Agent Foundry Core root. Defaults to configured core_root.")
    parser.add_argument("--vault-root", default="", help="Selected Agent Foundry Vault root. Defaults to configured vault_root.")
    parser.add_argument("--output-root", default="", help="Adapter output directory. Defaults to <core-root>/adapters.")
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    args = parser.parse_args()

    core_root, vault_root = configured_roots(args.core_root, args.vault_root)
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else core_root / "adapters"
    return publish(core_root, vault_root, output_root, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
