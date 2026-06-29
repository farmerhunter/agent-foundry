#!/usr/bin/env python3
"""AF9 advanced capability workflow surface regression checks."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from deploy_capability_pack import parse_simple_yaml, top_level_scalars


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
PLAN = ROOT / "scripts" / "plan_capability_pack.py"
LIFECYCLE = ROOT / "scripts" / "manage_capability_pack_lifecycle.py"
TRANSFER = ROOT / "scripts" / "plan_capability_pack_transfer.py"
BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
CATALOG_INDEX = ROOT / "catalog" / "capability-packs" / "index.yaml"
CATALOG_SCHEMA = ROOT / "schemas" / "capability-pack-catalog.schema.yaml"
CATALOG_STATUSES = {"available", "deprecated", "retired", "blocked"}
CANONICAL_LIFECYCLE_STATUSES = {
    "candidate",
    "reviewed",
    "proposed",
    "active",
    "exportable",
    "deprecated",
    "retired",
    "archived",
    "blocked",
}
REQUIRED_CATALOG_ENTRY_FIELDS = {
    "pack_id",
    "title",
    "channel",
    "catalog_status",
    "latest_version",
    "manifest_path",
    "manifest_sha256",
    "compatibility_summary",
    "compatibility_metadata",
    "changelog_path",
    "readme_path",
    "review_evidence",
    "authority_after_deployment",
    "private_local_evidence",
    "core_release_axis",
    "candidate_review_packet",
    "release_artifact_published",
}
REQUIRED_COMPATIBILITY_METADATA_FIELDS = {
    "core_schema_version_min",
    "core_schema_version_max",
    "vault_layout_versions",
    "requires_bootstrap_pack",
}


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


def scalar(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(scalar(item) for item in value) + "]"
    return ""


def validate_official_catalog() -> list[str]:
    errors: list[str] = []
    if not CATALOG_INDEX.exists():
        return [f"{CATALOG_INDEX.relative_to(ROOT)} missing"]
    if not CATALOG_SCHEMA.exists():
        errors.append(f"{CATALOG_SCHEMA.relative_to(ROOT)} missing")

    try:
        catalog = parse_simple_yaml(CATALOG_INDEX.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{CATALOG_INDEX.relative_to(ROOT)} parse error: {exc}"]

    if scalar(catalog.get("catalog_schema_version")) != "1":
        errors.append("official catalog schema version must be 1")
    if catalog.get("catalog_id") != "core.official-capability-packs":
        errors.append("official catalog_id must be core.official-capability-packs")
    if catalog.get("source") != "core_repo":
        errors.append("official catalog source must be core_repo")

    entries = catalog.get("entries", [])
    if not isinstance(entries, list) or not entries:
        errors.append("official catalog entries must be a non-empty list")
        return errors

    seen_versions: dict[tuple[str, str], str] = {}
    entries_by_id: dict[str, dict[object, object]] = {}
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append("official catalog entry must be a mapping")
            continue
        entry = raw_entry
        pack_id = scalar(entry.get("pack_id", "<unknown>"))
        entries_by_id[pack_id] = entry
        missing = sorted(REQUIRED_CATALOG_ENTRY_FIELDS - set(entry.keys()))
        for field in missing:
            errors.append(f"official catalog {pack_id} missing {field}")

        if entry.get("channel") != "official":
            errors.append(f"official catalog {pack_id} channel must be official")
        if entry.get("catalog_status") not in CATALOG_STATUSES:
            errors.append(f"official catalog {pack_id} invalid catalog_status {entry.get('catalog_status')}")
        if "lifecycle_status" in entry:
            errors.append(f"official catalog {pack_id} must use catalog_status, not lifecycle_status")
        if entry.get("core_release_axis") != "independent":
            errors.append(f"official catalog {pack_id} must keep pack version and Core release/tag independent")
        if scalar(entry.get("candidate_review_packet")) != "false":
            errors.append(f"official catalog {pack_id} must not be a candidate review packet")
        if scalar(entry.get("release_artifact_published")) != "false":
            errors.append(f"official catalog {pack_id} must not publish release artifacts in AF12")
        if scalar(entry.get("authority_after_deployment")) != "selected_user_vault":
            errors.append(f"official catalog {pack_id} must name selected User Vault authority after deployment")
        if scalar(entry.get("private_local_evidence")) != "excluded":
            errors.append(f"official catalog {pack_id} must exclude private/local evidence")

        compatibility = entry.get("compatibility_metadata", {})
        if not isinstance(compatibility, dict):
            errors.append(f"official catalog {pack_id} compatibility_metadata must be a mapping")
        else:
            for field in sorted(REQUIRED_COMPATIBILITY_METADATA_FIELDS - set(compatibility.keys())):
                errors.append(f"official catalog {pack_id} compatibility_metadata missing {field}")

        manifest_rel = scalar(entry.get("manifest_path"))
        manifest_path = ROOT / manifest_rel
        if not manifest_rel or not manifest_path.exists():
            errors.append(f"official catalog {pack_id} manifest_path missing: {manifest_rel}")
            continue
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if entry.get("manifest_sha256") != manifest_hash:
            errors.append(f"official catalog {pack_id} manifest_sha256 mismatch")

        manifest = top_level_scalars(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("pack_id") != pack_id:
            errors.append(f"official catalog {pack_id} manifest pack_id mismatch")
        if manifest.get("version") != scalar(entry.get("latest_version")):
            errors.append(f"official catalog {pack_id} latest_version must match manifest version")
        if manifest.get("lifecycle_status") not in CANONICAL_LIFECYCLE_STATUSES:
            errors.append(f"official catalog {pack_id} manifest lifecycle_status must use canonical lifecycle namespace")
        if manifest.get("lifecycle_status") == scalar(entry.get("catalog_status")):
            errors.append(f"official catalog {pack_id} catalog_status must be separate from manifest lifecycle_status")

        version_key = (pack_id, scalar(entry.get("latest_version")))
        prior_hash = seen_versions.get(version_key)
        if prior_hash and prior_hash != scalar(entry.get("manifest_sha256")):
            errors.append(f"official catalog {pack_id} same version has conflicting manifest_sha256")
        seen_versions[version_key] = scalar(entry.get("manifest_sha256"))

        for path_field in ["changelog_path", "readme_path"]:
            rel_path = scalar(entry.get(path_field))
            if not rel_path or not (ROOT / rel_path).exists():
                errors.append(f"official catalog {pack_id} missing {path_field}: {rel_path}")

    catalog_text = CATALOG_INDEX.read_text(encoding="utf-8")
    if "candidate_schema_version" in catalog_text:
        errors.append("official catalog must not contain candidate review packet fields")
    for forbidden in ["/Users/", "gho_", "runtime/local/", "usage/local/"]:
        if forbidden in catalog_text:
            errors.append(f"official catalog contains private/local marker {forbidden}")

    required_starter_packs = {
        "pack.bootstrap.minimal",
        "pack.multi-agent.optional",
    }
    for pack_id in sorted(required_starter_packs - set(entries_by_id)):
        errors.append(f"official starter catalog missing {pack_id}")
    if "pack.architecture-boundary-review.starter" in entries_by_id:
        errors.append("architecture boundary guidance must be folded into bootstrap, not cataloged standalone")

    bootstrap_manifest = (ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal" / "manifest.yaml").read_text(
        encoding="utf-8"
    )
    bootstrap_readme = (ROOT / "catalog" / "capability-packs" / "pack.bootstrap.minimal" / "README.md").read_text(
        encoding="utf-8"
    )
    for snippet in [
        "ASSET-META-001",
        "runtime and generated status",
        "standalone capability pack",
        "architecture boundary",
        "Generated and Runtime downstream-status orientation",
        "Local Private evidence exclusion",
    ]:
        if snippet not in bootstrap_manifest + bootstrap_readme:
            errors.append(f"bootstrap starter catalog must preserve {snippet!r}")

    multi_manifest_path = ROOT / "fixtures" / "capability-packs" / "optional-multi-agent" / "manifest.yaml"
    multi_manifest = multi_manifest_path.read_text(encoding="utf-8")
    multi_top = top_level_scalars(multi_manifest)
    if multi_top.get("lifecycle_status") != "reviewed":
        errors.append("GitHub collaboration starter manifest must be reviewed")
    for snippet in [
        "pack.multi-agent.optional",
        "manual_review",
        "selected User Vault records",
        "Project v2 as the scheduler source of truth",
        "project issue numbers, branch names, Project ids, and local cache files",
    ]:
        if snippet not in multi_manifest:
            errors.append(f"GitHub collaboration starter missing compatibility anchor {snippet!r}")

    architecture_pack_paths = [
        ROOT / "catalog" / "capability-packs" / "pack.architecture-boundary-review.starter",
        ROOT / "fixtures" / "capability-packs" / "architecture-boundary-review",
    ]
    for path in architecture_pack_paths:
        if path.exists() and any(child.is_file() for child in path.rglob("*")):
            errors.append(f"architecture boundary starter must not exist as standalone current-stage pack: {path.relative_to(ROOT)}")

    for path in [ROOT / "README.md", ROOT / "docs" / "usage.md", CATALOG_INDEX]:
        text = path.read_text(encoding="utf-8")
        if "pack.architecture-boundary-review.starter" in text:
            errors.append(f"{path.relative_to(ROOT)} must not advertise architecture boundary as a standalone pack")

    usage_text = (ROOT / "docs" / "usage.md").read_text(encoding="utf-8")
    for snippet in [
        "First-Party Pack Selection Principles",
        "independent user value beyond bootstrap",
        "cohesive reusable goal",
        "thin checklist",
        "selected User Vault remains canonical",
        "Generated, Runtime, and Local Private artifacts cannot be pack authority",
        "Provider, frontend, private-project",
    ]:
        if snippet not in usage_text:
            errors.append(f"docs/usage.md missing first-party selection principle {snippet!r}")

    print("official capability catalog surface: ok")
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
    errors.extend(validate_official_catalog())
    errors.extend(
        require_text(
            CATALOG_SCHEMA,
            [
                "catalog_status",
                "available | deprecated | retired | blocked",
                "selected User Vault",
                "Pack version and Core release/tag are independent axes",
                "Same pack_id plus same latest_version plus different manifest_sha256 must fail closed",
                "Candidate review packets are not official catalog entries",
                "Current AF-12 catalog work does not publish release artifacts",
            ],
        )
    )
    errors.extend(
        require_text(
            ROOT / "workflows" / "discover-capability-packs.md",
            [
                "Skill-First Entry Points",
                "discover capability packs",
                "scan capability pack candidate boundaries",
                "assemble capability pack draft",
                "power-user maintenance-level requests",
                "review packets only",
                "diagnostic review-list workflow by default",
                "Do not run candidate discovery automatically",
                "Group every possible candidate by one reusable normal-user goal",
                "Return a concise diagnostic review list by default",
                "do not write candidate records",
                "later reviewed power-user step",
                "Advanced Workflow Surface",
                "Advanced capability discovery is optional",
                "scripts/manage_capability_pack_lifecycle.py",
                "scripts/plan_capability_pack_transfer.py",
                "writes: none",
                "separate from the official Core catalog",
                "cannot become an official catalog entry",
            ],
        )
    )
    errors.extend(
        require_text(
            ROOT / "workflows" / "manage-capability-pack-lifecycle.md",
            [
                "Skill-First Entry Points",
                "Normal-User Consumption Contract",
                "Power-User Maintenance Contract",
                "list capability packs",
                "recommend capability packs for my setup",
                "verify capability pack",
                "update capability pack",
                "disable capability pack",
                "scan, propose, or evaluate candidate boundaries",
                "review a pack release or version update",
                "review exportability",
                "review packets by default",
                "official Core catalog",
                "catalog_status",
                "selected Vault remains canonical",
                "same `pack_id` plus same pack version with",
                "pack version and Core release/tag remain independent axes",
                "pack identity",
                "adopter display status",
                "exact selected Vault write target",
                "review capability pack lifecycle",
                "activate",
                "exportable",
                "writes: none",
                "#176",
            ],
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
        "scan capability pack candidate boundaries",
        "assemble capability pack draft",
        "review capability pack release",
        "review capability pack exportability",
        "review capability pack deprecation",
        "review capability pack split or merge",
        "list capability packs",
        "recommend capability packs for my setup",
        "preview capability pack deployment",
        "apply reviewed capability pack",
        "verify capability pack",
        "update capability pack",
        "disable capability pack",
        "review capability pack lifecycle",
        "preview capability pack transfer",
    ]
    for path in [
        ROOT / "docs" / "commands.md",
        ROOT / "docs" / "usage.md",
    ]:
        errors.extend(require_text(path, skill_first_snippets))
    adapter_skill_first_snippets = [
        "discover capability packs",
        "preview capability pack deployment",
        "apply reviewed capability pack",
        "review capability pack lifecycle",
        "preview capability pack transfer",
    ]
    for path in [
        ROOT / "adapters" / "codex" / "skills" / "practice-harvester" / "SKILL.md",
        ROOT / "adapters" / "hermes" / "skills" / "practice-harvester" / "SKILL.md",
        ROOT / "adapters" / "trae" / "skills" / "agent-foundry" / "SKILL.md",
        ROOT / "adapters" / "claude-code" / "CLAUDE.md",
        ROOT / "adapters" / "chatgpt" / "custom-instructions.md",
        ROOT / "adapters" / "chatgpt" / "knowledge" / "commands.md",
    ]:
        errors.extend(require_text(path, adapter_skill_first_snippets))
    errors.extend(
        require_text(
            ROOT / "docs" / "usage.md",
            [
                "pack identity",
                "advanced maintenance-level workflows",
                "taxonomy, versioning, distribution,",
                "without a later reviewed step",
                "review packet",
                "diagnostic review-list flow",
                "does not run automatically during normal-user pack consumption",
                "does not create candidate files",
                "display status",
                "inspected layers",
                "changed layers",
                "exact selected Vault write target",
                "next safe action",
                "rollback or defer guidance",
                "Do not write `recommended`, `compatible`, `merge_required`,",
            ],
        )
    )
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
        errors.extend(expect("advanced-basic-pack-flow-still-works", basic_plan, True, "add: 25"))
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
