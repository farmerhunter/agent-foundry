#!/usr/bin/env python3
"""Stage explicit runtime/source files as reviewed import evidence."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from operation_context import (
    CONTEXT_CORE,
    CONTEXT_GENERATED,
    CONTEXT_VAULT,
    build_context,
    classify_context,
    configured_roots,
    is_relative_to,
    text_report,
)


RUNTIMES = {"codex", "claude-code", "hermes", "chatgpt", "prompts", "helper-files", "other"}
ROUTES = {
    "practice_candidate",
    "asset_candidate",
    "pack_candidate",
    "project_local_decision",
    "design_note",
    "discard",
    "future_work",
}
OUTCOMES = {
    "discard",
    "reference_only",
    "defer",
    "merge_into_existing",
    "propose_practice",
    "propose_asset",
}
POST_APPROVAL_ACTIONS = {"publish_adapters", "runtime_followup", "manual_re_review"}
TEXT_EXTENSIONS = {
    ".cfg",
    ".cjs",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".prompt",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SCRIPT_EXTENSIONS = {".cjs", ".js", ".jsx", ".mjs", ".py", ".sh", ".ts", ".tsx"}
DEFAULT_MAX_BYTES = 200_000


@dataclass
class SourceRecord:
    path: Path
    source_context: str
    status: str
    routing: str
    reason: str
    text: str
    size_bytes: int
    sha256: str
    has_script_surface: bool
    has_network_surface: bool
    has_file_write_surface: bool
    has_credential_surface: bool
    has_install_surface: bool
    has_permission_change_surface: bool
    has_destructive_surface: bool
    has_prompt_injection_surface: bool


def yaml_scalar(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "runtime-import"


def fence_for(text: str) -> str:
    longest = 2
    for match in re.finditer(r"`+", text):
        longest = max(longest, len(match.group(0)))
    return "`" * (longest + 1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def looks_like_script(path: Path, text: str) -> bool:
    if path.suffix.lower() in SCRIPT_EXTENSIONS:
        return True
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return first_line.startswith("#!")


def contains_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def risk_flags(path: Path, text: str) -> dict[str, bool]:
    has_script_surface = looks_like_script(path, text)
    return {
        "has_script_surface": has_script_surface,
        "has_network_surface": contains_any(
            [
                r"\b(curl|wget)\b",
                r"\b(requests|fetch)\s*[.(]",
                r"https?://",
                r"\bgh\s+api\b",
            ],
            text,
        ),
        "has_file_write_surface": contains_any(
            [
                r">\s*[^&]",
                r"\b(write_text|write_bytes)\s*\(",
                r"\bopen\s*\([^,\n]+,\s*['\"]w",
                r"\btouch\s+",
            ],
            text,
        ),
        "has_credential_surface": contains_any(
            [
                r"\b(token|credential|api[_-]?key|secret|password)\b",
                r"\b[A-Z0-9_]*(TOKEN|SECRET|PASSWORD|KEY)\b",
            ],
            text,
        ),
        "has_install_surface": contains_any(
            [
                r"\b(pip|npm|pnpm|yarn|brew|uv)\s+(install|sync|add)\b",
                r"\binstaller?\b",
            ],
            text,
        ),
        "has_permission_change_surface": contains_any([r"\bchmod\b", r"\bchown\b"], text),
        "has_destructive_surface": contains_any(
            [
                r"\brm\s+-rf\b",
                r"\bgit\s+reset\s+--hard\b",
                r"\bdelete\s+all\b",
                r"\bdrop\s+database\b",
            ],
            text,
        ),
        "has_prompt_injection_surface": contains_any(
            [
                r"ignore (all )?(previous|prior|above) instructions",
                r"disregard (all )?(previous|prior|above) instructions",
                r"reveal (the )?(system|developer) prompt",
                r"exfiltrate",
            ],
            text,
        ),
    }


def infer_routing(path: Path, runtime: str, has_script_surface: bool, rejected: bool) -> str:
    if rejected:
        return "discard"
    name = path.name.lower()
    suffix = path.suffix.lower()
    if has_script_surface:
        return "asset_candidate"
    if name in {"skill.md", "agents.md", "claude.md"}:
        return "practice_candidate"
    if "prompt" in name or runtime in {"chatgpt", "prompts"}:
        return "pack_candidate"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "design_note"
    return "asset_candidate"


def collect_sources(paths: list[Path], recursive: bool) -> list[Path]:
    sources: list[Path] = []
    seen: set[Path] = set()
    for source in paths:
        source = source.expanduser().resolve()
        if source.is_file():
            candidates = [source]
        elif source.is_dir():
            iterator = source.rglob("*") if recursive else source.iterdir()
            candidates = [path.resolve() for path in iterator if path.is_file() and not path.name.startswith(".")]
        else:
            candidates = [source]
        for candidate in sorted(candidates):
            if candidate not in seen:
                seen.add(candidate)
                sources.append(candidate)
    return sources


def read_source(
    path: Path,
    core_root: Path,
    vault_root: Path,
    adapter_root: Path,
    max_bytes: int,
    source_runtime: str,
    routing_override: str,
) -> SourceRecord:
    source_context = classify_context(path.parent if path.is_file() else path, core_root, vault_root, adapter_root)
    if source_context in {CONTEXT_CORE, CONTEXT_VAULT, CONTEXT_GENERATED}:
        return SourceRecord(
            path=path,
            source_context=source_context,
            status="rejected",
            routing="discard",
            reason=f"source context {source_context} is not a runtime or evidence input",
            text="",
            size_bytes=0,
            sha256="",
            has_script_surface=False,
            has_network_surface=False,
            has_file_write_surface=False,
            has_credential_surface=False,
            has_install_surface=False,
            has_permission_change_surface=False,
            has_destructive_surface=False,
            has_prompt_injection_surface=False,
        )
    if not path.exists() or not path.is_file():
        return SourceRecord(
            path=path,
            source_context=source_context,
            status="rejected",
            routing="discard",
            reason="source file does not exist or is not a file",
            text="",
            size_bytes=0,
            sha256="",
            has_script_surface=False,
            has_network_surface=False,
            has_file_write_surface=False,
            has_credential_surface=False,
            has_install_surface=False,
            has_permission_change_surface=False,
            has_destructive_surface=False,
            has_prompt_injection_surface=False,
        )

    data = path.read_bytes()
    digest = sha256_bytes(data)
    if len(data) > max_bytes:
        return SourceRecord(
            path=path,
            source_context=source_context,
            status="rejected",
            routing="discard",
            reason=f"source file exceeds max_bytes={max_bytes}",
            text="",
            size_bytes=len(data),
            sha256=digest,
            has_script_surface=path.suffix.lower() in SCRIPT_EXTENSIONS,
            has_network_surface=False,
            has_file_write_surface=False,
            has_credential_surface=False,
            has_install_surface=False,
            has_permission_change_surface=False,
            has_destructive_surface=False,
            has_prompt_injection_surface=False,
        )
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return SourceRecord(
            path=path,
            source_context=source_context,
            status="rejected",
            routing="discard",
            reason=f"unsupported text extension: {path.suffix or '<none>'}",
            text="",
            size_bytes=len(data),
            sha256=digest,
            has_script_surface=False,
            has_network_surface=False,
            has_file_write_surface=False,
            has_credential_surface=False,
            has_install_surface=False,
            has_permission_change_surface=False,
            has_destructive_surface=False,
            has_prompt_injection_surface=False,
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return SourceRecord(
            path=path,
            source_context=source_context,
            status="rejected",
            routing="discard",
            reason="source file is not valid UTF-8 text",
            text="",
            size_bytes=len(data),
            sha256=digest,
            has_script_surface=False,
            has_network_surface=False,
            has_file_write_surface=False,
            has_credential_surface=False,
            has_install_surface=False,
            has_permission_change_surface=False,
            has_destructive_surface=False,
            has_prompt_injection_surface=False,
        )

    flags = risk_flags(path, text)
    routing = routing_override or infer_routing(path, source_runtime, flags["has_script_surface"], rejected=False)
    return SourceRecord(
        path=path,
        source_context=source_context,
        status="candidate",
        routing=routing,
        reason="explicit source path staged for human review",
        text=text,
        size_bytes=len(data),
        sha256=digest,
        has_script_surface=flags["has_script_surface"],
        has_network_surface=flags["has_network_surface"],
        has_file_write_surface=flags["has_file_write_surface"],
        has_credential_surface=flags["has_credential_surface"],
        has_install_surface=flags["has_install_surface"],
        has_permission_change_surface=flags["has_permission_change_surface"],
        has_destructive_surface=flags["has_destructive_surface"],
        has_prompt_injection_surface=flags["has_prompt_injection_surface"],
    )


def render_record(
    record: SourceRecord,
    source_runtime: str,
    sensitivity: str,
    license_status: str,
    retrieved_at: str,
    import_outcome: str,
    post_approval_actions: list[str],
) -> str:
    action_lines = ["post_approval_actions: []"]
    if post_approval_actions:
        action_lines = ["post_approval_actions:"]
        action_lines.extend(f"  - {action}" for action in post_approval_actions)
    lines = [
        "---",
        "schema_version: 1",
        "record_type: runtime_import_evidence",
        f"status: {record.status}",
        f"import_outcome: {import_outcome}",
        *action_lines,
        f"source_runtime: {source_runtime}",
        f"source_context: {record.source_context}",
        f"source_path: {yaml_scalar(record.path)}",
        f"source_sha256: {yaml_scalar(record.sha256)}",
        f"source_size_bytes: {record.size_bytes}",
        f"retrieved_at: {retrieved_at}",
        f"license_status: {yaml_scalar(license_status)}",
        f"sensitivity: {yaml_scalar(sensitivity)}",
        "review_required: true",
        f"routing_recommendation: {record.routing}",
        f"has_script_surface: {'true' if record.has_script_surface else 'false'}",
        "risk_flags:",
        f"  scripts_present: {'true' if record.has_script_surface else 'false'}",
        f"  network_access: {'true' if record.has_network_surface else 'false'}",
        f"  file_writes: {'true' if record.has_file_write_surface else 'false'}",
        f"  credential_access: {'true' if record.has_credential_surface else 'false'}",
        f"  install_steps: {'true' if record.has_install_surface else 'false'}",
        f"  permission_changes: {'true' if record.has_permission_change_surface else 'false'}",
        f"  destructive_actions: {'true' if record.has_destructive_surface else 'false'}",
        f"  prompt_injection_concerns: {'true' if record.has_prompt_injection_surface else 'false'}",
        "runtime_source_preserved: true",
        "activation_performed: false",
        "runtime_write_performed: false",
        "---",
        "",
        "# Runtime Import Evidence",
        "",
        "## Provenance",
        "",
        f"- Source runtime: `{source_runtime}`",
        f"- Source path: `{record.path}`",
        f"- Source context: `{record.source_context}`",
        f"- Source SHA-256: `{record.sha256}`",
        f"- Retrieved at: `{retrieved_at}`",
        "",
        "## Review Routing",
        "",
        f"- Status: `{record.status}`",
        f"- Recommendation: `{record.routing}`",
        f"- Reason: {record.reason}",
        f"- Sensitivity: `{sensitivity}`",
        f"- License: `{license_status}`",
        f"- Script or executable surface present: `{'yes' if record.has_script_surface else 'no'}`",
        "",
        "## Risk Flags",
        "",
        f"- Network access: `{'yes' if record.has_network_surface else 'no'}`",
        f"- File writes: `{'yes' if record.has_file_write_surface else 'no'}`",
        f"- Credential access: `{'yes' if record.has_credential_surface else 'no'}`",
        f"- Install steps: `{'yes' if record.has_install_surface else 'no'}`",
        f"- Permission changes: `{'yes' if record.has_permission_change_surface else 'no'}`",
        f"- Destructive actions: `{'yes' if record.has_destructive_surface else 'no'}`",
        f"- Prompt injection concerns: `{'yes' if record.has_prompt_injection_surface else 'no'}`",
        "",
        "## Safety Notes",
        "",
        "- Imported content is review evidence only.",
        "- Do not execute bundled scripts or helper files during review.",
        "- Do not activate, publish, or install this content without human approval.",
        "- Preserve the native runtime/source file.",
    ]
    if record.text:
        fence = fence_for(record.text)
        lines.extend(["", "## Source Snapshot", "", fence, record.text.rstrip("\n"), fence])
    else:
        lines.extend(["", "## Source Snapshot", "", f"Content omitted: {record.reason}"])
    return "\n".join(lines) + "\n"


def plan_records(
    args: argparse.Namespace,
    core_root: Path,
    vault_root: Path,
    adapter_root: Path,
) -> tuple[Path, list[tuple[SourceRecord, Path, str]]]:
    staging_root = (vault_root / "imports" / "inbox").resolve()
    if not is_relative_to(staging_root, vault_root / "imports" / "inbox"):
        raise SystemExit(f"Refusing staging root outside Vault imports/inbox: {staging_root}")

    explicit_paths = [Path(path) for path in args.source]
    sources = collect_sources(explicit_paths, args.recursive)
    if not sources:
        raise SystemExit("No source files found from explicit source paths.")
    if len(sources) > args.max_files:
        raise SystemExit(f"Refusing to stage {len(sources)} files; pass a narrower path or raise --max-files.")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[tuple[SourceRecord, Path, str]] = []
    used_names: set[str] = set()
    for source in sources:
        record = read_source(
            source,
            core_root,
            vault_root,
            adapter_root,
            args.max_bytes,
            args.source_runtime,
            args.routing or "",
        )
        slug = slugify(f"{args.source_runtime}-{source.stem}-{record.sha256[:10] or record.status}")
        name = f"runtime-import-{now[:10]}-{slug}.md"
        counter = 2
        while name in used_names:
            name = f"runtime-import-{now[:10]}-{slug}-{counter}.md"
            counter += 1
        used_names.add(name)
        content = render_record(
            record,
            args.source_runtime,
            args.sensitivity,
            args.license,
            now,
            args.outcome,
            args.post_approval_action or [],
        )
        records.append((record, staging_root / name, content))
    return staging_root, records


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage explicit runtime/source paths as import evidence.")
    parser.add_argument("--source", action="append", required=True, help="Explicit runtime/source file or directory.")
    parser.add_argument("--source-runtime", required=True, choices=sorted(RUNTIMES), help="Runtime or source family.")
    parser.add_argument("--routing", choices=sorted(ROUTES), default="", help="Override routing recommendation.")
    parser.add_argument("--outcome", choices=sorted(OUTCOMES), default="reference_only", help="Import review outcome recorded in staged evidence.")
    parser.add_argument(
        "--post-approval-action",
        action="append",
        choices=sorted(POST_APPROVAL_ACTIONS),
        default=[],
        help="Report-only post-approval action. Does not authorize writes during import review.",
    )
    parser.add_argument("--sensitivity", default="unknown-review-required", help="Sensitivity review status.")
    parser.add_argument("--license", default="unknown-review-required", help="License review status.")
    parser.add_argument("--core-root", default="", help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", default="", help="Selected Vault root. Writes go to imports/inbox only.")
    parser.add_argument("--adapter-root", default="", help="Generated adapter output root.")
    parser.add_argument("--recursive", action="store_true", help="Read files recursively under explicit directories.")
    parser.add_argument("--max-files", type=int, default=20, help="Maximum source files to stage.")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum bytes copied per source file.")
    parser.add_argument("--apply", action="store_true", help="Write staged records. Default is dry-run.")
    parser.add_argument("--quiet-context", action="store_true", help="Do not print operation context report.")
    return parser


def main() -> int:
    args = parser().parse_args()
    core_root, vault_root = configured_roots(args.core_root, args.vault_root)
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else core_root / "adapters"
    context = build_context("import", Path.cwd(), core_root, vault_root, adapter_root)
    if not args.quiet_context:
        print(text_report(context))
    if context["root_validation"] != "passed":
        print("Refusing import staging because Core/Vault root validation failed.", file=sys.stderr)
        return 1

    staging_root, records = plan_records(args, core_root, vault_root, adapter_root)
    print(f"{'write' if args.apply else 'would write'} staging root: {staging_root}")
    for record, output_path, content in records:
        print(f"{'write' if args.apply else 'would write'}: {output_path}")
        print(f"  source: {record.path}")
        print(f"  status: {record.status}")
        print(f"  routing: {record.routing}")
        print(f"  reason: {record.reason}")
        if args.apply:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
    if not args.apply:
        print("Dry-run only. Re-run with --apply to stage records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
