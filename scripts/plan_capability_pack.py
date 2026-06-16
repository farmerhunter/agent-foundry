#!/usr/bin/env python3
"""Plan a capability pack deployment without writing Vault or runtime files."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from check_foundry_roots import (
    VAULT_LAYOUT_MARKER,
    frontmatter,
    parse_marker,
    scan_yaml_field,
    simple_yaml_entries,
    validate,
)
from deploy_capability_pack import (
    REQUIRED_RECORD_FIELDS,
    SHA256_RE,
    deployed_record_text,
    inline_list,
    list_entries,
    parse_simple_yaml,
    read,
    safe_segment,
    section_scalars,
    sha256,
    top_level_scalars,
)
from foundry_config import ROOT


ALLOWED_DISTRIBUTION_TYPES = {"mandatory_bootstrap", "optional_capability", "product_project_candidate"}
ALLOWED_IMPORT_ACTIONS = {"create_or_review_update", "skip_if_present", "stage_only"}
ALLOWED_DESTINATION_LAYERS = {"canonical_vault_record", "vault_metadata", "import_staging_reference"}
ALLOWED_PAYLOAD_INSTALL_BOUNDARIES = {"managed_runtime_copy_required", "manual_import_only", "no_install"}
REQUIRED_PLAN_MANIFEST_FIELDS = {
    "manifest_schema_version",
    "pack_id",
    "title",
    "description",
    "lifecycle_status",
    "version",
    "exported_at",
    "distribution_type",
    "source_provenance",
    "maintainer_contact",
    "license",
    "sensitivity",
    "review_state",
}
SUPPORTED_MANIFEST_SCHEMA_VERSION = "1"
SUPPORTED_CORE_SCHEMA_VERSION = 1
REQUIRED_CONFLICT_POLICY_FIELDS = {
    "id_collision",
    "same_version_hash_mismatch",
    "newer_version_update",
    "local_edit_behavior",
    "rollback_notes",
}
REQUIRED_INTEGRITY_FIELDS = {
    "digest_algorithm",
    "manifest_paths_are_relative",
    "private_vault_content",
}
REQUIRED_DEPLOYED_PACK_FIELDS = {"pack_id", "version", "source"}


@dataclass(frozen=True)
class PlannedRecord:
    item_id: str
    kind: str
    import_action: str
    source_path: Path
    destination_path: Path
    source_sha256: str
    current_sha256: str
    imported_sha256: str
    outcome: str
    detail: str


@dataclass(frozen=True)
class PlannedPayload:
    payload_id: str
    path: Path
    install_boundary: str
    outcome: str
    detail: str


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def destination_for(vault_root: Path, kind: str, source_path: Path) -> tuple[Path, list[str]]:
    errors: list[str] = []
    if kind == "practice":
        metadata = frontmatter(source_path)
        item_id = metadata.get("id", "")
        domain = metadata.get("domain", "")
        if not item_id:
            errors.append(f"{source_path}: practice missing id")
        domain = safe_segment(domain, f"{source_path}: practice domain", errors, "uncategorized")
        return vault_root / "practices" / domain / source_path.name, errors
    if kind == "asset":
        item_id = scan_yaml_field(source_path, "id") or ""
        asset_type = scan_yaml_field(source_path, "asset_type") or ""
        if not item_id:
            errors.append(f"{source_path}: asset missing id")
        asset_type = safe_segment(asset_type, f"{source_path}: asset_type", errors, "asset")
        directory = {"skill": "skills", "subagent": "subagents", "automation": "automations"}.get(
            asset_type, f"{asset_type}s"
        )
        return vault_root / "assets" / directory / source_path.name, errors
    return vault_root / source_path.name, [f"{source_path}: unsupported record kind {kind}"]


def indexed_records(vault_root: Path) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    practice_index = vault_root / "indexes" / "practice_index.yaml"
    asset_index = vault_root / "indexes" / "asset_index.yaml"
    if practice_index.exists():
        for entry in simple_yaml_entries(read(practice_index), "practices")[0]:
            item_id = entry.get("id", "")
            if item_id:
                records[item_id] = {"kind": "practice", **entry}
    if asset_index.exists():
        for entry in simple_yaml_entries(read(asset_index), "assets")[0]:
            item_id = entry.get("id", "")
            if item_id:
                records[item_id] = {"kind": "asset", **entry}
    return records


def deployed_pack_records(vault_root: Path, pack_id: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not path.exists():
        return {}, []
    try:
        index = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {}, [f"deployed-pack-index.yaml parse error: {exc}"]
    records: dict[str, dict[str, str]] = {}
    packs = index.get("deployed_packs", [])
    if not isinstance(packs, list):
        return {}, ["deployed-pack-index.yaml deployed_packs must be a list"]
    for pack in packs:
        if not isinstance(pack, dict) or pack.get("pack_id") != pack_id:
            continue
        metadata_errors = validate_deployed_pack_metadata(pack, pack_id)
        if metadata_errors:
            return {}, metadata_errors
        pack_records = pack.get("records", [])
        if pack_records in ({}, None):
            return {}, []
        if not isinstance(pack_records, list):
            return {}, [f"deployed pack {pack_id} records must be a list"]
        for record in pack_records:
            if not isinstance(record, dict):
                return {}, [f"deployed pack {pack_id} contains non-mapping record metadata"]
            item_id = str(record.get("id", ""))
            if item_id:
                records[item_id] = {key: str(value) for key, value in record.items() if not isinstance(value, (dict, list))}
        return records, []
    return {}, []


def validate_deployed_pack_metadata(pack: dict[object, object], pack_id: str) -> list[str]:
    errors: list[str] = []
    for field in sorted(REQUIRED_DEPLOYED_PACK_FIELDS - {str(key) for key in pack}):
        errors.append(f"deployed pack {pack_id} missing {field}")
    source = pack.get("source", {})
    if not isinstance(source, dict):
        errors.append(f"deployed pack {pack_id} source must be a mapping")
    else:
        manifest_sha = str(source.get("manifest_sha256", ""))
        if not SHA256_RE.match(manifest_sha):
            errors.append(f"deployed pack {pack_id} source.manifest_sha256 must be sha256")
    return errors


def vault_mentions_pack(vault_root: Path, pack_id: str) -> bool:
    metadata = vault_root / "packs" / "deployed-pack-index.yaml"
    if metadata.exists() and pack_id in metadata.read_text(encoding="utf-8"):
        return True
    for base in [vault_root / "practices", vault_root / "assets"]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and pack_id in path.read_text(encoding="utf-8"):
                return True
    return False


def safe_pack_path(pack_root: Path, raw_path: str, label: str) -> tuple[Path | None, str]:
    if not raw_path:
        return None, f"{label} missing path"
    relative = Path(raw_path)
    if relative.is_absolute():
        return None, f"{label} path must be relative: {raw_path}"
    root = pack_root.resolve()
    candidate = (pack_root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, f"{label} path escapes pack root: {raw_path}"
    return candidate, ""


def source_record_id(kind: str, source_path: Path) -> str:
    if kind == "practice":
        return frontmatter(source_path).get("id", "")
    if kind == "asset":
        return scan_yaml_field(source_path, "id") or ""
    return ""


def validate_manifest(core_root: Path, vault_root: Path, pack_root: Path) -> tuple[dict[str, str], list[str], str]:
    manifest_path = pack_root / "manifest.yaml"
    if not manifest_path.exists():
        return {}, [f"Capability pack manifest missing: {manifest_path}"], ""
    manifest_text = read(manifest_path)
    manifest = top_level_scalars(manifest_text)
    errors: list[str] = []
    for field in sorted(REQUIRED_PLAN_MANIFEST_FIELDS - manifest.keys()):
        errors.append(f"manifest missing {field}")
    if manifest.get("manifest_schema_version", "") != SUPPORTED_MANIFEST_SCHEMA_VERSION:
        errors.append(
            "unsupported manifest_schema_version "
            f"{manifest.get('manifest_schema_version', '')}; expected {SUPPORTED_MANIFEST_SCHEMA_VERSION}"
        )
    if manifest.get("distribution_type") not in ALLOWED_DISTRIBUTION_TYPES:
        errors.append(f"invalid distribution_type {manifest.get('distribution_type', '')}")
    if manifest.get("sensitivity") != "public":
        errors.append("only public fixture packs are supported by this planner")
    if manifest.get("review_state") not in {"reviewed", "accepted", "unreviewed"}:
        errors.append(f"invalid review_state {manifest.get('review_state', '')}")

    compatibility = section_scalars(manifest_text, "compatibility")
    for field in ["core_schema_version_min", "core_schema_version_max", "vault_layout_versions", "requires_bootstrap_pack"]:
        if field not in compatibility:
            errors.append(f"compatibility missing {field}")
    try:
        core_min = int(compatibility.get("core_schema_version_min", "0"))
        core_max = int(compatibility.get("core_schema_version_max", "0"))
        if not (core_min <= SUPPORTED_CORE_SCHEMA_VERSION <= core_max):
            errors.append(f"pack does not support Core schema version {SUPPORTED_CORE_SCHEMA_VERSION}")
    except ValueError:
        errors.append("compatibility core schema versions must be integers")
    vault_marker, marker_errors = parse_marker(vault_root / VAULT_LAYOUT_MARKER)
    errors.extend(f"vault marker {error}" for error in marker_errors)
    vault_layout = str(vault_marker.get("layout_version", ""))
    if vault_layout and vault_layout not in inline_list(compatibility.get("vault_layout_versions", "")):
        errors.append(f"pack does not support selected Vault layout version {vault_layout}")
    if compatibility.get("requires_bootstrap_pack") == "true" and not vault_mentions_pack(
        vault_root, "pack.bootstrap.minimal"
    ):
        errors.append("pack requires bootstrap pack but selected Vault does not show pack.bootstrap.minimal")

    conflict_policy = section_scalars(manifest_text, "conflict_policy")
    for field in sorted(REQUIRED_CONFLICT_POLICY_FIELDS - conflict_policy.keys()):
        errors.append(f"conflict_policy missing {field}")
    if conflict_policy.get("id_collision") != "fail_closed":
        errors.append("conflict_policy id_collision must be fail_closed")
    if conflict_policy.get("same_version_hash_mismatch") != "fail_closed":
        errors.append("conflict_policy same_version_hash_mismatch must be fail_closed")

    integrity = section_scalars(manifest_text, "integrity")
    for field in sorted(REQUIRED_INTEGRITY_FIELDS - integrity.keys()):
        errors.append(f"integrity missing {field}")
    if integrity.get("digest_algorithm") != "sha256":
        errors.append("integrity digest_algorithm must be sha256")
    if integrity.get("manifest_paths_are_relative") != "true":
        errors.append("integrity manifest_paths_are_relative must be true")
    if integrity.get("private_vault_content") != "excluded":
        errors.append("integrity private_vault_content must be excluded")

    if not (core_root / "schemas" / "capability-pack-manifest.schema.yaml").exists():
        errors.append("core capability pack manifest schema missing")
    return manifest, errors, manifest_text


def validate_records(pack_root: Path, manifest_text: str) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    valid_records: list[dict[str, str]] = []
    records = list_entries(manifest_text, "included_records")
    if not records:
        errors.append("included_records must not be empty")
        return valid_records, errors
    seen: set[str] = set()
    for entry in records:
        item_id = entry.get("id", "<unknown>")
        entry_errors: list[str] = []
        for field in sorted(REQUIRED_RECORD_FIELDS - entry.keys()):
            entry_errors.append(f"included_record {item_id} missing {field}")
        if item_id in seen:
            entry_errors.append(f"duplicate included_record id {item_id}")
        seen.add(item_id)
        if entry.get("destination_layer") not in ALLOWED_DESTINATION_LAYERS:
            entry_errors.append(
                f"included_record {item_id} has unsupported destination_layer {entry.get('destination_layer', '')}"
            )
        if entry.get("import_action") not in ALLOWED_IMPORT_ACTIONS:
            entry_errors.append(f"included_record {item_id} has unsupported import_action {entry.get('import_action', '')}")
        digest = entry.get("content_sha256", "")
        if not SHA256_RE.match(digest):
            entry_errors.append(f"included_record {item_id} has invalid content_sha256")
        source_path, path_error = safe_pack_path(pack_root, entry.get("path", ""), f"included_record {item_id}")
        if path_error:
            entry_errors.append(path_error)
        elif source_path is None:
            entry_errors.append(f"included_record {item_id} source path unavailable")
        elif not source_path.exists():
            entry_errors.append(f"included_record {item_id} source path missing: {entry.get('path', '')}")
        elif sha256(source_path) != digest:
            entry_errors.append(f"included_record {item_id} content_sha256 mismatch")
        else:
            source_id = source_record_id(entry.get("kind", ""), source_path)
            if source_id and source_id != item_id:
                entry_errors.append(f"included_record {item_id} does not match source metadata id {source_id}")
        errors.extend(entry_errors)
        if not entry_errors and source_path is not None:
            valid_entry = dict(entry)
            valid_entry["_source_path"] = str(source_path)
            valid_records.append(valid_entry)
    return valid_records, errors


def validate_payloads(pack_root: Path, manifest_text: str) -> tuple[list[PlannedPayload], list[str]]:
    errors: list[str] = []
    planned: list[PlannedPayload] = []
    for payload in list_entries(manifest_text, "executable_payloads"):
        payload_id = payload.get("id", "<unknown>")
        install_boundary = payload.get("install_boundary", "")
        source_path, path_error = safe_pack_path(pack_root, payload.get("path", ""), f"executable_payload {payload_id}")
        if payload.get("execute_from_pack") != "false":
            errors.append(f"executable_payload {payload_id} must not execute from pack")
        if install_boundary not in ALLOWED_PAYLOAD_INSTALL_BOUNDARIES:
            errors.append(f"executable_payload {payload_id} has unsupported install_boundary {install_boundary}")
        digest = payload.get("source_sha256", "")
        if not SHA256_RE.match(digest):
            errors.append(f"executable_payload {payload_id} has invalid source_sha256")
        elif path_error:
            errors.append(path_error)
        elif source_path is None:
            errors.append(f"executable_payload {payload_id} source path unavailable")
        elif not source_path.exists():
            errors.append(f"executable_payload {payload_id} source path missing: {payload.get('path', '')}")
        elif sha256(source_path) != digest:
            errors.append(f"executable_payload {payload_id} source_sha256 mismatch")
        if source_path is not None:
            planned.append(
                PlannedPayload(
                    payload_id=payload_id,
                    path=source_path,
                    install_boundary=install_boundary,
                    outcome="blocked_executable_install"
                    if install_boundary == "managed_runtime_copy_required"
                    else "no_install",
                    detail="Executable payloads are inert in #106; managed install belongs to later issues.",
                )
            )
    return planned, errors


def plan_records(
    vault_root: Path,
    pack_root: Path,
    manifest: dict[str, str],
    record_entries: list[dict[str, str]],
) -> tuple[list[PlannedRecord], list[str]]:
    errors: list[str] = []
    planned: list[PlannedRecord] = []
    indexed = indexed_records(vault_root)
    imported, metadata_errors = deployed_pack_records(vault_root, manifest.get("pack_id", ""))
    errors.extend(metadata_errors)
    id_kind = {item_id: entry.get("kind", "") for item_id, entry in indexed.items()}
    planned_destinations: dict[Path, str] = {}

    for entry in record_entries:
        item_id = entry.get("id", "<unknown>")
        kind = entry.get("kind", "")
        import_action = entry.get("import_action", "")
        source_path = Path(entry.get("_source_path", ""))
        destination_path, destination_errors = destination_for(vault_root, kind, source_path)
        if destination_errors:
            errors.extend(destination_errors)
            continue
        current_hash = sha256(destination_path) if destination_path.exists() else ""
        imported_hash = imported.get(item_id, {}).get("deployed_sha256", "") or imported.get(item_id, {}).get(
            "imported_sha256", ""
        )
        source_hash = entry.get("content_sha256", "")
        deployed_hash = ""
        if source_path.exists():
            deployed_text = deployed_record_text(kind, read(source_path), manifest)
            deployed_hash = hashlib.sha256(deployed_text.encode("utf-8")).hexdigest()
        indexed_entry = indexed.get(item_id)

        outcome = "add"
        detail = f"would create {rel(destination_path, vault_root)}"
        if destination_path in planned_destinations:
            outcome = "fail"
            detail = f"duplicate planned destination also used by {planned_destinations[destination_path]}"
        elif indexed_entry and indexed_entry.get("kind") != kind:
            outcome = "fail"
            detail = f"id exists as {indexed_entry.get('kind')} but pack record is {kind}"
        elif indexed_entry and indexed_entry.get("path") != rel(destination_path, vault_root):
            outcome = "fail"
            detail = f"index path {indexed_entry.get('path')} differs from destination {rel(destination_path, vault_root)}"
        elif destination_path.exists() and not indexed_entry:
            outcome = "fail"
            detail = "record file exists without matching index entry"
        elif indexed_entry and not destination_path.exists():
            outcome = "fail"
            detail = "index entry exists but record file is missing"
        elif import_action == "stage_only":
            outcome = "stage_only"
            detail = "record is stage_only; #106 reports it but does not plan canonical write"
        elif destination_path.exists() and current_hash in {source_hash, deployed_hash}:
            outcome = "skip"
            detail = "current Vault record hash matches pack source or deployed form"
        elif destination_path.exists() and imported_hash and current_hash != imported_hash:
            outcome = "merge_required"
            detail = "current Vault record differs from prior deployed hash; preserve local edit"
        elif destination_path.exists():
            outcome = "update"
            detail = "record exists and differs from pack source; reviewed update required"
        elif item_id in id_kind:
            outcome = "fail"
            detail = "id exists in Vault index without a usable destination"
        planned_destinations.setdefault(destination_path, item_id)

        planned.append(
            PlannedRecord(
                item_id=item_id,
                kind=kind,
                import_action=import_action,
                source_path=source_path,
                destination_path=destination_path,
                source_sha256=source_hash,
                current_sha256=current_hash,
                imported_sha256=imported_hash,
                outcome=outcome,
                detail=detail,
            )
        )
    return planned, errors


def manifest_hash(pack_root: Path) -> str:
    return sha256(pack_root / "manifest.yaml")


def same_version_hash_mismatch(vault_root: Path, manifest: dict[str, str], current_manifest_hash: str) -> bool:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not path.exists():
        return False
    try:
        index = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except ValueError:
        return True
    packs = index.get("deployed_packs", [])
    if not isinstance(packs, list):
        return True
    for pack in packs:
        if not isinstance(pack, dict) or pack.get("pack_id") != manifest.get("pack_id", ""):
            continue
        source = pack.get("source", {})
        manifest_sha = source.get("manifest_sha256", "") if isinstance(source, dict) else ""
        return (
            str(pack.get("version", "")) == manifest.get("version", "")
            and bool(manifest_sha)
            and str(manifest_sha) != current_manifest_hash
        )
    return False


def print_plan(
    pack_root: Path,
    vault_root: Path,
    manifest: dict[str, str],
    records: list[PlannedRecord],
    payloads: list[PlannedPayload],
    errors: list[str],
) -> None:
    print("Capability pack plan/check report")
    print(f"pack_root: {pack_root}")
    print(f"vault_root: {vault_root}")
    if manifest:
        print(f"pack_id: {manifest.get('pack_id', '')}")
        print(f"version: {manifest.get('version', '')}")
        print(f"distribution_type: {manifest.get('distribution_type', '')}")
        print(f"review_state: {manifest.get('review_state', '')}")
        print(f"manifest_sha256: {manifest_hash(pack_root) if (pack_root / 'manifest.yaml').exists() else ''}")
    counts: dict[str, int] = {}
    for record in records:
        counts[record.outcome] = counts.get(record.outcome, 0) + 1
    for payload in payloads:
        counts[payload.outcome] = counts.get(payload.outcome, 0) + 1
    if errors:
        counts["fail"] = counts.get("fail", 0) + len(errors)
    print("summary:")
    for key in ["add", "update", "skip", "merge_required", "stage_only", "blocked_executable_install", "no_install", "fail"]:
        print(f"{key}: {counts.get(key, 0)}")
    print("records:")
    if not records:
        print("- none")
    for record in records:
        print(f"- {record.item_id} {record.kind} {record.outcome}: {record.detail}")
    print("executable_payloads:")
    if not payloads:
        print("- none")
    for payload in payloads:
        print(f"- {payload.payload_id} {payload.outcome}: {payload.detail}")
    if errors:
        print("failures:")
        for error in errors:
            print(f"- {error}")
    print("writes: none")


def plan(core_root: Path, vault_root: Path, pack_root: Path) -> int:
    root_errors = validate(core_root, vault_root)
    manifest, manifest_errors, manifest_text = validate_manifest(core_root, vault_root, pack_root)
    records_raw, record_errors = validate_records(pack_root, manifest_text) if manifest_text else ([], [])
    payloads, payload_errors = validate_payloads(pack_root, manifest_text) if manifest_text else ([], [])
    records, planning_errors = plan_records(vault_root, pack_root, manifest, records_raw) if manifest else ([], [])
    errors = root_errors + manifest_errors + record_errors + payload_errors + planning_errors
    if manifest and same_version_hash_mismatch(vault_root, manifest, manifest_hash(pack_root)):
        errors.append("same pack id and version has different manifest_sha256 in deployed-pack-index.yaml")
    print_plan(pack_root, vault_root, manifest, records, payloads, errors)
    return 1 if errors or any(record.outcome == "fail" for record in records) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a capability pack deployment without writing Vault or runtime files.")
    parser.add_argument("pack_root", help="Capability pack directory containing manifest.yaml.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    args = parser.parse_args()
    return plan(
        Path(args.core_root).expanduser().resolve(),
        Path(args.vault_root).expanduser().resolve(),
        Path(args.pack_root).expanduser().resolve(),
    )


if __name__ == "__main__":
    sys.exit(main())
