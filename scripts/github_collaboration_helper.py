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
    "collaboration-readiness",
    "foundry-board",
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
VALID_ROLE_VALUES_BY_FIELD = {
    "Owner role": {"none", "implementer", "reviewer", "architect", "tester", "harvester", "human"},
    "Review role": {"none", "reviewer"},
    "Acceptance role": {"none", "architect", "reviewer", "human"},
}
VALID_COMPLETION_HANDOFFS = {
    "none",
    "to:implementer",
    "to:reviewer",
    "to:architect",
    "to:tester",
    "to:human",
    "batch checkpoint",
}
READINESS_ROLES = ["coordinator", "architect", "implementer", "tester", "reviewer", "human", "harvester"]
READINESS_NEEDS_LABELS = [
    "needs:architect",
    "needs:implementer",
    "needs:reviewer",
    "needs:tester",
    "needs:harvester",
    "needs:human",
]
READINESS_PROJECT_FIELDS = ["Status", "Roadmap Status", "Stage", "Owner Role", "Risk"]
READINESS_PROJECT_OPTIONS = ["Architect", "Implementer", "Tester", "Reviewer", "Human", "Harvester"]
V2_INTEGRATION_BRANCH = "codex/v2-local-first-orchestration"
BRANCH_STRATEGIES = [
    "mainline-maintenance",
    "integration-branch",
    "release-branch",
    "trunk-based",
    "stacked-pr",
    "multi-branch",
    "custom",
]
BRANCH_CONTRACT_FIELDS = (
    "Branch strategy",
    "Release line",
    "Target branch",
    "Affected branches",
    "Verification branches",
    "Base branch verified from",
    "Working branch",
    "Worktree expectation",
    "PR target",
    "Merge rule",
    "Forward-merge expectation",
)
LEGACY_BRANCH_TARGET_FIELD = "Branch target"


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


def strip_markdown_fenced_blocks(text: str) -> str:
    output: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        if fence:
            char, length = fence
            if re.match(rf"^\s*{re.escape(char)}{{{length},}}\s*$", line.rstrip("\n\r")):
                fence = None
            output.append("\n" if line.endswith(("\n", "\r")) else "")
            continue
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            fence = (marker[0], len(marker))
            output.append("\n" if line.endswith(("\n", "\r")) else "")
            continue
        output.append(line)
    return "".join(output)


def extract_execution_contract(body: str) -> tuple[str | None, str]:
    body = strip_markdown_fenced_blocks(body or "")
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
                expected=sorted(VALID_ROLE_VALUES_BY_FIELD["Review role"]),
                actual=None,
                hint="Use `Review role: reviewer` and keep natural-language reviewer details in `Reviewer target:`.",
            )
        )

    for field in ROLE_FIELDS:
        value = fields.get(field)
        if value is None:
            continue
        valid_values = VALID_ROLE_VALUES_BY_FIELD[field]
        if value not in valid_values:
            hint = f"Use one lowercase machine role token from {', '.join(sorted(valid_values))}."
            if field == "Acceptance role" and "/" in value:
                hint = "Use `Acceptance role: architect` and keep human gates in `Human verification needed:` or `Human review prompt:`."
            if field == "Review role" and value == "tester":
                hint = "Use `Owner role: tester` or `Completion handoff: to:tester`; Tester supplies evidence and is not Reviewer authority."
            errors.append(
                contract_error(
                    field,
                    "malformed_role_field",
                    f"{field} must be a single lowercase machine role token.",
                    expected=sorted(valid_values),
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


def extract_branch_contract(body: str) -> dict[str, Any]:
    heading, contract = extract_execution_contract(body)
    fields: dict[str, str] = {}
    if heading:
        for field in BRANCH_CONTRACT_FIELDS:
            value = markdown_field(contract, field)
            if value:
                fields[field] = value
        legacy_target = markdown_field(contract, LEGACY_BRANCH_TARGET_FIELD)
        if legacy_target and "Target branch" not in fields:
            fields["Target branch"] = legacy_target
            fields["legacy_target_field"] = LEGACY_BRANCH_TARGET_FIELD
    return {
        "heading": heading,
        "fields": fields,
        "status": "present" if fields else "missing",
    }


def extract_markdown_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"^#+\s+{re.escape(heading)}\s*$"
        r"(?P<body>.*?)(?=^#+\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(strip_markdown_fenced_blocks(body or ""))
    return match.group("body") if match else ""


def markdown_field_loose(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(field)}:\s*(.*?)\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def has_markdown_field(text: str, field: str) -> bool:
    return re.search(rf"^\s*{re.escape(field)}:\s*", text, re.MULTILINE | re.IGNORECASE) is not None


def validate_testing_contract(body: str, labels: list[str] | None = None) -> dict[str, Any]:
    labels = labels or []
    text = strip_markdown_fenced_blocks(body or "")
    responsibility = markdown_field_loose(text, "Testing Responsibility")
    tester_trigger_present = has_markdown_field(text, "Tester Trigger")
    testing_contract = extract_markdown_section(text, "Testing Contract")
    evidence_handoff = extract_markdown_section(text, "Test Evidence Handoff")
    handoff_to = markdown_field_loose(evidence_handoff, "to") if evidence_handoff else None
    needs_tester = "needs:tester" in labels
    tester_related = needs_tester or responsibility == "tester" or bool(testing_contract) or bool(evidence_handoff)
    errors: list[dict[str, Any]] = []

    if not tester_related:
        return {
            "status": "missing",
            "fields": {},
            "errors": [],
        }

    if needs_tester and responsibility != "tester":
        errors.append(
            contract_error(
                "Testing Responsibility",
                "missing_testing_contract_field",
                "needs:tester requires Testing Responsibility: tester.",
                expected="tester",
                actual=responsibility,
            )
        )
    if responsibility == "tester" and not tester_trigger_present:
        errors.append(
            contract_error(
                "Tester Trigger",
                "missing_testing_contract_field",
                "Testing Responsibility: tester requires a Tester Trigger field.",
                expected="Tester Trigger",
                actual=None,
            )
        )
    if needs_tester and not testing_contract:
        errors.append(
            contract_error(
                "Testing Contract",
                "missing_testing_contract_field",
                "needs:tester requires a Testing Contract section.",
                expected="Testing Contract section",
                actual=None,
            )
        )
    if evidence_handoff and not handoff_to:
        errors.append(
            contract_error(
                "Test Evidence Handoff.to",
                "missing_testing_contract_field",
                "Test Evidence Handoff requires a to value.",
                expected=["reviewer", "architect", "implementer", "human"],
                actual=None,
            )
        )
    if handoff_to and handoff_to not in {"reviewer", "architect", "implementer", "human"}:
        errors.append(
            contract_error(
                "Test Evidence Handoff.to",
                "malformed_testing_handoff",
                "Test Evidence Handoff to must name the next authority role.",
                expected=["reviewer", "architect", "implementer", "human"],
                actual=handoff_to,
            )
        )

    fields = {}
    if responsibility is not None:
        fields["Testing Responsibility"] = responsibility
    if tester_trigger_present:
        fields["Tester Trigger"] = "present"
    if testing_contract:
        fields["Testing Contract"] = "present"
    if evidence_handoff:
        fields["Test Evidence Handoff"] = "present"
    if handoff_to:
        fields["Test Evidence Handoff.to"] = handoff_to
    return {
        "status": "ok" if not errors else "invalid",
        "fields": fields,
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
                    "testing_contract_validation": validate_testing_contract(issue.get("body") or "", issue_labels),
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
    testing_contract_validation = validate_testing_contract(body, labels)
    print_json_or_text(
        {
            "repo": repo,
            "issue": issue.get("number", args.issue),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "labels": labels,
            "contract_hints": contract_hints,
            "contract_validation": contract_validation,
            "testing_contract_validation": testing_contract_validation,
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


def project_metadata_from_fixture(data: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    fields_seen: set[str] = set()
    options_seen: set[str] = set()
    explicit_metadata = False
    if isinstance(data, dict):
        fields = data.get("fields")
        if isinstance(fields, list):
            explicit_metadata = True
            for field in fields:
                if isinstance(field, dict):
                    name = field.get("name")
                    if name:
                        fields_seen.add(str(name))
                    for option in field.get("options") or []:
                        if isinstance(option, dict):
                            option_name = option.get("name")
                        else:
                            option_name = option
                        if field.get("name") == "Owner Role" and option_name:
                            options_seen.add(str(option_name))
                elif field:
                    fields_seen.add(str(field))
        options = data.get("options")
        if isinstance(options, dict):
            explicit_metadata = True
            for option in options.get("Owner Role") or options.get("owner_role") or []:
                if isinstance(option, dict):
                    option = option.get("name")
                if option:
                    options_seen.add(str(option))
        elif isinstance(options, list):
            explicit_metadata = True
            for option in options:
                if isinstance(option, dict):
                    option = option.get("name")
                if option:
                    options_seen.add(str(option))
    for item in items:
        for field in READINESS_PROJECT_FIELDS:
            if project_field_value(item, field):
                fields_seen.add(field)
        field_values = item.get("fieldValues") or item.get("field_values")
        if isinstance(field_values, list):
            for value in field_values:
                if not isinstance(value, dict):
                    continue
                name = value.get("fieldName") or value.get("name")
                if name:
                    fields_seen.add(str(name))
                if name == "Owner Role":
                    raw = value.get("value") or value.get("text") or value.get("name")
                    if isinstance(raw, dict):
                        raw = raw.get("name") or raw.get("text") or raw.get("title")
                    if raw:
                        options_seen.add(str(raw))
        owner = project_field_value(item, "Owner Role")
        if owner:
            options_seen.add(owner)
    return {
        "fields_seen": sorted(fields_seen),
        "options_seen": sorted(options_seen),
        "explicit_metadata": explicit_metadata,
    }


def normalize_label_collection(data: Any) -> list[str]:
    if data is None:
        return []
    if isinstance(data, dict) and "labels" in data:
        data = data["labels"]
    if not isinstance(data, list):
        fail("invalid_labels_json", "labels JSON must be a list or object with labels")
    labels: list[str] = []
    for item in data:
        if isinstance(item, dict):
            name = item.get("name")
        else:
            name = item
        if name:
            labels.append(str(name))
    return labels


def run_git_read(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or Path.cwd(),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout).strip()}
    return {"ok": True, "stdout": result.stdout}


def parse_git_status_short(output: str) -> dict[str, Any]:
    lines = output.splitlines()
    branch_line = lines[0] if lines and lines[0].startswith("## ") else ""
    branch = None
    upstream = None
    ahead = 0
    behind = 0
    if branch_line:
        status_text = branch_line[3:]
        branch_part = status_text.split(" [", 1)[0]
        if "..." in branch_part:
            branch, upstream = branch_part.split("...", 1)
        else:
            branch = branch_part
        match = re.search(r"ahead (\d+)", branch_line)
        if match:
            ahead = int(match.group(1))
        match = re.search(r"behind (\d+)", branch_line)
        if match:
            behind = int(match.group(1))
    change_lines = [line for line in lines[1:] if line]
    staged = [
        line
        for line in change_lines
        if len(line) >= 2 and line[:2] != "??" and line[0] not in {" ", "?"}
    ]
    unstaged = [
        line
        for line in change_lines
        if len(line) >= 2 and line[:2] != "??" and line[1] not in {" ", "?"}
    ]
    untracked = [line for line in change_lines if line.startswith("??")]
    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty": bool(change_lines),
        "staged_count": len(staged),
        "unstaged_count": len(unstaged),
        "untracked_count": len(untracked),
        "raw_status": lines,
    }


def read_local_git_state(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if getattr(args, "local_git_json", None):
        data = load_json(args.local_git_json)
        if not isinstance(data, dict):
            fail("invalid_local_git_json", "local git JSON must be an object")
        return (
            {
                "source": "fixture",
                "status": data.get("status", "ok"),
                "branch": data.get("branch"),
                "upstream": data.get("upstream"),
                "ahead": int(data.get("ahead", 0) or 0),
                "behind": int(data.get("behind", 0) or 0),
                "dirty": bool(data.get("dirty")),
                "staged_count": int(data.get("staged_count", 0) or 0),
                "unstaged_count": int(data.get("unstaged_count", 0) or 0),
                "untracked_count": int(data.get("untracked_count", 0) or 0),
                "commit": data.get("commit"),
                "worktree_path": data.get("worktree_path"),
            },
            {"source": "fixture", "status": data.get("status", "ok"), "error": data.get("error")},
            {"attempts": 0},
        )
    status_result = run_git_read(["status", "--short", "--branch"])
    if not status_result["ok"]:
        return (
            {"source": "local_git", "status": "unavailable", "error": status_result.get("error")},
            {"source": "local_git", "status": "unavailable", "error": status_result.get("error")},
            {"attempts": 1},
        )
    state = parse_git_status_short(status_result["stdout"])
    state.update({"source": "local_git", "status": "ok", "worktree_path": str(Path.cwd())})
    commit_result = run_git_read(["rev-parse", "HEAD"])
    if commit_result["ok"]:
        state["commit"] = commit_result["stdout"].strip()
    worktree_result = run_git_read(["worktree", "list", "--porcelain"])
    if worktree_result["ok"]:
        state["worktrees"] = [line.split(" ", 1)[1] for line in worktree_result["stdout"].splitlines() if line.startswith("worktree ")]
    return state, {"source": "local_git", "status": "ok"}, {"attempts": 1}


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
                    "number,title,state,labels,body,url",
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
                "number,title,state,labels,body,url",
            ]
        )
        if not result["ok"]:
            fail(result["error_type"], result["message"], 5)
        return normalize_issue_collection(result["data"]), {"mode": "stage", "stage": args.stage, "limit": args.limit}
    fail("audit_scope_missing", "pass --issues, --stage, --issues-json, or --fixture-json")


def read_readiness_issues(repo: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if args.issues_json:
        issues = normalize_issue_collection(load_json(args.issues_json))
        return issues, {"source": "fixture", "status": "ok", "mode": "fixture", "count": len(issues)}, {"attempts": 0}
    if args.fixture_json:
        issues = normalize_issue_collection(load_json(args.fixture_json))
        return issues, {"source": "fixture", "status": "ok", "mode": "fixture", "count": len(issues)}, {"attempts": 0}
    if not args.issues and not args.stage:
        return [], {"source": "skipped", "status": "skipped", "mode": "not_requested", "count": 0}, {"attempts": 0}
    issues, scope = read_live_issues(repo, args)
    return issues, {"source": "github_rest", "status": "ok", **scope, "count": len(issues)}, {"attempts": 1}


def read_readiness_prs(repo: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if args.prs_json:
        prs = normalize_issue_collection(load_json(args.prs_json))
        return prs, {"source": "fixture", "status": "ok", "count": len(prs)}, {"attempts": 0}
    if not args.prs:
        return [], {"source": "skipped", "status": "skipped", "count": 0}, {"attempts": 0}
    numbers = [number.strip() for number in args.prs.split(",") if number.strip()]
    prs: list[dict[str, Any]] = []
    for number in numbers[: args.limit]:
        result = run_gh_read(
            [
                "pr",
                "view",
                number,
                "--repo",
                repo,
                "--json",
                "number,title,state,labels,body,headRefOid,baseRefName,headRefName",
            ]
        )
        if not result["ok"]:
            status = "transient_failure" if result["error_type"] == "transient" else result["error_type"]
            return [], {"source": "github_rest", "status": status, "error": result["message"]}, {"attempts": 1}
        prs.append(result["data"])
    return prs, {"source": "github_rest", "status": "ok", "count": len(prs)}, {"attempts": len(prs)}


def read_readiness_labels(repo: str, args: argparse.Namespace) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    if args.labels_json:
        labels = normalize_label_collection(load_json(args.labels_json))
        return labels, {"source": "fixture", "status": "ok", "count": len(labels)}, {"attempts": 0}
    result = run_gh_read(["label", "list", "--repo", repo, "--limit", "100", "--json", "name"])
    if not result["ok"]:
        return [], {"source": "github_rest", "status": result["error_type"], "error": result["message"]}, {"attempts": 1}
    labels = normalize_label_collection(result["data"])
    return labels, {"source": "github_rest", "status": "ok", "count": len(labels)}, {"attempts": 1}


def read_project_items(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if args.project_items_json:
        data = load_json(args.project_items_json)
        items = normalize_project_items(data)
        metadata = project_metadata_from_fixture(data, items)
        return (
            items,
            {
                "source": "fixture",
                "status": "ok",
                "item_count": len(items),
                **metadata,
            },
            {"attempts": 0, "transient_failures": []},
        )
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
            metadata = project_metadata_from_fixture(result["data"], items)
            return (
                items,
                {
                    "source": "live_gh",
                    "status": "ok",
                    "owner": args.project_owner,
                    "number": args.project_number,
                    "item_count": len(items),
                    **metadata,
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
    elif last_result and last_result["error_type"] == "transient":
        availability = "degraded"
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
    testing_contract_validation = validate_testing_contract(issue.get("body") or "", labels)
    if testing_contract_validation["status"] == "invalid":
        for error in testing_contract_validation["errors"]:
            issue_findings.append(
                finding(
                    "testing_contract_invalid",
                    number,
                    "error",
                    error["message"],
                    expected={error["field"]: error.get("expected")},
                    actual={error["field"]: error.get("actual")},
                )
            )
        repairs.append(repair("fix_testing_contract", number, "Testing Contract", "add Tester pickup fields and evidence handoff values"))
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


def readiness_repair(action: str, subject: str, expected_effect: str, source_evidence: str = "", risk: str = "medium") -> dict[str, Any]:
    return {
        "action": action,
        "subject": subject,
        "expected_effect": expected_effect,
        "risk": risk,
        "source_evidence": source_evidence or subject,
        "apply_supported_now": False,
        "requires_later_gate": True,
    }


def readiness_contract_summary(
    item: dict[str, Any],
    needs: set[str],
    project_item: dict[str, Any] | None = None,
    project_requested: bool = False,
    default_stage: str | None = None,
    item_type: str = "issue",
    local_git: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = label_names(item)
    contract = validate_execution_contract(item.get("body") or "")
    testing = validate_testing_contract(item.get("body") or "", labels)
    findings, repairs = audit_issue(item, project_item, needs, project_requested=project_requested, default_stage=default_stage)
    branch = evaluate_branch_contract(item, item_type, local_git)
    findings.extend(branch["findings"])
    repairs.extend(branch["repair_plan"])
    return {
        "number": issue_number(item),
        "title": item.get("title"),
        "state": item.get("state"),
        "labels": labels,
        "contract_validation": contract["status"],
        "testing_contract_validation": testing["status"],
        "branch_readiness": {key: value for key, value in branch.items() if key not in {"findings", "repair_plan"}},
        "findings": findings,
        "repair_plan": [
            readiness_repair(
                repair_item.get("action", "review"),
                f"issue:{repair_item.get('issue')}",
                f"{repair_item.get('field', 'routing')} -> {repair_item.get('value', 'review required')}",
                source_evidence="issue_contract_label_or_project_state",
            )
            if "apply_supported_now" not in repair_item
            else repair_item
            for repair_item in repairs
        ],
    }


def branch_family(branch: str | None) -> str:
    if not branch:
        return "unknown"
    if branch == "main":
        return "v1.x-maintenance"
    if branch == V2_INTEGRATION_BRANCH or branch.startswith(f"{V2_INTEGRATION_BRANCH}/"):
        return "v2-integration"
    if branch.startswith("codex/v2-"):
        return "v2-integration"
    return "integration-or-task"


def infer_branch_strategy(release_line: str | None, target_branch: str | None, pr_target: str | None) -> tuple[str | None, str]:
    if release_line == "v1.x-maintenance":
        return "mainline-maintenance", "inferred_from_release_line"
    if release_line == "v2-integration":
        return "integration-branch", "inferred_from_release_line"
    if target_branch == "main":
        return "mainline-maintenance", "inferred_from_target_branch"
    if target_branch and target_branch.startswith("release/"):
        return "release-branch", "inferred_from_target_branch"
    if pr_target and target_branch and pr_target != target_branch:
        return "stacked-pr", "inferred_from_pr_target"
    if target_branch:
        return "integration-branch", "inferred_from_target_branch"
    return None, "missing"


def split_branch_list(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,;\n]+", value)
    return [part.strip() for part in parts if part.strip()]


def pr_base_name(item: dict[str, Any]) -> str | None:
    base = item.get("baseRefName") or item.get("base_ref_name")
    if base:
        return str(base)
    base_ref = item.get("baseRef") or item.get("base")
    if isinstance(base_ref, dict):
        return base_ref.get("name") or base_ref.get("ref") or base_ref.get("label")
    return None


def pr_head_name(item: dict[str, Any]) -> str | None:
    head = item.get("headRefName") or item.get("head_ref_name")
    if head:
        return str(head)
    head_ref = item.get("headRef") or item.get("head")
    if isinstance(head_ref, dict):
        return head_ref.get("name") or head_ref.get("ref") or head_ref.get("label")
    return None


def pr_head_oid(item: dict[str, Any]) -> str | None:
    oid = item.get("headRefOid") or item.get("head_ref_oid")
    if oid:
        return str(oid)
    head_ref = item.get("headRef") or item.get("head")
    if isinstance(head_ref, dict):
        return head_ref.get("oid") or head_ref.get("sha")
    return None


def branch_readiness_repair(action: str, subject: str, expected_effect: str) -> dict[str, Any]:
    return readiness_repair(action, subject, expected_effect, "branch_readiness", risk="medium")


def evaluate_branch_contract(item: dict[str, Any], item_type: str, local_git: dict[str, Any] | None = None) -> dict[str, Any]:
    number = issue_number(item)
    branch_contract = extract_branch_contract(item.get("body") or "")
    fields = branch_contract["fields"]
    configured_strategy = fields.get("Branch strategy")
    release_line = fields.get("Release line")
    target_branch = fields.get("Target branch")
    pr_target = fields.get("PR target")
    branch_strategy, branch_strategy_source = (
        (configured_strategy, "Branch strategy")
        if configured_strategy
        else infer_branch_strategy(release_line, target_branch, pr_target)
    )
    affected_branches = split_branch_list(fields.get("Affected branches"))
    verification_branches = split_branch_list(fields.get("Verification branches"))
    forward_merge_expectation = fields.get("Forward-merge expectation")
    actual_pr_base = pr_base_name(item) if item_type == "pr" else None
    actual_pr_head = pr_head_name(item) if item_type == "pr" else None
    head_oid = pr_head_oid(item) if item_type == "pr" else None
    findings: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    status = "branch_ready"

    action_plan_concepts: list[str] = []

    if not branch_strategy or not target_branch:
        status = "branch_needs_contract"
        findings.append(
            finding(
                "branch_contract_missing",
                number,
                "error",
                "Execution Contract must include Branch strategy and Target branch before branch-sensitive work is pickup-ready.",
                expected={"Branch strategy": " | ".join(BRANCH_STRATEGIES), "Target branch": "main | <integration-branch> | <release-branch>"},
                actual={"Branch strategy": branch_strategy, "Target branch": target_branch},
            )
        )
        repairs.append(branch_readiness_repair("add_branch_contract_fields", f"{item_type}:{number}", "add Branch strategy and Target branch through issue/PR workflow"))
    elif branch_strategy not in BRANCH_STRATEGIES:
        status = "architect_decision_required"
        action_plan_concepts.append("architect_decision_required")
        findings.append(
            finding(
                "branch_strategy_unknown",
                number,
                "warning",
                "Unknown Branch strategy is treated as custom/unknown and must route to Architect instead of failing as a V1/V2 mismatch.",
                expected={"Branch strategy": BRANCH_STRATEGIES},
                actual={"Branch strategy": branch_strategy},
            )
        )
    elif branch_strategy == "custom":
        status = "architect_decision_required"
        action_plan_concepts.append("architect_decision_required")
        findings.append(
            finding(
                "branch_strategy_custom",
                number,
                "warning",
                "Custom Branch strategy requires Architect interpretation before branch-sensitive work is considered ready.",
                expected={"strategy": "documented repo-specific branch policy"},
                actual={"Branch strategy": branch_strategy},
            )
        )
    if fields.get("legacy_target_field"):
        findings.append(
            finding(
                "legacy_branch_target_field",
                number,
                "warning",
                "Legacy Branch target field was mapped as Target branch; prefer Target branch in new contracts.",
                expected="Target branch",
                actual="Branch target",
            )
        )

    if release_line == "v2-integration" and target_branch == "main":
        status = "branch_mismatch"
        findings.append(
            finding(
                "v2_work_targets_main",
                number,
                "error",
                "V2 integration work must not target main.",
                expected={"Target branch": V2_INTEGRATION_BRANCH},
                actual={"Target branch": target_branch},
            )
        )
    if release_line == "v1.x-maintenance" and target_branch == V2_INTEGRATION_BRANCH:
        status = "branch_mismatch"
        findings.append(
            finding(
                "v1_work_targets_v2",
                number,
                "error",
                "V1.x maintenance work must not target the V2 integration branch unless Architect accepts cross-line scope.",
                expected={"Target branch": "main"},
                actual={"Target branch": target_branch},
            )
        )

    expected_pr_base = pr_target or target_branch
    if item_type == "pr" and expected_pr_base and actual_pr_base and expected_pr_base != "none" and actual_pr_base != expected_pr_base:
        status = "branch_mismatch"
        findings.append(
            finding(
                "wrong_pr_base",
                number,
                "error",
                "PR base does not match the branch contract.",
                expected={"PR base": expected_pr_base},
                actual={"PR base": actual_pr_base},
            )
        )
        repairs.append(branch_readiness_repair("defer_pr_retarget", f"pr:{number}", "PR retarget is unsupported in AF16; route to Architect/Human if product consequences exist"))
    if item_type == "pr" and release_line == "v2-integration" and actual_pr_base == "main":
        status = "branch_mismatch"
        findings.append(
            finding(
                "v2_pr_targets_main",
                number,
                "error",
                "V2 PR targets main; final V2-to-main integration remains a later readiness and Human gate.",
                expected={"PR base": V2_INTEGRATION_BRANCH},
                actual={"PR base": actual_pr_base},
            )
        )

    if branch_strategy in {"stacked-pr", "multi-branch"}:
        action_plan_concepts.append("split_work_recommended")
    if branch_strategy == "stacked-pr":
        action_plan_concepts.append("current_branch_ok" if item_type == "pr" and actual_pr_base == expected_pr_base else "architect_decision_required")
    if branch_strategy == "multi-branch" or len(set([*affected_branches, *verification_branches])) > 1:
        action_plan_concepts.extend(["verify_on_multiple_lines", "split_work_recommended"])
    if forward_merge_expectation and forward_merge_expectation.lower() not in {"none", "n/a", "not required"}:
        action_plan_concepts.append("forward_merge_needed_later")

    local_status = None
    if local_git and local_git.get("status") == "ok":
        local_status = {
            "branch": local_git.get("branch"),
            "branch_family": branch_family(local_git.get("branch")),
            "upstream": local_git.get("upstream"),
            "ahead": local_git.get("ahead", 0),
            "behind": local_git.get("behind", 0),
            "dirty": local_git.get("dirty", False),
            "staged_count": local_git.get("staged_count", 0),
            "unstaged_count": local_git.get("unstaged_count", 0),
            "untracked_count": local_git.get("untracked_count", 0),
            "commit": local_git.get("commit"),
            "worktree_path": local_git.get("worktree_path"),
        }
        if target_branch and local_git.get("branch") == target_branch:
            action_plan_concepts.append("current_branch_ok")
        elif target_branch:
            action_plan_concepts.append("switch_context_required")
        if local_git.get("dirty") or local_git.get("staged_count") or local_git.get("unstaged_count") or local_git.get("untracked_count"):
            status = "dirty_or_ambiguous_worktree" if status == "branch_ready" else status
            findings.append(
                finding(
                    "local_worktree_dirty",
                    number,
                    "warning",
                    "Local checkout has dirty, staged, unstaged, or untracked state; do not silently checkout, reset, clean, merge, or review from it.",
                    expected={"dirty": False, "staged_count": 0, "unstaged_count": 0, "untracked_count": 0},
                    actual=local_status,
                )
            )
        if local_git.get("ahead") or local_git.get("behind"):
            status = "dirty_or_ambiguous_worktree" if status == "branch_ready" else status
            findings.append(
                finding(
                    "local_branch_ahead_or_behind",
                    number,
                    "warning",
                    "Local branch is ahead or behind upstream; report before review, dispatch, or merge requests.",
                    expected={"ahead": 0, "behind": 0},
                    actual={"ahead": local_git.get("ahead", 0), "behind": local_git.get("behind", 0), "upstream": local_git.get("upstream")},
                )
            )
    elif local_git and local_git.get("status") not in {None, "skipped"}:
        status = "remote_degraded" if status == "branch_ready" else status
        findings.append(
            finding(
                "local_git_degraded",
                number,
                "warning",
                "Local git state could not be read; branch readiness must treat local checkout as unknown.",
                expected={"local_git": "ok"},
                actual={"status": local_git.get("status"), "error": local_git.get("error")},
            )
        )

    return {
        "number": number,
        "item_type": item_type,
        "status": status,
        "branch_strategy": branch_strategy,
        "branch_strategy_source": branch_strategy_source,
        "release_line": release_line,
        "target_branch": target_branch,
        "target_branch_source": "legacy:Branch target" if fields.get("legacy_target_field") else ("Target branch" if target_branch else "missing"),
        "affected_branches": affected_branches,
        "verification_branches": verification_branches,
        "pr_target": pr_target,
        "actual_pr_base": actual_pr_base,
        "actual_pr_head": actual_pr_head,
        "head_oid": head_oid,
        "expected_branch_family": release_line or "unknown",
        "actual_pr_base_family": branch_family(actual_pr_base),
        "local_checkout": local_status,
        "action_plan_concepts": sorted(set(action_plan_concepts)),
        "findings": findings,
        "repair_plan": repairs,
    }


def build_branch_readiness(
    issue_rows: list[dict[str, Any]],
    pr_rows: list[dict[str, Any]],
    local_git: dict[str, Any],
    remote_statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = [*(row.get("branch_readiness") for row in issue_rows), *(row.get("branch_readiness") for row in pr_rows)]
    rows = [row for row in rows if isinstance(row, dict)]
    statuses = [row.get("status") for row in rows]
    action_plan_concepts = sorted(
        {
            concept
            for row in rows
            for concept in row.get("action_plan_concepts", [])
        }
    )
    remote_degraded = any(status.get("status") not in {"ok", "skipped", "config_missing"} for status in remote_statuses)
    if remote_degraded:
        overall = "remote_degraded"
    elif any(status == "branch_mismatch" for status in statuses):
        overall = "branch_mismatch"
    elif any(status == "dirty_or_ambiguous_worktree" for status in statuses):
        overall = "dirty_or_ambiguous_worktree"
    elif any(status == "branch_needs_contract" for status in statuses):
        overall = "branch_needs_contract"
    elif any(status == "architect_decision_required" for status in statuses):
        overall = "architect_decision_required"
    elif rows:
        overall = "branch_ready"
    else:
        overall = "blocked" if local_git.get("status") not in {"ok", "skipped"} else "branch_needs_contract"
    return {
        "status": overall,
        "mutation_performed": False,
        "apply_supported_now": False,
        "summary": "Branch readiness is read-only; AF16 reports branch/worktree/PR-target evidence and refuses automated repair/apply.",
        "local_git": local_git,
        "items": rows,
        "action_plan_concepts": action_plan_concepts,
        "forbidden_actions": [
            "checkout/switch",
            "branch/worktree creation",
            "PR retarget",
            "rebase",
            "merge",
            "pull",
            "push except normal task branch push/PR creation",
            "reset",
            "clean",
            "force push",
            "Project repair/apply",
            "V2 implementation",
        ],
    }


def project_availability(project_status: dict[str, Any]) -> str:
    status = project_status.get("status")
    if status == "ok":
        return "ok"
    if status == "degraded":
        return "degraded"
    if status == "config_missing":
        return "config_missing"
    if status in {"permission_denied", "auth_unavailable"}:
        return status
    if status == "skipped":
        return "skipped"
    if status:
        return "unavailable"
    return "unknown"


def source_status(source: str, status: dict[str, Any], attempts: dict[str, Any], fallback: str = "none") -> dict[str, Any]:
    raw_status = status.get("status", "unknown")
    mapped = raw_status
    if raw_status in {"config_missing", "skipped"}:
        mapped = raw_status
    elif raw_status not in {"ok", "unavailable", "degraded", "permission_denied", "auth_unavailable", "transient_failure"}:
        mapped = "unavailable" if raw_status not in {"fixture"} else "ok"
    return {
        "source": source,
        "status": mapped,
        "attempts": attempts.get("attempts", "unknown"),
        "fallback_used": fallback,
        "error": status.get("error"),
    }


def readiness_action_category(finding_item: dict[str, Any]) -> str:
    code = str(finding_item.get("code", ""))
    subject = str(finding_item.get("subject", ""))
    if code in {
        "wrong_pr_base",
        "v2_pr_targets_main",
        "v2_work_targets_main",
        "v1_work_targets_v2",
    }:
        return "unsupported_deferred_repair_apply"
    if code in {
        "branch_contract_missing",
        "legacy_branch_target_field",
        "local_worktree_dirty",
        "local_branch_ahead_or_behind",
        "local_git_degraded",
        "branch_strategy_unknown",
        "branch_strategy_custom",
    }:
        return "agent_handled_existing_workflow"
    if code in {"project_v2_degraded"}:
        return "informational_only"
    if code.startswith("missing_project") or code in {
        "empty_project_field",
        "project_field_mismatch",
        "closed_issue_not_done",
        "open_needs_label_status_mismatch",
    }:
        return "explicit_human_gate"
    if "project_" in subject:
        return "explicit_human_gate"
    return "agent_handled_existing_workflow"


def readiness_owner_for_category(category: str) -> str:
    return {
        "informational_only": "coordinator",
        "agent_handled_existing_workflow": "architect",
        "explicit_human_gate": "human",
        "unsupported_deferred_repair_apply": "architect",
    }.get(category, "architect")


def readiness_workflow_for_category(category: str) -> str:
    return {
        "informational_only": "none",
        "agent_handled_existing_workflow": "child_issue",
        "explicit_human_gate": "hdc",
        "unsupported_deferred_repair_apply": "hold",
    }.get(category, "hold")


def readiness_action(
    title: str,
    category: str,
    why: str,
    evidence_source: str,
    allowed_now: bool,
) -> dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "owner_role": readiness_owner_for_category(category),
        "why": why,
        "existing_workflow": readiness_workflow_for_category(category),
        "allowed_now": allowed_now,
        "evidence_source": evidence_source,
    }


def build_readiness_action_plan(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings") or []
    repairs = payload.get("dry_run_repair_plan") or []
    degraded_sources = [
        source
        for source in payload.get("degraded_sources") or []
        if source.get("status") in {"unavailable", "degraded", "permission_denied", "auth_unavailable", "transient_failure"}
    ]
    project_state = payload.get("observed_github_state", {}).get("project_v2", {})
    branch_state = payload.get("branch_readiness") or {}
    mutation_performed = bool(payload.get("mutation_performed"))
    unsupported_repairs = [repair for repair in repairs if repair.get("apply_supported_now") is False]
    human_gate_findings = [
        finding_item for finding_item in findings if readiness_action_category(finding_item) == "explicit_human_gate"
    ]

    if any(source.get("source") in {"github_rest_labels", "github_rest_issues"} for source in degraded_sources):
        readiness_status = "blocked"
    elif degraded_sources:
        readiness_status = "degraded"
    elif human_gate_findings:
        readiness_status = "needs_human_decision"
    elif findings or repairs:
        readiness_status = "needs_setup"
    else:
        readiness_status = "ready"

    ready_now = [
        "Readiness report is read-only and keeps raw JSON as evidence/debug output.",
        "GitHub issue/PR durable state remains the source of truth.",
    ]
    if project_state.get("availability") in {"config_missing", "skipped"}:
        ready_now.append("Project v2 mirror is optional; missing Project config does not block issue/PR readiness checks.")
    if payload.get("network", {}).get("full_project_scan_performed") is False:
        ready_now.append("No default full Project scan was performed.")
    if branch_state:
        ready_now.append("Branch/worktree/PR-target checks are report-only and do not checkout, retarget, merge, rebase, reset, or clean.")
        if "current_branch_ok" in (branch_state.get("action_plan_concepts") or []):
            ready_now.append("Current branch evidence matches at least one sampled branch contract.")

    blocking_gaps = [
        {
            "code": finding_item.get("code"),
            "subject": finding_item.get("subject") or finding_item.get("issue"),
            "consequence": finding_item.get("message") or "Readiness gap needs routing before the repo is fully ready.",
            "recommended_action": readiness_action_category(finding_item),
        }
        for finding_item in findings
        if readiness_action_category(finding_item) != "informational_only"
    ]
    unknown_or_degraded = [
        {
            "source": source.get("source"),
            "status": source.get("status"),
            "impact": "Recorded as degraded/unknown; do not infer this source is healthy.",
            "safe_fallback": source.get("fallback_used") or "none",
            "error": source.get("error"),
        }
        for source in degraded_sources
    ]
    if project_state.get("availability") in {"config_missing", "skipped", "unknown"}:
        unknown_or_degraded.append(
            {
                "source": "github_graphql_project_v2",
                "status": project_state.get("availability"),
                "impact": "Optional Project mirror was not evaluated; issue/PR evidence may still be usable.",
                "safe_fallback": "github_rest_issue_pr_labels",
                "error": project_state.get("error"),
            }
        )

    recommended_next_actions: list[dict[str, Any]] = []
    if not findings and not degraded_sources:
        recommended_next_actions.append(
            readiness_action(
                "Continue with normal Agent Foundry collaboration workflow.",
                "informational_only",
                "No readiness blocker was found in the sampled evidence.",
                "readiness_summary",
                True,
            )
        )
    for finding_item in findings:
        category = readiness_action_category(finding_item)
        recommended_next_actions.append(
            readiness_action(
                f"Resolve {finding_item.get('code', 'readiness finding')} for {finding_item.get('subject') or finding_item.get('issue')}.",
                category,
                finding_item.get("message") or "Finding needs a routed follow-up before readiness is complete.",
                f"finding:{finding_item.get('code', 'unknown')}",
                category in {"informational_only", "agent_handled_existing_workflow"},
            )
        )
    for source in degraded_sources:
        recommended_next_actions.append(
            readiness_action(
                f"Treat {source.get('source')} as degraded evidence, not a healthy source.",
                "informational_only",
                source.get("error") or "Source was unavailable or degraded during readiness inspection.",
                f"degraded_source:{source.get('source')}",
                True,
            )
        )
    if project_state.get("availability") in {"config_missing", "skipped", "unknown"}:
        recommended_next_actions.append(
            readiness_action(
                "Treat Project v2 mirror setup as optional unless the repo chooses to configure it.",
                "informational_only",
                "Project v2 is not the source of truth for collaboration readiness.",
                "observed_github_state:project_v2",
                True,
            )
        )
    for concept in branch_state.get("action_plan_concepts") or []:
        concept_title = concept.replace("_", " ")
        if concept == "architect_decision_required":
            category = "agent_handled_existing_workflow"
            allowed_now = True
        elif concept in {"switch_context_required", "forward_merge_needed_later"}:
            category = "unsupported_deferred_repair_apply"
            allowed_now = False
        else:
            category = "agent_handled_existing_workflow"
            allowed_now = True
        recommended_next_actions.append(
            readiness_action(
                f"Branch action plan: {concept_title}.",
                category,
                "Branch readiness reports the safe next-action concept only; it does not perform checkout, merge, retarget, or repair.",
                f"branch_readiness:{concept}",
                allowed_now,
            )
        )
    for repair in unsupported_repairs:
        recommended_next_actions.append(
            readiness_action(
                f"Defer live apply for {repair.get('subject')}.",
                "unsupported_deferred_repair_apply",
                "AF15 readiness reports may preview repairs but must not execute them.",
                f"dry_run_repair_plan:{repair.get('action')}",
                False,
            )
        )

    action_categories = sorted({action["category"] for action in recommended_next_actions})
    summary_bits = [
        f"Readiness status: {readiness_status}.",
        f"{len(findings)} finding(s), {len(degraded_sources)} degraded source(s), {len(repairs)} dry-run repair item(s).",
        "Raw JSON remains evidence/debug output; this action plan is the user-facing interpretation layer.",
    ]
    if branch_state:
        summary_bits.append(f"Branch readiness: {branch_state.get('status', 'unknown')}.")
    if readiness_status == "ready":
        summary_bits.append("The sampled repo state is ready for normal collaboration workflow.")
    elif readiness_status == "needs_setup":
        summary_bits.append("Setup gaps can be routed through existing Agent Foundry issue/comment workflow.")
    elif readiness_status == "needs_human_decision":
        summary_bits.append("At least one readiness gap touches a Project/governance surface and should use a Human Decision Contract or equivalent review gate.")
    elif readiness_status == "degraded":
        summary_bits.append("Some optional or remote sources were degraded; do not guess hidden state.")
    else:
        summary_bits.append("Core GitHub readiness sources were unavailable; unblock source access before relying on the report.")

    return {
        "readiness_status": readiness_status,
        "summary": " ".join(summary_bits),
        "ready_now": ready_now,
        "blocking_gaps": blocking_gaps,
        "unknown_or_degraded": unknown_or_degraded,
        "recommended_next_actions": recommended_next_actions,
        "action_categories": action_categories,
        "forbidden_actions": [
            "live repair/apply",
            "Project v2 mutation",
            "branch repair/apply",
            "PR retarget",
            "checkout/switch",
            "rebase/merge/reset/clean",
            "Vault/private/runtime/generated mutation",
            "generated Skill/adapter publish",
            "capability-pack deploy/apply",
            "V2 implementation",
        ]
        + [action for action in branch_state.get("forbidden_actions", []) if action not in {"Project repair/apply", "V2 implementation"}],
        "telemetry": {
            "unknown_not_available_fields": [item["source"] for item in unknown_or_degraded],
            "source_counts": {
                "findings": len(findings),
                "degraded_sources": len(degraded_sources),
                "dry_run_repair_items": len(repairs),
            },
            "mutation_performed": mutation_performed,
        },
    }


BOARD_LANES = [
    "planned",
    "ready",
    "in_progress",
    "tester_evidence",
    "review",
    "architect_acceptance",
    "human_gate",
    "blocked",
    "stale_conflict",
    "done",
    "superseded",
]


def normalize_board_items(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    elif isinstance(data, dict) and "board_items" in data:
        data = data["board_items"]
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        fail("invalid_board_items_json", "Board items JSON must be a list or object with items/board_items")
    return [item for item in data if isinstance(item, dict)]


def issue_url(item: dict[str, Any]) -> str | None:
    return item.get("url") or item.get("html_url") or item.get("github_issue_url")


def issue_pr_url(item: dict[str, Any]) -> str | None:
    return item.get("pull_request", {}).get("url") if isinstance(item.get("pull_request"), dict) else item.get("github_pr_url")


def board_state_from_issue(issue: dict[str, Any], labels: list[str], project_item: dict[str, Any] | None) -> str:
    explicit = issue.get("board_state") or issue.get("lifecycle_state")
    if explicit:
        return str(explicit)
    lowered = {label.lower() for label in labels}
    if issue.get("state", "").upper() == "CLOSED":
        return "done"
    if "superseded" in lowered or "state:superseded" in lowered:
        return "superseded"
    if "blocked" in lowered or "status:blocked" in lowered:
        return "blocked"
    if "needs:human" in lowered:
        return "human_gate"
    if "needs:reviewer" in lowered:
        return "review"
    if "needs:tester" in lowered:
        return "tester_evidence"
    if "needs:architect" in lowered:
        return "architect_acceptance"
    if "needs:implementer" in lowered:
        return "ready"
    roadmap = project_field_value(project_item or {}, "Roadmap Status")
    if roadmap == "In Progress":
        return "in_progress"
    if roadmap == "Done":
        return "done"
    return "planned"


def board_action_for_state(state: str, next_owner: str | None, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    if conflicts:
        return readiness_action(
            "Review conflict evidence before advancing this item.",
            "agent_handled_existing_workflow",
            "Board state has conflict, stale, degraded, or mirror-drift evidence.",
            "foundry_board:conflict",
            True,
        )
    owner = next_owner or "Coordinator"
    titles = {
        "planned": "Wait for dependency release or Architect routing.",
        "ready": f"Dispatch {owner} through the normal issue workflow.",
        "in_progress": f"Wait for {owner} callback or inspect latest evidence.",
        "tester_evidence": "Collect Tester evidence before review or acceptance.",
        "review": "Run Reviewer exact-target review.",
        "architect_acceptance": "Architect should accept, hold, or release downstream work.",
        "human_gate": "Human decision required; surface decision basis and exact approval phrase.",
        "blocked": "Resolve blocker through the owning role before proceeding.",
        "stale_conflict": "Rehydrate durable state and resolve conflict route.",
        "done": "No action required; read completion evidence if needed.",
        "superseded": "Follow the replacement path instead of this item.",
    }
    category = "explicit_human_gate" if state == "human_gate" else "informational_only" if state in {"done", "superseded"} else "agent_handled_existing_workflow"
    return {
        "title": titles.get(state, "Inspect latest evidence and route through normal workflow."),
        "category": category,
        "owner_role": owner.lower(),
        "why": f"Derived from board state `{state}`.",
        "existing_workflow": readiness_workflow_for_category(category),
        "allowed_now": state not in {"blocked"},
        "evidence_source": "foundry_board:derived_state",
    }


def board_mirror_status(issue: dict[str, Any], project_item: dict[str, Any] | None, project_status: dict[str, Any], state: str) -> tuple[str, list[dict[str, Any]]]:
    conflicts: list[dict[str, Any]] = []
    if project_status.get("status") in {"config_missing", "skipped"}:
        return "not_configured", conflicts
    if project_status.get("status") not in {"ok", None}:
        return "degraded", [
            {
                "type": "degraded_source",
                "severity": "warning",
                "message": "Project mirror could not be evaluated.",
                "source": "github_graphql_project_v2",
            }
        ]
    if not project_item:
        return "unknown", conflicts
    status = project_field_value(project_item, "Status")
    roadmap = project_field_value(project_item, "Roadmap Status")
    if issue.get("state", "").upper() == "CLOSED" and (status != "Done" or roadmap != "Done"):
        conflicts.append(
            {
                "type": "project_mirror_drift",
                "severity": "warning",
                "message": "Closed issue is not mirrored as Done in Project fields.",
                "observed_remote": {"Status": status, "Roadmap Status": roadmap},
            }
        )
    if issue.get("state", "").upper() == "OPEN" and (status == "Done" or roadmap == "Done") and state != "done":
        conflicts.append(
            {
                "type": "project_mirror_drift",
                "severity": "warning",
                "message": "Open issue is mirrored as Done in Project fields.",
                "observed_remote": {"Status": status, "Roadmap Status": roadmap},
            }
        )
    return ("drift" if conflicts else "in_sync"), conflicts


def board_item_from_issue(
    issue: dict[str, Any],
    project_item: dict[str, Any] | None,
    project_status: dict[str, Any],
    local_git: dict[str, Any],
) -> dict[str, Any]:
    labels = label_names(issue)
    body = issue.get("body") or ""
    branch = extract_branch_contract(body)
    branch_fields = branch.get("fields") or {}
    state = board_state_from_issue(issue, labels, project_item)
    next_owner = owner_from_needs(next((label for label in labels if label.startswith("needs:")), None))
    if not next_owner:
        next_owner = project_field_value(project_item or {}, "Owner Role")
    contract = validate_execution_contract(body)
    branch_eval = evaluate_branch_contract(issue, "issue", local_git if local_git.get("status") == "ok" else None)
    mirror_status, conflicts = board_mirror_status(issue, project_item, project_status, state)
    if contract["status"] in {"missing", "invalid"} and state not in {"done", "superseded"}:
        conflicts.append(
            {
                "type": "missing_or_invalid_contract",
                "severity": "warning",
                "message": "Issue lacks a valid machine-readable Execution Contract.",
                "contract_validation": contract["status"],
            }
        )
    if branch_eval["status"] not in {"branch_ready"}:
        conflicts.append(
            {
                "type": "branch_readiness",
                "severity": "warning",
                "message": "Branch readiness is not clean for this item.",
                "branch_status": branch_eval["status"],
            }
        )
    if conflicts and state not in {"blocked", "done", "superseded"}:
        state = "stale_conflict"
    evidence_refs = []
    if issue_url(issue):
        evidence_refs.append({"label": f"GitHub issue #{issue_number(issue)}", "source_type": "github_issue", "url_or_path": issue_url(issue), "availability": "available"})
    if issue_pr_url(issue):
        evidence_refs.append({"label": "Linked pull request", "source_type": "github_pr", "url_or_path": issue_pr_url(issue), "availability": "available"})
    latest_evidence = evidence_refs[0] if evidence_refs else {"label": "Issue metadata", "source_type": "github_issue", "availability": "available" if issue else "unknown"}
    confidence = issue.get("confidence") or issue.get("source_confidence") or ("observed" if issue.get("number") else "unknown")
    state_authority = issue.get("state_authority") or issue.get("migration_state") or ("candidate" if "migration_candidate" in labels else "accepted")
    action = board_action_for_state(state, next_owner, conflicts)
    return {
        "board_item_id": f"issue:{issue_number(issue)}" if issue_number(issue) is not None else issue.get("local_id", "issue:unknown"),
        "work_item_id": issue.get("local_id") or (f"github-issue-{issue_number(issue)}" if issue_number(issue) is not None else "unknown"),
        "title": issue.get("title"),
        "item_kind": "migration_candidate" if state_authority == "candidate" else ("epic" if "type:epic" in labels else "issue"),
        "github_issue_url": issue_url(issue),
        "github_pr_url": issue_pr_url(issue),
        "labels": labels,
        "state": state,
        "lane": state if state in BOARD_LANES else "planned",
        "owner_role": project_field_value(project_item or {}, "Owner Role") or next_owner,
        "next_owner_role": next_owner,
        "roadmap_status": project_field_value(project_item or {}, "Roadmap Status"),
        "stage": stage_from_labels(labels),
        "risk": risk_from_labels(labels),
        "target_branch": branch_fields.get("Target branch"),
        "branch_readiness": branch_eval["status"],
        "latest_evidence": latest_evidence,
        "evidence_refs": evidence_refs,
        "blocking_reason": "; ".join(conflict.get("message", "") for conflict in conflicts if conflict.get("severity") == "blocker") or None,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "mirror_status": mirror_status,
        "confidence": confidence,
        "state_authority": state_authority,
        "recommended_next_actions": [action],
        "forbidden_actions": [
            "live repair/apply",
            "Project v2 mutation",
            "GitHub write-back",
            "branch repair/apply",
            "PR retarget",
            "checkout/switch",
            "rebase/merge/reset/clean",
            "Vault/private/runtime/generated mutation",
            "generated Skill/adapter publish",
            "capability-pack deploy/apply",
        ],
    }


def build_foundry_board(
    repo: str,
    issues: list[dict[str, Any]],
    project_items: list[dict[str, Any]],
    project_status: dict[str, Any],
    local_git: dict[str, Any],
    board_name: str,
    scope: dict[str, Any],
) -> dict[str, Any]:
    project_by_issue = {project_item_issue_number(item): item for item in project_items if project_item_issue_number(item) is not None}
    items = [
        board_item_from_issue(issue, project_by_issue.get(issue_number(issue)), project_status, local_git)
        for issue in issues
    ]
    lanes = [
        {
            "lane": lane,
            "items": [item["board_item_id"] for item in items if item["lane"] == lane],
            "count": sum(1 for item in items if item["lane"] == lane),
        }
        for lane in BOARD_LANES
    ]
    conflict_items = [item for item in items if item["conflict_count"]]
    human_gate_items = [item for item in items if item["state"] == "human_gate"]
    candidate_items = [item for item in items if item["state_authority"] == "candidate"]
    accepted_items = [item for item in items if item["state_authority"] == "accepted"]
    mirror_statuses = sorted({item["mirror_status"] for item in items})
    return {
        "schema_version": 1,
        "command": "foundry-board",
        "repo": repo,
        "board": {
            "name": board_name,
            "authority_statement": "local_ledger_authoritative_when_available_read_only_preview_now",
            "source_of_truth": "local_collaboration_ledger_events",
            "github_project_role": "optional_visual_mirror",
            "scope": scope,
        },
        "mode": "read_only",
        "mutation_performed": False,
        "apply_supported_now": False,
        "items": items,
        "lanes": lanes,
        "summary": {
            "item_count": len(items),
            "candidate_count": len(candidate_items),
            "accepted_count": len(accepted_items),
            "conflict_count": len(conflict_items),
            "human_gate_count": len(human_gate_items),
            "mirror_statuses": mirror_statuses,
            "read_only_board_ready": True,
        },
        "user_next_actions": [
            item["recommended_next_actions"][0]
            for item in items
            if item.get("recommended_next_actions")
        ],
        "unknown_or_degraded": [
            {
                "source": "github_graphql_project_v2",
                "status": project_status.get("status"),
                "impact": "Project mirror is optional; Board can still render issue-derived state.",
                "safe_fallback": "github_issue_pr_evidence",
                "error": project_status.get("error"),
            }
        ]
        if project_status.get("status") in {"config_missing", "skipped", "degraded", "unavailable", "permission_denied", "auth_unavailable"}
        else [],
        "forbidden_actions": [
            "live repair/apply",
            "Project v2 mutation",
            "GitHub write-back",
            "real migration/backfill write",
            "branch repair/apply",
            "checkout/switch",
            "PR retarget",
            "rebase/merge/reset/clean",
            "runtime/Vault/private/generated mutation",
            "generated Skill/adapter publish",
            "capability-pack deploy/apply",
        ],
        "telemetry": {
            "full_project_scan_performed": False,
            "mutation_performed": False,
            "implementation_slice": "V2-5 read-only Foundry Board MVP",
            "unknown_not_available_fields": ["exact_elapsed_time", "exact_api_call_count", "billing_grade_token_count"],
        },
    }


def cmd_foundry_board(args: argparse.Namespace) -> None:
    repo, repo_source = resolve_repo(args)
    if args.board_items_json:
        issues = normalize_board_items(load_json(args.board_items_json))
        scope = {"mode": "board_items_fixture", "item_count": len(issues)}
        project_items: list[dict[str, Any]] = []
        project_status = {"source": "skipped", "status": "skipped", "item_count": 0}
    elif args.issues_json or args.fixture_json:
        issues = normalize_issue_collection(load_json(args.issues_json or args.fixture_json))
        scope = {"mode": "fixture", "issue_numbers": [issue_number(issue) for issue in issues if issue_number(issue) is not None]}
        project_items, project_status, _project_attempts = read_project_items(args)
    else:
        issues, scope = read_live_issues(repo, args)
        project_items, project_status, _project_attempts = read_project_items(args)
    local_git, _local_git_status, _local_git_attempts = read_local_git_state(args)
    board = build_foundry_board(repo, issues[: args.limit], project_items, project_status, local_git, args.name, {"repo_source": repo_source, **scope})
    print_json_or_text(board, args.json)


def cmd_collaboration_readiness(args: argparse.Namespace) -> None:
    repo, repo_source = resolve_repo(args)
    config = parse_simple_yaml(Path(args.config)) if args.config else {}
    config_errors = role_config_errors(config) if config else ["role routing config missing"]
    expected_needs = set(config.get("needs_labels", [])) or set(READINESS_NEEDS_LABELS)

    labels, labels_status, labels_attempts = read_readiness_labels(repo, args)
    issues, issues_status, issues_attempts = read_readiness_issues(repo, args)
    prs, prs_status, prs_attempts = read_readiness_prs(repo, args)
    project_items, project_status, project_attempts = read_project_items(args)
    local_git, local_git_status, local_git_attempts = read_local_git_state(args)

    findings: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    for error in config_errors:
        findings.append(
            {
                "severity": "error",
                "code": "role_config_invalid",
                "subject": "local_template",
                "expected": {"config": "valid role routing template"},
                "actual": {"error": error},
            }
        )
        repairs.append(readiness_repair("update_role_config", "routing_template", error, "local_template"))

    label_set = set(labels)
    for label in sorted(expected_needs):
        if label not in label_set:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_needs_label",
                    "subject": f"label:{label}",
                    "expected": {"label": label},
                    "actual": {"present": False},
                }
            )
            repairs.append(readiness_repair("create_label", f"label:{label}", f"create missing role label {label}", "github_rest_labels"))

    project_requested = project_status.get("source") in ("fixture", "live_gh") and project_status.get("status") == "ok"
    project_by_issue = {project_item_issue_number(item): item for item in project_items if project_item_issue_number(item) is not None}
    issue_rows = [
        readiness_contract_summary(
            issue,
            expected_needs,
            project_item=project_by_issue.get(issue_number(issue)),
            project_requested=project_requested,
            default_stage=args.stage,
            item_type="issue",
            local_git=local_git,
        )
        for issue in issues[: args.limit]
    ]
    pr_rows = [
        readiness_contract_summary(pr, expected_needs, item_type="pr", local_git=local_git)
        for pr in prs[: args.limit]
    ]
    for row in (*issue_rows, *pr_rows):
        findings.extend(row["findings"])
        repairs.extend(row["repair_plan"])

    project_fields_seen = project_status.get("fields_seen") or sorted({field for item in project_items for field in READINESS_PROJECT_FIELDS if project_field_value(item, field)})
    project_options_seen = project_status.get("options_seen") or []
    project_ok = project_status.get("status") == "ok"
    if project_ok:
        missing_project_fields = sorted(set(READINESS_PROJECT_FIELDS) - set(project_fields_seen))
        for field in missing_project_fields:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_project_field",
                    "subject": f"project_field:{field}",
                    "expected": {"field": field},
                    "actual": {"present": False},
                }
            )
            repairs.append(readiness_repair("create_project_field", f"project_field:{field}", f"create Project mirror field {field}", "github_graphql_project_v2"))
        if project_status.get("explicit_metadata"):
            missing_role_options = sorted(set(READINESS_PROJECT_OPTIONS) - set(project_options_seen))
            for option in missing_role_options:
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_project_role_option",
                        "subject": f"project_option:Owner Role:{option}",
                        "expected": {"Owner Role": option},
                        "actual": {"present": False},
                    }
                )
                repairs.append(
                    readiness_repair(
                        "create_project_option",
                        f"project_option:Owner Role:{option}",
                        f"create Owner Role option {option}",
                        "github_graphql_project_v2",
                    )
                )
    if project_status.get("source") == "live_gh" and not project_ok:
        findings.append(
            {
                "severity": "warning",
                "code": "project_v2_degraded",
                "subject": "project_v2",
                "expected": {"availability": "ok or config_missing"},
                "actual": {"availability": project_availability(project_status), "error": project_status.get("error")},
            }
        )

    status = "ok"
    degraded = any(
        source.get("status") in {"unavailable", "permission_denied", "auth_unavailable", "transient_failure"}
        for source in (labels_status, issues_status, prs_status)
    ) or project_availability(project_status) in {"unavailable", "permission_denied", "auth_unavailable", "degraded"}
    if findings:
        status = "findings"
    if degraded:
        status = "degraded"

    local_template_status = "ok" if not config_errors else "unavailable"
    if not args.config:
        local_template_status = "config_missing"
    branch_readiness = build_branch_readiness(
        issue_rows,
        pr_rows,
        local_git,
        [labels_status, issues_status, prs_status],
    )

    payload = {
        "schema_version": 1,
        "command": "collaboration-readiness",
        "repo": repo,
        "repo_source": repo_source,
        "status": status,
        "mutation_performed": False,
        "mode": "read_only",
        "checked_at": "unknown",
        "expected_collaboration_model": {
            "roles": READINESS_ROLES,
            "needs_labels": sorted(expected_needs),
            "project_fields": READINESS_PROJECT_FIELDS,
            "project_options": READINESS_PROJECT_OPTIONS,
            "execution_contract_values": {
                "Owner role": sorted(VALID_ROLE_VALUES_BY_FIELD["Owner role"]),
                "Review role": sorted(VALID_ROLE_VALUES_BY_FIELD["Review role"]),
                "Acceptance role": sorted(VALID_ROLE_VALUES_BY_FIELD["Acceptance role"]),
                "Completion handoff": sorted(VALID_COMPLETION_HANDOFFS),
            },
            "testing_contract_values": {
                "Testing Responsibility": ["tester"],
                "Test Evidence Handoff.to": ["reviewer", "architect", "implementer", "human"],
            },
            "branch_contract_values": {
                "Branch strategy": BRANCH_STRATEGIES,
                "Release line": ["v1.x-maintenance", "v2-integration", "cross-line"],
                "Target branch": ["main", V2_INTEGRATION_BRANCH, "<integration-branch>"],
                "Affected branches": ["optional comma-separated branch list for multi-branch work"],
                "Verification branches": ["optional comma-separated branch list for ordered verification"],
                "legacy_input_mapping": {"Branch target": "Target branch"},
                "agent_foundry_presets": {
                    "v1.x-maintenance": {"Branch strategy": "mainline-maintenance", "Target branch": "main"},
                    "v2-integration": {"Branch strategy": "integration-branch", "Target branch": V2_INTEGRATION_BRANCH},
                },
            },
        },
        "observed_github_state": {
            "labels": sorted(labels),
            "issues_sampled": [row["number"] for row in issue_rows],
            "prs_sampled": [row["number"] for row in pr_rows],
            "project_v2": {
                "availability": project_availability(project_status),
                "fields_seen": project_fields_seen,
                "options_seen": project_options_seen,
                "item_count": project_status.get("item_count", "unknown"),
                "source": project_status.get("source"),
                "error": project_status.get("error"),
                "metadata_source": "explicit" if project_status.get("explicit_metadata") else "observed_items",
            },
            "local_git": local_git,
        },
        "routing_state": {
            "issues": issue_rows,
            "prs": pr_rows,
        },
        "branch_readiness": branch_readiness,
        "findings": findings,
        "dry_run_repair_plan": repairs,
        "degraded_sources": [
            source_status("github_rest_labels", labels_status, labels_attempts),
            source_status("github_rest_issues", issues_status, issues_attempts),
            source_status("github_rest_prs", prs_status, prs_attempts),
            source_status("github_graphql_project_v2", {"status": project_availability(project_status), **project_status}, project_attempts),
            source_status("local_template", {"status": local_template_status}, {"attempts": 1 if args.config else 0}),
            source_status("local_git", local_git_status, local_git_attempts),
        ],
        "network": {
            "strategy": "rest_first_targeted_graphql",
            "bounded_retries": True,
            "full_project_scan_performed": False,
        },
        "v2_migration": {
            "local_ledger_candidate": True,
            "backfill_keys": [
                "issue_number",
                "pr_number",
                "role",
                "needs_label",
                "contract_values",
                "project_mirror_values",
                "release_line",
                "target_branch",
                "pr_target",
                "actual_pr_base",
                "actual_pr_head",
                "local_branch",
                "local_worktree_path",
                "local_commit",
                "findings",
            ],
        },
        "residual_risks": [
            "Project v2 is an optional visual mirror and may be unavailable without blocking issue/PR readiness findings.",
            "Branch readiness is report-only and cannot prove hidden remote branch state beyond sampled issue/PR/local git evidence.",
        ],
        "next_safe_actions": [
            "Review findings and dry_run_repair_plan; apply remains unsupported in AF15/AF16 readiness reports.",
            "Use existing issue/PR workflow for branch contract fixes; branch repair/apply and PR retarget remain unsupported.",
        ],
    }
    action_plan = build_readiness_action_plan(payload)
    payload["readiness_status"] = action_plan["readiness_status"]
    payload["summary"] = action_plan["summary"]
    payload["user_readiness_action_plan"] = action_plan
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

    readiness = sub.add_parser("collaboration-readiness")
    readiness.add_argument("--config")
    readiness.add_argument("--labels-json", help="Fixture repo labels as a list or object with labels.")
    readiness.add_argument("--fixture-json", help="Legacy single-issue fixture; prefer --issues-json for new tests.")
    readiness.add_argument("--issues-json", help="Fixture issue object, list, or object with issues/items.")
    readiness.add_argument("--prs-json", help="Fixture PR object, list, or object with issues/items.")
    readiness.add_argument("--local-git-json", help="Fixture local git state for branch-readiness tests.")
    readiness.add_argument("--project-items-json", help="Fixture Project item list or gh project item-list JSON.")
    readiness.add_argument("--issues", help="Comma-separated explicit issue numbers for bounded live readiness audit.")
    readiness.add_argument("--prs", help="Comma-separated explicit PR numbers for bounded live readiness audit.")
    readiness.add_argument("--stage", help="Stage value or label for bounded live issue audit.")
    readiness.add_argument("--limit", type=int, default=20, help="Maximum issues/PRs to audit.")
    readiness.add_argument("--project-owner", help="Project owner for targeted live Project item-list, such as @me or an org.")
    readiness.add_argument("--project-number", type=int, help="Project number for targeted live Project item-list.")
    readiness.add_argument("--project-limit", type=int, default=50, help="Maximum Project items to read when explicitly configured.")
    readiness.add_argument("--project-retries", type=int, default=2, help="Bounded retries for transient Project reads.")
    readiness.add_argument("--project-retry-backoff", type=float, default=0.5, help="Seconds between transient Project read retries.")
    readiness.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON for collaboration-readiness.")
    readiness.set_defaults(func=cmd_collaboration_readiness)

    board = sub.add_parser("foundry-board")
    board.add_argument("--config", help="Reserved for future board config; currently informational.")
    board.add_argument("--fixture-json", help="Legacy issue fixture; prefer --issues-json or --board-items-json for tests.")
    board.add_argument("--issues-json", help="Fixture issue object, list, or object with issues/items.")
    board.add_argument("--board-items-json", help="Fixture board items in issue-like or board item form.")
    board.add_argument("--project-items-json", help="Fixture Project item list or gh project item-list JSON.")
    board.add_argument("--local-git-json", help="Fixture local git state for branch/readiness display.")
    board.add_argument("--issues", help="Comma-separated explicit issue numbers for bounded live board report.")
    board.add_argument("--stage", help="Stage value or label for bounded live issue report.")
    board.add_argument("--limit", type=int, default=20, help="Maximum issues/items to render.")
    board.add_argument("--project-owner", help="Project owner for targeted live Project item-list, such as @me or an org.")
    board.add_argument("--project-number", type=int, help="Project number for targeted live Project item-list.")
    board.add_argument("--project-limit", type=int, default=50, help="Maximum Project items to read when explicitly configured.")
    board.add_argument("--project-retries", type=int, default=2, help="Bounded retries for transient Project reads.")
    board.add_argument("--project-retry-backoff", type=float, default=0.5, help="Seconds between transient Project read retries.")
    board.add_argument("--name", default="Foundry Board", help="Board name shown in the read-only report.")
    board.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON for foundry-board.")
    board.set_defaults(func=cmd_foundry_board)

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
