#!/usr/bin/env python3
"""Regression fixtures for the AF11 GitHub collaboration helper pilot."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "github_collaboration_helper.py"
TEMPLATE = ROOT / "templates" / "github-role-routing.template.yaml"


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=merged_env,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def expect_ok(name: str, result: subprocess.CompletedProcess[str], expected: str) -> list[str]:
    output = result.stdout + result.stderr
    if result.returncode == 0 and expected in output:
        print(f"{name}: ok")
        return []
    return [f"{name}: expected success containing {expected!r}, got {result.returncode}\n{output}"]


def expect_fail(name: str, result: subprocess.CompletedProcess[str], expected: str) -> list[str]:
    output = result.stdout + result.stderr
    if result.returncode != 0 and expected in output:
        print(f"{name}: ok")
        return []
    return [f"{name}: expected failure containing {expected!r}, got {result.returncode}\n{output}"]


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-gh-helper-") as tmp:
        base = Path(tmp)
        fixture = base / "issue.json"
        audit_issues = base / "audit-issues.json"
        audit_project = base / "audit-project.json"
        inbox = base / "inbox.json"
        auth = base / "auth.json"
        runtime_skill = base / "runtime-skill.md"
        generated_skill = base / "generated-skill.md"
        launcher = base / "bin" / "agent-foundry-github-collab"
        fake_bin = base / "fake-bin"
        fake_gh = fake_bin / "gh"
        write(auth, json.dumps({"status": "ok", "nameWithOwner": "farmerhunter/agent-foundry"}))
        write(
            runtime_skill,
            "activation evidence\n target runtime\n user-facing activation instructions\n",
        )
        write(
            generated_skill,
            "activation evidence\n target runtime\n user-facing activation instructions\n",
        )
        write(launcher, "#!/bin/sh\nexit 0\n")
        write(fake_gh, "#!/bin/sh\nprintf '%s\\n' 'EOF while reading Project v2' >&2\nexit 1\n")
        fake_gh.chmod(0o755)
        write(
            fixture,
            json.dumps(
                {
                    "number": 205,
                    "title": "Unit B",
                    "state": "OPEN",
                    "labels": [{"name": "needs:implementer"}, {"name": "stage:AF-11"}],
                    "body": "## Execution Contract\n\n## Acceptance Criteria\n\n## Depends On",
                    "comments": [{"body": "latest"}, {"body": "older"}],
                }
            ),
        )
        write(
            audit_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 224,
                            "title": "Missing Project item",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                        },
                        {
                            "number": 225,
                            "title": "Empty Owner Role",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:reviewer"}],
                        },
                        {
                            "number": 226,
                            "title": "Closed but ready",
                            "state": "CLOSED",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}],
                        },
                        {
                            "number": 227,
                            "title": "Open done",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                        },
                        {
                            "number": 228,
                            "title": "Multiple needs",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "needs:architect"}, {"name": "needs:reviewer"}],
                        },
                        {
                            "number": 229,
                            "title": "No next owner",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "type:task"}],
                        },
                    ]
                }
            ),
        )
        write(
            audit_project,
            json.dumps(
                {
                    "items": [
                        {
                            "content": {"number": 225},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "AF-11"},
                            "owner Role": None,
                            "risk": {"name": "Medium"},
                        },
                        {
                            "content": {"number": 226},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "AF-11"},
                            "owner Role": {"name": "Reviewer"},
                            "risk": {"name": "Medium"},
                        },
                        {
                            "content": {"number": 227},
                            "status": {"name": "Done"},
                            "roadmap Status": {"name": "Done"},
                            "stage": {"name": "AF-10"},
                            "owner Role": {"name": "Reviewer"},
                            "risk": {"name": "Medium"},
                        },
                        {
                            "content": {"number": 228},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "AF-11"},
                            "owner Role": {"name": "Architect"},
                            "risk": {"name": "Medium"},
                        },
                        {
                            "content": {"number": 229},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "AF-11"},
                            "owner Role": {"name": "Implementer"},
                            "risk": {"name": "Medium"},
                        },
                    ]
                }
            ),
        )
        write(
            inbox,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 205,
                            "title": "Unit B",
                            "labels": [{"name": "needs:implementer"}],
                            "updatedAt": "2026-06-18T00:00:00Z",
                        },
                        {
                            "number": 206,
                            "title": "Evidence",
                            "labels": [{"name": "stage:AF-11"}],
                            "updatedAt": "2026-06-18T00:00:00Z",
                        },
                    ]
                }
            ),
        )
        bad_config = base / "bad-routing.yaml"
        legacy_config = base / "legacy-routing.yaml"
        write(
            bad_config,
            "\n".join(
                [
                    "schema_version: 1",
                    "roles:",
                    "  reviewer:",
                    "    review_target: missing label",
                    "needs_labels: []",
                    "project_v2:",
                    "  mode: required_scheduler",
                ]
            ),
        )
        write(
            legacy_config,
            "\n".join(
                [
                    "schema_version: 1",
                    "roles:",
                    "  reviewer:",
                    "    inbox_label: needs:reviewer",
                    "needs_labels:",
                    "  - needs:reviewer",
                    "completion_handoff:",
                    "  required_fields:",
                    "    - workflow_telemetry",
                    "telemetry:",
                    "  required_for_meaningful_transitions: true",
                    "project_v2:",
                    "  mode: optional_visual_mirror",
                ]
            ),
        )

        errors.extend(
            expect_ok(
                "repo-env-resolve",
                run(["--json", "repo-resolve"], base, {"AGENT_REPO": "farmerhunter/agent-foundry"}),
                '"source": "AGENT_REPO"',
            )
        )
        git_repo = base / "git-repo"
        git_repo.mkdir()
        subprocess.run(["git", "init"], cwd=git_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:farmerhunter/agent-foundry.git"],
            cwd=git_repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        errors.extend(
            expect_ok(
                "repo-git-remote-resolve",
                run(["repo-resolve"], git_repo, {"AGENT_REPO": ""}),
                "source: current_git_remote_after_confirmation",
            )
        )
        errors.extend(
            expect_ok(
                "auth-fixture",
                run(["--repo", "farmerhunter/agent-foundry", "auth-smoke", "--fixture-json", str(auth)], base),
                "read_permission: ok",
            )
        )
        errors.extend(
            expect_ok(
                "role-config-template",
                run(["role-config-check", "--config", str(TEMPLATE)], base),
                "status: ok",
            )
        )
        errors.extend(
            expect_fail(
                "role-config-fails-closed",
                run(["role-config-check", "--config", str(bad_config)], base),
                "status: invalid",
            )
        )
        errors.extend(
            expect_ok(
                "role-config-legacy-comparison-optional",
                run(["role-config-check", "--config", str(legacy_config)], base),
                "status: ok",
            )
        )
        errors.extend(
            expect_ok(
                "inbox-fixture",
                run(
                    [
                        "--repo",
                        "farmerhunter/agent-foundry",
                        "inbox",
                        "--config",
                        str(TEMPLATE),
                        "--fixture-json",
                        str(inbox),
                    ],
                    base,
                ),
                "needs:implementer",
            )
        )
        errors.extend(
            expect_ok(
                "issue-context-fixture",
                run(["--repo", "farmerhunter/agent-foundry", "issue-context", "205", "--fixture-json", str(fixture)], base),
                "summary_is_authority: False",
            )
        )
        errors.extend(
            expect_ok(
                "scheduler-audit-fixture",
                run(
                    [
                        "--repo",
                        "farmerhunter/agent-foundry",
                        "scheduler-audit",
                        "--config",
                        str(TEMPLATE),
                        "--fixture-json",
                        str(fixture),
                    ],
                    base,
                ),
                "mutation_performed: False",
            )
        )
        scheduler_json = run(
            [
                "scheduler-audit",
                "--config",
                str(TEMPLATE),
                "--issues-json",
                str(audit_issues),
                "--project-items-json",
                str(audit_project),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for code in (
            "missing_project_item",
            "empty_project_field",
            "project_field_mismatch",
            "closed_issue_not_done",
            "open_needs_label_status_mismatch",
            "multiple_needs_labels",
            "no_next_owner_label",
        ):
            errors.extend(expect_ok(f"scheduler-audit-{code}", scheduler_json, f'"code": "{code}"'))
        errors.extend(expect_ok("scheduler-audit-json-status", scheduler_json, '"status": "findings"'))
        errors.extend(expect_ok("scheduler-audit-json-no-mutation", scheduler_json, '"mutation_performed": false'))
        degraded = run(
            [
                "scheduler-audit",
                "--config",
                str(TEMPLATE),
                "--issues-json",
                str(audit_issues),
                "--project-owner",
                "@me",
                "--project-number",
                "3",
                "--project-retries",
                "1",
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry", "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
        )
        errors.extend(expect_ok("scheduler-audit-project-degraded", degraded, '"status": "degraded"'))
        errors.extend(expect_ok("scheduler-audit-project-unavailable", degraded, '"availability": "unavailable"'))
        errors.extend(expect_ok("scheduler-audit-project-read-once", degraded, '"attempts": 1'))
        errors.extend(
            expect_ok(
                "activation-report-fixture",
                run(
                    [
                        "activation-report",
                        "--launcher",
                        str(launcher),
                        "--runtime-skill",
                        str(runtime_skill),
                        "--generated-skill",
                        str(generated_skill),
                    ],
                    base,
                ),
                "user_entrypoint:",
            )
        )
        errors.extend(
            expect_fail(
                "permission-forbidden",
                run(["permission-smoke", "agent-label"], base),
                "unit_b_forbidden_mutation",
            )
        )
        errors.extend(
            expect_fail(
                "permission-project-write-forbidden",
                run(["permission-smoke", "project-write"], base),
                "unit_b_forbidden_mutation",
            )
        )
        errors.extend(
            expect_ok(
                "permission-comparison-dry-run",
                run(["permission-smoke", "comparison-draft"], base),
                "dry_run_allowed",
            )
        )
        errors.extend(
            expect_ok(
                "handoff-draft",
                run(
                    [
                        "handoff-draft",
                        "--issue",
                        "205",
                        "--parent-issue",
                        "201",
                        "--next-owner",
                        "Reviewer",
                        "--scope",
                        "Unit B helper",
                    ],
                    base,
                ),
                "workflow_telemetry:",
            )
        )
        errors.extend(
            expect_ok(
                "dispatch-draft-no-dispatch",
                run(["dispatch-evidence-draft", "--issue", "205", "--mode", "generated_note"], base),
                "no dispatch occurred",
            )
        )
        errors.extend(
            expect_ok(
                "release-draft-no-write",
                run(
                    [
                        "release-next-draft",
                        "--issue",
                        "205",
                        "--next-issue",
                        "206",
                        "--dependency",
                        "#205 complete",
                    ],
                    base,
                ),
                "no labels, comments, Project fields",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-draft",
                run(
                    [
                        "comparison-draft",
                        "--subject",
                        "AF10 #215 telemetry comparison",
                        "--unit",
                        "issue_batch",
                        "--issue-count",
                        "4",
                        "--single-agent-transitions",
                        "2",
                        "--unoptimized-transitions",
                        "8",
                        "--unoptimized-full-rehydrates",
                        "6",
                        "--optimized-transitions",
                        "4",
                        "--optimized-compact-rehydrates",
                        "4",
                        "--optimized-full-rehydrates",
                        "0",
                        "--quality-benefit",
                        "preserved independent review only where useful",
                    ],
                    base,
                ),
                "workflow_comparison_telemetry:",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-draft-three-modes",
                run(["comparison-draft", "--subject", "AF10 #215"], base),
                "unoptimized_collaboration_counterfactual:",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-draft-no-write",
                run(["comparison-draft", "--subject", "AF10 #215"], base),
                "no comments, labels, Project fields",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-negative-quality-insufficient",
                run(
                    [
                        "comparison-draft",
                        "--subject",
                        "AF10 #215 quality guardrail",
                        "--human-holds",
                        "1",
                        "--unoptimized-transitions",
                        "8",
                        "--optimized-transitions",
                        "4",
                    ],
                    base,
                ),
                "recommendation: insufficient_data",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-unknown-benefit-prefers-single-agent",
                run(
                    [
                        "comparison-draft",
                        "--subject",
                        "AF10 #215 unknown benefit",
                        "--single-agent-transitions",
                        "1",
                        "--unoptimized-transitions",
                        "8",
                        "--unoptimized-full-rehydrates",
                        "6",
                        "--optimized-transitions",
                        "4",
                        "--optimized-full-rehydrates",
                        "0",
                    ],
                    base,
                ),
                "recommendation: single_agent",
            )
        )

    if errors:
        print("GitHub collaboration helper fixture tests failed:")
        for error in errors:
            print(error)
        return 1
    print("GitHub collaboration helper fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
