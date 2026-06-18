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
        inbox = base / "inbox.json"
        auth = base / "auth.json"
        write(auth, json.dumps({"status": "ok", "nameWithOwner": "farmerhunter/agent-foundry"}))
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
        errors.extend(
            expect_fail(
                "permission-forbidden",
                run(["permission-smoke", "agent-label"], base),
                "unit_b_forbidden_mutation",
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

    if errors:
        print("GitHub collaboration helper fixture tests failed:")
        for error in errors:
            print(error)
        return 1
    print("GitHub collaboration helper fixture tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
