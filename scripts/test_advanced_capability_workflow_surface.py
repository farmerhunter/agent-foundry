#!/usr/bin/env python3
"""AF9 advanced capability workflow surface regression checks."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
PLAN = ROOT / "scripts" / "plan_capability_pack.py"
LIFECYCLE = ROOT / "scripts" / "manage_capability_pack_lifecycle.py"
TRANSFER = ROOT / "scripts" / "plan_capability_pack_transfer.py"
BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def expect(name: str, result: subprocess.CompletedProcess[str], should_pass: bool, expected_text: str = "") -> list[str]:
    output = result.stdout + result.stderr
    if (result.returncode == 0) == should_pass and (not expected_text or expected_text in output):
        print(f"{name}: ok")
        return []
    return [
        f"{name}: expected {'pass' if should_pass else 'failure'}"
        + (f" containing {expected_text!r}" if expected_text else "")
        + f", got exit {result.returncode}\n{output.strip()}"
    ]


def require_text(path: Path, snippets: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for snippet in snippets:
        if snippet not in text:
            errors.append(f"{path.relative_to(ROOT)} missing {snippet!r}")
        else:
            print(f"{path.relative_to(ROOT)} contains {snippet}: ok")
    return errors


def write_candidate_as_manifest(base: Path) -> Path:
    pack = base / "candidate-as-manifest"
    pack.mkdir(parents=True)
    (pack / "manifest.yaml").write_text(
        "\n".join(
            [
                "candidate_schema_version: 1",
                "candidate_id: candidate.pack.review-only",
                "proposed_pack_id: pack.review-only",
                "title: Review-only candidate",
                "outcome: candidate",
                "confidence: medium",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return pack


def write_deployed_index(vault: Path) -> None:
    packs = vault / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / "deployed-pack-index.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "updated: 2026-06-17",
                "deployed_packs:",
                "  - pack_id: pack.bootstrap.minimal",
                "    version: 0.2.0",
                "    lifecycle_status: active",
                "    source:",
                f"      manifest_sha256: {'0' * 64}",
                "    records:",
                "      - id: BOOT-001",
                "        kind: practice",
                "        path: practices/meta/BOOT-001-bootstrap-orientation.md",
                f"        deployed_sha256: {'1' * 64}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    errors: list[str] = []
    errors.extend(
        require_text(
            ROOT / "workflows" / "discover-capability-packs.md",
            [
                "Skill-First Entry Points",
                "discover capability packs",
                "Advanced Workflow Surface",
                "Advanced capability discovery is optional",
                "scripts/manage_capability_pack_lifecycle.py",
                "scripts/plan_capability_pack_transfer.py",
                "writes: none",
            ],
        )
    )
    errors.extend(
        require_text(
            ROOT / "workflows" / "manage-capability-pack-lifecycle.md",
            ["Skill-First Entry Points", "review capability pack lifecycle", "activate", "exportable", "writes: none", "#176"],
        )
    )
    errors.extend(
        require_text(
            ROOT / "workflows" / "export-import-capability-packs.md",
            ["Skill-First Entry Points", "preview capability pack transfer", "review-first", "Import States", "writes: none", "private Vault"],
        )
    )
    skill_first_snippets = [
        "discover capability packs",
        "preview capability pack deployment",
        "apply reviewed capability pack",
        "review capability pack lifecycle",
        "preview capability pack transfer",
    ]
    for path in [
        ROOT / "docs" / "commands.md",
        ROOT / "docs" / "usage.md",
        ROOT / "adapters" / "codex" / "skills" / "practice-harvester" / "SKILL.md",
        ROOT / "adapters" / "hermes" / "skills" / "practice-harvester" / "SKILL.md",
        ROOT / "adapters" / "trae" / "skills" / "agent-foundry" / "SKILL.md",
        ROOT / "adapters" / "claude-code" / "CLAUDE.md",
        ROOT / "adapters" / "chatgpt" / "custom-instructions.md",
        ROOT / "adapters" / "chatgpt" / "knowledge" / "commands.md",
    ]:
        errors.extend(require_text(path, skill_first_snippets))
    for path in [
        ROOT / "docs" / "usage.md",
        ROOT / "adapters" / "codex" / "skills" / "practice-harvester" / "SKILL.md",
        ROOT / "adapters" / "trae" / "skills" / "agent-foundry" / "SKILL.md",
    ]:
        errors.extend(
            require_text(
                path,
                ["raw scripts", "implementation details", "advanced/debug"],
            )
        )

    with tempfile.TemporaryDirectory(prefix="agent-foundry-advanced-workflow-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        errors.extend(
            expect(
                "advanced-init-blank-vault",
                run([str(INIT), str(vault), "--core-root", str(ROOT), "--apply"]),
                True,
                "Blank Vault initialized and validated.",
            )
        )

        basic_plan = run([str(PLAN), str(BOOTSTRAP_PACK), "--core-root", str(ROOT), "--vault-root", str(vault)])
        errors.extend(expect("advanced-basic-pack-flow-still-works", basic_plan, True, "add: 24"))
        errors.extend(expect("advanced-basic-pack-writes-none", basic_plan, True, "writes: none"))

        candidate_pack = write_candidate_as_manifest(base)
        candidate_plan = run([str(PLAN), str(candidate_pack), "--core-root", str(ROOT), "--vault-root", str(vault)])
        errors.extend(expect("advanced-candidate-not-active-manifest", candidate_plan, False, "review-only"))

        transfer_preview = run(
            [
                str(TRANSFER),
                str(BOOTSTRAP_PACK),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--action",
                "import-preview",
                "--import-state",
                "preview",
            ]
        )
        errors.extend(expect("advanced-transfer-dry-run-first", transfer_preview, False, "writes: none"))
        errors.extend(expect("advanced-transfer-needs-export-policy", transfer_preview, False, "export_policy is required"))

        write_deployed_index(vault)
        lifecycle_exportable = run(
            [
                str(LIFECYCLE),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--pack-id",
                "pack.bootstrap.minimal",
                "--action",
                "exportable",
            ]
        )
        errors.extend(expect("advanced-lifecycle-exportable-review-gated", lifecycle_exportable, False, "review_gate:"))
        errors.extend(expect("advanced-lifecycle-exportable-writes-none", lifecycle_exportable, False, "writes: none"))

    if errors:
        print("Advanced capability workflow surface test failed:")
        for error in errors:
            print(error)
        return 1
    print("Advanced capability workflow surface test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
