#!/usr/bin/env python3
"""Report-only privacy validation for capability pack export/import transfer."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from foundry_config import ROOT
from plan_capability_pack import (
    plan_records,
    rel,
    validate_manifest,
    validate_payloads,
    validate_records,
)


TRANSFER_STATES = {"preview", "dry-run", "proposed", "accepted", "rejected", "blocked"}
PRIVATE_TEXT_RE = re.compile(
    r"(^~|/Users/|\.agent-foundry|\.codex|\.trae|secret|token|password|raw session|session transcript|"
    r"raw log|runtime/local|usage/local|sync/local|local receipt|runtime manifest|private vault|memory-system|"
    r"memory system)",
    re.IGNORECASE,
)
PRIVATE_PATH_RE = re.compile(
    r"(^|/)(runtime/local|usage/local|sync/local|memory|knowledge|research_memos|project_memory)(/|$)|"
    r"(^|/)(\.codex|\.trae|\.agent-foundry)(/|$)",
    re.IGNORECASE,
)
GENERATED_AUTHORITY_RE = re.compile(
    r"\b(generated adapter authority|runtime authority|canonical runtime|generated output is canonical|"
    r"runtime install is canonical|activate automatically|auto activate|execute on import)\b",
    re.IGNORECASE,
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def transfer_privacy_errors(pack_root: Path) -> list[str]:
    errors: list[str] = []
    for path in files_under(pack_root):
        relative = rel(path, pack_root)
        if PRIVATE_PATH_RE.search(relative):
            errors.append(f"{relative}: private/local path is not allowed in a capability pack transfer")
            continue
        try:
            text = read(path)
        except UnicodeDecodeError:
            errors.append(f"{relative}: binary or non-UTF-8 transfer payload requires separate review")
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if line.strip().startswith(("excluded_material:", "exclusions:", "forbidden_references:")):
                continue
            if PRIVATE_TEXT_RE.search(line):
                errors.append(f"{relative}:{line_no}: private/local reference is not exportable")
            if GENERATED_AUTHORITY_RE.search(line):
                errors.append(f"{relative}:{line_no}: generated/runtime output must not claim transfer authority")
    return errors


def transfer_state_errors(state: str) -> list[str]:
    if state not in TRANSFER_STATES:
        return [f"import_state must be one of {sorted(TRANSFER_STATES)}"]
    if state == "accepted":
        return ["accepted import state still requires reviewed apply handoff; this planner writes nothing"]
    return []


def export_policy_errors(manifest_text: str) -> list[str]:
    if "export_policy:" not in manifest_text:
        return ["export_policy is required before capability pack export/import transfer review"]
    if "review_required: true" not in manifest_text:
        return ["export_policy review_required must be true for transfer review"]
    if "private_vault_content: excluded" not in manifest_text:
        return ["integrity private_vault_content must be excluded"]
    return []


def report(
    *,
    action: str,
    import_state: str,
    pack_root: Path,
    vault_root: Path,
    manifest: dict[str, str],
    errors: list[str],
    diff_rows: list[str],
) -> None:
    print("Capability pack export/import transfer report")
    print(f"action: {action}")
    print(f"import_state: {import_state if action.startswith('import') else 'n/a'}")
    print(f"pack_root: {pack_root}")
    print(f"vault_root: {vault_root}")
    if manifest:
        print(f"pack_id: {manifest.get('pack_id', '')}")
        print(f"version: {manifest.get('version', '')}")
        print(f"review_state: {manifest.get('review_state', '')}")
    print("allowed_export_contents:")
    print("- manifest and reviewed metadata")
    print("- sanitized included records with checksums")
    print("- public Core references, examples, fixtures, and validation metadata")
    print("excluded_material:")
    print("- private Vault history, raw evidence, sessions, secrets, local paths")
    print("- runtime receipts, user settings, generated/runtime files as authority")
    print("- memory-system records or references")
    print("diff_before_write:")
    if diff_rows:
        for row in diff_rows:
            print(f"- {row}")
    else:
        print("- none")
    print("validation:")
    if errors:
        print("status: blocked")
        for error in errors:
            print(f"- {error}")
    else:
        print("status: review_required")
        print("- privacy review required before export sharing or import acceptance")
        print("- dry-run diff required before any selected Vault write")
    print("rollback:")
    print("- discard staged transfer material or revert the reviewed Vault change")
    print("- rebuild generated output from Core plus selected Vault after approved changes")
    print("handoff:")
    print("- route privacy/export review to human or Reviewer before sharing")
    print("- route accepted import material through existing practice/asset review gates")
    print("writes: none")


def plan_transfer(core_root: Path, vault_root: Path, pack_root: Path, action: str, import_state: str) -> int:
    manifest, manifest_errors, manifest_text = validate_manifest(core_root, vault_root, pack_root)
    records_raw, record_errors = validate_records(pack_root, manifest_text) if manifest_text else ([], [])
    payloads, payload_errors = validate_payloads(pack_root, manifest_text) if manifest_text else ([], [])
    records, planning_errors = plan_records(vault_root, pack_root, manifest, records_raw) if manifest else ([], [])
    errors = (
        manifest_errors
        + record_errors
        + payload_errors
        + planning_errors
        + transfer_privacy_errors(pack_root)
        + export_policy_errors(manifest_text)
    )
    if action.startswith("import"):
        errors.extend(transfer_state_errors(import_state))
    for payload in payloads:
        if payload.outcome == "blocked_executable_install":
            errors.append(f"executable_payload {payload.payload_id} cannot install or execute during transfer")
    diff_rows = [f"{record.item_id} {record.kind} {record.outcome}: {record.detail}" for record in records]
    report(
        action=action,
        import_state=import_state,
        pack_root=pack_root,
        vault_root=vault_root,
        manifest=manifest,
        errors=errors,
        diff_rows=diff_rows,
    )
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate capability pack export/import transfer without writes.")
    parser.add_argument("pack_root", help="Capability pack directory containing manifest.yaml.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument(
        "--action",
        choices=["export-preview", "import-preview", "import-dry-run"],
        default="import-preview",
        help="Report-only transfer action.",
    )
    parser.add_argument("--import-state", default="preview", help="Import state to validate for import actions.")
    args = parser.parse_args()
    return plan_transfer(
        Path(args.core_root).expanduser().resolve(),
        Path(args.vault_root).expanduser().resolve(),
        Path(args.pack_root).expanduser().resolve(),
        args.action,
        args.import_state,
    )


if __name__ == "__main__":
    sys.exit(main())
