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
READ_ONLY_ACTIONS = {"repo-resolve", "auth-smoke", "role-config-check", "inbox", "issue-context", "scheduler-audit"}
DRY_RUN_ACTIONS = {
    "handoff-draft",
    "dispatch-evidence-draft",
    "release-next-draft",
    "permission-smoke",
    "comparison-draft",
}
REMOTE_RE = re.compile(r"(?:github\.com[:/])([^/]+)/([^/.]+)(?:\.git)?$")


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
                "number,title,labels,updatedAt",
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
    print_json_or_text(
        {
            "repo": repo,
            "issue": issue.get("number", args.issue),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "labels": labels,
            "contract_hints": contract_hints,
            "comment_count_returned": len(comments),
            "summary_is_authority": False,
            "mutation_performed": False,
        },
        args.json,
    )


def cmd_scheduler_audit(args: argparse.Namespace) -> None:
    fixture = load_json(args.fixture_json)
    if fixture is None:
        fail("fixture_required", "scheduler-audit Unit B pilot requires --fixture-json or a later accepted live-read design")
    labels = [label["name"] if isinstance(label, dict) else label for label in fixture.get("labels", [])]
    config = parse_simple_yaml(Path(args.config)) if args.config else {}
    needs = set(config.get("needs_labels", []))
    present = sorted(set(labels).intersection(needs))
    findings = []
    if len(present) > 1:
        findings.append("multiple_needs_labels")
    if fixture.get("state", "").upper() == "CLOSED" and present:
        findings.append("closed_issue_has_needs_label")
    if not present:
        findings.append("no_next_owner_label")
    payload = {
        "issue": fixture.get("number"),
        "findings": findings,
        "next_owner_labels": present,
        "project_v2": "optional_project_mirror_unavailable",
        "overhead_class": "state_sync_cost" if findings else "necessary_delivery_cost",
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
    audit.add_argument("--fixture-json", required=True)
    audit.set_defaults(func=cmd_scheduler_audit)

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
