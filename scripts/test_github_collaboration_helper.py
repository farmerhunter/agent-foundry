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
                "Local Collaboration Ledger Storage And Replay",
                "usage/local/collaboration-ledger/events.jsonl",
                "local-ledger-report",
                "local-ledger-backfill-preview",
                "guided-onboarding",
                "project-sync-plan",
                "writes_supported_now: false",
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
        foundry_board_issues = base / "foundry-board-issues.json"
        foundry_board_project = base / "foundry-board-project.json"
        foundry_board_ledger_root = base / "foundry-board-ledger"
        foundry_board_candidate_events = base / "foundry-board-candidate-events.json"
        sync_plan_issues = base / "sync-plan-issues.json"
        sync_plan_project = base / "sync-plan-project.json"
        sync_plan_ledger_root = base / "sync-plan-ledger"
        sync_plan_candidate_events = base / "sync-plan-candidate-events.json"
        mixed_recovery_issues = base / "mixed-recovery-issues.json"
        mixed_recovery_project = base / "mixed-recovery-project.json"
        mixed_recovery_ledger_root = base / "mixed-recovery-ledger"
        mixed_recovery_candidate_events = base / "mixed-recovery-candidate-events.json"
        cockpit_health = base / "operational-cockpit-health.json"
        cockpit_html = base / "operational-cockpit.html"
        guided_onboarding_issues = base / "guided-onboarding-issues.json"
        guided_onboarding_prs = base / "guided-onboarding-prs.json"
        guided_trial_responses = base / "guided-trial-responses.json"
        guided_trial_transcript = base / "guided-trial-root" / "transcripts" / "trial.json"
        guided_trial_response_errors = base / "guided-trial-response-errors.json"
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
            guided_onboarding_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 276,
                            "title": "[M14][P0] Deployment target and runtime config contract",
                            "state": "CLOSED",
                            "labels": [{"name": "area:testing"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/276",
                        },
                        {
                            "number": 277,
                            "title": "[M14][P1] Production auth, origin, CORS, and secret hardening",
                            "state": "CLOSED",
                            "labels": [{"name": "area:backend"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/277",
                        },
                        {
                            "number": 278,
                            "title": "[M14][P1] VPS install and systemd runbook",
                            "state": "CLOSED",
                            "labels": [{"name": "area:tooling"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/278",
                        },
                        {
                            "number": 279,
                            "title": "[M14][P2] Frontend build and reverse-proxy routing contract",
                            "state": "CLOSED",
                            "labels": [{"name": "area:frontend"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/279",
                        },
                        {
                            "number": 280,
                            "title": "[M14][P2] SQLite backup and restore dry-run verification",
                            "state": "CLOSED",
                            "labels": [{"name": "area:backend"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/280",
                        },
                        {
                            "number": 281,
                            "title": "[M14][P3] Deployment smoke and rollback checklist",
                            "state": "CLOSED",
                            "labels": [{"name": "area:tooling"}, {"name": "type:task"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/281",
                        },
                        {
                            "number": 282,
                            "title": "[M14][P4] VPS deployment readiness review and human deployment gate",
                            "state": "OPEN",
                            "labels": [{"name": "area:testing"}, {"name": "needs:user"}, {"name": "type:review"}],
                            "url": "https://github.com/farmerhunter/tiny-ipa/issues/282",
                        },
                    ]
                }
            ),
        )
        write(guided_onboarding_prs, json.dumps({"items": []}))
        write(
            guided_trial_responses,
            json.dumps(
                {
                    "responses": [
                        {
                            "step": 1,
                            "choice": "start trial",
                            "human_response": "I understand this is a read-only trial and want to continue.",
                            "timestamp": "2026-07-15T09:00:00Z",
                        },
                        {
                            "step": 2,
                            "choice": "confirm current context",
                            "human_response": "The current tiny-ipa M14 context is correct.",
                            "timestamp": "2026-07-15T09:01:00Z",
                        },
                        {
                            "step": 3,
                            "choice": "accept proposed set",
                            "human_response": "Use #282 as the gate and #276-#281 as completed context.",
                            "timestamp": "2026-07-15T09:02:00Z",
                        },
                        {
                            "step": 4,
                            "choice": "inspect evidence",
                            "human_response": "I want to inspect #282 evidence before considering it.",
                            "timestamp": "2026-07-15T09:03:00Z",
                            "evidence_refs": ["https://github.com/farmerhunter/tiny-ipa/issues/282"],
                        },
                        {
                            "step": 5,
                            "choice": "preview only",
                            "human_response": "Keep ledger work in no-mutation preview mode.",
                            "timestamp": "2026-07-15T09:04:00Z",
                        },
                        {
                            "step": 6,
                            "choice": "continue with decision support",
                            "human_response": "The Project sync plan is not executed and only decision support.",
                            "timestamp": "2026-07-15T09:05:00Z",
                        },
                        {
                            "step": 7,
                            "choice": "defer candidate",
                            "human_response": "Defer the candidate until I finish reading the evidence.",
                            "timestamp": "2026-07-15T09:06:00Z",
                        },
                        {
                            "step": 8,
                            "choice": "deferred",
                            "human_response": "The trial is understandable, but I want more time before acceptance.",
                            "timestamp": "2026-07-15T09:07:00Z",
                        },
                    ],
                    "final_evaluation": {
                        "clarity_of_starting_context": "clear",
                        "confidence_in_current_state_evidence": "medium",
                        "candidate_non_authority_clarity": "clear",
                        "isolated_ledger_boundary_clarity": "clear",
                        "project_sync_not_executed_clarity": "clear",
                        "next_step_actionability": "actionable",
                        "remaining_friction": "Need to read #282 details before accepting.",
                        "final_decision": "deferred",
                    },
                }
            ),
        )
        write(
            guided_trial_response_errors,
            json.dumps({"responses": [{"step": 1, "choice": "start trial"}]}),
        )
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
                            + "\nBranch strategy: mainline-maintenance\nRelease line: v1.x-maintenance\nTarget branch: main\nPR target: main\n",
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
                            + "\nBranch strategy: integration-branch\nRelease line: v2-integration\nTarget branch: main\nPR target: main\n",
                        },
                        {
                            "number": 353,
                            "title": "V1 targeting V2",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: mainline-maintenance\nRelease line: v1.x-maintenance\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
                        },
                        {
                            "number": 354,
                            "title": "Legacy branch target",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: mainline-maintenance\nRelease line: v1.x-maintenance\nBranch target: main\nPR target: main\n",
                        },
                        {
                            "number": 355,
                            "title": "Generic integration branch",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: integration-branch\nTarget branch: codex/customer-integration\nPR target: codex/customer-integration\n",
                        },
                        {
                            "number": 356,
                            "title": "Custom strategy",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: custom\nTarget branch: maintainer/special-flow\nPR target: maintainer/special-flow\n",
                        },
                        {
                            "number": 357,
                            "title": "Multi-line evidence",
                            "state": "OPEN",
                            "labels": [{"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: multi-branch\nTarget branch: main\nAffected branches: main, codex/v2-local-first-orchestration\nVerification branches: main, codex/v2-local-first-orchestration\nPR target: main\nForward-merge expectation: verify and forward-merge after main acceptance\n",
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
                            + "\nBranch strategy: integration-branch\nRelease line: v2-integration\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
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
                            + "\nBranch strategy: integration-branch\nRelease line: v2-integration\nTarget branch: codex/v2-local-first-orchestration\nPR target: codex/v2-local-first-orchestration\n",
                        },
                        {
                            "number": 503,
                            "title": "Stacked PR",
                            "state": "OPEN",
                            "labels": [{"name": "needs:reviewer"}],
                            "baseRefName": "codex/parent-feature",
                            "headRefName": "codex/child-feature",
                            "headRefOid": "abc503",
                            "body": "## Execution Contract\n\n"
                            + branch_contract_base
                            + "\nBranch strategy: stacked-pr\nTarget branch: main\nPR target: codex/parent-feature\n",
                        },
                    ]
                }
            ),
        )
        board_contract = "\n".join(
            [
                "Owner role: architect",
                "Review role: reviewer",
                "Acceptance role: architect",
                "Completion handoff: to:reviewer",
                "Branch strategy: integration-branch",
                "Release line: v2.0",
                "Target branch: codex/v2-local-first-orchestration",
                "Base branch: codex/v2-local-first-orchestration",
                "PR target: codex/v2-local-first-orchestration",
            ]
        )
        write(
            foundry_board_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 297,
                            "title": "Read-only Foundry Board MVP",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/297",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n" + board_contract + "\n",
                        },
                        {
                            "number": 296,
                            "title": "Backfill candidate from existing project",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/296",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}, {"name": "migration_candidate"}],
                            "source_confidence": "inferred",
                            "state_authority": "candidate",
                            "board_state": "planned",
                            "body": "## Execution Contract\n\n" + board_contract + "\n",
                        },
                        {
                            "number": 299,
                            "title": "Human-gated V2 readiness",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/299",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}, {"name": "needs:human"}],
                            "body": "## Execution Contract\n\n"
                            + board_contract.replace("Owner role: architect", "Owner role: human").replace("Completion handoff: to:reviewer", "Completion handoff: to:human")
                            + "\n",
                        },
                    ]
                }
            ),
        )
        write(
            foundry_board_project,
            json.dumps(
                {
                    "items": [
                        {
                            "content": {"number": 297},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "stage": {"name": "V2.0"},
                            "owner Role": {"name": "Implementer"},
                            "risk": {"name": "High"},
                        },
                        {
                            "content": {"number": 296},
                            "status": {"name": "Done"},
                            "roadmap Status": {"name": "Done"},
                            "stage": {"name": "V2.0"},
                            "owner Role": {"name": "Architect"},
                            "risk": {"name": "High"},
                        },
                        {
                            "content": {"number": 299},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "In Progress"},
                            "stage": {"name": "V2.0"},
                            "owner Role": {"name": "Human"},
                            "risk": {"name": "High"},
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
        guided_onboarding_json = run(
            [
                "--json",
                "--repo",
                "farmerhunter/tiny-ipa",
                "guided-onboarding",
                "--issues-json",
                str(guided_onboarding_issues),
                "--prs-json",
                str(guided_onboarding_prs),
                "--trial-root",
                "/private/tmp/af390-tiny-ipa-guided-trial",
                "--adopter-path",
                "/Users/example/tiny-ipa",
                "--adopter-branch",
                "main",
            ],
            base,
        )
        for name, expected in [
            ("guided-onboarding-command", '"command": "guided-onboarding"'),
            ("guided-onboarding-surface", "ten-minute guided onboarding"),
            ("guided-onboarding-read-only", '"mode": "read_only"'),
            ("guided-onboarding-no-mutation", '"mutation_performed": false'),
            ("guided-onboarding-no-apply", '"apply_supported_now": false'),
            ("guided-onboarding-raw-json-debug", '"raw_json_primary_ux": false'),
            ("guided-onboarding-fallback", "explicit issue/PR fallback"),
            ("guided-onboarding-current-gate", '"issue_numbers": [\n      282\n    ]'),
            ("guided-onboarding-current-state", "#276-#281 closed and #282 needs:user"),
            ("guided-onboarding-candidate-actions", "inspect evidence"),
            ("guided-onboarding-candidate-non-authority", "candidate_non_authoritative_until_accepted_into_isolated_ledger"),
            ("guided-onboarding-isolated-ledger", "isolated_ledger_no_effect_guarantee"),
            ("guided-onboarding-project-not-executed", '"status": "not executed"'),
            ("guided-onboarding-no-stale-snapshot", "stale #386 active-item snapshot"),
            ("guided-onboarding-no-proceed", '"no_proceed_without_human_response": true'),
            ("guided-onboarding-blocked", '"status": "blocked_waiting_for_human_response"'),
            ("guided-onboarding-start-consent", "Starting context / consent"),
            ("guided-onboarding-final-evaluation", "Final structured Human evaluation"),
        ]:
            errors.extend(expect_ok(name, guided_onboarding_json, expected))
        guided_onboarding_text = run(
            [
                "--repo",
                "farmerhunter/tiny-ipa",
                "guided-onboarding",
                "--issues-json",
                str(guided_onboarding_issues),
                "--prs-json",
                str(guided_onboarding_prs),
                "--trial-root",
                "/private/tmp/af390-tiny-ipa-guided-trial",
            ],
            base,
        )
        for name, expected in [
            ("guided-onboarding-text-title", "Ten-minute guided onboarding packet"),
            ("guided-onboarding-text-reads", "What the agent reads:"),
            ("guided-onboarding-text-writes", "What it may write:"),
            ("guided-onboarding-text-not-touch", "What it will not touch:"),
            ("guided-onboarding-text-decision", "One Human decision required now:"),
            ("guided-onboarding-text-not-executed", "Project sync plan status: not executed"),
            ("guided-onboarding-text-no-proceed", "No proceed without Human response: True"),
            ("guided-onboarding-text-final-eval", "Final structured Human evaluation is required"),
        ]:
            errors.extend(expect_ok(name, guided_onboarding_text, expected))
        guided_trial_complete = run(
            [
                "--json",
                "--repo",
                "farmerhunter/tiny-ipa",
                "guided-onboarding",
                "--issues-json",
                str(guided_onboarding_issues),
                "--prs-json",
                str(guided_onboarding_prs),
                "--trial-root",
                str(guided_trial_transcript.parents[1]),
                "--trial-response-json",
                str(guided_trial_responses),
                "--transcript-out",
                str(guided_trial_transcript),
            ],
            base,
        )
        for name, expected in [
            ("guided-trial-response-complete", '"status": "complete"'),
            ("guided-trial-progression-allowed", '"progression_allowed": true'),
            ("guided-trial-response-captured", '"captured_before_progression": true'),
            ("guided-trial-response-count", '"captured_response_count": 8'),
            ("guided-trial-inspect-path", "inspect evidence"),
            ("guided-trial-defer-path", "Defer the candidate"),
            ("guided-trial-final-decision", '"final_decision": "deferred"'),
            ("guided-trial-default-no-mutation", '"default_trial_mode": "no_mutation_preview_only"'),
            ("guided-trial-local-gate", '"local_temp_apply_requires_later_explicit_gate": true'),
            ("guided-trial-transcript-written", '"status": "written"'),
            ("guided-trial-transcript-scope", '"write_scope": "local_trial_transcript_only"'),
        ]:
            errors.extend(expect_ok(name, guided_trial_complete, expected))
        if guided_trial_transcript.exists():
            transcript_text = guided_trial_transcript.read_text(encoding="utf-8")
            errors.extend(expect_text_contains("guided-trial-transcript-file", transcript_text, ["actual_human_response_required_before_progression", "deferred"]))
        else:
            errors.append("guided-trial-transcript-file: transcript was not written")
        guided_trial_invalid = run(
            [
                "--json",
                "--repo",
                "farmerhunter/tiny-ipa",
                "guided-onboarding",
                "--issues-json",
                str(guided_onboarding_issues),
                "--prs-json",
                str(guided_onboarding_prs),
                "--trial-response-json",
                str(guided_trial_response_errors),
            ],
            base,
        )
        errors.extend(expect_ok("guided-trial-invalid-response-blocks", guided_trial_invalid, "response #1 missing human_response"))
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
        board_accepted_events = [
            {
                "schema_version": 1,
                "event_id": "board-accepted-297",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T11:10:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:297", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 297},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/297#ledger"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "board-accepted-299",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T11:11:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:299", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 299},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/299#ledger"]},
                "payload": {"owner_role": "human"},
            },
        ]
        for event in board_accepted_events:
            event_path = base / f"{event['event_id']}.json"
            write(event_path, json.dumps(event))
            errors.extend(
                expect_ok(
                    f"foundry-board-ledger-append-{event['event_id']}",
                    run(["local-ledger-append", "--ledger-root", str(foundry_board_ledger_root), "--event-json", str(event_path), "--json"], base),
                    '"mutation_performed": true',
                )
            )
        candidate_event = {
            "schema_version": 1,
            "event_id": "board-candidate-296",
            "event_type": "assignment",
            "occurred_at": "2026-07-08T11:12:00Z",
            "work_item": {"id": "farmerhunter/agent-foundry#issue:296", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 296},
            "actor_role": "coordinator",
            "confidence": "inferred",
            "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/296#candidate"]},
            "payload": {"owner_role": "architect"},
        }
        write(foundry_board_candidate_events, json.dumps({"candidate_imported_events": [candidate_event]}))
        board_ledger_before = (foundry_board_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        foundry_board_json = run(
            [
                "foundry-board",
                "--issues-json",
                str(foundry_board_issues),
                "--project-items-json",
                str(foundry_board_project),
                "--local-git-json",
                str(branch_local_clean),
                "--ledger-root",
                str(foundry_board_ledger_root),
                "--candidate-events-json",
                str(foundry_board_candidate_events),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("foundry-board-command", '"command": "foundry-board"'),
            ("foundry-board-read-only", '"mode": "read_only"'),
            ("foundry-board-no-mutation", '"mutation_performed": false'),
            ("foundry-board-no-apply", '"apply_supported_now": false'),
            ("foundry-board-source-of-truth", '"source_of_truth": "local_collaboration_ledger_events"'),
            ("foundry-board-mirror-role", '"github_project_role": "optional_visual_mirror"'),
            ("foundry-board-ready-lane", '"lane": "ready"'),
            ("foundry-board-human-gate-lane", '"lane": "human_gate"'),
            ("foundry-board-stale-conflict", '"lane": "stale_conflict"'),
            ("foundry-board-accepted", '"state_authority": "accepted_local_ledger"'),
            ("foundry-board-candidate", '"state_authority": "candidate_import"'),
            ("foundry-board-confidence", '"confidence": "inferred"'),
            ("foundry-board-mirror-drift", '"mirror_status": "drift"'),
            ("foundry-board-remote-mirror", '"remote_mirror_state"'),
            ("foundry-board-human-action", '"category": "explicit_human_gate"'),
            ("foundry-board-branch-target", '"target_branch": "codex/v2-local-first-orchestration"'),
            ("foundry-board-forbidden-project", "Project v2 mutation"),
            ("foundry-board-telemetry", '"implementation_slice": "V2-5B ledger-backed Foundry Board"'),
            ("foundry-board-telemetry-issue", '"telemetry_issue": "#266"'),
            ("foundry-board-remote-only-count", '"remote_mirror_only_count": 0'),
        ):
            errors.extend(expect_ok(name, foundry_board_json, expected))
        board_ledger_after = (foundry_board_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        if board_ledger_before == board_ledger_after:
            print("foundry-board-no-ledger-write: ok")
        else:
            errors.append("foundry-board-no-ledger-write: board mutated accepted ledger")
        degraded_foundry_board = run(
            [
                "foundry-board",
                "--issues-json",
                str(foundry_board_issues),
                "--local-git-json",
                str(branch_local_clean),
                "--ledger-root",
                str(foundry_board_ledger_root),
                "--project-owner",
                "@me",
                "--project-number",
                "3",
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry", "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")},
        )
        for name, expected in (
            ("foundry-board-project-degraded-renders-local", '"accepted_count": 2'),
            ("foundry-board-project-degraded-status", '"mirror_status": "degraded"'),
            ("foundry-board-project-degraded-count", '"remote_read_degradation_count": 1'),
            ("foundry-board-project-degraded-fallback", "accepted_local_ledger_replay"),
        ):
            errors.extend(expect_ok(name, degraded_foundry_board, expected))
        v2_contract = "\n".join(
            [
                "Owner role: implementer",
                "Review role: reviewer",
                "Acceptance role: architect",
                "Completion handoff: to:reviewer",
                "Branch strategy: integration-branch",
                "Release line: v2.0",
                "Target branch: codex/v2-local-first-orchestration",
                "Base branch: codex/v2-local-first-orchestration",
                "PR target: codex/v2-local-first-orchestration",
            ]
        )
        main_contract = v2_contract.replace("Target branch: codex/v2-local-first-orchestration", "Target branch: main").replace(
            "PR target: codex/v2-local-first-orchestration",
            "PR target: main",
        )
        write(
            sync_plan_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 420,
                            "title": "Open local work item",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/420",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n" + v2_contract + "\n",
                        },
                        {
                            "number": 421,
                            "title": "Closed local work item",
                            "state": "CLOSED",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/421",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}],
                            "body": "## Execution Contract\n\n" + v2_contract + "\n",
                        },
                        {
                            "number": 422,
                            "title": "Wrong branch line",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/422",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:high"}, {"name": "needs:implementer"}],
                            "body": "## Execution Contract\n\n" + main_contract + "\n",
                        },
                        {
                            "number": 424,
                            "title": "Ambiguous Project item",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/424",
                            "labels": [{"name": "stage:v2.0"}, {"name": "risk:medium"}, {"name": "needs:reviewer"}],
                            "body": "## Execution Contract\n\n" + v2_contract + "\n",
                        },
                    ]
                }
            ),
        )
        write(
            sync_plan_project,
            json.dumps(
                {
                    "fields": [
                        {"name": "Status"},
                        {"name": "Roadmap Status"},
                        {"name": "Owner Role", "options": [{"name": "Architect"}, {"name": "Implementer"}]},
                    ],
                    "items": [
                        {
                            "id": "P420A",
                            "content": {"number": 420},
                            "status": {"name": "Done"},
                            "roadmap Status": {"name": "Done"},
                            "owner Role": {"name": "Reviewer"},
                            "updatedAt": "2026-07-08T11:00:00Z",
                        },
                        {
                            "id": "P421A",
                            "content": {"number": 421},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "owner Role": {"name": "Reviewer"},
                            "updatedAt": "2026-07-08T13:00:00Z",
                        },
                        {
                            "id": "P422A",
                            "content": {"number": 422},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "owner Role": {"name": "Implementer"},
                            "updatedAt": "2026-07-08T11:00:00Z",
                        },
                        {
                            "id": "P424A",
                            "content": {"number": 424},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "owner Role": {"name": "Reviewer"},
                            "updatedAt": "2026-07-08T11:00:00Z",
                        },
                        {
                            "id": "P424B",
                            "content": {"number": 424},
                            "status": {"name": "Todo"},
                            "roadmap Status": {"name": "Ready"},
                            "owner Role": {"name": "Reviewer"},
                            "updatedAt": "2026-07-08T11:01:00Z",
                        },
                    ],
                }
            ),
        )
        sync_plan_events = [
            {
                "schema_version": 1,
                "event_id": "sync-accepted-420",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:00:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:420", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 420},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/420#ledger"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "sync-accepted-421",
                "event_type": "closure",
                "occurred_at": "2026-07-08T12:01:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:421", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 421},
                "actor_role": "architect",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/421#closed"]},
                "payload": {"state": "closed"},
            },
            {
                "schema_version": 1,
                "event_id": "sync-accepted-422",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:02:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:422", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 422},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["/Users/private/token.txt"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "sync-accepted-424",
                "event_type": "review",
                "occurred_at": "2026-07-08T12:03:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:424", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 424},
                "actor_role": "reviewer",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/424#review"]},
                "payload": {"decision": "approved"},
            },
        ]
        for event in sync_plan_events:
            event_path = base / f"{event['event_id']}.json"
            write(event_path, json.dumps(event))
            errors.extend(
                expect_ok(
                    f"project-sync-plan-ledger-append-{event['event_id']}",
                    run(["local-ledger-append", "--ledger-root", str(sync_plan_ledger_root), "--event-json", str(event_path), "--json"], base),
                    '"mutation_performed": true',
                )
            )
        write(
            sync_plan_candidate_events,
            json.dumps(
                {
                    "candidate_imported_events": [
                        {
                            "schema_version": 1,
                            "event_id": "sync-candidate-423",
                            "event_type": "assignment",
                            "occurred_at": "2026-07-08T12:04:00Z",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:423", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 423},
                            "actor_role": "coordinator",
                            "confidence": "inferred",
                            "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/423#candidate"]},
                            "payload": {"owner_role": "architect"},
                        }
                    ]
                }
            ),
        )
        sync_plan = run(
            [
                "project-sync-plan",
                "--issues-json",
                str(sync_plan_issues),
                "--project-items-json",
                str(sync_plan_project),
                "--ledger-root",
                str(sync_plan_ledger_root),
                "--candidate-events-json",
                str(sync_plan_candidate_events),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("project-sync-plan-command", '"command": "project-sync-plan"'),
            ("project-sync-plan-dry-run", '"mode": "dry_run"'),
            ("project-sync-plan-no-mutation", '"mutation_performed": false'),
            ("project-sync-plan-no-writes", '"writes_supported_now": false'),
            ("project-sync-plan-source", '"source_of_truth": "local_collaboration_ledger_board"'),
            ("project-sync-plan-operation", '"operation": "set_project_field"'),
            ("project-sync-plan-before", '"before": "Done"'),
            ("project-sync-plan-after", '"after": "Blocked"'),
            ("project-sync-plan-idempotency", '"idempotency_key"'),
            ("project-sync-plan-evidence", '"evidence_refs"'),
            ("project-sync-plan-readback", '"readback_required"'),
            ("project-sync-plan-human-gate", '"gate": "explicit_human_gate"'),
            ("project-sync-plan-missing-field", "missing_project_field"),
            ("project-sync-plan-missing-option", "missing_project_option"),
            ("project-sync-plan-ambiguous-item", "ambiguous_project_item"),
            ("project-sync-plan-project-done-open", "project_done_while_issue_open"),
            ("project-sync-plan-closed-not-done", "issue_closed_project_not_done"),
            ("project-sync-plan-owner-mismatch", "owner_mismatch"),
            ("project-sync-plan-newer", "local_remote_newer"),
            ("project-sync-plan-privacy", "privacy_sensitive_value"),
            ("project-sync-plan-branch-line", "branch_line_mismatch"),
            ("project-sync-plan-candidate", "candidate_state_not_authoritative"),
            ("project-sync-plan-built-in-gate", "built_in_status_side_effect"),
            ("project-sync-plan-issue-gate", "issue_closure_or_reopen_side_effect"),
            ("project-sync-plan-privacy-gate", "privacy_security_sensitive_sync"),
            ("project-sync-plan-policy-gate", "broad_project_policy_change"),
            ("project-sync-plan-future-write-gate", "future_write_apply_transition"),
            ("project-sync-plan-user-report", '"user_facing_report"'),
            ("project-sync-plan-telemetry", '"telemetry_issue": "#266"'),
            ("project-sync-plan-api-attempts", '"api_attempts"'),
            ("project-sync-plan-elapsed", '"elapsed_time_ms"'),
            ("project-sync-plan-item-count", '"item_count"'),
            ("project-sync-plan-operation-count", '"planned_operation_count"'),
            ("project-sync-plan-conflict-count", '"conflict_count"'),
            ("project-sync-plan-human-count", '"human_gate_count"'),
            ("project-sync-plan-no-full-scan", '"full_project_scan_performed": false'),
            ("project-sync-plan-unsupported-project-write", "live Project mutation"),
            ("project-sync-plan-unsupported-branch", "checkout/switch"),
        ):
            errors.extend(expect_ok(name, sync_plan, expected))
        sync_apply_plan = base / "project-sync-plan.json"
        write(sync_apply_plan, sync_plan.stdout)
        sync_apply_doc = json.loads(sync_plan.stdout)
        fake_project_write = base / "fake-project-write.json"
        fake_results = {}
        for operation in sync_apply_doc.get("planned_operations", []):
            if operation.get("gate") == "agent_handled_existing_workflow" and operation.get("project_item_id"):
                fake_results[operation["idempotency_key"]] = {"status": "ok", "readback": operation.get("after")}
        if fake_results:
            first_key = sorted(fake_results)[0]
            fake_results[first_key] = {"status": "partial_failure", "error": "transient GraphQL EOF"}
        write(fake_project_write, json.dumps({"results": fake_results}))
        sync_apply_acceptance = base / "project-sync-acceptance.json"
        write(
            sync_apply_acceptance,
            json.dumps(
                {
                    "accepted": True,
                    "approved_by_role": "architect",
                    "evidence_refs": ["https://github.com/farmerhunter/agent-foundry/issues/372#accepted-plan"],
                }
            ),
        )
        sync_apply_rejected_acceptance = base / "project-sync-rejected-acceptance.json"
        write(sync_apply_rejected_acceptance, json.dumps({"accepted": False, "evidence_refs": ["https://example.invalid/rejected"]}))
        rejected_sync_apply = run(
            [
                "project-sync-apply",
                "--ledger-root",
                str(sync_plan_ledger_root),
                "--sync-plan-json",
                str(sync_apply_plan),
                "--acceptance-json",
                str(sync_apply_rejected_acceptance),
                "--fake-project-write-json",
                str(fake_project_write),
                "--json",
            ],
            base,
        )
        errors.extend(expect_fail("project-sync-apply-rejects-unaccepted-plan", rejected_sync_apply, "accepted plan evidence must set accepted: true"))
        sync_apply = run(
            [
                "project-sync-apply",
                "--ledger-root",
                str(sync_plan_ledger_root),
                "--sync-plan-json",
                str(sync_apply_plan),
                "--acceptance-json",
                str(sync_apply_acceptance),
                "--fake-project-write-json",
                str(fake_project_write),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("project-sync-apply-command", '"command": "project-sync-apply"'),
            ("project-sync-apply-mode", '"mode": "apply"'),
            ("project-sync-apply-mutates", '"mutation_performed": true'),
            ("project-sync-apply-no-live-project", '"live_project_mutation_performed": false'),
            ("project-sync-apply-fake-project", '"fake_project_write_performed": true'),
            ("project-sync-apply-write-scope", '"write_scope": "fake_project_write_executor_and_local_sync_readback_events_only"'),
            ("project-sync-apply-source", '"source_of_truth": "local_collaboration_ledger"'),
            ("project-sync-apply-mirror", '"project_role": "optional_visual_mirror"'),
            ("project-sync-apply-accepted-evidence", '"accepted_plan_evidence_refs"'),
            ("project-sync-apply-human-gate", '"reason": "explicit_human_gate_required"'),
            ("project-sync-apply-partial", "partial Project write/readback failures remain visible"),
            ("project-sync-apply-readback-event", "project-sync-readback"),
            ("project-sync-apply-no-closure", "live issue closure/reopen automation"),
            ("project-sync-apply-no-broad-scan", '"full_project_scan_performed": false'),
            ("project-sync-apply-telemetry", '"telemetry_issue": "#266"'),
        ):
            errors.extend(expect_ok(name, sync_apply, expected))
        sync_apply_report = run(["local-ledger-report", "--ledger-root", str(sync_plan_ledger_root), "--json"], base)
        errors.extend(expect_ok("project-sync-apply-replay-sync-readback", sync_apply_report, "project-sync-readback"))
        sync_apply_again = run(
            [
                "project-sync-apply",
                "--ledger-root",
                str(sync_plan_ledger_root),
                "--sync-plan-json",
                str(sync_apply_plan),
                "--acceptance-json",
                str(sync_apply_acceptance),
                "--fake-project-write-json",
                str(fake_project_write),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("project-sync-apply-idempotent-skips", '"idempotent_skip_count"'),
            ("project-sync-apply-idempotent-reason", "idempotent_duplicate_event_id"),
        ):
            errors.extend(expect_ok(name, sync_apply_again, expected))
        degraded_sync_plan = run(
            [
                "project-sync-plan",
                "--issues-json",
                str(sync_plan_issues),
                "--ledger-root",
                str(sync_plan_ledger_root),
                "--project-owner",
                "@me",
                "--project-number",
                "3",
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry", "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")},
        )
        for name, expected in (
            ("project-sync-plan-degraded", "degraded_project_readback"),
            ("project-sync-plan-partial", '"partial_results"'),
            ("project-sync-plan-degraded-source", "github_graphql_project_v2"),
        ):
            errors.extend(expect_ok(name, degraded_sync_plan, expected))
        mixed_recovery_events = [
            {
                "schema_version": 1,
                "event_id": "mixed-local-newer-430",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:10:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:430", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 430},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/430#local"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "mixed-remote-newer-431",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:10:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:431", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 431},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/431#local"]},
                "payload": {"owner_role": "architect"},
            },
            {
                "schema_version": 1,
                "event_id": "mixed-partial-432",
                "event_type": "sync_readback",
                "occurred_at": "2026-07-08T12:11:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:432", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 432},
                "actor_role": "sync",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/432#sync"]},
                "payload": {"local_state": "In Progress", "observed_state": "Done", "field": "Status"},
            },
            {
                "schema_version": 1,
                "event_id": "mixed-branch-433",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:12:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:433", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 433},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/433#local"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "mixed-superseded-434",
                "event_type": "supersession",
                "occurred_at": "2026-07-08T12:13:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:434", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 434},
                "actor_role": "architect",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/434#superseded"]},
                "payload": {"superseded_by": "farmerhunter/agent-foundry#issue:435"},
            },
            {
                "schema_version": 1,
                "event_id": "mixed-out-of-band-436",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T12:14:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:436", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 436},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/436#local"]},
                "payload": {"owner_role": "reviewer"},
            },
        ]
        for event in mixed_recovery_events:
            event_path = base / f"{event['event_id']}.json"
            write(event_path, json.dumps(event))
            errors.extend(
                expect_ok(
                    f"mixed-state-ledger-append-{event['event_id']}",
                    run(["local-ledger-append", "--ledger-root", str(mixed_recovery_ledger_root), "--event-json", str(event_path), "--json"], base),
                    '"mutation_performed": true',
                )
            )
        issue_body_v2 = "\n".join(
            [
                "## Execution Contract",
                "Owner role: implementer",
                "Review role: reviewer",
                "Acceptance role: architect",
                "Completion handoff: to:reviewer",
                "Branch strategy: integration-branch",
                "Release line: v2.0",
                "Target branch: codex/v2-local-first-orchestration",
            ]
        )
        issue_body_v1_on_v2 = issue_body_v2.replace("Release line: v2.0", "Release line: v1.x-maintenance").replace(
            "Target branch: codex/v2-local-first-orchestration",
            "Target branch: main",
        )
        write(
            mixed_recovery_issues,
            json.dumps(
                {
                    "issues": [
                        {"number": 430, "title": "Local newer", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}, {"name": "needs:implementer"}], "body": issue_body_v2},
                        {"number": 431, "title": "Remote newer", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}, {"name": "needs:architect"}], "body": issue_body_v2},
                        {"number": 432, "title": "Partial sync", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}], "body": issue_body_v2},
                        {"number": 433, "title": "Branch drift", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}], "body": issue_body_v1_on_v2},
                        {"number": 434, "title": "Superseded", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}], "body": issue_body_v2},
                        {"number": 436, "title": "Out-of-band owner", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}, {"name": "needs:architect"}], "body": issue_body_v2},
                        {"number": 437, "title": "Remote only", "state": "OPEN", "updatedAt": "2026-07-08T12:20:00Z", "labels": [{"name": "stage:v2.0"}, {"name": "needs:reviewer"}], "body": issue_body_v2},
                    ]
                }
            ),
        )
        write(
            mixed_recovery_project,
            json.dumps(
                {
                    "items": [
                        {"content": {"number": 430}, "updatedAt": "2026-07-08T12:00:00Z", "Status": "Todo", "Owner Role": "Implementer"},
                        {"content": {"number": 431}, "updatedAt": "2026-07-08T12:45:00Z", "Status": "Todo", "Owner Role": "Architect"},
                        {"content": {"number": 432}, "updatedAt": "2026-07-08T12:45:00Z", "Status": "Done", "Owner Role": "Implementer"},
                        {"content": {"number": 433}, "updatedAt": "2026-07-08T12:45:00Z", "Status": "Todo", "Owner Role": "Implementer"},
                        {"content": {"number": 436}, "updatedAt": "2026-07-08T12:45:00Z", "Status": "Todo", "Owner Role": "Architect"},
                        {"content": {"number": 437}, "updatedAt": "2026-07-08T12:45:00Z", "Status": "In Progress", "Owner Role": "Reviewer"},
                    ]
                }
            ),
        )
        write(
            mixed_recovery_candidate_events,
            json.dumps(
                {
                    "candidate_imported_events": [
                        {
                            "schema_version": 1,
                            "event_id": "mixed-candidate-435",
                            "event_type": "assignment",
                            "occurred_at": "2026-07-08T12:15:00Z",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:435", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 435},
                            "actor_role": "coordinator",
                            "confidence": "inferred",
                            "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/435#candidate"]},
                            "payload": {"owner_role": "architect"},
                        }
                    ]
                }
            ),
        )
        mixed_recovery = run(
            [
                "mixed-state-recovery",
                "--issues-json",
                str(mixed_recovery_issues),
                "--project-items-json",
                str(mixed_recovery_project),
                "--ledger-root",
                str(mixed_recovery_ledger_root),
                "--candidate-events-json",
                str(mixed_recovery_candidate_events),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("mixed-state-recovery-command", '"command": "mixed-state-recovery"'),
            ("mixed-state-recovery-read-only", '"mode": "read_only"'),
            ("mixed-state-recovery-no-mutation", '"mutation_performed": false'),
            ("mixed-state-recovery-no-apply", '"apply_supported_now": false'),
            ("mixed-state-recovery-source", '"source_of_truth": "local_collaboration_ledger"'),
            ("mixed-state-recovery-local-newer", '"case_type": "local_newer"'),
            ("mixed-state-recovery-remote-newer", '"case_type": "remote_newer"'),
            ("mixed-state-recovery-remote-only", '"case_type": "remote_only"'),
            ("mixed-state-recovery-candidate-only", '"case_type": "candidate_only"'),
            ("mixed-state-recovery-partial-sync", '"case_type": "partial_sync"'),
            ("mixed-state-recovery-branch-drift", '"case_type": "branch_line_drift"'),
            ("mixed-state-recovery-superseded", '"case_type": "superseded_work"'),
            ("mixed-state-recovery-human-edit", '"case_type": "out_of_band_human_edit"'),
            ("mixed-state-recovery-safe-action", "record_recovery_with_local-ledger-action-apply"),
            ("mixed-state-recovery-forbidden-hidden", "hidden repair"),
            ("mixed-state-recovery-forbidden-authority", "guessing authority from GitHub issue or Project mirror"),
            ("mixed-state-recovery-telemetry", '"telemetry_issue": "#266"'),
        ):
            errors.extend(expect_ok(name, mixed_recovery, expected))
        degraded_recovery = run(
            [
                "--repo",
                "farmerhunter/agent-foundry",
                "mixed-state-recovery",
                "--issues-json",
                str(mixed_recovery_issues),
                "--ledger-root",
                str(mixed_recovery_ledger_root),
                "--project-owner",
                "@me",
                "--project-number",
                "3",
                "--json",
            ],
            base,
            {"PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")},
        )
        errors.extend(expect_ok("mixed-state-recovery-degraded-project", degraded_recovery, '"case_type": "degraded_project"'))
        write(
            cockpit_health,
            json.dumps(
                {
                    "local_runtime": {"status": "missing", "confidence": "observed"},
                    "generated_skill": {"status": "stale", "confidence": "observed"},
                    "core_helper": {"status": "current", "confidence": "observed"},
                    "ledger_schema": {"status": "version_mismatch", "confidence": "observed"},
                    "capability_pack": {"status": "stale", "confidence": "inferred"},
                    "runtime_receipt": {"status": "missing", "confidence": "not_available"},
                    "project_field_schema": {"status": "mismatch", "confidence": "observed"},
                    "diagnostic_note": "/Users/example/private/runtime-receipt.json",
                    "local_private_paths": ["/Users/example/private/raw-vault"],
                }
            ),
        )
        cockpit_ledger_before = (mixed_recovery_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        operational_cockpit = run(
            [
                "operational-cockpit",
                "--issues-json",
                str(mixed_recovery_issues),
                "--project-items-json",
                str(mixed_recovery_project),
                "--ledger-root",
                str(mixed_recovery_ledger_root),
                "--candidate-events-json",
                str(mixed_recovery_candidate_events),
                "--health-json",
                str(cockpit_health),
                "--html-out",
                str(cockpit_html),
                "--json",
            ],
            base,
            {"AGENT_REPO": "farmerhunter/agent-foundry"},
        )
        for name, expected in (
            ("operational-cockpit-command", '"command": "operational-cockpit"'),
            ("operational-cockpit-surface", '"surface": "static_html_local_operational_cockpit"'),
            ("operational-cockpit-read-only", '"mode": "read_only"'),
            ("operational-cockpit-no-mutation", '"mutation_performed": false'),
            ("operational-cockpit-no-apply", '"apply_supported_now": false'),
            ("operational-cockpit-no-writes", '"writes_supported_now": false'),
            ("operational-cockpit-source", '"source_of_truth": "local_collaboration_ledger"'),
            ("operational-cockpit-project-role", "richer_remote_collaboration_control_surface_and_optional_mirror"),
            ("operational-cockpit-on-demand-sync", '"sync_cadence": "on_demand_by_default"'),
            ("operational-cockpit-sections-board", '"board"'),
            ("operational-cockpit-sections-item-detail", '"item_detail"'),
            ("operational-cockpit-sections-migration", '"migration_review"'),
            ("operational-cockpit-sections-apply", '"local_apply_review"'),
            ("operational-cockpit-sections-sync", '"sync_handoff"'),
            ("operational-cockpit-sections-recovery", '"mixed_state_recovery"'),
            ("operational-cockpit-sections-health", '"health"'),
            ("operational-cockpit-sections-telemetry", '"telemetry"'),
            ("operational-cockpit-candidate", '"candidate_count"'),
            ("operational-cockpit-mirror-only", '"remote_mirror_only_count"'),
            ("operational-cockpit-conflict", '"case_type": "branch_line_drift"'),
            ("operational-cockpit-stale-runtime", '"status": "missing"'),
            ("operational-cockpit-stale-skill", '"generated_skill"'),
            ("operational-cockpit-version-mismatch", '"ledger_schema"'),
            ("operational-cockpit-project-plan", "run_project_sync_plan_when"),
            ("operational-cockpit-project-apply", "run_accepted_project_sync_apply_when"),
            ("operational-cockpit-retry-project", "retry_degraded_project_later_when"),
            ("operational-cockpit-no-external-assets", '"html_external_asset_fetches": false'),
            ("operational-cockpit-no-analytics", '"analytics_enabled": false'),
            ("operational-cockpit-private-redacted", "[local-private-path]"),
            ("operational-cockpit-telemetry", '"telemetry_issue": "#266"'),
            ("operational-cockpit-html-written", '"html_output_written": true'),
        ):
            errors.extend(expect_ok(name, operational_cockpit, expected))
        cockpit_ledger_after = (mixed_recovery_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        if cockpit_ledger_before == cockpit_ledger_after:
            print("operational-cockpit-no-ledger-write: ok")
        else:
            errors.append("operational-cockpit-no-ledger-write: cockpit mutated accepted ledger")
        if cockpit_html.exists():
            cockpit_html_text = cockpit_html.read_text(encoding="utf-8")
            for name, expected in (
                ("operational-cockpit-html-title", "Operational Cockpit"),
                ("operational-cockpit-html-board", "<h2>Board</h2>"),
                ("operational-cockpit-html-sync", "<h2>Sync Handoff</h2>"),
                ("operational-cockpit-html-health", "<h2>Health</h2>"),
                ("operational-cockpit-html-forbidden", "live GitHub Project mutation"),
            ):
                if expected in cockpit_html_text:
                    print(f"{name}: ok")
                else:
                    errors.append(f"{name}: expected HTML containing {expected!r}")
            if "/Users/example/private" not in cockpit_html_text and 'src="http' not in cockpit_html_text and 'href="http' not in cockpit_html_text:
                print("operational-cockpit-html-public-safe: ok")
            else:
                errors.append("operational-cockpit-html-public-safe: HTML leaked local private path or external asset link")
        else:
            errors.append("operational-cockpit-html-exists: expected HTML report to be written")
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
            ("branch-readiness-strategy-field", '"Branch strategy"'),
            ("branch-readiness-strategy-values", '"multi-branch"'),
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
            ("branch-readiness-generic-integration", '"target_branch": "codex/customer-integration"'),
            ("branch-readiness-custom-strategy", '"code": "branch_strategy_custom"'),
            ("branch-readiness-stacked-pr", '"branch_strategy": "stacked-pr"'),
            ("branch-readiness-multi-branch", '"branch_strategy": "multi-branch"'),
            ("branch-readiness-current-branch-ok", '"current_branch_ok"'),
            ("branch-readiness-switch-context", '"switch_context_required"'),
            ("branch-readiness-split-work", '"split_work_recommended"'),
            ("branch-readiness-forward-merge", '"forward_merge_needed_later"'),
            ("branch-readiness-multiple-lines", '"verify_on_multiple_lines"'),
            ("branch-readiness-architect-decision", '"architect_decision_required"'),
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
        ledger_root = base / "ledger"
        ledger_events = [
            {
                "schema_version": 1,
                "event_id": "evt-001",
                "event_type": "assignment",
                "occurred_at": "2026-07-08T10:00:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359"]},
                "payload": {"owner_role": "implementer"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-002",
                "event_type": "dispatch",
                "occurred_at": "2026-07-08T10:01:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#issuecomment-4914188818"]},
                "payload": {"target_role": "implementer", "thread_id": "019ea64c-33ed-79e1-9bee-0f414e0ca8f4"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-003",
                "event_type": "callback",
                "occurred_at": "2026-07-08T10:02:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "implementer",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#callback"]},
                "payload": {"summary": "implementation started"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-004",
                "event_type": "review",
                "occurred_at": "2026-07-08T10:03:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "reviewer",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/pull/000#review"]},
                "payload": {"decision": "request_changes"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-005",
                "event_type": "review",
                "occurred_at": "2026-07-08T10:04:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "reviewer",
                "confidence": "observed",
                "supersedes_event_ids": ["evt-004"],
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/pull/000#review2"]},
                "payload": {"decision": "approved"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-006",
                "event_type": "acceptance",
                "occurred_at": "2026-07-08T10:05:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "architect",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#acceptance"]},
                "payload": {"decision": "accepted"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-007",
                "event_type": "merge",
                "occurred_at": "2026-07-08T10:06:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "human",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/pull/000"]},
                "payload": {"merge_sha": "abc123"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-008",
                "event_type": "closure",
                "occurred_at": "2026-07-08T10:07:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "architect",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#closed"]},
                "payload": {"state": "closed"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-009",
                "event_type": "blocked",
                "occurred_at": "2026-07-08T10:08:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:360", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 360},
                "actor_role": "implementer",
                "confidence": "inferred",
                "unknown_fields": ["exact_unblock_time"],
                "not_available_fields": ["human_decision_eta"],
                "degraded_evidence": [{"source": "github_project", "status": "not_available"}],
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/360"]},
                "payload": {"reason": "#359 not accepted yet"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-010",
                "event_type": "sync_readback",
                "occurred_at": "2026-07-08T10:09:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "coordinator",
                "confidence": "observed",
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#readback"]},
                "payload": {"local_state": "closed", "observed_state": "open"},
            },
            {
                "schema_version": 1,
                "event_id": "evt-011",
                "event_type": "custom_future_note",
                "occurred_at": "2026-07-08T10:10:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "coordinator",
                "confidence": "unknown",
                "unknown_fields": ["future_note"],
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#future"]},
            },
            {
                "schema_version": 2,
                "event_id": "evt-012",
                "event_type": "future_event",
                "occurred_at": "2026-07-08T10:11:00Z",
                "work_item": {"id": "farmerhunter/agent-foundry#issue:359", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 359},
                "actor_role": "coordinator",
                "confidence": "not_available",
                "not_available_fields": ["future_schema_decoder"],
                "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/359#future-schema"]},
            },
        ]
        for event in ledger_events:
            event_path = base / f"{event['event_id']}.json"
            write(event_path, json.dumps(event))
            errors.extend(
                expect_ok(
                    f"local-ledger-append-{event['event_id']}",
                    run(["local-ledger-append", "--ledger-root", str(ledger_root), "--event-json", str(event_path), "--json"], base),
                    f'"event_id": "{event["event_id"]}"',
                )
            )
        duplicate_event_path = base / "evt-010-duplicate.json"
        write(duplicate_event_path, json.dumps(ledger_events[9]))
        errors.extend(
            expect_ok(
                "local-ledger-append-duplicate-id",
                run(["local-ledger-append", "--ledger-root", str(ledger_root), "--event-json", str(duplicate_event_path), "--json"], base),
                '"event_id": "evt-010"',
            )
        )
        malformed_event = base / "malformed-event.json"
        write(malformed_event, json.dumps({"schema_version": 1, "event_id": "bad"}))
        errors.extend(
            expect_fail(
                "local-ledger-malformed-fails",
                run(["local-ledger-append", "--ledger-root", str(ledger_root), "--event-json", str(malformed_event), "--json"], base),
                '"status": "invalid"',
            )
        )
        ledger_report = run(["local-ledger-report", "--ledger-root", str(ledger_root), "--json"], base, {"PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")})
        for name, expected in (
            ("local-ledger-report-command", '"command": "local-ledger-report"'),
            ("local-ledger-report-read-only", '"mode": "read_only"'),
            ("local-ledger-report-no-mutation", '"mutation_performed": false'),
            ("local-ledger-report-no-apply", '"apply_supported_now": false'),
            ("local-ledger-report-no-github", '"github_dependency_for_replay": false'),
            ("local-ledger-report-authority", "local_collaboration_ledger_events_are_replay_authority_for_this_report"),
            ("local-ledger-report-assigned", '"state": "stale_conflict"'),
            ("local-ledger-report-blocked", '"state": "blocked"'),
            ("local-ledger-report-superseded", '"superseded_event_count": 1'),
            ("local-ledger-report-conflict", "sync_readback_state_mismatch"),
            ("local-ledger-report-unknown", '"unknown_or_forward_compatible_event_count": 2'),
            ("local-ledger-report-not-available", "human_decision_eta"),
            ("local-ledger-report-degraded", '"degraded_evidence_count": 1'),
            ("local-ledger-report-duplicate", '"duplicate_event_ids"'),
            ("local-ledger-report-telemetry", '"telemetry_issue": "#266"'),
            ("local-ledger-report-user-output-size", '"user_facing_output_bytes"'),
            ("local-ledger-report-next-action", "rehydrate_and_reconcile_evidence"),
            ("local-ledger-report-forbidden-backfill", "#360 backfill"),
        ):
            errors.extend(expect_ok(name, ledger_report, expected))
        ledger_report_again = run(["local-ledger-report", "--ledger-root", str(ledger_root), "--json"], base)
        if ledger_report.returncode == 0 and ledger_report_again.returncode == 0:
            first = json.loads(ledger_report.stdout)
            second = json.loads(ledger_report_again.stdout)
            for payload in (first, second):
                payload["telemetry"]["replay_time_ms"] = 0
                payload["telemetry"]["user_facing_output_bytes"] = 0
                payload["summary"]["replay_time_ms"] = 0
            if first == second:
                print("local-ledger-replay-deterministic: ok")
            else:
                errors.append("local-ledger-replay-deterministic: repeated report output differed after normalizing replay_time_ms")
        events_path = ledger_root / "events.jsonl"
        if events_path.exists() and str(events_path).startswith(str(base)):
            print("local-ledger-write-scope-temp-only: ok")
        else:
            errors.append("local-ledger-write-scope-temp-only: ledger did not write inside explicit temp root")
        backfill_issues = base / "backfill-issues.json"
        backfill_prs = base / "backfill-prs.json"
        backfill_project = base / "backfill-project.json"
        write(
            backfill_issues,
            json.dumps(
                {
                    "issues": [
                        {
                            "number": 410,
                            "title": "Open but Project Done",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/410",
                            "labels": [{"name": "needs:implementer"}, {"name": "stage:v2.0"}],
                            "updatedAt": "2026-07-08T11:00:00Z",
                            "comments": [
                                {"body": "Dispatch evidence sent to implementer thread.", "url": "https://github.com/farmerhunter/agent-foundry/issues/410#dispatch"},
                                {"body": "Callback: implementation evidence returned.", "url": "https://github.com/farmerhunter/agent-foundry/issues/410#callback"},
                                {"body": "Reviewer requested changes.", "url": "https://github.com/farmerhunter/agent-foundry/issues/410#review"},
                                {"body": "Architect acceptance after fix.", "url": "https://github.com/farmerhunter/agent-foundry/issues/410#acceptance"},
                                {"body": "Superseded by issue #411.", "url": "https://github.com/farmerhunter/agent-foundry/issues/410#superseded"},
                            ],
                        },
                        {
                            "number": 411,
                            "title": "Closed but Project Todo",
                            "state": "CLOSED",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/411",
                            "labels": [{"name": "needs:reviewer"}, {"name": "stage:v2.0"}],
                            "updatedAt": "2026-07-08T11:01:00Z",
                            "comments": [],
                        },
                        {
                            "number": 412,
                            "title": "Ambiguous owner and missing Project item",
                            "state": "OPEN",
                            "url": "https://github.com/farmerhunter/agent-foundry/issues/412",
                            "labels": [{"name": "needs:architect"}, {"name": "needs:reviewer"}, {"name": "stage:v2.0"}],
                            "updatedAt": "2026-07-08T11:02:00Z",
                            "comments": [],
                        },
                    ]
                }
            ),
        )
        write(
            backfill_prs,
            json.dumps(
                {
                    "items": [
                        {
                            "number": 413,
                            "title": "Merged PR",
                            "state": "MERGED",
                            "url": "https://github.com/farmerhunter/agent-foundry/pull/413",
                            "labels": [{"name": "stage:v2.0"}],
                            "updatedAt": "2026-07-08T11:03:00Z",
                            "merged": True,
                            "merge_sha": "def456",
                        }
                    ]
                }
            ),
        )
        write(
            backfill_project,
            json.dumps(
                {
                    "items": [
                        {
                            "content": {"number": 410},
                            "status": {"name": "Done"},
                            "owner Role": {"name": "Reviewer"},
                            "stage": {"name": "v2.0"},
                        },
                        {
                            "content": {"number": 411},
                            "status": {"name": "Todo"},
                            "owner Role": {"name": "Reviewer"},
                            "stage": {"name": "v2.0"},
                        },
                    ]
                }
            ),
        )
        accepted_ledger_root = base / "accepted-ledger"
        accepted_event = base / "accepted-410.json"
        write(
            accepted_event,
            json.dumps(
                {
                    "schema_version": 1,
                    "event_id": "accepted-410",
                    "event_type": "assignment",
                    "occurred_at": "2026-07-08T10:00:00Z",
                    "work_item": {"id": "farmerhunter/agent-foundry#issue:410", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 410},
                    "actor_role": "coordinator",
                    "confidence": "observed",
                    "provenance": {"links": ["https://github.com/farmerhunter/agent-foundry/issues/410#accepted-local"]},
                    "payload": {"owner_role": "implementer"},
                }
            ),
        )
        errors.extend(
            expect_ok(
                "local-ledger-backfill-accepted-fixture",
                run(["local-ledger-append", "--ledger-root", str(accepted_ledger_root), "--event-json", str(accepted_event), "--json"], base),
                '"mutation_performed": true',
            )
        )
        before_preview = (accepted_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        backfill_preview = run(
            [
                "--repo",
                "farmerhunter/agent-foundry",
                "local-ledger-backfill-preview",
                "--issues-json",
                str(backfill_issues),
                "--prs-json",
                str(backfill_prs),
                "--project-items-json",
                str(backfill_project),
                "--ledger-root",
                str(accepted_ledger_root),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("local-ledger-backfill-command", '"command": "local-ledger-backfill-preview"'),
            ("local-ledger-backfill-read-only", '"mode": "read_only"'),
            ("local-ledger-backfill-no-mutation", '"mutation_performed": false'),
            ("local-ledger-backfill-no-apply", '"apply_supported_now": false'),
            ("local-ledger-backfill-candidates-not-authority", '"candidate_events_are_authoritative": false'),
            ("local-ledger-backfill-accepted-separate", '"state_authority": "accepted_local_ledger"'),
            ("local-ledger-backfill-assignment", '"event_type": "assignment"'),
            ("local-ledger-backfill-dispatch", '"event_type": "dispatch"'),
            ("local-ledger-backfill-callback", '"event_type": "callback"'),
            ("local-ledger-backfill-review", '"event_type": "requested_changes"'),
            ("local-ledger-backfill-acceptance", '"event_type": "acceptance"'),
            ("local-ledger-backfill-merge", '"event_type": "merge"'),
            ("local-ledger-backfill-closure", '"event_type": "closure"'),
            ("local-ledger-backfill-sync", '"event_type": "sync_readback"'),
            ("local-ledger-backfill-owner-mismatch", "owner_mismatch"),
            ("local-ledger-backfill-closed-not-done", "closed_issue_not_mirrored_done"),
            ("local-ledger-backfill-project-done-open", "project_done_while_item_open"),
            ("local-ledger-backfill-stale-labels", "stale_or_conflicting_needs_labels"),
            ("local-ledger-backfill-superseded", "superseded_work"),
            ("local-ledger-backfill-missing-project", "missing_project_item"),
            ("local-ledger-backfill-partial-evidence", "partial existing-project evidence requires manual review"),
            ("local-ledger-backfill-accepted-conflict", "accepted_local_state_differs_from_candidate"),
            ("local-ledger-backfill-telemetry", '"telemetry_issue": "#266"'),
            ("local-ledger-backfill-candidate-count", '"candidate_count"'),
            ("local-ledger-backfill-manual-review", '"manual_review_count"'),
            ("local-ledger-backfill-writes-none", '"writes": "none"'),
            ("local-ledger-backfill-forbidden-project", "Project v2 mutation"),
            ("local-ledger-backfill-forbidden-board", "#361 ledger-backed Foundry Board"),
            ("local-ledger-backfill-next-action", "review_candidate_events_before_acceptance"),
        ):
            errors.extend(expect_ok(name, backfill_preview, expected))
        after_preview = (accepted_ledger_root / "events.jsonl").read_text(encoding="utf-8")
        if before_preview == after_preview:
            print("local-ledger-backfill-no-ledger-write: ok")
        else:
            errors.append("local-ledger-backfill-no-ledger-write: preview mutated accepted ledger")
        migration_preview = base / "migration-preview.json"
        migration_decisions = base / "migration-decisions.json"
        write(migration_preview, backfill_preview.stdout)
        write(
            migration_decisions,
            json.dumps(
                {
                    "decisions": [
                        {
                            "event_id": "candidate-issue-410-assignment",
                            "decision": "accept",
                            "reason": "reviewed owner candidate",
                            "manual_review_note": "accept implementer owner from needs label",
                        },
                        {
                            "event_id": "candidate-issue-410-dispatch-1",
                            "decision": "reject",
                            "reason": "dispatch comment is historical evidence only",
                        },
                        {
                            "event_id": "candidate-issue-410-callback-2",
                            "decision": "skip",
                            "reason": "callback belongs to superseded workflow",
                        },
                    ]
                }
            ),
        )
        migration_apply = run(
            [
                "local-ledger-migration-apply",
                "--ledger-root",
                str(accepted_ledger_root),
                "--candidate-events-json",
                str(migration_preview),
                "--decision-json",
                str(migration_decisions),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("local-ledger-migration-apply-command", '"command": "local-ledger-migration-apply"'),
            ("local-ledger-migration-apply-mode", '"mode": "apply"'),
            ("local-ledger-migration-apply-mutates-local", '"mutation_performed": true'),
            ("local-ledger-migration-apply-local-scope", '"write_scope": "local_ledger_events_jsonl_only"'),
            ("local-ledger-migration-apply-no-github", '"github_write_back_performed": false'),
            ("local-ledger-migration-apply-no-project", '"project_mutation_performed": false'),
            ("local-ledger-migration-apply-layer", '"capability_layer": "local_orchestration"'),
            ("local-ledger-migration-apply-accepted", '"accepted_count": 1'),
            ("local-ledger-migration-apply-rejected", '"rejected_count": 1'),
            ("local-ledger-migration-apply-skipped", '"skipped_count": 1'),
            ("local-ledger-migration-apply-before-after", '"before"'),
            ("local-ledger-migration-apply-compensating", "append compensating evidence or superseding events"),
            ("local-ledger-migration-apply-forbidden-project", "Project v2 mutation"),
            ("local-ledger-migration-apply-forbidden-371", "#371 local action apply"),
            ("local-ledger-migration-apply-telemetry", '"telemetry_issue": "#266"'),
        ):
            errors.extend(expect_ok(name, migration_apply, expected))
        migration_report = run(["local-ledger-report", "--ledger-root", str(accepted_ledger_root), "--json"], base)
        for name, expected in (
            ("local-ledger-migration-accepted-replay", "accepted-candidate-issue-410-assignment"),
            ("local-ledger-migration-rejected-replay", "rejected-candidate-issue-410-dispatch-1"),
            ("local-ledger-migration-skipped-replay", "skipped-candidate-issue-410-callback-2"),
        ):
            errors.extend(expect_ok(name, migration_report, expected))
        migration_apply_again = run(
            [
                "local-ledger-migration-apply",
                "--ledger-root",
                str(accepted_ledger_root),
                "--candidate-events-json",
                str(migration_preview),
                "--decision-json",
                str(migration_decisions),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("local-ledger-migration-idempotent-no-new-write", '"mutation_performed": false'),
            ("local-ledger-migration-idempotent-duplicates", '"duplicate_skip_count": 3'),
            ("local-ledger-migration-idempotent-reason", "idempotent_duplicate_event_id"),
        ):
            errors.extend(expect_ok(name, migration_apply_again, expected))
        local_action_root = base / "local-action-ledger"
        local_actions = base / "local-actions.json"
        write(
            local_actions,
            json.dumps(
                {
                    "actions": [
                        {
                            "action_id": "assign-510",
                            "action_type": "assignment",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:510", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 510},
                            "owner_role": "implementer",
                            "approved_by_role": "agent",
                            "evidence_refs": ["https://github.com/farmerhunter/agent-foundry/issues/510#assignment"],
                            "capability_layer": {"layer": "local_orchestration", "source": "issue_contract", "confidence": "observed"},
                        },
                        {
                            "action_id": "handoff-510",
                            "action_type": "handoff",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:510", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 510},
                            "target_role": "reviewer",
                            "approved_by_role": "agent",
                            "evidence_refs": ["https://github.com/farmerhunter/agent-foundry/issues/510#handoff"],
                        },
                        {
                            "action_id": "blocked-511",
                            "action_type": "blocked",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:511", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 511},
                            "reason": "missing external evidence",
                            "approved_by_role": "agent",
                            "degraded_evidence": [{"source": "github", "status": "degraded"}],
                        },
                        {
                            "action_id": "unblocked-511",
                            "action_type": "unblocked",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:511", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 511},
                            "approved_by_role": "agent",
                            "payload": {"next_review_or_action_needed": "resume_work"},
                        },
                        {
                            "action_id": "review-512",
                            "action_type": "review_result",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:512", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 512},
                            "required_gate": "reviewer",
                            "approved_by_role": "reviewer",
                            "decision": "request_changes",
                        },
                        {
                            "action_id": "accept-513",
                            "action_type": "architect_acceptance",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:513", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 513},
                            "required_gate": "architect",
                            "approved_by_role": "architect",
                        },
                        {
                            "action_id": "human-514",
                            "action_type": "human_approval",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:514", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 514},
                            "required_gate": "human",
                            "approved_by_role": "human",
                            "approval": "approved local ledger action",
                            "capability_layer": "mixed",
                        },
                        {
                            "action_id": "done-515",
                            "action_type": "local_done",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:515", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 515},
                            "required_gate": "reviewer",
                            "approved_by_role": "reviewer",
                        },
                        {
                            "action_id": "supersede-516",
                            "action_type": "supersession",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:516", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 516},
                            "approved_by_role": "agent",
                            "superseded_by": "farmerhunter/agent-foundry#issue:517",
                        },
                        {
                            "action_id": "recover-517",
                            "action_type": "recovery",
                            "work_item": {"id": "farmerhunter/agent-foundry#issue:517", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 517},
                            "approved_by_role": "agent",
                            "summary": "recorded interrupted apply recovery evidence",
                            "unknown_fields": ["remote_project_readback"],
                        },
                    ]
                }
            ),
        )
        local_action_apply = run(
            [
                "local-ledger-action-apply",
                "--ledger-root",
                str(local_action_root),
                "--action-json",
                str(local_actions),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("local-ledger-action-apply-command", '"command": "local-ledger-action-apply"'),
            ("local-ledger-action-apply-mode", '"mode": "apply"'),
            ("local-ledger-action-apply-mutates-local", '"mutation_performed": true'),
            ("local-ledger-action-apply-local-scope", '"write_scope": "local_ledger_events_jsonl_only"'),
            ("local-ledger-action-apply-no-github", '"github_write_back_performed": false'),
            ("local-ledger-action-apply-no-project", '"project_mutation_performed": false'),
            ("local-ledger-action-apply-no-runtime", '"runtime_vault_private_generated_write_performed": false'),
            ("local-ledger-action-apply-assignment", '"assignment": 1'),
            ("local-ledger-action-apply-handoff", '"handoff": 1'),
            ("local-ledger-action-apply-blocked", '"blocked": 1'),
            ("local-ledger-action-apply-unblocked", '"unblocked": 1'),
            ("local-ledger-action-apply-review", '"review_result": 1'),
            ("local-ledger-action-apply-acceptance", '"architect_acceptance": 1'),
            ("local-ledger-action-apply-human", '"human_approval": 1'),
            ("local-ledger-action-apply-closure", '"local_done": 1'),
            ("local-ledger-action-apply-supersession", '"supersession": 1'),
            ("local-ledger-action-apply-recovery", '"recovery": 1'),
            ("local-ledger-action-apply-reviewer-gate", '"reviewer": 2'),
            ("local-ledger-action-apply-architect-gate", '"architect": 1'),
            ("local-ledger-action-apply-human-gate", '"human": 1'),
            ("local-ledger-action-apply-layer", '"layer": "local_orchestration"'),
            ("local-ledger-action-apply-mixed", '"layer": "mixed"'),
            ("local-ledger-action-apply-user-report", "run_foundry-board_to_review_next_actions"),
            ("local-ledger-action-apply-forbidden-project", "GitHub Project mutation"),
            ("local-ledger-action-apply-forbidden-372", "#372 Project sync apply"),
            ("local-ledger-action-apply-telemetry", '"telemetry_issue": "#266"'),
        ):
            errors.extend(expect_ok(name, local_action_apply, expected))
        local_action_report = run(["local-ledger-report", "--ledger-root", str(local_action_root), "--json"], base)
        for name, expected in (
            ("local-ledger-action-replay-assigned", '"state": "dispatched"'),
            ("local-ledger-action-replay-unblocked", "resume_work"),
            ("local-ledger-action-replay-review", '"state": "review_changes_requested"'),
            ("local-ledger-action-replay-accepted", '"state": "accepted"'),
            ("local-ledger-action-replay-human", '"state": "human_approved"'),
            ("local-ledger-action-replay-closed", '"state": "closed"'),
            ("local-ledger-action-replay-superseded", '"state": "superseded"'),
            ("local-ledger-action-replay-recovery", "recorded interrupted apply recovery evidence"),
        ):
            errors.extend(expect_ok(name, local_action_report, expected))
        local_action_apply_again = run(
            [
                "local-ledger-action-apply",
                "--ledger-root",
                str(local_action_root),
                "--action-json",
                str(local_actions),
                "--json",
            ],
            base,
        )
        for name, expected in (
            ("local-ledger-action-idempotent-no-new-write", '"mutation_performed": false'),
            ("local-ledger-action-idempotent-duplicates", '"duplicate_skip_count": 10'),
            ("local-ledger-action-idempotent-reason", "idempotent_duplicate_event_id"),
        ):
            errors.extend(expect_ok(name, local_action_apply_again, expected))
        bad_local_action = base / "bad-local-action.json"
        write(
            bad_local_action,
            json.dumps(
                {
                    "action_type": "human_approval",
                    "work_item": {"id": "farmerhunter/agent-foundry#issue:518", "repo": "farmerhunter/agent-foundry", "type": "issue", "number": 518},
                    "required_gate": "human",
                    "approved_by_role": "reviewer",
                }
            ),
        )
        errors.extend(
            expect_fail(
                "local-ledger-action-gate-fails-closed",
                run(["local-ledger-action-apply", "--ledger-root", str(local_action_root), "--action-json", str(bad_local_action), "--json"], base),
                "requires human gate",
            )
        )
        dogfood_root = base / "ledger-dogfood-trial"
        dogfood_decisions = base / "ledger-dogfood-decisions.json"
        dogfood_candidates = json.loads(backfill_preview.stdout).get("candidate_imported_events", [])
        dogfood_candidate = next((event for event in dogfood_candidates if event.get("work_item", {}).get("number") == 410), None)
        if dogfood_candidate is None:
            errors.append("ledger-dogfood-fixture: expected a candidate for issue 410")
        else:
            write(
                dogfood_decisions,
                json.dumps(
                    {
                        "human_response": {
                            "context_confirmed": True,
                            "candidate_set": "accept issue 410 for isolated ledger dogfood",
                            "local_transition": "record human-gated blocked state",
                            "project_sync_interpretation": "mirror/control surface only; not executed",
                        },
                        "candidate_decisions": {
                            "decisions": [
                                {
                                    "event_id": dogfood_candidate["event_id"],
                                    "decision": "accept",
                                    "reason": "Human accepted bounded issue evidence for isolated dogfood.",
                                }
                            ]
                        },
                        "local_actions": {
                            "actions": [
                                {
                                    "action_id": "dogfood-blocked-410",
                                    "action_type": "blocked",
                                    "work_item": dogfood_candidate["work_item"],
                                    "approved_by_role": "human",
                                    "reason": "Human gate remains pending in the isolated local workflow.",
                                    "evidence_refs": ["https://github.com/farmerhunter/agent-foundry/issues/410"],
                                    "capability_layer": "local_orchestration",
                                }
                            ]
                        },
                    }
                ),
            )
            ledger_dogfood = run(
                [
                    "--repo",
                    "farmerhunter/agent-foundry",
                    "ledger-dogfood",
                    "--trial-root",
                    str(dogfood_root),
                    "--decision-json",
                    str(dogfood_decisions),
                    "--issues-json",
                    str(backfill_issues),
                    "--prs-json",
                    str(backfill_prs),
                    "--project-items-json",
                    str(backfill_project),
                    "--json",
                ],
                base,
            )
            for name, expected in (
                ("ledger-dogfood-command", '"command": "ledger-dogfood"'),
                ("ledger-dogfood-status", '"status": "ok"'),
                ("ledger-dogfood-local-authority", "accepted_local_collaboration_ledger_replay"),
                ("ledger-dogfood-local-write", '"write_scope": "explicit_trial_root_only"'),
                ("ledger-dogfood-issue-transition", "dogfood-blocked-410"),
                ("ledger-dogfood-project-mirror", "remote_collaboration_control_surface_and_optional_mirror"),
                ("ledger-dogfood-project-not-executed", '"project_sync_not_executed": true'),
                ("ledger-dogfood-no-github-write", '"github_write_back_performed": false'),
                ("ledger-dogfood-no-project-write", '"project_mutation_performed": false'),
                ("ledger-dogfood-cleanup", "remove only the explicit trial root"),
                ("ledger-dogfood-telemetry", '"telemetry_issue": "#266"'),
            ):
                errors.extend(expect_ok(name, ledger_dogfood, expected))
            for relative in (
                "local-collaboration-ledger/events.jsonl",
                "backfill-preview.json",
                "reviewed-migration-decisions.json",
                "local-action-apply-report.json",
                "before-replay.json",
                "after-replay.json",
                "foundry-board.json",
                "operational-cockpit.json",
                "operational-cockpit.html",
                "project-sync-plan.json",
                "mixed-state-recovery.json",
                "human-transcript.json",
                "audit-manifest.json",
            ):
                if (dogfood_root / relative).exists():
                    print(f"ledger-dogfood-artifact-{relative}: ok")
                else:
                    errors.append(f"ledger-dogfood-artifact-{relative}: expected isolated trial artifact")
            ledger_dogfood_again = run(
                [
                    "--repo",
                    "farmerhunter/agent-foundry",
                    "ledger-dogfood",
                    "--trial-root",
                    str(dogfood_root),
                    "--decision-json",
                    str(dogfood_decisions),
                    "--issues-json",
                    str(backfill_issues),
                    "--prs-json",
                    str(backfill_prs),
                    "--project-items-json",
                    str(backfill_project),
                    "--json",
                ],
                base,
            )
            errors.extend(expect_ok("ledger-dogfood-idempotent", ledger_dogfood_again, '"mutation_performed": false'))
        missing_dogfood_decision = base / "ledger-dogfood-missing-human.json"
        write(missing_dogfood_decision, json.dumps({"candidate_decisions": {}, "local_actions": {}}))
        errors.extend(
            expect_fail(
                "ledger-dogfood-human-decision-required",
                run(["ledger-dogfood", "--trial-root", str(base / "blocked-dogfood"), "--decision-json", str(missing_dogfood_decision), "--issues-json", str(backfill_issues), "--json"], base),
                "blocked_waiting_for_human_decision",
            )
        )
        degraded_backfill = run(
            [
                "--repo",
                "farmerhunter/agent-foundry",
                "local-ledger-backfill-preview",
                "--issues-json",
                str(backfill_issues),
                "--project-owner",
                "@me",
                "--project-number",
                "3",
                "--json",
            ],
            base,
            {"PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")},
        )
        for name, expected in (
            ("local-ledger-backfill-degraded-source", "github_graphql_project_v2"),
            ("local-ledger-backfill-degraded-count", '"degraded_source_count": 1'),
            ("local-ledger-backfill-degraded-events", '"degraded_evidence"'),
        ):
            errors.extend(expect_ok(name, degraded_backfill, expected))

    if errors:
        print("GitHub collaboration helper fixture tests failed:")
        for error in errors:
            print(error)
        return 1
    print("GitHub collaboration helper fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
