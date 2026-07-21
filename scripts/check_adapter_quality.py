#!/usr/bin/env python3
"""Adapter quality checks for Agent Foundry.

This script is intentionally dependency-free. It separates Core high-fidelity
adapter validation from selected-Vault generated output validation.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from foundry_config import CONFIG_PATH, parse_config


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}
SKILL_FOLDER_ADAPTERS = {"codex", "hermes", "trae"}
TRAE_COMPATIBLE_SKILL_ADAPTERS = {"codex", "hermes"}


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


def yaml_scalar(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def yaml_list(text: str, key: str) -> list[str]:
    values: list[str] = []
    in_list = False
    for line in text.splitlines():
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
    stem = Path(entry.get("path", "")).name.removesuffix(".asset.yaml").removesuffix(".yaml")
    prefix = f"{entry.get('id', '')}-"
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or re.sub(r"[^a-z0-9]+", "-", entry.get("title", entry.get("id", "")).lower()).strip("-")


def active_asset_entries(vault_root: Path) -> list[dict[str, str]]:
    return [
        entry
        for entry in parse_index_entries(vault_root / "indexes" / "asset_index.yaml")
        if entry.get("status") in ACTIVE_STATUSES
    ]


def active_skill_assets(vault_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for entry in active_asset_entries(vault_root):
        path = vault_root / entry.get("path", "")
        if not path.exists():
            continue
        text = read(path)
        if yaml_scalar(text, "asset_type") != "skill":
            continue
        record = dict(entry)
        record.update(
            {
                "slug": slug_from_asset(entry),
                "source_path": entry.get("path", ""),
                "title": yaml_scalar(text, "title") or entry.get("title", entry["id"]),
                "purpose": yaml_scalar(text, "purpose"),
                "responsibility": yaml_scalar(text, "responsibility"),
                "usage_triggers": yaml_list(text, "usage_triggers"),
                "process": yaml_list(text, "process"),
                "canonical_practices": yaml_list(text, "canonical_practices"),
                "published_to": yaml_list(text, "published_to") or inline_list(entry.get("published_to", "")),
            }
        )
        records.append(record)
    return records


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


def expected_skill_path(generated_root: Path, adapter_id: str, slug: str) -> Path:
    return generated_root / adapter_id / "skills" / slug / "SKILL.md"


def manifest_skill_artifacts(manifest: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_list = False
    for raw in read(manifest).splitlines():
        line = raw.rstrip()
        if line.startswith("generated_skill_artifacts:"):
            in_list = True
            if line.split(":", 1)[1].strip() == "[]":
                return []
            continue
        if in_list and line and not line.startswith(" "):
            break
        if not in_list:
            continue
        stripped = line.strip()
        if stripped.startswith("- adapter:"):
            if current:
                artifacts.append(current)
            current = {"adapter": stripped.split(":", 1)[1].strip().strip('"').strip("'")}
        elif current is not None and stripped.startswith(("asset_id:", "slug:", "path:", "source_path:")):
            key, value = stripped.split(":", 1)
            current[key] = value.strip().strip('"').strip("'")
    if current:
        artifacts.append(current)
    return artifacts


def check_generated_skill_artifacts(generated_root: Path, vault_root: Path, manifest: Path) -> list[str]:
    errors: list[str] = []
    manifest_artifacts = manifest_skill_artifacts(manifest)
    asset_contract_phrases = {
        "ASSET-COLLAB-001": [
            "rehydration checkpoint",
            "risky collaboration transitions",
            "`needs:*` label changes are backed by transition gate evidence",
            "reviewer handoff to `needs:reviewer` includes peer-session dispatch evidence",
            "Human Decision Contract",
            "explicit authorization phrase",
            "delegated Architect or acceptance role",
            "Epic closure",
            "final `main` integration",
        ],
        "ASSET-COLLAB-002": [
            "rehydration step from durable sources",
            "transition gate it is satisfying",
            "target role to rehydrate durable sources",
        ],
    }
    for record in active_skill_assets(vault_root):
        published_to = record.get("published_to", [])
        if not isinstance(published_to, list):
            continue
        for adapter_id in sorted(SKILL_FOLDER_ADAPTERS):
            if adapter_id not in published_to and not (
                adapter_id == "trae" and TRAE_COMPATIBLE_SKILL_ADAPTERS.intersection(published_to)
            ):
                continue
            path = expected_skill_path(generated_root, adapter_id, str(record["slug"]))
            rel_path = str(path.relative_to(generated_root))
            matching_artifact = next(
                (
                    artifact
                    for artifact in manifest_artifacts
                    if artifact.get("adapter") == adapter_id
                    and artifact.get("asset_id") == str(record["id"])
                    and artifact.get("slug") == str(record["slug"])
                ),
                None,
            )
            if matching_artifact is None:
                errors.append(
                    f"Selected output skill artifact: {adapter_id} manifest missing generated skill artifact "
                    f"for active skill asset {record['id']}"
                )
            elif matching_artifact.get("path") != rel_path:
                errors.append(
                    f"Selected output skill artifact: {adapter_id} manifest path mismatch for {record['id']}: "
                    f"expected {rel_path}, got {matching_artifact.get('path', '')}"
                )
            if not path.exists():
                errors.append(
                    f"Selected output skill artifact: {adapter_id} missing generated SKILL.md "
                    f"for active skill asset {record['id']}: {path}"
                )
                continue
            text = read(path)
            checks = {
                "front matter": text.startswith("---\n") and "\n---\n" in text[4:],
                "asset ID": str(record["id"]) in text,
                "title": str(record.get("title", "")) in text,
                "purpose": str(record.get("purpose", "")) in text,
                "responsibility": "## Responsibility" in text and str(record.get("responsibility", "")) in text,
                "trigger or process": "## Trigger Guidance" in text or "## Process" in text,
            }
            for label, ok in checks.items():
                if not ok:
                    errors.append(
                        f"Selected output skill artifact: {adapter_id} {record['id']} SKILL.md missing {label}: {path}"
                    )
            for phrase in asset_contract_phrases.get(str(record["id"]), []):
                if phrase not in text:
                    errors.append(
                        f"Selected output skill artifact: {adapter_id} {record['id']} "
                        f"SKILL.md missing contract phrase {phrase!r}: {path}"
                    )
    return errors


def active_practice_records(vault_root: Path) -> dict[str, dict[str, str]]:
    return {
        entry["id"]: entry
        for entry in parse_index_entries(vault_root / "indexes" / "practice_index.yaml")
        if entry.get("status") in ACTIVE_STATUSES and entry.get("id") and entry.get("path")
    }


def semantic_route_paths(adapter_id: str, slug: str, practice_id: str) -> tuple[str, str, str]:
    if adapter_id in SKILL_FOLDER_ADAPTERS:
        root = f"{adapter_id}/skills/{slug}"
        return f"{root}/SKILL.md", f"{root}/references/{practice_id}.md", "skill_reference"
    if adapter_id == "claude-code":
        return "claude-code/CLAUDE.md", f"claude-code/references/{slug}/{practice_id}.md", "claude_reference"
    if adapter_id == "chatgpt":
        return "chatgpt/custom-instructions.md", f"chatgpt/knowledge/{slug}/{practice_id}.md", "knowledge_file"
    raise ValueError(f"unsupported semantic adapter target: {adapter_id}")


def semantic_installed_path(adapter_id: str, slug: str, practice_id: str) -> str:
    if adapter_id == "claude-code":
        return f"references/{slug}/{practice_id}.md"
    return ""


def semantic_manifest_routes(path: Path) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_routes = False
    for raw in read(path).splitlines():
        line = raw.rstrip()
        if line.startswith("routes:"):
            in_routes = line.split(":", 1)[1].strip() != "[]"
            continue
        if in_routes and line and not line.startswith(" "):
            break
        if not in_routes:
            continue
        stripped = line.strip()
        if stripped.startswith("- target:"):
            if current:
                routes.append(current)
            current = {"target": stripped.split(":", 1)[1].strip().strip('"').strip("'")}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key] = value.strip().strip('"').strip("'")
    if current:
        routes.append(current)
    return routes


def contained_generated_path(generated_root: Path, relative: str) -> Path | None:
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts:
        return None
    candidate = (generated_root / path).resolve()
    try:
        candidate.relative_to(generated_root.resolve())
    except ValueError:
        return None
    return candidate


def expected_semantic_routes(vault_root: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    practices = active_practice_records(vault_root)
    expected: dict[tuple[str, str, str], dict[str, str]] = {}
    for asset in active_skill_assets(vault_root):
        practices_for_asset = asset.get("canonical_practices", [])
        published_to = asset.get("published_to", [])
        if not isinstance(practices_for_asset, list) or not isinstance(published_to, list):
            continue
        for practice_id in practices_for_asset:
            practice = practices.get(str(practice_id))
            if practice is None:
                continue
            source = vault_root / practice["path"]
            if not source.is_file():
                continue
            source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
            for target in sorted(SKILL_FOLDER_ADAPTERS | {"claude-code", "chatgpt"}):
                if target not in published_to and not (
                    target == "trae" and TRAE_COMPATIBLE_SKILL_ADAPTERS.intersection(published_to)
                ):
                    continue
                router_path, target_path, packaging = semantic_route_paths(target, str(asset["slug"]), str(practice_id))
                expected[(target, str(asset["id"]), str(practice_id))] = {
                    "source_path": practice["path"],
                    "source_sha256": source_sha256,
                    "router_path": router_path,
                    "target_path": target_path,
                    "installed_path": semantic_installed_path(target, str(asset["slug"]), str(practice_id)),
                    "packaging": packaging,
                }
    return expected


def check_semantic_reachability(generated_root: Path, vault_root: Path, manifest: Path) -> list[str]:
    errors: list[str] = []
    pointer = yaml_scalar(read(manifest), "semantic_reachability_manifest")
    if pointer != "semantic-reachability-manifest.yaml":
        return [
            "Selected output semantic reachability: publish manifest missing the authoritative "
            "semantic_reachability_manifest pointer. Re-run publish_adapters.py for this generated root."
        ]
    semantic_path = contained_generated_path(generated_root, pointer)
    if semantic_path is None or not semantic_path.is_file():
        return [
            "Selected output semantic reachability: missing semantic_reachability_manifest under the exact "
            "--generated-root. Core adapter templates are not a substitute."
        ]

    semantic_text = read(semantic_path)
    if yaml_scalar(semantic_text, "surface") != "selected_output" or yaml_scalar(
        semantic_text, "authoritative_generated_root"
    ) != "true":
        return [
            "Selected output semantic reachability: manifest is not marked as the authoritative "
            "selected-output root. Re-run publish_adapters.py for the exact --generated-root."
        ]

    expected = expected_semantic_routes(vault_root)
    routes = semantic_manifest_routes(semantic_path)
    seen: set[tuple[str, str, str]] = set()
    for route in routes:
        key = (route.get("target", ""), route.get("asset_id", ""), route.get("practice_id", ""))
        if key in seen:
            errors.append(f"Selected output semantic reachability: duplicate mapping: {key}")
            continue
        seen.add(key)
        contract = expected.get(key)
        if contract is None:
            errors.append(
                "Selected output semantic reachability: dangling mapping for "
                f"target={key[0]} asset={key[1]} practice={key[2]}"
            )
            continue
        if route.get("declared_required") != "true":
            errors.append(f"Selected output semantic reachability: required mapping not declared required: {key}")
        if not route.get("condition") or route.get("condition") == "not_applicable":
            errors.append(f"Selected output semantic reachability: missing conditional route: {key}")
        if route.get("route_kind") != "reference_file":
            errors.append(f"Selected output semantic reachability: unsupported or ID-only route kind: {key}")
        for field in ["source_path", "source_sha256", "router_path", "target_path", "installed_path", "packaging"]:
            if route.get(field) != contract[field]:
                reason = "stale or missing provenance" if field.startswith("source_") else "target-specific packaging omission"
                errors.append(
                    f"Selected output semantic reachability: {reason} for {key}: "
                    f"expected {field}={contract[field]!r}, got {route.get(field, '')!r}"
                )

        router = contained_generated_path(generated_root, route.get("router_path", ""))
        target = contained_generated_path(generated_root, route.get("target_path", ""))
        if router is None or not router.is_file():
            errors.append(f"Selected output semantic reachability: missing or out-of-root router for {key}")
        elif key[2] not in read(router) or (
            route.get("installed_path") or route.get("target_path", "")
        ) not in read(router):
            errors.append(
                f"Selected output semantic reachability: ID-only router has no readable reference route for {key}"
            )
        if target is None or not target.is_file():
            errors.append(f"Selected output semantic reachability: missing or out-of-root readable target for {key}")
        elif key[2] not in read(target) or route.get("source_sha256", "") not in read(target):
            errors.append(f"Selected output semantic reachability: readable target lacks provenance for {key}")

    for key in expected:
        if key not in seen:
            errors.append(
                "Selected output semantic reachability: missing declared practice route "
                f"for target={key[0]} asset={key[1]} practice={key[2]}"
            )
    return errors


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
    errors.extend(check_generated_skill_artifacts(generated_root, vault_root, manifest))
    errors.extend(check_semantic_reachability(generated_root, vault_root, manifest))
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
