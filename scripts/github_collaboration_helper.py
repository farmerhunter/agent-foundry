#!/usr/bin/env python3
"""Read-only and dry-run GitHub collaboration helper pilot.

This AF11 Unit B helper is intentionally bounded: it may read GitHub state and
draft handoff text, but it must not mutate GitHub, Project v2, runtime, Vault,
generated output, private state, or memory-system records.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


FORBIDDEN_ACTIONS = {
    "agent-comment",
    "agent-label",
    "comment",
    "label",
    "project-write",
    "merge",
    "close",
    "dispatch",
    "runtime-install",
    "adapter-publish",
    "vault-write",
    "memory-write",
}
READ_ONLY_ACTIONS = {
    "repo-resolve",
    "auth-smoke",
    "role-config-check",
    "inbox",
    "issue-context",
    "scheduler-audit",
    "activation-report",
}
DRY_RUN_ACTIONS = {
    "handoff-draft",
    "dispatch-evidence-draft",
    "release-next-draft",
    "permission-smoke",
    "comparison-draft",
}
REMOTE_RE = re.compile(r"(?:github\.com[:/])([^/]+)/([^/.]+)(?:\.git)?$")
CONTRACT_HEADINGS = ("Final Execution Contract", "Execution Contract", "Draft Execution Contract")
ROLE_FIELDS = ("Owner role", "Review role", "Acceptance role")
VALID_ROLE_VALUES = {"none", "implementer", "reviewer", "architect"}
VALID_COMPLETION_HANDOFFS = {
    "none",
    "to:implementer",
    "to:reviewer",
    "to:architect",
    "to:human",
    "batch checkpoint",
}


def fail(code: str, detail: str, exit_code: int = 2) -> None:
    print(f"{code}: {detail}", file=sys.stderr)
    raise SystemExit(exit_code)


def load_json(path: str | None) -> Any | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_gh(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        if "authentication" in output.lower() or "not logged" in output.lower():
            fail("auth_unavailable", output, 3)
        if "not found" in output.lower() or "permission" in output.lower():
            fail("permission_denied", output, 4)
        fail("github_read_failed", output or "gh command failed", 5)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout


def run_gh_read(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = (result.stderr or result.stdout).strip()
    if result.returncode != 0:
        lower = output.lower()
        if "authentication" in lower or "not logged" in lower:
            return {"ok": False, "error_type": "auth_unavailable", "message": output}
        if "not found" in lower or "permission" in lower:
            return {"ok": False, "error_type": "permission_denied", "message": output}
        if any(marker in lower for marker in ("eof", "499", "tls", "timeout", "rate limit", "temporarily")):
            return {"ok": False, "error_type": "transient", "message": output}
        return {"ok": False, "error_type": "github_read_failed", "message": output or "gh command failed"}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = result.stdout
    return {"ok": True, "data": data}


def default_core_root() -> Path:
    return Path(__file__).resolve().parents[1]


def path_status(path: Path, required_text: list[str] | None = None) -> dict[str, Any]:
    exists = path.exists()
    payload: dict[str, Any] = {"path": str(path), "exists": exists}
    if not exists or required_text is None:
        return payload
    text = path.read_text(encoding="utf-8")
    payload["required_text_present"] = {item: item in text for item in required_text}
    payload["ok"] = all(payload["required_text_present"].values())
    return payload


def repo_from_remote(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    match = REMOTE_RE.search(result.stdout.strip())
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def resolve_repo(args: argparse.Namespace) -> tuple[str, str]:
    if args.repo:
        return args.repo, "explicit_owner_repo_argument"
    env_repo = os.environ.get("AGENT_REPO")
    if env_repo:
        return env_repo, "AGENT_REPO"
    remote_repo = repo_from_remote(Path.cwd())
    if remote_repo:
        return remote_repo, "current_git_remote_after_confirmation"
    fail("repo_unresolved", "pass --repo <owner>/<repo>, set AGENT_REPO, or run inside a GitHub checkout")


def yaml_list(text: str, key: str, indent: int = 0) -> list[str]:
    prefix = " " * indent
    inline = re.search(rf"^{prefix}{re.escape(key)}:\s*\\[(.*?)\\]\s*$", text, re.MULTILINE)
    if inline:
        return [item.strip().strip('"') for item in inline.group(1).split(",") if item.strip()]
    match = re.search(rf"^{prefix}{re.escape(key)}:\n((?:{prefix}  - .+\n)+)", text, re.MULTILINE)
    if not match:
        return []
    return [line.strip()[2:].strip('"') for line in match.group(1).splitlines()]


def block(text: str, key: str, indent: int = 0) -> str:
    prefix = " " * indent
    match = re.search(rf"^{prefix}{re.escape(key)}:\n(?P<body>(?:{prefix}  .+\n?)*)", text, re.MULTILINE)
    return match.group("body") if match else ""


def scalar_in_block(block_text: str, key: str) -> str | None:
    match = re.search(rf"^\s+{re.escape(key)}:\s*(.+?)\s*$", block_text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"')


def extract_execution_contract(body: str) -> tuple[str | None, str]:
    sections: list[tuple[str, str]] = []
    pattern = re.compile(
        r"^##\s+(Final Execution Contract|Execution Contract|Draft Execution Contract)\s*$"
        r"(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(body or ""):
        sections.append((match.group(1), match.group("body")))
    if not sections:
        return None, ""
    for preferred in CONTRACT_HEADINGS:
        for heading, text in reversed(sections):
            if heading == preferred:
                return heading, text
    return sections[-1]


def markdown_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def contract_error(field: str, code: str, message: str, expected: Any = None, actual: Any = None, hint: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"field": field, "code": code, "message": message}
    if expected is not None:
        payload["expected"] = expected
    if actual is not None:
        payload["actual"] = actual
    if hint:
        payload["hint"] = hint
    return payload


def validate_execution_contract(body: str) -> dict[str, Any]:
    heading, contract = extract_execution_contract(body)
    if not heading:
        return {"status": "missing", "heading": None, "fields": {}, "errors": []}
    fields = {field: markdown_field(contract, field) for field in (*ROLE_FIELDS, "Completion handoff")}
    reviewer_target = markdown_field(contract, "Reviewer target")
    human_prompt = markdown_field(contract, "Human review prompt")
    human_verification = markdown_field(contract, "Human verification needed")
    errors: list[dict[str, Any]] = []

    for field in ("Owner role", "Completion handoff"):
        if not fields.get(field):
            errors.append(
                contract_error(
                    field,
                    "missing_contract_field",
                    f"{field} is required for pickup-ready Execution Contracts.",
                    actual=None,
                )
            )
    if reviewer_target and not fields.get("Review role"):
        errors.append(
            contract_error(
                "Review role",
                "missing_contract_field",
                "Reviewer target is present but Review role is missing.",
                expected=sorted(VALID_ROLE_VALUES),
                actual=None,
                hint="Use `Review role: reviewer` and keep natural-language reviewer details in `Reviewer target:`.",
            )
        )

    for field in ROLE_FIELDS:
        value = fields.get(field)
        if value is None:
            continue
        if value not in VALID_ROLE_VALUES:
            hint = "Use a single lowercase machine role token: none, implementer, reviewer, or architect."
            if field == "Acceptance role" and "/" in value:
                hint = "Use `Acceptance role: architect` and keep human gates in `Human verification needed:` or `Human review prompt:`."
            errors.append(
                contract_error(
                    field,
                    "malformed_role_field",
                    f"{field} must be a single lowercase machine role token.",
                    expected=sorted(VALID_ROLE_VALUES),
                    actual=value,
                    hint=hint,
                )
            )

    handoff = fields.get("Completion handoff")
    if handoff is not None and handoff not in VALID_COMPLETION_HANDOFFS:
        errors.append(
            contract_error(
                "Completion handoff",
                "malformed_completion_handoff",
                "Completion handoff must be a machine-readable handoff value.",
                expected=sorted(VALID_COMPLETION_HANDOFFS),
                actual=handoff,
                hint="Use `Completion handoff: to:reviewer` for ordinary review handoff.",
            )
        )

    natural_fields = {
        "Reviewer target": reviewer_target,
        "Human review prompt": human_prompt,
        "Human verification needed": human_verification,
    }
    return {
        "status": "ok" if not errors else "invalid",
        "heading": heading,
        "fields": {key: value for key, value in fields.items() if value is not None},
        "natural_language_fields_present": sorted(key for key, value in natural_fields.items() if value),
        "errors": errors,
    }


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Extract the role-routing fields Unit B needs without a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    roles: dict[str, dict[str, str]] = {}
    roles_block = block(text, "roles")
    for match in re.finditer(r"^  ([A-Za-z0-9_-]+):\n((?:    .+\n?)*)", roles_block, re.MULTILINE):
        role_name = match.group(1)
        role_body = match.group(2)
        inbox_label = scalar_in_block(role_body, "inbox_label")
        review_target = scalar_in_block(role_body, "review_target")
        roles[role_name] = {}
        if inbox_label:
            roles[role_name]["inbox_label"] = inbox_label
        if review_target:
            roles[role_name]["review_target"] = review_target
    completion = block(text, "completion_handoff")
    telemetry = block(text, "telemetry")
    project = block(text, "project_v2")
    return {
        "roles": roles,
        "needs_labels": yaml_list(text, "needs_labels"),
        "completion_handoff": {
            "required_fields": yaml_list(completion, "required_fields", indent=2),
            "dispatch_evidence_modes": yaml_list(completion, "dispatch_evidence_modes", indent=2),
        },
        "telemetry": {
            "required_for_meaningful_transitions": scalar_in_block(telemetry, "required_for_meaningful_transitions"),
            "workflow": scalar_in_block(telemetry, "workflow"),
            "supports_workflow_comparison": scalar_in_block(telemetry, "supports_workflow_comparison"),
            "comparison_modes": yaml_list(telemetry, "comparison_modes", indent=2),
        },
        "project_v2": {
            "mode": scalar_in_block(project, "mode"),
            "source_of_truth": scalar_in_block(project, "source_of_truth"),
        },
    }


def role_config_errors(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    roles = config.get("roles")
    needs_labels = config.get("needs_labels")
    handoff = config.get("completion_handoff", {})
    telemetry = config.get("telemetry", {})
    project = config.get("project_v2", {})
    if not isinstance(roles, dict) or not roles:
        errors.append("roles missing or empty")
    else:
        for role, spec in roles.items():
            if not isinstance(spec, dict) or not spec.get("inbox_label"):
                errors.append(f"role {role} missing inbox_label")
    if not isinstance(needs_labels, list) or not needs_labels:
        errors.append("needs_labels missing or empty")
    required = handoff.get("required_fields") if isinstance(handoff, dict) else None
    if not isinstance(required, list) or "workflow_telemetry" not in required:
        errors.append("completion_handoff.required_fields must include workflow_telemetry")
    if telemetry.get("required_for_meaningful_transitions") not in ("true", True):
        errors.append("telemetry.required_for_meaningful_transitions must be true")
    comparison_enabled = telemetry.get("supports_workflow_comparison") in ("true", True)
    modes = telemetry.get("comparison_modes")
    required_modes = {
        "single_agent_baseline",
        "unoptimized_collaboration_counterfactual",
        "optimized_collaboration_observed",
    }
    if comparison_enabled and (not isinstance(modes, list) or not required_modes.issubset(set(modes))):
        errors.append("telemetry.comparison_modes must include all three workflow comparison modes")
    if project.get("mode") != "optional_visual_mirror":
        errors.append("project_v2.mode must be optional_visual_mirror")
    return errors


def print_json_or_text(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, sort_keys=True)}")
        else:
            print(f"{key}: {value}")


def cmd_repo_resolve(args: argparse.Namespace) -> None:
    repo, source = resolve_repo(args)
    print_json_or_text({"repo": repo, "source": source, "mutation_performed": False}, args.json)


def cmd_auth_smoke(args: argparse.Namespace) -> None:
    repo, source = resolve_repo(args)
    fixture = load_json(args.fixture_json)
    if fixture is not None:
        status = fixture.get("status", "ok")
        if status != "ok":
            fail(fixture.get("code", "auth_unavailable"), fixture.get("message", "fixture failure"), 3)
        owner = fixture.get("nameWithOwner", repo)
    else:
        data = run_gh(["repo", "view", repo, "--json", "nameWithOwner"])
        owner = data.get("nameWithOwner", repo)
    print_json_or_text(
        {"repo": owner, "repo_source": source, "read_permission": "ok", "mutation_performed": False},
        args.json,
    )


def cmd_role_config_check(args: argparse.Namespace) -> None:
    if not args.config:
        fail("role_config_missing", "pass --config templates/github-role-routing.template.yaml or a repo config")
    config = parse_simple_yaml(Path(args.config))
    errors = role_config_errors(config)
    payload = {
        "config": args.config,
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "mutation_performed": False,
    }
    print_json_or_text(payload, args.json)
    if errors:
        raise SystemExit(6)


def cmd_inbox(args: argparse.Namespace) -> None:
    repo, _source = resolve_repo(args)
    if args.config:
        config = parse_simple_yaml(Path(args.config))
        labels = config.get("needs_labels", [])
    else:
        labels = []
    if not labels:
        fail("role_config_missing", "needs_labels unavailable; pass --config to claim role-ready inbox state")
    fixture = load_json(args.fixture_json)
    if fixture is not None:
        issues = fixture.get("issues", fixture)
    else:
        search = " OR ".join(f"label:{label}" for label in labels)
        issues = run_gh(
            [
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--limit",
                str(args.limit),
                "--search",
                search,
                "--json",
                "number,title,labels,updatedAt,body",
            ]
        )
    rows = []
    for issue in issues[: args.limit]:
        issue_labels = [label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])]
        if set(issue_labels).intersection(labels):
            rows.append(
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "labels": issue_labels,
                    "updatedAt": issue.get("updatedAt"),
                    "contract_validation": validate_execution_contract(issue.get("body") or ""),
                }
            )
    print_json_or_text({"repo": repo, "issues": rows, "mutation_performed": False}, args.json)


def cmd_issue_context(args: argparse.Namespace) -> None:
    repo, _source = resolve_repo(args)
    fixture = load_json(args.fixture_json)
    if fixture is not None:
        issue = fixture
    else:
        issue = run_gh(
            [
                "issue",
                "view",
                str(args.issue),
                "--repo",
                repo,
                "--json",
                "number,title,state,labels,body,comments",
            ]
        )
    comments = issue.get("comments", [])[-args.comment_limit :]
    labels = [label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])]
    contract_hints = []
    body = issue.get("body") or ""
    for marker in ("Execution Contract", "Depends On", "Acceptance Criteria", "Forbidden actions"):
        if marker.lower() in body.lower():
            contract_hints.append(marker)
    contract_validation = validate_execution_contract(body)
    print_json_or_text(
        {
            "repo": repo,
            "issue": issue.get("number", args.issue),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "labels": labels,
            "contract_hints": contract_hints,
            "contract_validation": contract_validation,
            "comment_count_returned": len(comments),
            "summary_is_authority": False,
            "mutation_performed": False,
        },
        args.json,
    )


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label["name"] if isinstance(label, dict) else str(label) for label in issue.get("labels", [])]


def issue_number(issue: dict[str, Any]) -> int | None:
    number = issue.get("number")
    try:
        return int(number)
    except (TypeError, ValueError):
        return None


def stage_from_labels(labels: list[str]) -> str | None:
    for label in labels:
        if label.startswith("stage:"):
            return label.split(":", 1)[1]
    return None


def risk_from_labels(labels: list[str]) -> str | None:
    for label in labels:
        if label.startswith("risk:"):
            return label.split(":", 1)[1].capitalize()
    return None


def owner_from_needs(label: str | None) -> str | None:
    if not label or not label.startswith("needs:"):
        return None
    value = label.split(":", 1)[1]
    if value == "human":
        return "Human"
    return value.replace("-", " ").title().replace(" ", "")


def is_transition_routable(labels: list[str]) -> bool:
    return any(label.startswith(("stage:", "type:", "area:", "risk:")) for label in labels)


def normalize_issue_collection(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict) and "issues" in data:
        data = data["issues"]
    elif isinstance(data, dict) and "items" in data:
        data = data["items"]
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        fail("invalid_issues_json", "issues JSON must be an issue object, list, or object with issues/items")
    return [item for item in data if isinstance(item, dict)]


def normalize_project_items(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        fail("invalid_project_items_json", "Project items JSON must be a list or object with items")
    return [item for item in data if isinstance(item, dict)]


def project_item_issue_number(item: dict[str, Any]) -> int | None:
    candidates = [
        item.get("number"),
        item.get("issue"),
        item.get("content", {}).get("number") if isinstance(item.get("content"), dict) else None,
    ]
    for candidate in candidates:
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def project_field_value(item: dict[str, Any], field: str) -> str | None:
    aliases = {
        "Status": ["Status", "status"],
        "Roadmap Status": ["Roadmap Status", "roadmap Status", "roadmap_status", "roadmapStatus"],
        "Stage": ["Stage", "stage"],
        "Owner Role": ["Owner Role", "owner Role", "owner_role", "ownerRole"],
        "Risk": ["Risk", "risk"],
    }
    for key in aliases[field]:
        if key not in item:
            continue
        value = item[key]
        if isinstance(value, dict):
            value = value.get("name") or value.get("text") or value.get("title")
        if value is None:
            return None
        value = str(value).strip()
        return value or None
    field_values = item.get("fieldValues") or item.get("field_values")
    if isinstance(field_values, list):
        for value in field_values:
            if not isinstance(value, dict):
                continue
            name = value.get("fieldName") or value.get("name")
            if name != field:
                continue
            raw = value.get("value") or value.get("text") or value.get("name")
            if isinstance(raw, dict):
                raw = raw.get("name") or raw.get("text") or raw.get("title")
            return str(raw).strip() if raw is not None else None
    return None


def finding(code: str, issue: int | None, severity: str, message: str, expected: Any = None, actual: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "issue": issue,
        "severity": severity,
        "code": code,
        "message": message,
    }
    if expected is not None:
        payload["expected"] = expected
    if actual is not None:
        payload["actual"] = actual
    return payload


def repair(action: str, issue: int | None, field: str | None = None, value: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": action, "issue": issue, "mutation_performed": False}
    if field:
        payload["field"] = field
    if value is not None:
        payload["value"] = value
    return payload


def read_live_issues(repo: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if args.issues:
        numbers = [number.strip() for number in args.issues.split(",") if number.strip()]
        if not numbers:
            fail("issue_selector_empty", "--issues must include at least one issue number")
        if len(numbers) > args.limit:
            fail("issue_limit_exceeded", f"--issues selected {len(numbers)} issues but --limit is {args.limit}")
        issues = []
        for number in numbers:
            result = run_gh_read(
                [
                    "issue",
                    "view",
                    number,
                    "--repo",
                    repo,
                    "--json",
                    "number,title,state,labels,body",
                ]
            )
            if not result["ok"]:
                fail(result["error_type"], result["message"], 5)
            issues.append(result["data"])
        return issues, {"mode": "issues", "issue_numbers": [int(number) for number in numbers]}
    if args.stage:
        stage_label = args.stage if args.stage.startswith("stage:") else f"stage:{args.stage}"
        result = run_gh_read(
            [
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "all",
                "--limit",
                str(args.limit),
                "--label",
                stage_label,
                "--json",
                "number,title,state,labels,body",
            ]
        )
        if not result["ok"]:
            fail(result["error_type"], result["message"], 5)
        return normalize_issue_collection(result["data"]), {"mode": "stage", "stage": args.stage, "limit": args.limit}
    fail("audit_scope_missing", "pass --issues, --stage, --issues-json, or --fixture-json")


def read_project_items(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if args.project_items_json:
        data = load_json(args.project_items_json)
        items = normalize_project_items(data)
        return items, {"source": "fixture", "status": "ok", "item_count": len(items)}, {"attempts": 0, "transient_failures": []}
    if not args.project_owner and not args.project_number:
        return [], {"source": "skipped", "status": "config_missing", "item_count": 0}, {"attempts": 0, "transient_failures": []}
    if not args.project_owner or not args.project_number:
        fail("project_config_incomplete", "pass both --project-owner and --project-number for live Project audit")
    transient_failures: list[str] = []
    attempts = max(args.project_retries, 1)
    last_result: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        result = run_gh_read(
            [
                "project",
                "item-list",
                str(args.project_number),
                "--owner",
                args.project_owner,
                "--format",
                "json",
                "--limit",
                str(args.project_limit),
            ]
        )
        if result["ok"]:
            items = normalize_project_items(result["data"])
            return (
                items,
                {
                    "source": "live_gh",
                    "status": "ok",
                    "owner": args.project_owner,
                    "number": args.project_number,
                    "item_count": len(items),
                },
                {"attempts": attempt, "transient_failures": transient_failures},
            )
        last_result = result
        if result["error_type"] != "transient":
            break
        transient_failures.append(result["message"])
        if attempt < attempts:
            time.sleep(args.project_retry_backoff)
    availability = "unavailable"
    if last_result and last_result["error_type"] == "permission_denied":
        availability = "permission_denied"
    elif last_result and last_result["error_type"] == "auth_unavailable":
        availability = "auth_unavailable"
    return (
        [],
        {
            "source": "live_gh",
            "status": availability,
            "owner": args.project_owner,
            "number": args.project_number,
            "item_count": 0,
            "error": last_result.get("message") if last_result else "Project read failed",
            "error_type": last_result.get("error_type") if last_result else "unknown",
        },
        {
            "attempts": attempts if transient_failures else 1,
            "transient_failures": transient_failures,
            "final_error": last_result.get("message") if last_result else "Project read failed",
        },
    )


def audit_issue(
    issue: dict[str, Any],
    item: dict[str, Any] | None,
    needs_labels: set[str],
    project_requested: bool,
    default_stage: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    labels = label_names(issue)
    number = issue_number(issue)
    present_needs = sorted(set(labels).intersection(needs_labels))
    issue_findings: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    if len(present_needs) > 1:
        issue_findings.append(
            finding("multiple_needs_labels", number, "warning", "Issue has more than one next-owner needs label.", expected="one needs:* label", actual=present_needs)
        )
        repairs.append(repair("adjust_label", number, "needs:*", "exactly one next-owner label"))
    if issue.get("state", "").upper() == "OPEN" and not present_needs and is_transition_routable(labels):
        issue_findings.append(
            finding("no_next_owner_label", number, "warning", "Open transition-routable issue lacks a next-owner needs:* label.", expected=sorted(needs_labels), actual=labels)
        )
        repairs.append(repair("adjust_label", number, "needs:*", "add the intended next-owner label"))
    contract_validation = validate_execution_contract(issue.get("body") or "")
    if contract_validation["status"] == "invalid":
        for error in contract_validation["errors"]:
            issue_findings.append(
                finding(
                    "execution_contract_invalid",
                    number,
                    "error",
                    error["message"],
                    expected={error["field"]: error.get("expected")},
                    actual={error["field"]: error.get("actual")},
                )
            )
        repairs.append(repair("fix_execution_contract", number, "Execution Contract", "use lowercase role tokens and machine-readable handoff values"))
    if project_requested and item is None:
        issue_findings.append(
            finding("missing_project_item", number, "error", "Issue is not present in the requested Project v2 item list.")
        )
        repairs.append(repair("add_project_item", number))
        return issue_findings, repairs
    if item is None:
        return issue_findings, repairs
    expected_stage = default_stage or stage_from_labels(labels)
    expected_risk = risk_from_labels(labels)
    expected_owner = owner_from_needs(present_needs[0]) if present_needs else None
    for field_name in ("Status", "Roadmap Status", "Stage", "Owner Role", "Risk"):
        actual = project_field_value(item, field_name)
        if not actual:
            issue_findings.append(
                finding("empty_project_field", number, "error", f"Project field {field_name} is empty.", expected="non-empty", actual=actual)
            )
            repairs.append(repair("set_project_field", number, field_name, "expected scheduler value"))
    comparisons = [
        ("Stage", expected_stage),
        ("Risk", expected_risk),
        ("Owner Role", expected_owner),
    ]
    for field_name, expected in comparisons:
        if not expected:
            continue
        actual = project_field_value(item, field_name)
        if actual and actual != expected:
            issue_findings.append(
                finding("project_field_mismatch", number, "error", f"Project field {field_name} does not match issue scheduler labels.", expected={field_name: expected}, actual={field_name: actual})
            )
            repairs.append(repair("set_project_field", number, field_name, expected))
    status = project_field_value(item, "Status")
    roadmap = project_field_value(item, "Roadmap Status")
    if issue.get("state", "").upper() == "CLOSED" and (status != "Done" or roadmap != "Done"):
        issue_findings.append(
            finding("closed_issue_not_done", number, "warning", "Closed issue is not Done in the Project mirror.", expected={"Status": "Done", "Roadmap Status": "Done"}, actual={"Status": status, "Roadmap Status": roadmap})
        )
        repairs.append(repair("set_project_field", number, "Status", "Done"))
        repairs.append(repair("set_project_field", number, "Roadmap Status", "Done"))
    if issue.get("state", "").upper() == "OPEN" and present_needs and (status == "Done" or roadmap == "Done"):
        issue_findings.append(
            finding("open_needs_label_status_mismatch", number, "error", "Open issue with a needs:* label is marked Done in the Project mirror.", expected={"Status": "not Done", "Roadmap Status": "not Done"}, actual={"Status": status, "Roadmap Status": roadmap})
        )
        repairs.append(repair("set_project_field", number, "Status", "Todo"))
    return issue_findings, repairs


def cmd_scheduler_audit(args: argparse.Namespace) -> None:
    repo, repo_source = resolve_repo(args)
    config = parse_simple_yaml(Path(args.config)) if args.config else {}
    needs = set(config.get("needs_labels", [])) or {"needs:architect", "needs:implementer", "needs:reviewer", "needs:harvester", "needs:human"}
    fixture = load_json(args.fixture_json)
    if args.issues_json:
        issues = normalize_issue_collection(load_json(args.issues_json))
        issue_source = "fixture"
        scope = {"mode": "fixture", "issue_numbers": [issue_number(issue) for issue in issues if issue_number(issue) is not None]}
    elif fixture is not None:
        issues = normalize_issue_collection(fixture)
        issue_source = "fixture"
        scope = {"mode": "fixture", "issue_numbers": [issue_number(issue) for issue in issues if issue_number(issue) is not None]}
    else:
        issues, scope = read_live_issues(repo, args)
        issue_source = "live_gh"
    project_items, project_status, retry_summary = read_project_items(args)
    project_requested = project_status["source"] in ("fixture", "live_gh") and project_status["status"] == "ok"
    project_by_issue = {project_item_issue_number(item): item for item in project_items if project_item_issue_number(item) is not None}
    findings: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    for issue in issues[: args.limit]:
        item = project_by_issue.get(issue_number(issue))
        issue_findings, issue_repairs = audit_issue(issue, item, needs, project_requested, args.stage)
        findings.extend(issue_findings)
        repairs.extend(issue_repairs)
    status = "ok"
    if findings:
        status = "findings"
    if project_status["status"] not in ("ok", "config_missing") and project_status["source"] == "live_gh":
        status = "degraded"
    payload = {
        "status": status,
        "repo": repo,
        "audit_scope": {
            **scope,
            "limit": args.limit,
            "project_owner": args.project_owner,
            "project_number": args.project_number,
        },
        "sources": {
            "repo": repo_source,
            "issues": issue_source,
            "project_items": project_status["source"],
            "config": args.config,
            "needs_labels": sorted(needs),
        },
        "project_v2": {
            "mode": "optional_visual_mirror",
            "availability": project_status["status"],
            "owner": project_status.get("owner"),
            "number": project_status.get("number"),
            "item_count": project_status.get("item_count", 0),
            "error": project_status.get("error"),
            "error_type": project_status.get("error_type"),
        },
        "retry_summary": {
            "project_item_list": retry_summary,
        },
        "findings": findings,
        "dry_run_repair_plan": repairs,
        "mutation_performed": False,
    }
    print_json_or_text(payload, args.json)


def cmd_permission_smoke(args: argparse.Namespace) -> None:
    action = args.action
    if action in FORBIDDEN_ACTIONS:
        status = "forbidden"
        code = "unit_b_forbidden_mutation"
    elif action in READ_ONLY_ACTIONS:
        status = "read_only_allowed"
        code = "ok"
    elif action in DRY_RUN_ACTIONS:
        status = "dry_run_allowed"
        code = "ok"
    else:
        status = "unknown_requires_architect_review"
        code = "unknown_action"
    print_json_or_text(
        {"action": action, "status": status, "code": code, "mutation_performed": False},
        args.json,
    )
    if status == "forbidden":
        raise SystemExit(7)


def cmd_activation_report(args: argparse.Namespace) -> None:
    core_root = Path(args.core_root).expanduser().resolve() if args.core_root else default_core_root()
    workflow = core_root / "workflows" / "github-collaboration-helper.md"
    helper = core_root / "scripts" / "github_collaboration_helper.py"
    routing = core_root / "templates" / "github-role-routing.template.yaml"
    launcher = (
        Path(args.launcher).expanduser()
        if args.launcher
        else Path.home() / ".agent-foundry" / "bin" / "agent-foundry-github-collab"
    )
    runtime_skill = Path(args.runtime_skill).expanduser() if args.runtime_skill else Path.home() / ".codex" / "skills" / "agent-collaboration" / "SKILL.md"
    generated_skill = (
        Path(args.generated_skill).expanduser()
        if args.generated_skill
        else Path.home()
        / ".agent-foundry"
        / "generated"
        / "agent-foundry-adapters"
        / "codex"
        / "skills"
        / "agent-collaboration"
        / "SKILL.md"
    )
    activation_terms = [
        "activation evidence",
        "target runtime",
        "user-facing activation instructions",
    ]
    helper_terms = [
        "activation-report",
        "GitHub collaboration helper",
    ]
    payload = {
        "core_root": str(core_root),
        "target_runtime": args.target_runtime,
        "launcher": path_status(launcher),
        "user_entrypoint": str(launcher),
        "helper": path_status(helper, ["Read-only and dry-run GitHub collaboration helper pilot"]),
        "workflow_contract": path_status(workflow, helper_terms),
        "routing_template": path_status(routing, ["needs_labels", "optional_visual_mirror"]),
        "installed_runtime_skill": path_status(runtime_skill, activation_terms),
        "generated_skill": path_status(generated_skill, activation_terms),
        "safe_trial_commands": [
            f"{launcher} --repo <owner>/<repo> auth-smoke",
            f"{launcher} role-config-check --config {routing}",
            f"{launcher} --repo <owner>/<repo> issue-context <issue> --comment-limit 3",
            f"{launcher} --json activation-report",
        ],
        "mutation_performed": False,
    }
    payload["status"] = "ok" if all(
        [
            payload["helper"].get("ok", payload["helper"]["exists"]),
            payload["launcher"]["exists"],
            payload["workflow_contract"].get("ok", payload["workflow_contract"]["exists"]),
            payload["routing_template"].get("ok", payload["routing_template"]["exists"]),
            payload["generated_skill"].get("ok", payload["generated_skill"]["exists"]),
            payload["installed_runtime_skill"].get("ok", payload["installed_runtime_skill"]["exists"]),
        ]
    ) else "incomplete"
    print_json_or_text(payload, args.json)
    if payload["status"] != "ok":
        raise SystemExit(8)


def telemetry_block(transition_type: str, role_from: str, role_to: str, note: str) -> str:
    return f"""workflow_telemetry:
  transition_type: {transition_type}
  role_from: {role_from}
  role_to: {role_to}
  rehydration_scope: compact
  durable_state_reads:
    github_issues: 1
    github_prs: 0
    github_comments: 1
    project_reads: 0
    local_files: 0
  durable_state_mutations:
    github_comments: 0
    labels_added: 0
    labels_removed: 0
    project_writes: 0
  duplicated_context_from_previous_role: low
  notes: "{note}"
"""


def comparison_telemetry_block(args: argparse.Namespace) -> str:
    optimized_transitions = args.optimized_transitions
    unoptimized_transitions = args.unoptimized_transitions
    single_agent_transitions = args.single_agent_transitions
    avoided_transitions = max(unoptimized_transitions - optimized_transitions, 0)
    full_rehydrate_delta = max(args.unoptimized_full_rehydrates - args.optimized_full_rehydrates, 0)
    optimized_overhead_delta = optimized_transitions - single_agent_transitions
    quality_benefit_available = args.quality_benefit not in ("", "unknown", "none")
    negative_quality_signal = any(
        (
            args.blocking_findings_missed,
            args.failed_verification,
            args.reopened_issues,
            args.human_holds,
            args.late_closure_corrections,
        )
    )
    recommendation = args.recommendation
    if recommendation == "auto":
        if negative_quality_signal:
            recommendation = "insufficient_data"
        elif optimized_transitions <= single_agent_transitions + 1 and not quality_benefit_available:
            recommendation = "single_agent"
        elif optimized_overhead_delta > 0 and not quality_benefit_available:
            recommendation = "single_agent"
        elif quality_benefit_available and (avoided_transitions > 0 or full_rehydrate_delta > 0):
            recommendation = "optimized_collaboration"
        else:
            recommendation = "insufficient_data"
    return f"""workflow_comparison_telemetry:
  subject: "{args.subject}"
  comparison_scope:
    unit: {args.unit}
    issue_count: {args.issue_count}
    pr_count: {args.pr_count}
    user_visible_scope: {str(args.user_visible_scope).lower()}
    risk_class: {args.risk_class}
    human_gate_count: {args.human_gate_count}
  instrumentation:
    observed_counter_available: {str(args.observed_counter_available).lower()}
    observed_counter_source: "{args.observed_counter_source}"
    elapsed_time_available: {str(args.elapsed_time_available).lower()}
    elapsed_time_source: "{args.elapsed_time_source}"
    github_api_read_attempts: "{args.github_api_read_attempts}"
    github_api_failures: "{args.github_api_failures}"
    project_read_attempts: "{args.project_read_attempts}"
    project_write_attempts: "{args.project_write_attempts}"
    fallback_review_used: {str(args.fallback_review_used).lower()}
    fallback_review_reason: "{args.fallback_review_reason}"
    hdc_superseded_count: {args.hdc_superseded_count}
    label_cleanup_count: {args.label_cleanup_count}
    source_threads_count: "{args.source_threads_count}"
    dispatch_mechanisms: "{args.dispatch_mechanisms}"
    durable_links_count:
      issues: "{args.durable_issue_links}"
      pull_requests: "{args.durable_pr_links}"
      comments: "{args.durable_comment_links}"
    closure_sync_passes: {args.closure_sync_passes}
    stale_state_repairs: {args.stale_state_repairs}
  single_agent_baseline:
    source: {args.single_agent_source}
    transitions: {single_agent_transitions}
    rehydration:
      none: {args.single_agent_none_rehydrates}
      compact: {args.single_agent_compact_rehydrates}
      full: {args.single_agent_full_rehydrates}
    role_dispatches: 0
    correction_cycles: {args.single_agent_correction_cycles}
    ledger_estimated_tokens:
      input: "{args.single_agent_estimated_input_tokens}"
      output: "{args.single_agent_estimated_output_tokens}"
      confidence: {args.single_agent_confidence}
    observed_goal_tokens:
      value: "{args.single_agent_observed_goal_tokens}"
      source: "{args.single_agent_observed_source}"
      notes: "Optional observed session or goal counter; not billing-grade."
  unoptimized_collaboration_counterfactual:
    source: estimated
    assumed_agents: {args.assumed_agents}
    assumed_transitions: {unoptimized_transitions}
    assumed_full_rehydrates: {args.unoptimized_full_rehydrates}
    assumed_compact_rehydrates: {args.unoptimized_compact_rehydrates}
    assumed_role_dispatches: {args.unoptimized_role_dispatches}
    assumed_human_gates: {args.unoptimized_human_gates}
    duplicated_context: {args.unoptimized_duplicated_context}
    ledger_estimated_tokens:
      input: "{args.unoptimized_estimated_input_tokens}"
      output: "{args.unoptimized_estimated_output_tokens}"
      confidence: {args.unoptimized_confidence}
    assumptions:
      - "{args.unoptimized_assumption}"
  optimized_collaboration_observed:
    source: {args.optimized_source}
    transitions: {optimized_transitions}
    rehydration:
      none: {args.optimized_none_rehydrates}
      compact: {args.optimized_compact_rehydrates}
      full: {args.optimized_full_rehydrates}
    role_dispatches: {args.optimized_role_dispatches}
    batch_checkpoints: {args.optimized_batch_checkpoints}
    bundled_human_gates: {args.optimized_bundled_human_gates}
    correction_cycles: {args.optimized_correction_cycles}
    avoided_transitions: {avoided_transitions}
    ledger_estimated_tokens:
      input: "{args.optimized_estimated_input_tokens}"
      output: "{args.optimized_estimated_output_tokens}"
      confidence: {args.optimized_confidence}
    observed_goal_tokens:
      value: "{args.optimized_observed_goal_tokens}"
      source: "{args.optimized_observed_source}"
      notes: "Keep separate from ledger estimates."
  quality_guardrails:
    blocking_findings_missed: {args.blocking_findings_missed}
    blocking_findings_caught: {args.blocking_findings_caught}
    failed_verification: {args.failed_verification}
    reopened_issues: {args.reopened_issues}
    human_holds: {args.human_holds}
    late_closure_corrections: {args.late_closure_corrections}
  savings_analysis:
    optimized_vs_unoptimized:
      transition_delta: {optimized_transitions - unoptimized_transitions}
      full_rehydrate_delta: {args.optimized_full_rehydrates - args.unoptimized_full_rehydrates}
      estimated_token_delta: "{args.estimated_token_delta}"
    optimized_vs_single_agent:
      overhead_delta: {optimized_overhead_delta}
      quality_or_parallelism_benefit: "{args.quality_benefit}"
    recommendation: {recommendation}
    confidence: {args.analysis_confidence}
    notes: "Decision-support estimate, not billing-grade accounting."
"""


def compact_packet(args: argparse.Namespace, next_owner: str) -> str:
    return f"""compact_rehydration_packet:
  packet_version: 1
  subject:
    issue: {args.issue}
    pull_request: {args.pr or 'null'}
    parent_issue: {args.parent_issue or 'null'}
    stage: "{args.stage}"
  current_owner: {args.current_owner}
  next_owner: {next_owner}
  authority_sources:
    must_read:
      - AGENTS.md
      - agent-collaboration skill
      - issue body and latest comments
  scope_summary:
    included:
      - "{args.scope}"
    excluded:
      - mutation helpers
      - Project v2 mutation
      - runtime/global/Vault/private/generated mutation
      - memory-system work
  human_gates:
    active: false
    required_phrase: null
  residual_risks:
    - "{args.risk}"
"""


def cmd_handoff_draft(args: argparse.Namespace) -> None:
    print("DRY RUN: no dispatch, comment, label, Project, merge, closure, runtime, Vault, generated, or memory mutation performed.")
    print()
    print(compact_packet(args, args.next_owner))
    print(telemetry_block("handoff_draft", args.current_owner, args.next_owner, "Preview-only handoff draft."))


def cmd_dispatch_evidence_draft(args: argparse.Namespace) -> None:
    print("DRY RUN: generated dispatch evidence only; no dispatch or mutation occurred.")
    print()
    print("dispatch_evidence:")
    print(f"  mode: {args.mode}")
    print(f"  target_role: {args.target_role}")
    print(f"  issue: {args.issue}")
    if args.mode == "generated_note":
        print("  status: no dispatch occurred")
    elif args.mode == "portable_prompt":
        print("  manual_bridge_warning: true")
    else:
        print("  required_external_evidence: true")
    print(telemetry_block("dispatch_evidence_draft", args.current_owner, args.target_role, "Preview-only dispatch evidence."))


def cmd_release_next_draft(args: argparse.Namespace) -> None:
    print("DRY RUN: release text only; no labels, comments, Project fields, merge, closure, or runtime mutation performed.")
    print()
    print(f"release_next_issue: {args.next_issue}")
    print(f"dependency_satisfied: {args.dependency}")
    print(compact_packet(args, args.next_owner))
    print(telemetry_block("release_next_draft", args.current_owner, args.next_owner, "Preview-only release draft."))


def cmd_comparison_draft(args: argparse.Namespace) -> None:
    print("DRY RUN: workflow comparison telemetry only; no comments, labels, Project fields, merge, closure, runtime, Vault, generated, or memory mutation performed.")
    print()
    print(comparison_telemetry_block(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Explicit GitHub repository as owner/repo.")
    parser.add_argument("--json", action="store_true", help="Emit JSON where supported.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("repo-resolve").set_defaults(func=cmd_repo_resolve)

    auth = sub.add_parser("auth-smoke")
    auth.add_argument("--fixture-json")
    auth.set_defaults(func=cmd_auth_smoke)

    role = sub.add_parser("role-config-check")
    role.add_argument("--config")
    role.set_defaults(func=cmd_role_config_check)

    inbox = sub.add_parser("inbox")
    inbox.add_argument("--config")
    inbox.add_argument("--fixture-json")
    inbox.add_argument("--limit", type=int, default=20)
    inbox.set_defaults(func=cmd_inbox)

    context = sub.add_parser("issue-context")
    context.add_argument("issue", type=int)
    context.add_argument("--fixture-json")
    context.add_argument("--comment-limit", type=int, default=5)
    context.set_defaults(func=cmd_issue_context)

    audit = sub.add_parser("scheduler-audit")
    audit.add_argument("--config")
    audit.add_argument("--fixture-json", help="Legacy single-issue fixture; prefer --issues-json for new tests.")
    audit.add_argument("--issues-json", help="Fixture issue object, list, or object with issues/items.")
    audit.add_argument("--project-items-json", help="Fixture Project item list or gh project item-list JSON.")
    audit.add_argument("--issues", help="Comma-separated explicit issue numbers for bounded live audit.")
    audit.add_argument("--stage", help="Stage value or label for bounded live audit, such as AF-11 or stage:AF-11.")
    audit.add_argument("--limit", type=int, default=20, help="Maximum issues to audit.")
    audit.add_argument("--project-owner", help="Project owner for live Project item-list, such as @me or an org.")
    audit.add_argument("--project-number", type=int, help="Project number for live Project item-list.")
    audit.add_argument("--project-limit", type=int, default=300, help="Maximum Project items to read once per batch.")
    audit.add_argument("--project-retries", type=int, default=3, help="Bounded retries for transient Project reads.")
    audit.add_argument("--project-retry-backoff", type=float, default=0.5, help="Seconds between transient Project read retries.")
    audit.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON for scheduler-audit.")
    audit.set_defaults(func=cmd_scheduler_audit)

    activation = sub.add_parser("activation-report")
    activation.add_argument("--core-root", help="Agent Foundry Core root. Defaults to this helper's checkout.")
    activation.add_argument("--launcher", help="Runtime launcher path to inspect.")
    activation.add_argument("--runtime-skill", help="Installed Codex agent-collaboration SKILL.md to inspect.")
    activation.add_argument("--generated-skill", help="Generated selected-output Codex agent-collaboration SKILL.md to inspect.")
    activation.add_argument("--target-runtime", default="codex", help="Runtime being checked; informational.")
    activation.set_defaults(func=cmd_activation_report)

    perm = sub.add_parser("permission-smoke")
    perm.add_argument("action")
    perm.set_defaults(func=cmd_permission_smoke)

    handoff = sub.add_parser("handoff-draft")
    add_draft_args(handoff)
    handoff.add_argument("--next-owner", default="Reviewer")
    handoff.set_defaults(func=cmd_handoff_draft)

    dispatch = sub.add_parser("dispatch-evidence-draft")
    dispatch.add_argument("--issue", type=int, required=True)
    dispatch.add_argument("--mode", choices=["live_thread_dispatch", "github_comment", "generated_note", "portable_prompt"], required=True)
    dispatch.add_argument("--target-role", default="Reviewer")
    dispatch.add_argument("--current-owner", default="Coordinator")
    dispatch.set_defaults(func=cmd_dispatch_evidence_draft)

    release = sub.add_parser("release-next-draft")
    add_draft_args(release)
    release.add_argument("--next-issue", type=int, required=True)
    release.add_argument("--next-owner", default="Implementer")
    release.add_argument("--dependency", required=True)
    release.set_defaults(func=cmd_release_next_draft)

    comparison = sub.add_parser("comparison-draft")
    add_comparison_args(comparison)
    comparison.set_defaults(func=cmd_comparison_draft)
    return parser


def add_draft_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--pr", type=int)
    parser.add_argument("--parent-issue", type=int)
    parser.add_argument("--stage", default="AF-11")
    parser.add_argument("--current-owner", default="Implementer")
    parser.add_argument("--scope", default="bounded helper work")
    parser.add_argument("--risk", default="Preview output must be verified against authority sources.")


def add_comparison_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--subject", required=True)
    parser.add_argument(
        "--unit",
        choices=["issue", "issue_batch", "pr", "epic", "milestone", "pilot", "session_goal"],
        default="issue",
    )
    parser.add_argument("--issue-count", type=int, default=1)
    parser.add_argument("--pr-count", type=int, default=0)
    parser.add_argument("--user-visible-scope", action="store_true")
    parser.add_argument("--risk-class", choices=["low", "medium", "high", "mixed"], default="medium")
    parser.add_argument("--human-gate-count", type=int, default=0)
    parser.add_argument("--observed-counter-available", action="store_true")
    parser.add_argument("--observed-counter-source", default="not_available")
    parser.add_argument("--elapsed-time-available", action="store_true")
    parser.add_argument("--elapsed-time-source", default="not_available")
    parser.add_argument("--github-api-read-attempts", default="unknown")
    parser.add_argument("--github-api-failures", default="unknown")
    parser.add_argument("--project-read-attempts", default="unknown")
    parser.add_argument("--project-write-attempts", default="unknown")
    parser.add_argument("--fallback-review-used", action="store_true")
    parser.add_argument("--fallback-review-reason", default="not_available")
    parser.add_argument("--hdc-superseded-count", type=int, default=0)
    parser.add_argument("--label-cleanup-count", type=int, default=0)
    parser.add_argument("--source-threads-count", default="unknown")
    parser.add_argument("--dispatch-mechanisms", default="unknown")
    parser.add_argument("--durable-issue-links", default="unknown")
    parser.add_argument("--durable-pr-links", default="unknown")
    parser.add_argument("--durable-comment-links", default="unknown")
    parser.add_argument("--closure-sync-passes", type=int, default=0)
    parser.add_argument("--stale-state-repairs", type=int, default=0)
    parser.add_argument("--single-agent-source", choices=["observed", "estimated", "unavailable"], default="estimated")
    parser.add_argument("--single-agent-transitions", type=int, default=1)
    parser.add_argument("--single-agent-none-rehydrates", type=int, default=1)
    parser.add_argument("--single-agent-compact-rehydrates", type=int, default=0)
    parser.add_argument("--single-agent-full-rehydrates", type=int, default=0)
    parser.add_argument("--single-agent-correction-cycles", type=int, default=0)
    parser.add_argument("--single-agent-estimated-input-tokens", default="unknown")
    parser.add_argument("--single-agent-estimated-output-tokens", default="unknown")
    parser.add_argument("--single-agent-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--single-agent-observed-goal-tokens", default="unknown")
    parser.add_argument("--single-agent-observed-source", default="null")
    parser.add_argument("--assumed-agents", type=int, choices=[3, 4], default=3)
    parser.add_argument("--unoptimized-transitions", type=int, default=4)
    parser.add_argument("--unoptimized-full-rehydrates", type=int, default=4)
    parser.add_argument("--unoptimized-compact-rehydrates", type=int, default=0)
    parser.add_argument("--unoptimized-role-dispatches", type=int, default=3)
    parser.add_argument("--unoptimized-human-gates", type=int, default=0)
    parser.add_argument("--unoptimized-duplicated-context", choices=["low", "medium", "high"], default="high")
    parser.add_argument("--unoptimized-estimated-input-tokens", default="unknown")
    parser.add_argument("--unoptimized-estimated-output-tokens", default="unknown")
    parser.add_argument("--unoptimized-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--unoptimized-assumption", default="Each role handoff performs full rehydration.")
    parser.add_argument("--optimized-source", choices=["observed", "estimated", "mixed"], default="observed")
    parser.add_argument("--optimized-transitions", type=int, default=1)
    parser.add_argument("--optimized-none-rehydrates", type=int, default=0)
    parser.add_argument("--optimized-compact-rehydrates", type=int, default=1)
    parser.add_argument("--optimized-full-rehydrates", type=int, default=0)
    parser.add_argument("--optimized-role-dispatches", type=int, default=0)
    parser.add_argument("--optimized-batch-checkpoints", type=int, default=0)
    parser.add_argument("--optimized-bundled-human-gates", type=int, default=0)
    parser.add_argument("--optimized-correction-cycles", type=int, default=0)
    parser.add_argument("--optimized-estimated-input-tokens", default="unknown")
    parser.add_argument("--optimized-estimated-output-tokens", default="unknown")
    parser.add_argument("--optimized-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--optimized-observed-goal-tokens", default="unknown")
    parser.add_argument("--optimized-observed-source", default="null")
    parser.add_argument("--blocking-findings-missed", type=int, default=0)
    parser.add_argument("--blocking-findings-caught", type=int, default=0)
    parser.add_argument("--failed-verification", type=int, default=0)
    parser.add_argument("--reopened-issues", type=int, default=0)
    parser.add_argument("--human-holds", type=int, default=0)
    parser.add_argument("--late-closure-corrections", type=int, default=0)
    parser.add_argument("--estimated-token-delta", default="unknown")
    parser.add_argument("--quality-benefit", default="unknown")
    parser.add_argument(
        "--recommendation",
        choices=["auto", "single_agent", "optimized_collaboration", "full_collaboration", "insufficient_data"],
        default="auto",
    )
    parser.add_argument("--analysis-confidence", choices=["low", "medium", "high"], default="low")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
