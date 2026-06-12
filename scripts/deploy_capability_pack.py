#!/usr/bin/env python3
"""Deploy a reviewed mandatory bootstrap capability pack into a selected Vault."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from check_foundry_roots import (
    VAULT_LAYOUT_MARKER,
    frontmatter,
    parse_marker,
    scan_yaml_field,
    simple_yaml_entries,
    validate,
)
from foundry_config import ROOT


REQUIRED_MANIFEST_FIELDS = {
    "manifest_schema_version",
    "pack_id",
    "title",
    "lifecycle_status",
    "version",
    "distribution_type",
    "sensitivity",
    "review_state",
}

REQUIRED_RECORD_FIELDS = {
    "id",
    "kind",
    "lifecycle_status",
    "path",
    "source_version",
    "content_sha256",
    "destination_layer",
    "membership_role",
    "activation_default",
    "import_action",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class PackRecord:
    item_id: str
    kind: str
    source_path: Path
    destination_path: Path
    index_entry: dict[str, str]
    source_sha256: str
    deployed_text: str
    deployed_sha256: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str, apply: bool) -> None:
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if value == "[]":
        return []
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError(f"unsupported inline list: {value}")
    return [unquote(item.strip()) for item in value[1:-1].split(",") if item.strip()]


def parse_scalar(value: str) -> str | list[str]:
    value = value.strip()
    if value.startswith("["):
        return parse_inline_list(value)
    return unquote(value)


def parse_simple_yaml(text: str) -> dict[str, object]:
    parsed_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"unsupported odd indentation: {raw}")
        parsed_lines.append((indent, raw.strip()))

    def parse_mapping(index: int, indent: int) -> tuple[dict[str, object], int]:
        data: dict[str, object] = {}
        while index < len(parsed_lines):
            line_indent, stripped = parsed_lines[index]
            if line_indent < indent:
                break
            if line_indent > indent:
                raise ValueError(f"unexpected indentation: {stripped}")
            if stripped.startswith("- "):
                break
            if ":" not in stripped:
                raise ValueError(f"expected mapping entry: {stripped}")
            key, value = stripped.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError("empty mapping key")
            if key in data:
                raise ValueError(f"duplicate mapping key: {key}")
            value = value.strip()
            index += 1
            if value:
                data[key] = parse_scalar(value)
                continue
            if index >= len(parsed_lines) or parsed_lines[index][0] <= line_indent:
                data[key] = {}
                continue
            child_indent, child = parsed_lines[index]
            if child_indent != line_indent + 2:
                raise ValueError(f"unexpected child indentation for {key}")
            if child.startswith("- "):
                child_value, index = parse_sequence(index, child_indent)
            else:
                child_value, index = parse_mapping(index, child_indent)
            data[key] = child_value
        return data, index

    def parse_sequence(index: int, indent: int) -> tuple[list[object], int]:
        items: list[object] = []
        while index < len(parsed_lines):
            line_indent, stripped = parsed_lines[index]
            if line_indent < indent:
                break
            if line_indent > indent:
                raise ValueError(f"unexpected sequence indentation: {stripped}")
            if not stripped.startswith("- "):
                break
            rest = stripped[2:].strip()
            index += 1
            if not rest:
                if index >= len(parsed_lines) or parsed_lines[index][0] <= line_indent:
                    items.append({})
                    continue
                if parsed_lines[index][0] != line_indent + 2:
                    raise ValueError("unexpected list child indentation")
                if parsed_lines[index][1].startswith("- "):
                    item, index = parse_sequence(index, line_indent + 2)
                else:
                    item, index = parse_mapping(index, line_indent + 2)
                items.append(item)
                continue
            if ":" not in rest:
                items.append(parse_scalar(rest))
                continue
            key, value = rest.split(":", 1)
            item: dict[str, object] = {key.strip(): parse_scalar(value.strip()) if value.strip() else {}}
            if index < len(parsed_lines) and parsed_lines[index][0] == line_indent + 2:
                continuation, index = parse_mapping(index, line_indent + 2)
                for cont_key, cont_value in continuation.items():
                    if cont_key in item:
                        raise ValueError(f"duplicate mapping key: {cont_key}")
                    item[cont_key] = cont_value
            items.append(item)
        return items, index

    data, index = parse_mapping(0, 0)
    if index != len(parsed_lines):
        raise ValueError("unexpected trailing YAML structure")
    return data


def scalar_string(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return ""


def top_level_scalars(text: str) -> dict[str, str]:
    parsed = parse_simple_yaml(text)
    return {key: scalar_string(value) for key, value in parsed.items() if not isinstance(value, dict)}


def section_scalars(text: str, section: str) -> dict[str, str]:
    parsed = parse_simple_yaml(text)
    data = parsed.get(section, {})
    if not isinstance(data, dict):
        return {}
    return {key: scalar_string(value) for key, value in data.items() if not isinstance(value, dict)}


def list_entries(text: str, section: str) -> list[dict[str, str]]:
    parsed = parse_simple_yaml(text)
    entries = parsed.get(section, [])
    if entries == {}:
        return []
    if not isinstance(entries, list):
        return []
    result: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        result.append({key: scalar_string(value) for key, value in entry.items() if not isinstance(value, dict)})
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inline_list(value: str) -> list[str]:
    try:
        return parse_inline_list(value)
    except ValueError:
        return []


def yaml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def safe_segment(value: str, label: str, errors: list[str], fallback: str) -> str:
    if not value:
        errors.append(f"{label} missing")
        return fallback
    if not SAFE_SEGMENT_RE.match(value):
        errors.append(f"{label} must be a safe single path segment: {value}")
        return fallback
    return value


def destination_for(vault_root: Path, kind: str, source_path: Path) -> tuple[Path, dict[str, str], list[str]]:
    errors: list[str] = []
    if kind == "practice":
        metadata = frontmatter(source_path)
        item_id = metadata.get("id", "")
        domain = metadata.get("domain", "")
        if not item_id:
            errors.append(f"{source_path}: practice missing id")
        domain = safe_segment(domain, f"{source_path}: practice domain", errors, "uncategorized")
        return (
            vault_root / "practices" / domain / source_path.name,
            {
                "id": item_id,
                "title": metadata.get("title", item_id),
                "domain": domain,
                "status": metadata.get("status", ""),
                "path": f"practices/{domain}/{source_path.name}",
            },
            errors,
        )
    if kind == "asset":
        item_id = scan_yaml_field(source_path, "id") or ""
        asset_type = scan_yaml_field(source_path, "asset_type") or ""
        if not item_id:
            errors.append(f"{source_path}: asset missing id")
        asset_type = safe_segment(asset_type, f"{source_path}: asset_type", errors, "asset")
        directory = {"skill": "skills", "subagent": "subagents", "automation": "automations"}.get(
            asset_type, f"{asset_type}s"
        )
        return (
            vault_root / "assets" / directory / source_path.name,
            {
                "id": item_id,
                "title": scan_yaml_field(source_path, "title") or item_id,
                "asset_type": asset_type,
                "status": scan_yaml_field(source_path, "status") or "",
                "path": f"assets/{directory}/{source_path.name}",
            },
            errors,
        )
    return vault_root / source_path.name, {}, [f"{source_path}: unsupported record kind {kind}"]


def pack_provenance(manifest: dict[str, str]) -> str:
    pack_id = manifest.get("pack_id", "")
    version = manifest.get("version", "")
    source = manifest.get("source_provenance", "")
    return f"Deployed from capability pack {pack_id} version {version}; source: {source}"


def add_markdown_deployment_metadata(text: str, manifest: dict[str, str]) -> str:
    if not text.startswith("---\n"):
        return text
    marker = "\n---\n"
    end = text.find(marker, len("---\n"))
    if end == -1:
        return text
    metadata = "\n".join(
        [
            f"provenance: {yaml_string(pack_provenance(manifest))}",
            f"pack_membership: [{manifest.get('pack_id', '')}]",
            f"pack_source_version: {yaml_string(manifest.get('version', ''))}",
        ]
    )
    return text[:end].rstrip() + "\n" + metadata + text[end:]


def add_yaml_deployment_metadata(text: str, manifest: dict[str, str]) -> str:
    metadata = "\n".join(
        [
            f"provenance: {yaml_string(pack_provenance(manifest))}",
            "pack_membership:",
            f"  - {manifest.get('pack_id', '')}",
            f"pack_source_version: {yaml_string(manifest.get('version', ''))}",
        ]
    )
    return text.rstrip() + "\n" + metadata + "\n"


def deployed_record_text(kind: str, source_text: str, manifest: dict[str, str]) -> str:
    if kind == "practice":
        return add_markdown_deployment_metadata(source_text, manifest)
    if kind == "asset":
        return add_yaml_deployment_metadata(source_text, manifest)
    return source_text


def parse_pack_records(
    pack_root: Path, vault_root: Path, manifest: dict[str, str], manifest_text: str
) -> tuple[list[PackRecord], list[str]]:
    records: list[PackRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for entry in list_entries(manifest_text, "included_records"):
        item_id = entry.get("id", "<unknown>")
        missing = sorted(REQUIRED_RECORD_FIELDS - entry.keys())
        for field in missing:
            errors.append(f"included_record {item_id} missing {field}")
        if item_id in seen_ids:
            errors.append(f"duplicate included_record id {item_id}")
        seen_ids.add(item_id)
        if missing:
            continue
        if entry.get("destination_layer") != "canonical_vault_record":
            errors.append(f"included_record {item_id} must target canonical_vault_record")
        if entry.get("import_action") not in {"create_or_review_update", "skip_if_present"}:
            errors.append(f"included_record {item_id} import_action is not supported by bootstrap deploy")
        digest = entry.get("content_sha256", "")
        if not SHA256_RE.match(digest):
            errors.append(f"included_record {item_id} has invalid content_sha256")
            continue
        source_path = pack_root / entry.get("path", "")
        if not source_path.exists():
            errors.append(f"included_record {item_id} source path missing: {entry.get('path')}")
            continue
        if sha256(source_path) != digest:
            errors.append(f"included_record {item_id} content_sha256 mismatch")
            continue
        source_text = read(source_path)
        text = deployed_record_text(entry["kind"], source_text, manifest)
        destination_path, index_entry, destination_errors = destination_for(vault_root, entry["kind"], source_path)
        errors.extend(destination_errors)
        if index_entry.get("id") and index_entry.get("id") != item_id:
            errors.append(f"included_record {item_id} id does not match record metadata {index_entry.get('id')}")
        if not destination_errors:
            records.append(
                PackRecord(
                    item_id=item_id,
                    kind=entry["kind"],
                    source_path=source_path,
                    destination_path=destination_path,
                    index_entry=index_entry,
                    source_sha256=digest,
                    deployed_text=text,
                    deployed_sha256=sha256_text(text),
                )
            )
    if not records:
        errors.append("included_records must not be empty")
    return records, errors


def validate_manifest(core_root: Path, vault_root: Path, pack_root: Path, manifest_path: Path) -> tuple[dict[str, str], list[PackRecord], list[str]]:
    errors: list[str] = []
    text = read(manifest_path)
    manifest = top_level_scalars(text)
    missing = sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    for field in missing:
        errors.append(f"manifest missing {field}")
    if manifest.get("distribution_type") != "mandatory_bootstrap":
        errors.append("only mandatory_bootstrap packs are supported by this deployment path")
    if manifest.get("lifecycle_status") != "reviewed" or manifest.get("review_state") != "reviewed":
        errors.append("mandatory bootstrap pack must be reviewed before deployment")
    if manifest.get("sensitivity") != "public":
        errors.append("mandatory bootstrap pack must be public")

    compatibility = section_scalars(text, "compatibility")
    if "vault_layout_versions" not in compatibility:
        errors.append("compatibility missing vault_layout_versions")
    else:
        vault_marker, marker_errors = parse_marker(vault_root / VAULT_LAYOUT_MARKER)
        errors.extend(f"vault marker {error}" for error in marker_errors)
        vault_layout = str(vault_marker.get("layout_version", ""))
        if vault_layout and vault_layout not in inline_list(compatibility["vault_layout_versions"]):
            errors.append(f"pack does not support selected Vault layout version {vault_layout}")
    if compatibility.get("requires_bootstrap_pack") != "false":
        errors.append("mandatory bootstrap pack must not require a prior bootstrap pack")

    if list_entries(text, "executable_payloads"):
        errors.append("bootstrap deployment refuses executable payloads")

    records, record_errors = parse_pack_records(pack_root, vault_root, manifest, text)
    errors.extend(record_errors)
    if not (core_root / "schemas" / "capability-pack-manifest.schema.yaml").exists():
        errors.append("core capability pack manifest schema missing")
    return manifest, records, errors


def existing_entries(vault_root: Path, kind: str) -> tuple[list[dict[str, str]], list[str]]:
    if kind == "practice":
        return simple_yaml_entries(read(vault_root / "indexes" / "practice_index.yaml"), "practices")
    return simple_yaml_entries(read(vault_root / "indexes" / "asset_index.yaml"), "assets")


def detect_conflicts(vault_root: Path, records: list[PackRecord]) -> tuple[list[PackRecord], list[PackRecord], list[str]]:
    added: list[PackRecord] = []
    skipped: list[PackRecord] = []
    conflicts: list[str] = []
    practice_ids = {entry.get("id", "") for entry in existing_entries(vault_root, "practice")[0]}
    asset_ids = {entry.get("id", "") for entry in existing_entries(vault_root, "asset")[0]}
    by_kind = {
        "practice": {entry.get("id", ""): entry for entry in existing_entries(vault_root, "practice")[0]},
        "asset": {entry.get("id", ""): entry for entry in existing_entries(vault_root, "asset")[0]},
    }

    for record in records:
        if record.kind == "practice" and record.item_id in asset_ids:
            conflicts.append(f"{record.item_id}: id already exists as an asset")
            continue
        if record.kind == "asset" and record.item_id in practice_ids:
            conflicts.append(f"{record.item_id}: id already exists as a practice")
            continue
        indexed = by_kind.get(record.kind, {}).get(record.item_id)
        rel_destination = str(record.destination_path.relative_to(vault_root))
        if indexed and indexed.get("path") != rel_destination:
            conflicts.append(
                f"{record.item_id}: index path {indexed.get('path')} conflicts with pack destination {rel_destination}"
            )
            continue
        if record.destination_path.exists():
            if not indexed:
                conflicts.append(f"{record.item_id}: record file exists without a matching index entry")
            elif sha256(record.destination_path) == record.deployed_sha256:
                skipped.append(record)
            else:
                conflicts.append(f"{record.item_id}: local Vault record differs from pack content")
            continue
        if indexed:
            conflicts.append(f"{record.item_id}: index entry exists but record file is missing")
            continue
        added.append(record)
    return added, skipped, conflicts


def update_grouping(text: str, group_key: str, item_key: str, item_id: str) -> str:
    empty_line = f"{group_key}: {{}}"
    if empty_line in text:
        return text.replace(empty_line, f"{group_key}:\n  {item_key}: [{item_id}]", 1)

    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"{group_key}:"), None)
    if start is None:
        return text.rstrip() + f"\n\n{group_key}:\n  {item_key}: [{item_id}]\n"

    end = start + 1
    while end < len(lines) and (not lines[end] or lines[end].startswith(" ")):
        end += 1

    for index in range(start + 1, end):
        if lines[index].startswith(f"  {item_key}:"):
            values = inline_list(lines[index].split(":", 1)[1].strip())
            if item_id not in values:
                values.append(item_id)
                lines[index] = f"  {item_key}: [{', '.join(values)}]"
            return "\n".join(lines).rstrip() + "\n"

    lines.insert(end, f"  {item_key}: [{item_id}]")
    return "\n".join(lines).rstrip() + "\n"


def append_index_entry(text: str, list_key: str, entry: dict[str, str]) -> str:
    if f"{list_key}: []" in text:
        head = text.replace(f"{list_key}: []", f"{list_key}:", 1).rstrip()
        return head + "\n" + index_entry_text(entry)
    if f"  - id: {entry['id']}" in text:
        return text
    return text.rstrip() + "\n" + index_entry_text(entry)


def index_entry_text(entry: dict[str, str]) -> str:
    lines = [f"  - id: {entry['id']}"]
    for key in ["title", "asset_type", "domain", "status", "path"]:
        value = entry.get(key, "")
        if value:
            lines.append(f"    {key}: {value}")
    return "\n".join(lines) + "\n"


def update_index_text(text: str, kind: str, records: list[PackRecord]) -> str:
    text = re.sub(r"^updated: .*$", f"updated: {date.today().isoformat()}", text, flags=re.MULTILINE)
    for record in records:
        if kind == "practice":
            text = update_grouping(text, "domains", record.index_entry["domain"], record.item_id)
            text = append_index_entry(text, "practices", record.index_entry)
        else:
            text = update_grouping(text, "asset_types", record.index_entry["asset_type"], record.item_id)
            text = append_index_entry(text, "assets", record.index_entry)
    return text


def deploy(core_root: Path, vault_root: Path, pack_root: Path, apply: bool) -> int:
    root_errors = validate(core_root, vault_root)
    if root_errors:
        print("Capability pack deployment failed root validation:")
        for error in root_errors:
            print(f"- {error}")
        return 1

    manifest_path = pack_root / "manifest.yaml"
    if not manifest_path.exists():
        print(f"Capability pack manifest missing: {manifest_path}")
        return 1

    manifest, records, manifest_errors = validate_manifest(core_root, vault_root, pack_root, manifest_path)
    if manifest_errors:
        print("Capability pack deployment failed manifest validation:")
        for error in manifest_errors:
            print(f"- {error}")
        return 1

    added, skipped, conflicts = detect_conflicts(vault_root, records)
    if conflicts:
        print("Capability pack deployment found conflicts:")
        for conflict in conflicts:
            print(f"- {conflict}")
        print("Deployment summary:")
        print("added: 0")
        print("updated: 0")
        print(f"skipped: {len(skipped)}")
        print(f"conflicts: {len(conflicts)}")
        return 1

    print(f"Deploying pack: {manifest['pack_id']} {manifest['version']}")
    for record in added:
        write(record.destination_path, record.deployed_text, apply)

    practice_adds = [record for record in added if record.kind == "practice"]
    asset_adds = [record for record in added if record.kind == "asset"]
    if practice_adds:
        path = vault_root / "indexes" / "practice_index.yaml"
        write(path, update_index_text(read(path), "practice", practice_adds), apply)
    if asset_adds:
        path = vault_root / "indexes" / "asset_index.yaml"
        write(path, update_index_text(read(path), "asset", asset_adds), apply)

    print("Deployment summary:")
    print(f"added: {len(added)}")
    print("updated: 0")
    print(f"skipped: {len(skipped)}")
    print("conflicts: 0")

    if apply:
        post_errors = validate(core_root, vault_root)
        if post_errors:
            print("Capability pack deployed but post-deploy validation failed:")
            for error in post_errors:
                print(f"- {error}")
            return 1
        print("Capability pack deployed and selected Vault validated.")
    else:
        print("Dry-run only. Re-run with --apply to deploy the bootstrap pack.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy a reviewed mandatory bootstrap capability pack into a selected Vault.")
    parser.add_argument("pack_root", help="Capability pack directory containing manifest.yaml.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    pack_root = Path(args.pack_root).expanduser().resolve()
    return deploy(core_root, vault_root, pack_root, args.apply)


if __name__ == "__main__":
    sys.exit(main())
