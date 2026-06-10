#!/usr/bin/env python3
"""Adapter quality checks for Agent Foundry.

This script is intentionally dependency-free. It separates Core high-fidelity
adapter validation from selected-Vault generated output validation.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from foundry_config import CONFIG_PATH, parse_config


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}


def configured_vault_root() -> Path:
    data = parse_config(CONFIG_PATH)
    vault_root = data.get("vault_root", "")
    if isinstance(vault_root, str) and vault_root:
        return Path(vault_root).expanduser().resolve()
    return DEFAULT_ROOT


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    return [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]


def parse_profiles(core_root: Path) -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = {}
    current: str | None = None
    section: str | None = None
    current_vocab: str | None = None
    in_adapters = False

    profile = core_root / "adapters" / "adapter_profiles.yaml"
    for raw in read(profile).splitlines():
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


def core_adapter_files(core_root: Path, outputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for output in outputs:
        path = core_root / output
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
    return files


def output_file(output_root: Path, output: str) -> Path:
    rel = Path(output)
    if rel.parts and rel.parts[0] == "adapters":
        rel = Path(*rel.parts[1:])
    if output.endswith("/") or rel.suffix == "":
        return output_root / rel / "README.md"
    return output_root / rel


def selected_output_files(output_root: Path, outputs: list[str]) -> list[Path]:
    return [path for path in (output_file(output_root, output) for output in outputs) if path.is_file()]


def output_text(files: list[Path]) -> str:
    chunks: list[str] = []
    for path in files:
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


def active_practices_by_domain(vault_root: Path) -> dict[str, list[str]]:
    by_domain: dict[str, list[str]] = {}
    for entry in parse_index_entries(vault_root / "indexes" / "practice_index.yaml"):
        if entry.get("status") not in ACTIVE_STATUSES:
            continue
        by_domain.setdefault(entry.get("domain", ""), []).append(entry["id"])
    return by_domain


def active_ids(vault_root: Path, index_rel: str) -> list[str]:
    ids: list[str] = []
    for entry in parse_index_entries(vault_root / index_rel):
        if entry.get("status") not in ACTIVE_STATUSES:
            continue
        ids.append(entry["id"])
    return ids


def manifest_ids(manifest: Path, key: str) -> list[str]:
    ids: list[str] = []
    in_list = False
    for raw in read(manifest).splitlines():
        line = raw.rstrip()
        if line.startswith(f"{key}:"):
            in_list = True
            if line.split(":", 1)[1].strip() == "[]":
                return []
            continue
        if in_list and line and not line.startswith(" "):
            break
        if in_list and line.strip().startswith("- "):
            ids.append(line.strip()[2:].strip().strip('"').strip("'"))
    return ids


def check_core_surface(core_root: Path, vault_root: Path) -> list[str]:
    errors: list[str] = []
    profiles = parse_profiles(core_root)
    split_mode = core_root.resolve() != vault_root.resolve()
    practices_by_domain = {} if split_mode else active_practices_by_domain(vault_root)

    for name, profile in profiles.items():
        if name == "deepseek":
            continue
        outputs = list(profile["outputs"])
        for output in outputs:
            if not (core_root / output).exists():
                errors.append(f"Core template quality: {name} profile output missing: {output}")

        text = output_text(core_adapter_files(core_root, outputs))
        if profile.get("direct_programming_agent") and not text.strip():
            errors.append(f"Core template quality: {name} direct programming adapter has no output text")

        for phrase in profile.get("command_phrases", []):
            if "<" in phrase:
                phrase = phrase.split("<", 1)[0].strip()
            if phrase and phrase not in text:
                errors.append(f"Core template quality: {name} command phrase missing from outputs: {phrase}")

        for domain in profile.get("included_domains", []):
            for pid in practices_by_domain.get(domain, []):
                if not id_visible(pid, text):
                    errors.append(f"Core template quality: {name} included active practice not visible: {pid}")

        if name == "chatgpt" and "knowledge/" not in "\n".join(outputs):
            errors.append("Core template quality: chatgpt full fidelity adapter should include knowledge files")
        if name == "hermes" and "Do not disable Hermes native memory" not in text:
            errors.append("Core template quality: hermes native memory/self-growth guardrail missing")
    return errors


def check_selected_output_surface(core_root: Path, vault_root: Path, generated_root: Path | None) -> list[str]:
    errors: list[str] = []
    if generated_root is None:
        return [
            "Missing publish step: selected generated output validation requires --generated-root from "
            "publish_adapters.py --output-root <dir> --apply"
        ]
    if generated_root.resolve() == (core_root / "adapters").resolve():
        return [
            "Unsafe Core overwrite attempt: selected generated output root is Core adapters/. "
            "Publish to a separate --output-root instead."
        ]

    manifest = generated_root / "adapter-publish-manifest.yaml"
    if not manifest.exists():
        return [
            f"Missing publish step: selected generated output manifest not found: {manifest}. "
            "Run publish_adapters.py --output-root <dir> --apply before selected-output validation."
        ]

    expected_practices = active_ids(vault_root, "indexes/practice_index.yaml")
    expected_assets = active_ids(vault_root, "indexes/asset_index.yaml")
    manifest_practices = manifest_ids(manifest, "active_practices")
    manifest_assets = manifest_ids(manifest, "active_assets")
    for pid in expected_practices:
        if pid not in manifest_practices:
            errors.append(f"Selected output coverage: active practice missing from publish manifest: {pid}")
    for aid in expected_assets:
        if aid not in manifest_assets:
            errors.append(f"Selected output coverage: active asset missing from publish manifest: {aid}")
    for pid in manifest_practices:
        if pid not in expected_practices:
            errors.append(f"Selected output coverage: manifest contains non-active or unknown practice: {pid}")
    for aid in manifest_assets:
        if aid not in expected_assets:
            errors.append(f"Selected output coverage: manifest contains non-active or unknown asset: {aid}")

    profiles = parse_profiles(core_root)
    expected_ids = expected_practices + expected_assets
    for name, profile in profiles.items():
        if name == "deepseek" or not profile.get("direct_programming_agent"):
            continue
        outputs = list(profile["outputs"])
        files = selected_output_files(generated_root, outputs)
        if not files:
            errors.append(f"Selected output coverage: {name} generated output missing under {generated_root}")
            continue
        text = output_text(files)
        for identifier in expected_ids:
            if identifier not in text:
                errors.append(f"Selected output coverage: {name} generated output missing active ID: {identifier}")
        for phrase in profile.get("command_phrases", []):
            if "<" in phrase:
                phrase = phrase.split("<", 1)[0].strip()
            if phrase and phrase not in text:
                errors.append(f"Selected output coverage: {name} generated output missing command phrase: {phrase}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Agent Foundry adapter quality surfaces.")
    parser.add_argument("--core-root", default=str(DEFAULT_ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", default="", help="Selected Vault root. Defaults to configured vault_root.")
    parser.add_argument(
        "--surface",
        choices=["core", "selected-output"],
        default="core",
        help="Validation surface: Core high-fidelity templates or selected generated output.",
    )
    parser.add_argument("--generated-root", default="", help="Generated adapter output root for selected-output surface.")
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve() if args.vault_root else configured_vault_root()
    generated_root = Path(args.generated_root).expanduser().resolve() if args.generated_root else None

    if args.surface == "core":
        errors = check_core_surface(core_root, vault_root)
    else:
        errors = check_selected_output_surface(core_root, vault_root, generated_root)

    if errors:
        print(f"Adapter quality check failed for {args.surface} surface:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Adapter quality check passed for {args.surface} surface.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
