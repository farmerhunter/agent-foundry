#!/usr/bin/env python3
"""Validate AF-5 capability pack manifest fixtures.

Dependency-free by design. This checks only the small YAML subset used by the
Core fixtures and never imports or executes declared payload sources.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from check_foundry_roots import validate as validate_roots


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "fixtures" / "capability-packs"
VAULT_FIXTURE_ROOT = ROOT / "fixtures" / "vaults"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_MANIFEST_FIELDS = {
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

REQUIRED_PAYLOAD_FIELDS = {
    "id",
    "title",
    "lifecycle_status",
    "path",
    "source_sha256",
    "interpreter",
    "execute_from_pack",
    "install_boundary",
    "permissions",
    "dependencies",
    "runtime_impact",
}

FORBIDDEN_PACK_TEXT = {
    "/Users/",
    "runtime/local",
    "usage/local",
    "sync/local",
    "gho_",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def top_level_scalars(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in text.splitlines():
        if raw.startswith(" ") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        value = value.strip()
        if value:
            data[key.strip()] = unquote(value)
    return data


def section_scalars(text: str, section: str) -> dict[str, str]:
    data: dict[str, str] = {}
    in_section = False
    for raw in text.splitlines():
        if raw == f"{section}:":
            in_section = True
            continue
        if in_section and raw and not raw.startswith(" "):
            break
        if in_section and raw.startswith("  ") and ":" in raw:
            key, value = raw.strip().split(":", 1)
            data[key] = unquote(value)
    return data


def list_entries(text: str, section: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_section = False
    saw_inline_empty = False

    for raw in text.splitlines():
        if raw.startswith(f"{section}:"):
            in_section = True
            saw_inline_empty = raw.split(":", 1)[1].strip() == "[]"
            continue
        if in_section and raw and not raw.startswith(" "):
            break
        if not in_section or saw_inline_empty:
            continue
        stripped = raw.strip()
        if raw.startswith("  - "):
            if current:
                entries.append(current)
            current = {}
            item = stripped[2:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = unquote(value)
            continue
        if current is not None and raw.startswith("    ") and not raw.startswith("      ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = unquote(value)

    if current:
        entries.append(current)
    return entries


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    text = read(path)
    rel_manifest = path.relative_to(ROOT)
    manifest = top_level_scalars(text)
    missing = sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    for field in missing:
        errors.append(f"{rel_manifest}: missing manifest field {field}")

    if manifest.get("distribution_type") not in {
        "mandatory_bootstrap",
        "optional_capability",
        "product_project_candidate",
    }:
        errors.append(f"{rel_manifest}: invalid distribution_type {manifest.get('distribution_type')}")
    if manifest.get("sensitivity") != "public":
        errors.append(f"{rel_manifest}: fixture pack sensitivity must be public")

    compatibility = section_scalars(text, "compatibility")
    for field in ["core_schema_version_min", "core_schema_version_max", "vault_layout_versions", "requires_bootstrap_pack"]:
        if field not in compatibility:
            errors.append(f"{rel_manifest}: compatibility missing {field}")
    if compatibility.get("vault_layout_versions") != "[1]":
        errors.append(f"{rel_manifest}: fixture must support Vault layout version [1]")

    conflict_policy = section_scalars(text, "conflict_policy")
    for field in [
        "id_collision",
        "same_version_hash_mismatch",
        "newer_version_update",
        "local_edit_behavior",
        "rollback_notes",
    ]:
        if field not in conflict_policy:
            errors.append(f"{rel_manifest}: conflict_policy missing {field}")
    if conflict_policy.get("id_collision") != "fail_closed":
        errors.append(f"{rel_manifest}: id_collision must fail closed")
    if conflict_policy.get("same_version_hash_mismatch") != "fail_closed":
        errors.append(f"{rel_manifest}: same-version hash mismatch must fail closed")

    integrity = section_scalars(text, "integrity")
    if integrity.get("digest_algorithm") != "sha256":
        errors.append(f"{rel_manifest}: integrity.digest_algorithm must be sha256")
    if integrity.get("private_vault_content") != "excluded":
        errors.append(f"{rel_manifest}: private_vault_content must be excluded")

    records = list_entries(text, "included_records")
    if not records:
        errors.append(f"{rel_manifest}: included_records must not be empty")
    seen_ids: set[str] = set()
    for entry in records:
        item_id = entry.get("id", "<unknown>")
        missing_record = sorted(REQUIRED_RECORD_FIELDS - entry.keys())
        for field in missing_record:
            errors.append(f"{rel_manifest}: included_record {item_id} missing {field}")
        if item_id in seen_ids:
            errors.append(f"{rel_manifest}: duplicate included_record id {item_id}")
        seen_ids.add(item_id)
        if entry.get("destination_layer") != "canonical_vault_record":
            errors.append(f"{rel_manifest}: {item_id} must target canonical_vault_record in MVP fixtures")
        digest = entry.get("content_sha256", "")
        if not SHA256_RE.match(digest):
            errors.append(f"{rel_manifest}: {item_id} has invalid content_sha256")
            continue
        item_path = path.parent / entry.get("path", "")
        if not item_path.exists():
            errors.append(f"{rel_manifest}: {item_id} path missing: {entry.get('path')}")
        else:
            if sha256(item_path) != digest:
                errors.append(f"{rel_manifest}: {item_id} content_sha256 mismatch")
            errors.extend(check_no_forbidden_fixture_text(rel_manifest, item_path))

    for payload in list_entries(text, "executable_payloads"):
        payload_id = payload.get("id", "<unknown>")
        missing_payload = sorted(REQUIRED_PAYLOAD_FIELDS - payload.keys())
        for field in missing_payload:
            errors.append(f"{rel_manifest}: executable_payload {payload_id} missing {field}")
        if payload.get("execute_from_pack") != "false":
            errors.append(f"{rel_manifest}: executable_payload {payload_id} must not execute from pack")
        if payload.get("install_boundary") not in {
            "managed_runtime_copy_required",
            "manual_import_only",
            "no_install",
        }:
            errors.append(f"{rel_manifest}: executable_payload {payload_id} has invalid install_boundary")
        digest = payload.get("source_sha256", "")
        if not SHA256_RE.match(digest):
            errors.append(f"{rel_manifest}: executable_payload {payload_id} has invalid source_sha256")
            continue
        payload_path = path.parent / payload.get("path", "")
        if not payload_path.exists():
            errors.append(f"{rel_manifest}: executable_payload {payload_id} path missing: {payload.get('path')}")
        else:
            if sha256(payload_path) != digest:
                errors.append(f"{rel_manifest}: executable_payload {payload_id} source_sha256 mismatch")
            errors.extend(check_no_forbidden_fixture_text(rel_manifest, payload_path))

    return errors


def check_no_forbidden_fixture_text(manifest_rel: Path, path: Path) -> list[str]:
    errors: list[str] = []
    text = read(path)
    rel_path = path.relative_to(ROOT)
    for marker in sorted(FORBIDDEN_PACK_TEXT):
        if marker in text:
            errors.append(f"{manifest_rel}: {rel_path} contains forbidden fixture text {marker}")
    return errors


def check_vault_fixtures() -> list[str]:
    errors: list[str] = []
    for name in ["blank", "bootstrap-only"]:
        vault_root = VAULT_FIXTURE_ROOT / name
        fixture_errors = validate_roots(ROOT, vault_root)
        errors.extend(f"fixtures/vaults/{name}: {error}" for error in fixture_errors)
    return errors


def main() -> int:
    errors: list[str] = []
    manifest_paths = sorted(PACK_ROOT.glob("*/manifest.yaml"))
    if not manifest_paths:
        errors.append("No capability pack manifest fixtures found")
    for manifest_path in manifest_paths:
        errors.extend(check_manifest(manifest_path))
    errors.extend(check_vault_fixtures())

    if errors:
        print("Capability pack fixture check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Capability pack fixture check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
