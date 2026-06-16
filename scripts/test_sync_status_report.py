#!/usr/bin/env python3
"""Regression tests for read-only install/status reporting."""

from __future__ import annotations

import subprocess
import tempfile
import sys
from pathlib import Path

import sync_status
from adapter_install_receipt import file_sha256
from sync_status import ROOT, DEFAULT_GENERATED_ROOT, default_adapter_root, deployed_packs, repo_progress_status, runtime_status, setup_report


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def assert_git(args: list[str], cwd: Path) -> None:
    result = git(args, cwd)
    assert result.returncode == 0, result.stdout + result.stderr


def assert_repo_progress_behind(base: Path) -> None:
    base.mkdir(parents=True)
    remote = base / "remote.git"
    work = base / "work"
    other = base / "other"
    assert_git(["init", "--bare", str(remote)], base)
    assert_git(["init", "-b", "main", str(work)], base)
    assert_git(["config", "user.email", "agent-foundry@example.com"], work)
    assert_git(["config", "user.name", "Agent Foundry"], work)
    write(work / "README.md", "one\n")
    assert_git(["add", "README.md"], work)
    assert_git(["commit", "-m", "initial"], work)
    assert_git(["remote", "add", "origin", str(remote)], work)
    assert_git(["push", "-u", "origin", "main"], work)

    assert_git(["clone", str(remote), str(other)], base)
    assert_git(["checkout", "main"], other)
    assert_git(["config", "user.email", "agent-foundry@example.com"], other)
    assert_git(["config", "user.name", "Agent Foundry"], other)
    write(other / "README.md", "two\n")
    assert_git(["commit", "-am", "remote progress"], other)
    assert_git(["push"], other)
    assert_git(["fetch"], work)

    original_root = sync_status.ROOT
    try:
        sync_status.ROOT = work
        report = repo_progress_status()
        assert "repo: behind ahead=0 behind=1" in report, report
        assert "repair: fetch/pull remote Core progress before publishing generated output or applying runtime changes" in report, report
    finally:
        sync_status.ROOT = original_root


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-sync-status.") as raw:
        base = Path(raw)
        assert_repo_progress_behind(base / "repo-progress")
        vault = base / "vault"
        generated = base / "generated-adapters"
        receipt = base / "adapter-install-receipt.json"
        (vault / "practices").mkdir(parents=True)
        (generated / "codex" / "skills").mkdir(parents=True)
        write(generated / "adapter-publish-manifest.yaml", "active_assets: []\n")
        write(
            vault / "indexes" / "practice_index.yaml",
            "\n".join(
                [
                    "schema_version: 1",
                    "practices:",
                    "  - id: PRACTICE-ACTIVE-001",
                    "    status: active",
                    "    path: practices/example/PRACTICE-ACTIVE-001.md",
                    "",
                ]
            ),
        )
        write(
            vault / "indexes" / "asset_index.yaml",
            "\n".join(
                [
                    "schema_version: 1",
                    "assets:",
                    "  - id: ASSET-ACTIVE-001",
                    "    status: active",
                    "    path: assets/skills/ASSET-ACTIVE-001.asset.yaml",
                    "",
                ]
            ),
        )
        write(
            receipt,
            "{\n"
            '  "schema_version": 1,\n'
            f'  "adapter_root": "{generated}",\n'
            '  "installed_files": []\n'
            "}\n",
        )
        write(
            vault / "packs" / "deployed-pack-index.yaml",
            "\n".join(
                [
                    "schema_version: 1",
                    "updated: 2026-06-12",
                    "deployed_packs:",
                    "  - pack_id: pack.bootstrap.minimal",
                    '    title: "Bootstrap Pack"',
                    '    version: "0.1.0"',
                    "    lifecycle_status: deployed",
                    "    distribution_type: mandatory_bootstrap",
                    "    source:",
                    "      kind: local_path",
                    f'      locator: "{base / "pack"}"',
                    "      manifest_sha256: abc123",
                    "      reviewed_by: architect",
                    "    records: []",
                    "    executable_payloads: []",
                    "    decisions:",
                    "      conflict_policy: fail_closed",
                    "      notes: []",
                    "",
                ]
            ),
        )

        packs = deployed_packs(vault)
        assert packs == [
            "pack.bootstrap.minimal (version=0.1.0, status=deployed, type=mandatory_bootstrap, source=local_path)"
        ], packs
        assert default_adapter_root(ROOT, vault, receipt) == generated.resolve()
        assert default_adapter_root(ROOT, vault, base / "absent-receipt.json") == DEFAULT_GENERATED_ROOT.resolve()

        missing_receipt = base / "missing-receipt.json"
        report = setup_report(ROOT, vault, generated, missing_receipt)
        expected = [
            "Agent Foundry setup/status report",
            "deployed_pack: pack.bootstrap.minimal",
            "deployed_packs:",
            "- pack.bootstrap.minimal (version=0.1.0, status=deployed, type=mandatory_bootstrap, source=local_path)",
            f"generated_output: ready path={generated} files=1",
            "activation: stale-generated-output missing_active_practices=1 missing_active_assets=1",
            "activation missing practice: PRACTICE-ACTIVE-001",
            "activation missing asset: ASSET-ACTIVE-001",
            "activation repair: publish selected Vault generated output, then dry-run runtime install before apply",
            "receipt: missing",
            "- chatgpt: manual import required",
            "next_safe_actions:",
            "- status-only: no files were written by this report",
            "- run runtime install only after generated output dry-run/review; receipt is currently missing",
            "- treat ChatGPT as manual import unless a future managed target is explicitly implemented",
        ]
        for text in expected:
            assert text in report, text

        trae_dest = base / "runtime" / "trae"
        write(generated / "trae" / "skills" / "role-automation-planner" / "SKILL.md", "generated trae skill\n")
        write(trae_dest / "role-automation-planner" / "SKILL.md", "stale installed skill\n")
        write(
            receipt,
            "{\n"
            '  "schema_version": 1,\n'
            f'  "adapter_root": "{generated}",\n'
            '  "installed_targets": ["trae"],\n'
            '  "installed_files": [\n'
            "    {\n"
            '      "target": "trae",\n'
            '      "source": "trae/skills/role-automation-planner/SKILL.md",\n'
            f'      "destination": "{trae_dest / "role-automation-planner" / "SKILL.md"}",\n'
            f'      "sha256": "{file_sha256(generated / "trae" / "skills" / "role-automation-planner" / "SKILL.md")}"\n'
            "    }\n"
            "  ]\n"
            "}\n",
        )
        drift_report = setup_report(ROOT, vault, generated, receipt)
        drift_expected = [
            "receipt: selected-output-drift",
            "receipt target: trae selected-output-drift checked=1 problems=1",
            "receipt repair: trae review generated output, run install dry-run, then apply only with runtime-write approval",
            "receipt repair: trae writes ~/.trae-cn/skills and requires durable human approval before --apply",
            "- review selected-output drift, regenerate generated output if needed, then dry-run runtime install before apply",
            "- for Trae, do not write ~/.trae-cn/skills unless durable human approval explicitly authorizes that runtime apply",
        ]
        for text in drift_expected:
            assert text in drift_report, text

        local_manifest = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
        before = local_manifest.read_bytes() if local_manifest.exists() else None
        original_root = sync_status.ROOT
        try:
            fake_core = base / "fake-core"
            write(
                fake_core / "runtime" / "templates" / "runtime_manifest.template.yaml",
                "\n".join(
                    [
                        "targets:",
                        "  codex:",
                        "    status: enabled",
                        "    install_path: ~/.codex/skills",
                        "    ownership_mode: managed-directories",
                        "  chatgpt:",
                        "    status: manual",
                        "    install_path: \"\"",
                        "    ownership_mode: manual-import",
                        "  trae:",
                        "    status: disabled",
                        "    install_path: ~/.trae-cn/skills",
                        "    ownership_mode: managed-directories",
                        "",
                    ]
                ),
            )
            sync_status.ROOT = fake_core
            text = runtime_status()
            assert "manifest_source: template-read-only" in text, text
            assert "trae: status=disabled path=~/.trae-cn/skills exists=" in text, text
            assert not (fake_core / "runtime" / "local" / "runtime_manifest.yaml").exists()
        finally:
            sync_status.ROOT = original_root
        if before is None:
            assert not local_manifest.exists()
        else:
            assert local_manifest.read_bytes() == before

        chatgpt_generated = base / "chatgpt-generated"
        chatgpt_dest = base / "chatgpt-runtime"
        write(chatgpt_generated / "chatgpt" / "custom-instructions.md", "# Manual instructions\n")
        write(chatgpt_generated / "chatgpt" / "knowledge" / "commands.md", "# Commands\n")
        dry_run = run(
            [
                str(ROOT / "scripts" / "sync_adapters.py"),
                "--target",
                "chatgpt",
                "--adapter-root",
                str(chatgpt_generated),
                "--dest",
                str(chatgpt_dest),
                "--dry-run",
            ]
        )
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        assert "ChatGPT has no managed local runtime" in dry_run.stdout
        assert "manual target destination ignored" in dry_run.stdout
        assert not chatgpt_dest.exists()

        apply = run(
            [
                str(ROOT / "scripts" / "sync_adapters.py"),
                "--target",
                "chatgpt",
                "--adapter-root",
                str(chatgpt_generated),
                "--dest",
                str(chatgpt_dest),
                "--apply",
            ]
        )
        assert apply.returncode != 0
        assert "Refusing managed ChatGPT runtime write" in apply.stdout + apply.stderr
        assert not chatgpt_dest.exists()

    print("Sync status report tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
