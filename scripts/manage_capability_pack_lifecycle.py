#!/usr/bin/env python3
"""Plan or apply safe lifecycle transitions for deployed capability packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from check_foundry_roots import validate
from deploy_capability_pack import parse_simple_yaml
from foundry_config import ROOT
from plan_capability_pack import scalar_texts, validate_deployed_pack_metadata


PRACTICE_RETIRE_STATUS = "archived"
ASSET_RETIRE_STATUS = "retired"
LIFECYCLE_STATES = {
    "candidate",
    "reviewed",
    "proposed",
    "active",
    "exportable",
    "deprecated",
    "retired",
    "archived",
    "blocked",
}
LEGACY_DEPLOYED_STATES = {"deployed", "disabled"}
WRITE_ACTIONS = {"activate", "disable", "retire"}
REVIEW_ONLY_ACTIONS = {"exportable", "deprecate", "split", "merge"}
REVIEW_ONLY_TARGET_LIFECYCLE = {
    "activate": "active",
    "exportable": "exportable",
    "deprecate": "deprecated",
}
REVIEW_ONLY_TRANSITION_OUTCOMES = {
    "split": "split",
    "merge": "merged",
}
LOCAL_PRIVATE_RE = re.compile(
    r"(^~|/Users/|\.agent-foundry|\.codex|\.trae|raw session|raw log|runtime manifest|"
    r"local receipt|secret|token)",
    re.IGNORECASE,
)
UNSAFE_CLAIM_RE = re.compile(
    r"\b(runtime authority|generated authority|canonical runtime|memory-system|memory system|"
    r"delete records|overwrite records|force merge|destructive)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PackRecord:
    item_id: str
    kind: str
    path: str


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    text: str
    pre_sha256: str = ""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def atomic_write_bytes(path: Path, value: bytes, mode: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.activation-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str, apply: bool) -> None:
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        path.write_text(text, encoding="utf-8")


def safe_vault_path(vault_root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute():
        raise SystemExit(f"Refusing absolute Vault record path: {relative}")
    target = (vault_root / rel).resolve()
    try:
        target.relative_to(vault_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Refusing Vault record path outside Vault: {relative}") from exc
    return target


def safe_backup_path(backup_root: Path, relative: str, bucket: str = "preimages") -> Path:
    artifact_root = (backup_root / bucket).resolve()
    target = (artifact_root / relative).resolve()
    try:
        target.relative_to(artifact_root)
    except ValueError as exc:
        raise RuntimeError(f"refusing backup path outside {bucket}: {relative}") from exc
    return target


def lifecycle_metadata_errors(pack: dict[object, object], pack_id: str) -> list[str]:
    errors = validate_deployed_pack_metadata(pack, pack_id)
    lifecycle_status = str(pack.get("lifecycle_status", ""))
    if lifecycle_status and lifecycle_status not in LIFECYCLE_STATES | LEGACY_DEPLOYED_STATES:
        errors.append(f"deployed pack {pack_id} lifecycle_status is unsupported: {lifecycle_status}")

    pack_records = pack.get("records", [])
    if isinstance(pack_records, list):
        for record in pack_records:
            if not isinstance(record, dict):
                continue
            item_id = str(record.get("id", "<unknown>"))
            if not record.get("deployed_sha256") and not record.get("imported_sha256"):
                errors.append(f"deployed pack {pack_id} record {item_id} missing deployed/imported hash")

    for section_name in [
        "lifecycle_policy",
        "lifecycle_transition",
        "transition_plan",
        "evidence_sources",
        "export_policy",
        "runtime_projection",
    ]:
        if section_name not in pack:
            continue
        section = pack.get(section_name)
        for text in scalar_texts(section):
            if LOCAL_PRIVATE_RE.search(text):
                errors.append(f"deployed pack {pack_id} {section_name} contains local-private reference: {text}")
            if UNSAFE_CLAIM_RE.search(text):
                errors.append(f"deployed pack {pack_id} {section_name} contains unsafe lifecycle claim: {text}")
    return errors


def pack_block_bounds(lines: list[str], pack_id: str) -> tuple[int, int]:
    start = -1
    for index, line in enumerate(lines):
        if line.startswith("  - pack_id:") and line.split(":", 1)[1].strip().strip('"') == pack_id:
            start = index
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("  - pack_id:"):
            end = index
            break
    return start, end


def deployed_pack_records(vault_root: Path, pack_id: str) -> tuple[list[PackRecord], list[str], int, int, list[str]]:
    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not metadata_path.exists():
        return [], [], -1, -1, []
    text = metadata_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        index = parse_simple_yaml(text)
    except ValueError as exc:
        return [], lines, -1, -1, [f"deployed-pack-index.yaml parse error: {exc}"]
    start, end = pack_block_bounds(lines, pack_id)
    if start == -1:
        return [], lines, -1, -1, []
    records: list[PackRecord] = []
    packs = index.get("deployed_packs", [])
    if not isinstance(packs, list):
        return [], lines, -1, -1, ["deployed-pack-index.yaml deployed_packs must be a list"]
    for pack in packs:
        if not isinstance(pack, dict) or pack.get("pack_id") != pack_id:
            continue
        metadata_errors = lifecycle_metadata_errors(pack, pack_id)
        if metadata_errors:
            return [], lines, start, end, metadata_errors
        pack_records = pack.get("records", [])
        if pack_records in ({}, None):
            return [], lines, start, end, []
        if not isinstance(pack_records, list):
            return [], lines, start, end, [f"deployed pack {pack_id} records must be a list"]
        for record in pack_records:
            if not isinstance(record, dict):
                return [], lines, start, end, [f"deployed pack {pack_id} contains non-mapping record metadata"]
            item_id = str(record.get("id", ""))
            if item_id:
                records.append(PackRecord(item_id, str(record.get("kind", "")), str(record.get("path", ""))))
        return records, lines, start, end, []
    return [], lines, -1, -1, []


def set_markdown_frontmatter_status(text: str, status: str) -> str:
    if not text.startswith("---\n"):
        raise SystemExit("Practice record missing frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise SystemExit("Practice record frontmatter is malformed")
    prefix = text[:end]
    suffix = text[end:]
    lines = prefix.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("status:"):
            lines[index] = f"status: {status}"
            return "\n".join(lines) + suffix
    raise SystemExit("Practice record frontmatter missing status")


def set_yaml_status(text: str, status: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("status:"):
            lines[index] = f"status: {status}"
            return "\n".join(lines).rstrip() + "\n"
    raise SystemExit("Asset record missing status")


def record_id(kind: str, text: str) -> str:
    if kind == "practice":
        if not text.startswith("---\n"):
            return ""
        end = text.find("\n---", 4)
        if end == -1:
            return ""
        for line in text[:end].splitlines():
            if line.startswith("id:"):
                return line.split(":", 1)[1].strip().strip('"')
        return ""
    if kind == "asset":
        for line in text.splitlines():
            if line.startswith("id:"):
                return line.split(":", 1)[1].strip().strip('"')
        return ""
    return ""


def record_status(kind: str, text: str) -> str:
    lines = text.splitlines()
    if kind == "practice":
        if not lines or lines[0] != "---":
            return ""
        lines = lines[1:]
        end = lines.index("---") if "---" in lines else len(lines)
        lines = lines[:end]
    for line in lines:
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def index_entry(text: str, item_id: str) -> dict[str, str]:
    entry: dict[str, str] = {}
    in_entry = False
    for line in text.splitlines():
        if line.startswith("  - id: "):
            if in_entry:
                break
            in_entry = line.split(":", 1)[1].strip().strip('"') == item_id
            if in_entry:
                entry["id"] = item_id
            continue
        if in_entry and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            entry[key] = value.strip().strip('"')
    return entry


def deployed_pack_metadata(vault_root: Path, pack_id: str) -> tuple[dict[object, object] | None, list[str]]:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not path.exists():
        return None, ["deployed-pack-index.yaml is missing"]
    try:
        data = parse_simple_yaml(read(path))
    except ValueError as exc:
        return None, [f"deployed-pack-index.yaml parse error: {exc}"]
    packs = data.get("deployed_packs", [])
    if not isinstance(packs, list):
        return None, ["deployed-pack-index.yaml deployed_packs must be a list"]
    matches = [pack for pack in packs if isinstance(pack, dict) and pack.get("pack_id") == pack_id]
    if len(matches) != 1:
        return None, [f"expected exactly one deployed pack {pack_id}, found {len(matches)}"]
    return matches[0], []


def index_entry_matches(text: str, item_id: str, relative_path: str) -> bool:
    lines = text.splitlines()
    in_entry = False
    found = False
    path_matches = False
    status_seen = False
    for line in lines:
        if line.startswith("  - id: "):
            in_entry = line.split(":", 1)[1].strip().strip('"') == item_id
            found = found or in_entry
            continue
        if not in_entry:
            continue
        if line.startswith("    path:"):
            path_matches = line.split(":", 1)[1].strip().strip('"') == relative_path
        if line.startswith("    status:"):
            status_seen = True
    return found and path_matches and status_seen


def set_index_status(text: str, item_id: str, status: str) -> str:
    lines = text.splitlines()
    in_entry = False
    found = False
    for index, line in enumerate(lines):
        if line.startswith("  - id: "):
            in_entry = line.split(":", 1)[1].strip().strip('"') == item_id
            found = found or in_entry
            continue
        if in_entry and line.startswith("    status:"):
            lines[index] = f"    status: {status}"
            return "\n".join(lines).rstrip() + "\n"
    if not found:
        raise SystemExit(f"Index entry not found for {item_id}")
    raise SystemExit(f"Index entry missing status for {item_id}")


def update_metadata(lines: list[str], start: int, end: int, action: str, state_by_id: dict[str, str]) -> str:
    updated = list(lines)
    current_record = ""
    for index in range(start, end):
        stripped = updated[index].strip()
        if updated[index].startswith("    lifecycle_status:"):
            updated[index] = f"    lifecycle_status: {action}d" if action == "disable" else "    lifecycle_status: retired"
            continue
        if updated[index].startswith("      - id:"):
            current_record = stripped.split(":", 1)[1].strip().strip('"')
            continue
        if current_record and updated[index].startswith("        current_state:") and current_record in state_by_id:
            updated[index] = f"        current_state: {state_by_id[current_record]}"
    return "\n".join(updated).rstrip() + "\n"


def update_activation_metadata(
    lines: list[str], start: int, end: int, post_sha_by_id: dict[str, str]
) -> str:
    updated = list(lines)
    current_record = ""
    for index in range(start, end):
        stripped = updated[index].strip()
        if updated[index].startswith("    lifecycle_status:"):
            updated[index] = "    lifecycle_status: active"
            continue
        if updated[index].startswith("      - id:"):
            current_record = stripped.split(":", 1)[1].strip().strip('"')
            continue
        if current_record and current_record in post_sha_by_id:
            if updated[index].startswith("        deployed_sha256:"):
                updated[index] = f"        deployed_sha256: {post_sha_by_id[current_record]}"
            elif updated[index].startswith("        current_state:"):
                updated[index] = "        current_state: active"
    return "\n".join(updated).rstrip() + "\n"


def activation_plan(
    vault_root: Path,
    pack_id: str,
) -> tuple[str, str, list[PlannedWrite], list[dict[str, str]], list[str]]:
    pack, errors = deployed_pack_metadata(vault_root, pack_id)
    if pack is None:
        return "", "", [], [], errors
    errors.extend(lifecycle_metadata_errors(pack, pack_id))
    version = str(pack.get("version", ""))
    if not version:
        errors.append(f"deployed pack {pack_id} has no version")
    if str(pack.get("lifecycle_status", "")) not in {"deployed", "proposed"}:
        errors.append(
            f"deployed pack {pack_id} must be deployed/proposed before activation, got {pack.get('lifecycle_status', '<missing>')}"
        )
    raw_records = pack.get("records", [])
    if not isinstance(raw_records, list) or not raw_records:
        errors.append(f"deployed pack {pack_id} has no activation members")
        raw_records = []

    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    metadata_text = read(metadata_path)
    metadata_lines = metadata_text.splitlines()
    start, end = pack_block_bounds(metadata_lines, pack_id)
    planned: list[PlannedWrite] = []
    members: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    index_texts: dict[Path, str] = {}
    index_preimages: dict[Path, str] = {}
    post_sha_by_id: dict[str, str] = {}

    for raw in raw_records:
        if not isinstance(raw, dict):
            errors.append(f"deployed pack {pack_id} contains non-mapping member")
            continue
        member = {key: str(raw.get(key, "")) for key in ("id", "kind", "path", "deployed_sha256")}
        item_id, kind, relative, expected_sha = (
            member["id"], member["kind"], member["path"], member["deployed_sha256"]
        )
        if not item_id or item_id in seen_ids:
            errors.append(f"deployed pack {pack_id} has missing/duplicate member id: {item_id or '<missing>'}")
            continue
        if not relative or relative in seen_paths:
            errors.append(f"deployed pack {pack_id} has missing/duplicate member path: {relative or '<missing>'}")
            continue
        seen_ids.add(item_id)
        seen_paths.add(relative)
        if kind not in {"practice", "asset"}:
            errors.append(f"{item_id}: unsupported activation member kind: {kind}")
            continue
        try:
            path = safe_vault_path(vault_root, relative)
        except SystemExit as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"{item_id}: record path missing: {relative}")
            continue
        text = read(path)
        actual_sha = sha256_text(text)
        if record_id(kind, text) != item_id:
            errors.append(f"{item_id}: record id/path binding mismatch: {relative}")
        if not expected_sha or actual_sha != expected_sha:
            errors.append(f"{item_id}: deployed record hash drift at {relative}")
        if record_status(kind, text) != "proposed":
            errors.append(f"{item_id}: activation requires record status proposed")
        index_path = vault_root / "indexes" / ("practice_index.yaml" if kind == "practice" else "asset_index.yaml")
        if not index_path.is_file():
            errors.append(f"{item_id}: index missing: {index_path.relative_to(vault_root)}")
            continue
        if index_path not in index_texts:
            index_texts[index_path] = read(index_path)
            index_preimages[index_path] = index_texts[index_path]
        index_text = index_texts[index_path]
        entry = index_entry(index_text, item_id)
        if entry.get("path") != relative or entry.get("status") != "proposed":
            errors.append(f"{item_id}: index path/status does not match proposed member")
        try:
            updated_record = (
                set_markdown_frontmatter_status(text, "active")
                if kind == "practice"
                else set_yaml_status(text, "active")
            )
        except SystemExit as exc:
            errors.append(f"{item_id}: {exc}")
            continue
        planned.append(PlannedWrite(path, updated_record, actual_sha))
        post_sha_by_id[item_id] = sha256_text(updated_record)
        index_texts[index_path] = set_index_status(index_text, item_id, "active")
        members.append({**member, "pre_sha256": actual_sha, "post_sha256": post_sha_by_id[item_id]})

    if errors:
        return version, "", [], sorted(members, key=lambda item: item["id"]), errors
    for index_path, updated in sorted(index_texts.items(), key=lambda item: str(item[0])):
        planned.append(PlannedWrite(index_path, updated, sha256_text(index_preimages[index_path])))
    planned.append(
        PlannedWrite(
            metadata_path,
            update_activation_metadata(metadata_lines, start, end, post_sha_by_id),
            sha256_text(metadata_text),
        )
    )
    planned = sorted(planned, key=lambda item: str(item.path.relative_to(vault_root)))
    token_payload = {
        "operation": "activate_capability_pack",
        "vault_root": str(vault_root.resolve()),
        "pack_id": pack_id,
        "version": version,
        "members": sorted(members, key=lambda item: item["id"]),
        "writes": [
            {
                "path": str(item.path.relative_to(vault_root)),
                "pre_sha256": item.pre_sha256,
                "post_sha256": sha256_text(item.text),
            }
            for item in planned
        ],
    }
    token = sha256_text(json.dumps(token_payload, sort_keys=True, separators=(",", ":")))
    return version, token, planned, sorted(members, key=lambda item: item["id"]), []


def retire_status(kind: str) -> tuple[str, str]:
    if kind == "practice":
        return PRACTICE_RETIRE_STATUS, "archived"
    if kind == "asset":
        return ASSET_RETIRE_STATUS, "retired"
    raise SystemExit(f"Unsupported pack record kind: {kind}")


def print_followup_guidance(action: str) -> None:
    print("governance: practice and asset lifecycle changes still require review-practices/review-assets approval")
    print("generated_followup: publish selected-Vault generated output only after reviewed Vault state changes")
    print("runtime_followup: run install dry-run and sync_status; runtime writes require explicit approval")
    print("rollback: keep selected Vault metadata canonical; revert reviewed metadata or restore from backup if an approved apply was wrong")
    print("defer: leave pack in blocked/proposed state, gather missing evidence, or route to needs:human for private/destructive decisions")
    if action in {"activate", "exportable"}:
        print("review_gate: human approval required; this command does not activate or mark exportable")
    if action in {"split", "merge"}:
        print("review_gate: split/merge requires before-after membership diff, conflict handling, rollback plan, and human approval")
    if action == "deprecate":
        print("review_gate: deprecation requires replacement or rationale and user-visible warning")


def report_review_only_action(records: list[PackRecord], action: str) -> int:
    if action in REVIEW_ONLY_TARGET_LIFECYCLE:
        print(f"target_lifecycle_status: {REVIEW_ONLY_TARGET_LIFECYCLE[action]}")
    else:
        print(f"transition_outcome: {REVIEW_ONLY_TRANSITION_OUTCOMES[action]}")
    print("status: review_required")
    print("records:")
    if not records:
        print("- none")
    for record in records:
        print(f"- {record.item_id} {record.kind}: {record.path}")
    print_followup_guidance(action)
    print("writes: none")
    return 1


def create_activation_backup(
    vault_root: Path, backup_root: Path, pack_id: str, version: str, token: str, planned: list[PlannedWrite]
) -> dict[str, object]:
    if backup_root.exists():
        raise RuntimeError(f"backup root must be fresh: {backup_root}")
    backup_root.mkdir(mode=0o700, parents=False)
    os.chmod(backup_root, 0o700)
    files: list[dict[str, str]] = []
    for item in planned:
        relative = item.path.relative_to(vault_root)
        current = item.path.read_bytes()
        if sha256_bytes(current) != item.pre_sha256:
            raise RuntimeError(f"preimage drift before backup: {relative}")
        backup = safe_backup_path(backup_root, str(relative))
        backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(backup.parent, 0o700)
        backup.write_bytes(current)
        os.chmod(backup, 0o600)
        postimage = safe_backup_path(backup_root, str(relative), "postimages")
        postimage.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(postimage.parent, 0o700)
        postimage.write_bytes(item.text.encode("utf-8"))
        os.chmod(postimage, 0o600)
        files.append(
            {
                "path": str(relative),
                "pre_sha256": item.pre_sha256,
                "post_sha256": sha256_text(item.text),
                "backup_sha256": sha256_bytes(backup.read_bytes()),
                "post_backup_sha256": sha256_bytes(postimage.read_bytes()),
            }
        )
    receipt: dict[str, object] = {
        "schema_version": 1,
        "operation": "activate_capability_pack",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vault_root": str(vault_root.resolve()),
        "pack_id": pack_id,
        "version": version,
        "review_token": token,
        "state": "prepared",
        "files": files,
    }
    receipt_path = backup_root / "activation-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    return receipt


def update_backup_receipt(backup_root: Path, receipt: dict[str, object], state: str) -> None:
    receipt["state"] = state
    receipt_path = backup_root / "activation-receipt.json"
    atomic_write_bytes(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"), 0o600)


def compensate_from_backup(
    vault_root: Path,
    backup_root: Path,
    receipt: dict[str, object],
    changed_paths: set[str] | None = None,
) -> None:
    files = receipt.get("files", [])
    if not isinstance(files, list):
        raise RuntimeError("backup receipt files are invalid")
    for entry in reversed(files):
        if not isinstance(entry, dict):
            raise RuntimeError("backup receipt contains invalid file entry")
        relative = str(entry.get("path", ""))
        if changed_paths is not None and relative not in changed_paths:
            continue
        target = safe_vault_path(vault_root, relative)
        backup = safe_backup_path(backup_root, relative)
        if not backup.is_file() or sha256_bytes(backup.read_bytes()) != str(entry.get("pre_sha256", "")):
            raise RuntimeError(f"backup preimage drift: {relative}")
        if changed_paths is not None and (
            not target.is_file() or sha256_bytes(target.read_bytes()) != str(entry.get("post_sha256", ""))
        ):
            raise RuntimeError(f"compensation target drift: {relative}")
        mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
        atomic_write_bytes(target, backup.read_bytes(), mode)
    for entry in files:
        if not isinstance(entry, dict):
            continue
        relative = str(entry.get("path", ""))
        if changed_paths is not None and relative not in changed_paths:
            continue
        target = safe_vault_path(vault_root, relative)
        if sha256_bytes(target.read_bytes()) != str(entry.get("pre_sha256", "")):
            raise RuntimeError(f"compensation readback failed: {entry.get('path', '')}")


def apply_activation(
    vault_root: Path,
    pack_id: str,
    review_token: str,
    backup_root: Path,
) -> int:
    version, actual_token, planned, members, errors = activation_plan(vault_root, pack_id)
    if errors:
        print("status: hold_prewrite")
        for error in errors:
            print(f"- {error}")
        print("writes: none")
        return 1
    if not review_token or review_token != actual_token:
        print("status: hold_review_token_drift")
        print(f"expected_review_token: {actual_token}")
        print("writes: none")
        return 1
    try:
        receipt = create_activation_backup(vault_root, backup_root, pack_id, version, actual_token, planned)
    except (OSError, RuntimeError) as exc:
        print("status: hold_backup_unavailable")
        print(f"- {exc}")
        print("writes: none")
        return 1
    try:
        changed_paths: set[str] = set()
        for item in planned:
            relative = str(item.path.relative_to(vault_root))
            if sha256_bytes(item.path.read_bytes()) != item.pre_sha256:
                raise RuntimeError(f"preimage drift immediately before write: {relative}")
            mode = item.path.stat().st_mode & 0o777
            atomic_write_bytes(item.path, item.text.encode("utf-8"), mode)
            changed_paths.add(relative)
        for item in planned:
            if sha256_bytes(item.path.read_bytes()) != sha256_text(item.text):
                raise RuntimeError(f"post-write readback mismatch: {item.path.relative_to(vault_root)}")
        update_backup_receipt(backup_root, receipt, "applied")
    except (OSError, RuntimeError) as exc:
        try:
            compensate_from_backup(vault_root, backup_root, receipt, changed_paths)
            update_backup_receipt(backup_root, receipt, "compensated")
            compensation = "complete"
        except (OSError, RuntimeError, SystemExit) as rollback_exc:
            try:
                update_backup_receipt(backup_root, receipt, "compensation_failed")
            except OSError:
                pass
            compensation = f"failed: {rollback_exc}"
        print("status: apply_failed")
        print(f"- {exc}")
        print(f"compensation: {compensation}")
        return 1
    print("status: activated")
    print(f"pack_id: {pack_id}")
    print(f"version: {version}")
    print(f"review_token: {actual_token}")
    print(f"members_activated: {len(members)}")
    print(f"backup_root: {backup_root}")
    print("changed_paths:")
    for item in planned:
        print(f"- {item.path.relative_to(vault_root)}")
    print("readback: passed")
    print("writes: applied")
    return 0


def restore_activation(core_root: Path, vault_root: Path, backup_root: Path, apply: bool) -> int:
    errors = validate(core_root, vault_root)
    receipt_path = backup_root / "activation-receipt.json"
    if errors or not receipt_path.is_file():
        print("status: hold_restore_preflight")
        for error in errors:
            print(f"- {error}")
        if not receipt_path.is_file():
            print(f"- activation receipt missing: {receipt_path}")
        print("writes: none")
        return 1
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print("status: hold_restore_preflight")
        print(f"- invalid activation receipt: {exc}")
        print("writes: none")
        return 1
    if not isinstance(receipt, dict) or receipt.get("vault_root") != str(vault_root.resolve()):
        print("status: hold_restore_preflight")
        print("- receipt selected Vault binding mismatch")
        print("writes: none")
        return 1
    files = receipt.get("files", [])
    preflight_errors: list[str] = []
    if receipt.get("state") != "applied" or not isinstance(files, list) or not files:
        preflight_errors.append("receipt is not an applied activation receipt")
        files = []
    for entry in files:
        if not isinstance(entry, dict):
            preflight_errors.append("receipt contains invalid file entry")
            continue
        try:
            target = safe_vault_path(vault_root, str(entry.get("path", "")))
        except SystemExit as exc:
            preflight_errors.append(str(exc))
            continue
        try:
            backup = safe_backup_path(backup_root, str(entry.get("path", "")))
            postimage = safe_backup_path(backup_root, str(entry.get("path", "")), "postimages")
        except RuntimeError as exc:
            preflight_errors.append(str(exc))
            continue
        if not target.is_file() or sha256_bytes(target.read_bytes()) != str(entry.get("post_sha256", "")):
            preflight_errors.append(f"current postimage drift: {entry.get('path', '')}")
        if not backup.is_file() or sha256_bytes(backup.read_bytes()) != str(entry.get("backup_sha256", "")):
            preflight_errors.append(f"backup preimage drift: {entry.get('path', '')}")
        if not postimage.is_file() or sha256_bytes(postimage.read_bytes()) != str(entry.get("post_backup_sha256", "")):
            preflight_errors.append(f"backup postimage drift: {entry.get('path', '')}")
    if preflight_errors:
        print("status: hold_restore_preflight")
        for error in preflight_errors:
            print(f"- {error}")
        print("writes: none")
        return 1
    print("status: restore_ready" if not apply else "status: restoring")
    print(f"backup_root: {backup_root}")
    print("restore_paths:")
    for entry in files:
        print(f"- {entry['path']}")
    if not apply:
        print("writes: none")
        return 0
    restored_paths: set[str] = set()
    try:
        for entry in reversed(files):
            relative = str(entry["path"])
            target = safe_vault_path(vault_root, relative)
            if sha256_bytes(target.read_bytes()) != str(entry["post_sha256"]):
                raise RuntimeError(f"current postimage drift immediately before restore: {relative}")
            preimage = safe_backup_path(backup_root, relative)
            mode = target.stat().st_mode & 0o777
            atomic_write_bytes(target, preimage.read_bytes(), mode)
            restored_paths.add(relative)
        for entry in files:
            target = safe_vault_path(vault_root, str(entry["path"]))
            if sha256_bytes(target.read_bytes()) != str(entry["pre_sha256"]):
                raise RuntimeError(f"restore readback failed: {entry['path']}")
        update_backup_receipt(backup_root, receipt, "restored")
    except (OSError, RuntimeError, SystemExit) as exc:
        compensation_errors: list[str] = []
        for entry in files:
            relative = str(entry.get("path", ""))
            if relative not in restored_paths:
                continue
            try:
                target = safe_vault_path(vault_root, relative)
                if sha256_bytes(target.read_bytes()) != str(entry.get("pre_sha256", "")):
                    raise RuntimeError(f"restore compensation target drift: {relative}")
                postimage = safe_backup_path(backup_root, relative, "postimages")
                mode = target.stat().st_mode & 0o777
                atomic_write_bytes(target, postimage.read_bytes(), mode)
            except (OSError, RuntimeError, SystemExit) as compensation_exc:
                compensation_errors.append(str(compensation_exc))
        state = "restore_compensation_failed" if compensation_errors else "restore_compensated"
        try:
            update_backup_receipt(backup_root, receipt, state)
        except OSError as receipt_exc:
            compensation_errors.append(str(receipt_exc))
        print("status: restore_failed")
        print(f"- {exc}")
        print(f"compensation: {'failed: ' + '; '.join(compensation_errors) if compensation_errors else 'complete'}")
        return 1
    print("status: restored")
    print("readback: passed")
    print("writes: applied")
    return 0


def plan_lifecycle_writes(
    vault_root: Path,
    records: list[PackRecord],
    metadata_lines: list[str],
    start: int,
    end: int,
    action: str,
) -> tuple[list[PlannedWrite], dict[str, str], list[str]]:
    writes: list[PlannedWrite] = []
    state_by_id: dict[str, str] = {}
    errors: list[str] = []
    for record in records:
        try:
            path = safe_vault_path(vault_root, record.path)
        except SystemExit as exc:
            errors.append(str(exc))
            continue
        if not path.exists():
            errors.append(f"{record.item_id}: record path missing: {record.path}")
            state_by_id[record.item_id] = "missing"
            continue
        text = read(path)
        actual_id = record_id(record.kind, text)
        if actual_id != record.item_id:
            errors.append(f"{record.item_id}: metadata path points to record id {actual_id or '<missing>'}: {record.path}")
            continue
        if action == "disable":
            state_by_id[record.item_id] = "unchanged"
            continue
        try:
            status, state = retire_status(record.kind)
        except SystemExit as exc:
            errors.append(str(exc))
            continue
        index_path = vault_root / "indexes" / ("practice_index.yaml" if record.kind == "practice" else "asset_index.yaml")
        if not index_path.exists():
            errors.append(f"{record.item_id}: index missing: {index_path.relative_to(vault_root)}")
            continue
        index_text = read(index_path)
        if not index_entry_matches(index_text, record.item_id, record.path):
            errors.append(f"{record.item_id}: index entry missing or path mismatch for {record.path}")
            continue
        try:
            updated_record = (
                set_markdown_frontmatter_status(text, status)
                if record.kind == "practice"
                else set_yaml_status(text, status)
            )
            updated_index = set_index_status(index_text, record.item_id, status)
        except SystemExit as exc:
            errors.append(f"{record.item_id}: {exc}")
            continue
        if updated_record != text:
            writes.append(PlannedWrite(path, updated_record))
        if updated_index != index_text:
            writes.append(PlannedWrite(index_path, updated_index))
        state_by_id[record.item_id] = state

    updated_metadata = update_metadata(metadata_lines, start, end, action, state_by_id)
    if updated_metadata != "\n".join(metadata_lines).rstrip() + "\n":
        writes.append(PlannedWrite(vault_root / "packs" / "deployed-pack-index.yaml", updated_metadata))
    return writes, state_by_id, errors


def lifecycle(
    core_root: Path,
    vault_root: Path,
    pack_id: str,
    action: str,
    apply: bool,
    review_token: str = "",
    backup_root: Path | None = None,
) -> int:
    errors = validate(core_root, vault_root)
    if errors:
        print("Pack lifecycle refused:")
        for error in errors:
            print(f"- {error}")
        print("writes: none")
        return 1

    records, metadata_lines, start, end, metadata_errors = deployed_pack_records(vault_root, pack_id)
    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    print("Capability pack lifecycle report")
    print(f"pack_id: {pack_id}")
    print(f"action: {action}")
    print(f"vault_root: {vault_root}")
    print(f"metadata: {metadata_path}")
    if metadata_errors:
        print("status: failed")
        for error in metadata_errors:
            print(f"- {error}")
        print_followup_guidance(action)
        print("writes: none")
        return 1
    if start == -1:
        print("status: not_deployed")
        print("writes: none")
        return 1
    if action == "activate":
        version, token, planned, members, activation_errors = activation_plan(vault_root, pack_id)
        if activation_errors:
            print("status: hold_prewrite")
            for error in activation_errors:
                print(f"- {error}")
            print("writes: none")
            return 1
        if apply:
            if backup_root is None:
                print("status: hold_backup_required")
                print("- --backup-root is required for activation apply")
                print("writes: none")
                return 1
            return apply_activation(vault_root, pack_id, review_token, backup_root)
        print("status: ready_for_review")
        print(f"version: {version}")
        print("members:")
        for member in members:
            print(f"- {member['id']} {member['kind']}: {member['path']}")
        print("changed_paths:")
        for item in planned:
            print(f"- {item.path.relative_to(vault_root)}")
        print(f"review_token: {token}")
        print("approval_boundary: review_token binds current bytes but does not authorize activation")
        print("generated_followup: none")
        print("runtime_followup: none")
        print("writes: none")
        return 0
    if action in REVIEW_ONLY_ACTIONS:
        if apply:
            print("status: failed")
            print(f"- {action} is review-only in #175 and cannot be applied")
            print_followup_guidance(action)
            print("writes: none")
            return 1
        return report_review_only_action(records, action)
    print("records:")
    if not records:
        print("- none")

    for record in records:
        path = safe_vault_path(vault_root, record.path)
        if not path.exists():
            print(f"- {record.item_id} missing: {record.path}")
            continue
        if action == "disable":
            print(f"- {record.item_id} metadata_only: {record.path}")
            continue
        status, state = retire_status(record.kind)
        print(f"- {record.item_id} {record.kind} -> {status}: {record.path}")

    planned_writes, _state_by_id, planning_errors = plan_lifecycle_writes(
        vault_root, records, metadata_lines, start, end, action
    )
    if planning_errors:
        print("status: failed")
        for error in planning_errors:
            print(f"- {error}")
        print_followup_guidance(action)
        print("writes: none")
        return 1
    for planned in planned_writes:
        write(planned.path, planned.text, apply)
    print_followup_guidance(action)
    print("runtime_cleanup: use selected generated-output refresh and managed runtime receipt rollback; ChatGPT remains manual")
    print("restore: rebuild from public Core plus selected Vault; do not copy another machine's runtime files")
    print(f"writes: {'applied' if apply else 'none'}")
    if not apply:
        print("Dry-run only. Re-run with --apply to write Vault metadata or lifecycle states.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply safe deployed capability pack lifecycle transitions.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument("--pack-id", default="", help="Deployed capability pack id.")
    parser.add_argument("--action", choices=sorted(WRITE_ACTIONS | REVIEW_ONLY_ACTIONS), default="")
    parser.add_argument("--apply", action="store_true", help="Write lifecycle changes. Default is dry-run.")
    parser.add_argument("--review-token", default="", help="Exact token printed by a reviewed activation dry-run.")
    parser.add_argument("--backup-root", default="", help="Fresh private backup root required for activation apply.")
    parser.add_argument("--restore-backup", default="", help="Activation backup root to validate or restore.")
    args = parser.parse_args()
    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    if args.restore_backup:
        if args.action or args.pack_id or args.review_token or args.backup_root:
            parser.error("--restore-backup cannot be combined with lifecycle action arguments")
        return restore_activation(core_root, vault_root, Path(args.restore_backup).expanduser().resolve(), args.apply)
    if not args.action or not args.pack_id:
        parser.error("--action and --pack-id are required unless --restore-backup is used")
    return lifecycle(
        core_root,
        vault_root,
        args.pack_id,
        args.action,
        args.apply,
        args.review_token,
        Path(args.backup_root).expanduser().resolve() if args.backup_root else None,
    )


if __name__ == "__main__":
    sys.exit(main())
