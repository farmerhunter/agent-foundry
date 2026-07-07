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
WORKFLOW = ROOT / "workflows" / "github-collaboration-helper.md"


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


def expect_text_contains(name: str, text: str, snippets: list[str]) -> list[str]:
    missing = [snippet for snippet in snippets if snippet not in text]
    if not missing:
        print(f"{name}: ok")
        return []
    return [f"{name}: missing {missing!r}"]


def main() -> int:
    errors: list[str] = []
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")
    errors.extend(
        expect_text_contains(
            "github-operation-policy-workflow",
            workflow_text,
            [
                "GitHub Operation Policy",
                "Each role/session must discover",
                "GitHub connector or structured tools",
                "repo-local helper paths first",
                "controlled `gh api` with a body-file or structured JSON payload",
                "bare `gh issue comment --body` only as a last resort",
                "permission-smoke agent-comment",
                "Do not document or imply that `agent-comment --apply`",
                "Project v2 was not meaningfully evaluated",
                "Workflow authorization does not override product/runtime approval prompts",
                "Tester Routing",
                "Do not use `Review role: tester`",
                "Collaboration Readiness",
                "check collaboration readiness for this repo",
                "prepare this repo for multi-agent collaboration",
                "audit existing collaboration setup",
                "`apply_supported_now` set to `false`",
                "Project v2 remains an optional visual mirror",
            ],
        )
    )
    errors.extend(
        expect_text_contains(
            "github-operation-policy-template",
            template_text,
            [
                "operation_policy: \"hybrid_runtime_discovery_then_connector_helper_api_bare_gh\"",
                "tester:",
                "inbox_label: \"needs:tester\"",
                "needs:tester",
                "runtime_discovery_required_per_session: true",
                "connector_preferred_for_low_risk:",
                "helper_first_for:",
                "current_helper_comment_write_apply: false",
                "controlled_gh_api_fallback: \"body_file_or_structured_json_when_connector_unavailable_or_unclear\"",
                "bare_gh_last_resort: \"short_low_risk_comments_only_with_bounded_retry_and_failure_recording\"",
                "project_v2_policy: \"optional_visual_mirror_only_no_generalized_write_policy\"",
                "runtime_approval_prompt_boundary: \"workflow_authorization_does_not_override_app_level_approval_prompts\"",
            ],
        )
    )
    with tempfile.TemporaryDirectory(prefix="agent-foundry-gh-helper-") as tmp:
        base = Path(tmp)
        fixture = base / "issue.json"
        audit_issues = base / "audit-issues.json"
        audit_project = base / "audit-project.json"
        readiness_project = base / "readiness-project.json"
        readiness_labels = base / "readiness-labels.json"
        readiness_prs = base / "readiness-prs.json"
        branch_readiness_issues = base / "branch-readiness-issues.json"
        branch_readiness_prs = base / "branch-readiness-prs.json"
        branch_local_git = base / "branch-local-git.json"
        branch_local_clean = base / "branch-local-clean.json"
        new_repo_labels = base / "new-repo-labels.json"
        new_repo_issues = base / "new-repo-issues.json"
        new_repo_prs = base / "new-repo-prs.json"
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
                    "body": "\n".join(
                        [
                            "```markdown",
                            "## Final Execution Contract",
                            "",
                            "Example only; this fenced heading must not be validated.",
                            "```",
                            "",
                            "```text",
                            "## Execution Contract",
                            "Owner role: Implementer",
                            "Completion handoff: move to Review",
                            "```",
                            "",
                            "## Execution Contract",
                            "",
                            "Owner role: implementer",
                            "Review role: reviewer",
                            "Acceptance role: architect",
                            "Completion handoff: to:reviewer",
                            "",
                            "## Acceptance Criteria",
                            "",
                            "## Depends On",
                        ]
                    ),
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
                        {
                            "number": 230,
                            "title": "Uppercase owner role",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\nOwner role: Implementer\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n",
                        },
                        {
                            "number": 231,
                            "title": "Compound acceptance role",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: reviewer\nAcceptance role: architect / user\nCompletion handoff: to:reviewer\nHuman review prompt: ask user after merge\n",
                        },
                        {
                            "number": 232,
                            "title": "Reviewer target without review role",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nAcceptance role: architect\nCompletion handoff: to:reviewer\nReviewer target: separate Reviewer agent\n",
                        },
                        {
                            "number": 233,
                            "title": "Legacy handoff",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-11"}, {"name": "risk:medium"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: move to Review\n",
                        },
                        {
                            "number": 234,
                            "title": "Tester missing contract",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-14"}, {"name": "risk:high"}, {"name": "needs:tester"}],
                            "body": "## Execution Contract\n\nOwner role: tester\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n",
                        },
                        {
                            "number": 235,
                            "title": "Tester as reviewer",
                            "state": "OPEN",
                            "labels": [{"name": "stage:AF-14"}, {"name": "risk:high"}, {"name": "needs:tester"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: tester\nAcceptance role: architect\nCompletion handoff: to:tester\n\n## Testing Contract\n\nTesting Responsibility: tester\nTester Trigger:\n  - stateful workflow risk\nuser_value_or_risk: stale state\n\n## Test Evidence Handoff\n\nto: reviewer\nresult_summary: passed\nresidual_risks: none\n",
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
            readiness_project,
            json.dumps(
                {
                    "fields": [
                        {"name": "Status"},
                        {"name": "Roadmap Status"},
                        {"name": "Stage"},
                        {
                            "name": "Owner Role",
                            "options": [
                                {"name": "Architect"},
                                {"name": "Implementer"},
                                {"name": "Reviewer"},
                                {"name": "Tester"},
                                {"name": "Human"},
                            ],
                        },
                    ],
                    "items": [
                        {
                            "content": {"number": 225},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "AF-11"},
                            "owner Role": None,
                        },
                        {
                            "content": {"number": 227},
                            "status": {"name": "Done"},
                            "roadmap Status": {"name": "Done"},
                            "stage": {"name": "AF-10"},
                            "owner Role": {"name": "Reviewer"},
                        },
                    ],
                }
            ),
        )
        write(
            readiness_labels,
            json.dumps(
                {
                    "labels": [
                        {"name": "needs:architect"},
                        {"name": "needs:implementer"},
                        {"name": "needs:reviewer"},
                        {"name": "needs:tester"},
                        {"name": "needs:human"},
                        {"name": "stage:AF-15"},
                    ]
                }
            ),
        )
        write(new_repo_labels, json.dumps({"labels": []}))
        write(new_repo_issues, json.dumps({"issues": []}))
        write(new_repo_prs, json.dumps({"items": []}))
        write(
            readiness_prs,
            json.dumps(
                {
                    "items": [
                        {
                            "number": 42,
                            "title": "Ready PR",
                            "state": "OPEN",
                            "labels": [{"name": "needs:reviewer"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n",
                            "headRefOid": "abc123",
                        },
                        {
                            "number": 43,
                            "title": "Bad PR contract",
                            "state": "OPEN",
                            "labels": [{"name": "needs:reviewer"}],
                            "body": "## Execution Contract\n\nOwner role: Implementer\nCompletion handoff: move to Review\n",
                            "headRefOid": "def456",
                        },
                    ]
                }
            ),
        )
        branch_contract_base = "\n".join(
            [
                "Owner role: implementer",
                "Review role: reviewer",
                "Acceptance role: architect",
                "Completion handoff: to:reviewer",
                "Base branch verified from: durable issue contract",
                "Working branch: codex/example-task",
                "Worktree expectation: current checkout must be reported before review",
                "Merge rule: no final main merge without delegated gate",
                "Forward-merge expectation: route through later readiness gate",
            ]
        )
        write(
            branch_readiness_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 350,
                            "title": "AF16 branch readiness",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v1.x-maintenance\nTarget branch: main\nPR target: main\n",
                        },
                        {
                            "number": 351,
                            "title": "Missing branch contract",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n",
                        },
                        {
                            "number": 352,
                            "title": "V2 targeting main",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v2-integration\nTarget branch: main\nPR target: main\n",
                        },
                        {
                            "number": 353,
                            "title": "V1 targeting V2",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v1.x-maintenance\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
                        },
                        {
                            "number": 354,
                            "title": "Legacy branch target",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v1.x-maintenance\nBranch target: main\nPR target: main\n",
                        },
                    ]
                }
            ),
        )
        write(
            branch_readiness_prs,
            json.dumps(
                {
                    "items": [
                        {
                            "number": 501,
                            "title": "Wrong V2 PR base",
                            "state": "OPEN",
                            "labels": [{"name": "needs:reviewer"}],
                            "baseRefName": "main",
                            "headRefName": "codex/v2-feature",
                            "headRefOid": "abc501",
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v2-integration\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
                        },
                        {
                            "number": 502,
                            "title": "Correct V2 PR base",
                            "state": "OPEN",
                            "labels": [{"name": "needs:reviewer"}],
                            "baseRefName": "codex/v2-local-first-orchestration",
                            "headRefName": "codex/v2-safe",
                            "headRefOid": "abc502",
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nRelease line: v2-integration\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
                        },
                    ]
                }
            ),
        )
        write(
            branch_local_git,
            json.dumps(
                {
                    "status": "ok",
                    "branch": "codex/af16-350-branch-readiness",
                    "upstream": "origin/codex/af16-350-branch-readiness",
                    "ahead": 1,
                    "behind": 1,
                    "dirty": True,
                    "staged_count": 1,
                    "unstaged_count": 1,
                    "untracked_count": 1,
                    "commit": "abc-local",
                    "worktree_path": "/tmp/agent-foundry-task",
                }
            ),
        )
        write(
            branch_local_clean,
            json.dumps(
                {
                    "status": "ok",
                    "branch": "main",
                    "upstream": "origin/main",
                    "ahead": 0,
                    "behind": 0,
                    "dirty": False,
                    "commit": "abc-clean",
                    "worktree_path": "/tmp/agent-foundry-clean",
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
                            "body": "## Execution Contract\n\nOwner role: implementer\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n",
                        },
                        {
                            "number": 207,
                            "title": "Bad contract",
                            "labels": [{"name": "needs:implementer"}],
                            "updatedAt": "2026-06-18T00:00:00Z",
                            "body": "## Execution Contract\n\nOwner role: Implementer\nCompletion handoff: move to Review\nReviewer target: separate Reviewer agent\n",
                        },
                        {
                            "number": 206,
                            "title": "Evidence",
                            "labels": [{"name": "stage:AF-11"}],
                            "updatedAt": "2026-06-18T00:00:00Z",
                        },
                        {
                            "number": 208,
                            "title": "Tester evidence",
                            "labels": [{"name": "needs:tester"}],
                            "updatedAt": "2026-06-18T00:00:00Z",
                            "body": "## Execution Contract\n\nOwner role: tester\nReview role: reviewer\nAcceptance role: architect\nCompletion handoff: to:reviewer\n\n## Testing Contract\n\nTesting Responsibility: tester\nTester Trigger:\n  - route mock does not prove backend persistence\nuser_value_or_risk: user can trust the preview does not write\n\n## Test Evidence Handoff\n\nto: reviewer\nresult_summary: passed\nresidual_risks: backend persistence not covered\n",
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
        inbox_result = run(
            [
                "--json",
                "--repo",
                "farmerhunter/agent-foundry",
                "inbox",
                "--config",
                str(TEMPLATE),
                "--fixture-json",
                str(inbox),
            ],
            base,
        )
        errors.extend(expect_ok("inbox-contract-validation-surface", inbox_result, '"contract_validation"'))
        errors.extend(expect_ok("inbox-contract-validation-invalid", inbox_result, '"status": "invalid"'))
        errors.extend(expect_ok("inbox-contract-validation-role", inbox_result, '"actual": "Implementer"'))
        errors.extend(expect_ok("inbox-contract-validation-handoff", inbox_result, '"actual": "move to Review"'))
        errors.extend(expect_ok("inbox-testing-contract-validation-surface", inbox_result, '"testing_contract_validation"'))
        errors.extend(expect_ok("inbox-testing-contract-validation-ok", inbox_result, '"Testing Responsibility": "tester"'))
        issue_context_result = run(
            ["--repo", "farmerhunter/agent-foundry", "issue-context", "205", "--fixture-json", str(fixture)],
            base,
        )
        errors.extend(
            expect_ok(
                "issue-context-fixture",
                issue_context_result,
                "summary_is_authority: False",
            )
        )
        errors.extend(expect_ok("issue-context-ignores-fenced-contract-heading", issue_context_result, '"status": "ok"'))
        errors.extend(expect_ok("issue-context-real-contract-owner", issue_context_result, '"Owner role": "implementer"'))
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
            "execution_contract_invalid",
            "testing_contract_invalid",
        ):
            errors.extend(expect_ok(f"scheduler-audit-{code}", scheduler_json, f'"code": "{code}"'))
        for name, expected in (
            ("scheduler-audit-uppercase-role", '"Owner role": "Implementer"'),
            ("scheduler-audit-compound-acceptance", '"Acceptance role": "architect / user"'),
            ("scheduler-audit-missing-review-role", "Reviewer target is present but Review role is missing."),
            ("scheduler-audit-legacy-handoff", '"Completion handoff": "move to Review"'),
            ("scheduler-audit-tester-missing-contract", "needs:tester requires Testing Responsibility: tester."),
            ("scheduler-audit-review-role-tester", '"Review role": "tester"'),
        ):
            errors.extend(expect_ok(name, scheduler_json, expected))
        errors.extend(expect_ok("scheduler-audit-json-status", scheduler_json, '"status": "findings"'))
        errors.extend(expect_ok("scheduler-audit-json-no-mutation", scheduler_json, '"mutation_performed": false'))
        readiness_json = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
                "--issues-json",
                str(audit_issues),
                "--prs-json",
                str(readiness_prs),
                "--project-items-json",
                str(readiness_project),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("collaboration-readiness-command", '"command": "collaboration-readiness"'),
            ("collaboration-readiness-no-mutation", '"mutation_performed": false'),
            ("collaboration-readiness-read-only", '"mode": "read_only"'),
            ("collaboration-readiness-missing-label", '"code": "missing_needs_label"'),
            ("collaboration-readiness-missing-harvester", '"label:needs:harvester"'),
            ("collaboration-readiness-contract-invalid", '"code": "execution_contract_invalid"'),
            ("collaboration-readiness-testing-invalid", '"code": "testing_contract_invalid"'),
            ("collaboration-readiness-missing-project-item", '"code": "missing_project_item"'),
            ("collaboration-readiness-missing-project-field", '"code": "missing_project_field"'),
            ("collaboration-readiness-missing-role-option", '"code": "missing_project_role_option"'),
            ("collaboration-readiness-action-plan", '"user_readiness_action_plan"'),
            ("collaboration-readiness-status", '"readiness_status"'),
            ("collaboration-readiness-summary", "Raw JSON remains evidence/debug output"),
            ("collaboration-readiness-human-readable-summary", '"summary"'),
            ("collaboration-readiness-agent-action", '"category": "agent_handled_existing_workflow"'),
            ("collaboration-readiness-human-gate-action", '"category": "explicit_human_gate"'),
            ("collaboration-readiness-deferred-action", '"category": "unsupported_deferred_repair_apply"'),
            ("collaboration-readiness-pr-sampled", '"prs_sampled"'),
            ("collaboration-readiness-repair-not-supported", '"apply_supported_now": false'),
            ("collaboration-readiness-project-option-repair", '"action": "create_project_option"'),
            ("collaboration-readiness-no-full-project-scan", '"full_project_scan_performed": false'),
            ("collaboration-readiness-v2-shape", '"local_ledger_candidate": true'),
        ):
            errors.extend(expect_ok(name, readiness_json, expected))
        branch_readiness_json = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
                "--issues-json",
                str(branch_readiness_issues),
                "--prs-json",
                str(branch_readiness_prs),
                "--local-git-json",
                str(branch_local_git),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("branch-readiness-surface", '"branch_readiness"'),
            ("branch-readiness-target-branch", '"Target branch"'),
            ("branch-readiness-legacy-mapping", '"target_branch_source": "legacy:Branch target"'),
            ("branch-readiness-missing-contract", '"code": "branch_contract_missing"'),
            ("branch-readiness-v2-main", '"code": "v2_work_targets_main"'),
            ("branch-readiness-v1-v2", '"code": "v1_work_targets_v2"'),
            ("branch-readiness-wrong-pr-base", '"code": "wrong_pr_base"'),
            ("branch-readiness-v2-pr-main", '"code": "v2_pr_targets_main"'),
            ("branch-readiness-dirty-worktree", '"code": "local_worktree_dirty"'),
            ("branch-readiness-ahead-behind", '"code": "local_branch_ahead_or_behind"'),
            ("branch-readiness-actual-base", '"actual_pr_base": "main"'),
            ("branch-readiness-no-apply", '"apply_supported_now": false'),
            ("branch-readiness-no-mutation", '"mutation_performed": false'),
            ("branch-readiness-no-retarget", "PR retarget"),
            ("branch-readiness-no-checkout", "checkout/switch"),
            ("branch-readiness-no-reset-clean", "rebase/merge/reset/clean"),
            ("branch-readiness-action-plan", "Branch readiness: branch_mismatch."),
            ("branch-readiness-agent-action", '"category": "agent_handled_existing_workflow"'),
            ("branch-readiness-deferred-action", '"category": "unsupported_deferred_repair_apply"'),
            ("branch-readiness-no-full-scan", '"full_project_scan_performed": false'),
        ):
            errors.extend(expect_ok(name, branch_readiness_json, expected))
        write(fake_gh, "#!/bin/sh\nprintf '%s\\n' 'TLS handshake timeout while reading PR base' >&2\nexit 1\n")
        fake_gh.chmod(0o755)
        pr_degraded_json = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
                "--issues-json",
                str(branch_readiness_issues),
                "--prs",
                "501",
                "--local-git-json",
                str(branch_local_clean),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry", "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
        )
        for name, expected in (
            ("branch-readiness-pr-read-degraded", '"source": "github_rest_prs"'),
            ("branch-readiness-pr-read-transient", '"status": "transient_failure"'),
            ("branch-readiness-pr-read-recorded", "TLS handshake timeout while reading PR base"),
        ):
            errors.extend(expect_ok(name, pr_degraded_json, expected))
        new_repo_readiness = run(
            [
                "collaboration-readiness",
                "--labels-json",
                str(new_repo_labels),
                "--issues-json",
                str(new_repo_issues),
                "--prs-json",
                str(new_repo_prs),
                "--local-git-json",
                str(branch_local_clean),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/new-repo"},
        )
        for name, expected in (
            ("collaboration-readiness-new-repo-needs-setup", '"readiness_status": "needs_setup"'),
            ("collaboration-readiness-new-repo-label-action", '"label:needs:architect"'),
            ("collaboration-readiness-new-repo-project-informational", '"category": "informational_only"'),
            ("collaboration-readiness-new-repo-raw-json-debug", "Raw JSON remains evidence/debug output"),
            ("collaboration-readiness-new-repo-no-mutation", '"mutation_performed": false'),
        ):
            errors.extend(expect_ok(name, new_repo_readiness, expected))
        write(fake_gh, "#!/bin/sh\nprintf '%s\\n' 'EOF while reading Project v2' >&2\nexit 1\n")
        fake_gh.chmod(0o755)
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
        errors.extend(expect_ok("scheduler-audit-project-degraded-availability", degraded, '"availability": "degraded"'))
        errors.extend(expect_ok("scheduler-audit-project-read-once", degraded, '"attempts": 1'))
        readiness_degraded = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
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
        errors.extend(expect_ok("collaboration-readiness-project-degraded", readiness_degraded, '"status": "degraded"'))
        errors.extend(expect_ok("collaboration-readiness-project-degraded-availability", readiness_degraded, '"availability": "degraded"'))
        errors.extend(expect_ok("collaboration-readiness-project-read-once", readiness_degraded, '"attempts": 1'))
        errors.extend(expect_ok("collaboration-readiness-project-eof-recorded", readiness_degraded, "EOF while reading Project v2"))
        errors.extend(expect_ok("collaboration-readiness-no-project-write", readiness_degraded, '"apply_supported_now": false'))
        write(fake_gh, "#!/bin/sh\nprintf '%s\\n' 'GraphQL rate limit exceeded' >&2\nexit 1\n")
        fake_gh.chmod(0o755)
        readiness_rate_limited = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
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
        errors.extend(expect_ok("collaboration-readiness-rate-limit-degraded", readiness_rate_limited, '"availability": "degraded"'))
        errors.extend(expect_ok("collaboration-readiness-rate-limit-recorded", readiness_rate_limited, "GraphQL rate limit exceeded"))
        write(fake_gh, "#!/bin/sh\nprintf '%s\\n' 'TLS handshake timeout while reading Project v2' >&2\nexit 1\n")
        fake_gh.chmod(0o755)
        readiness_tls = run(
            [
                "collaboration-readiness",
                "--config",
                str(TEMPLATE),
                "--labels-json",
                str(readiness_labels),
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
        errors.extend(expect_ok("collaboration-readiness-tls-degraded", readiness_tls, '"availability": "degraded"'))
        errors.extend(expect_ok("collaboration-readiness-tls-recorded", readiness_tls, "TLS handshake timeout"))
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
                "comparison-draft-instrumentation-defaults",
                run(["comparison-draft", "--subject", "AF10 #264 instrumentation defaults"], base),
                "github_api_read_attempts: \"unknown\"",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-draft-instrumentation-boundaries",
                run(["comparison-draft", "--subject", "AF10 #264 instrumentation defaults"], base),
                "observed_counter_source: \"not_available\"",
            )
        )
        errors.extend(
            expect_ok(
                "comparison-draft-fallback-review",
                run(
                    [
                        "comparison-draft",
                        "--subject",
                        "AF10 #264 fallback review",
                        "--fallback-review-used",
                        "--fallback-review-reason",
                        "reviewer_thread_unavailable",
                        "--project-read-attempts",
                        "3",
                        "--github-api-failures",
                        "2",
                        "--durable-comment-links",
                        "5",
                    ],
                    base,
                ),
                "fallback_review_reason: \"reviewer_thread_unavailable\"",
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
