#!/usr/bin/env python3
"""Regression fixtures for runtime import staging."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
IMPORT = ROOT / "scripts" / "import_runtime_assets.py"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def digest_tree(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    digests: dict[str, str] = {}
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = str(file_path.relative_to(path))
        digests[rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return digests


def expect_contains(name: str, result: subprocess.CompletedProcess[str], expected: str) -> list[str]:
    output = result.stdout + result.stderr
    if result.returncode == 0 and expected in output:
        print(f"{name}: ok")
        return []
    return [f"{name}: expected pass containing {expected!r}, got {result.returncode}\n{output}"]


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"], ROOT)


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-runtime-import-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        runtime = base / "runtime" / "codex" / "skills" / "sample-skill"
        generated = base / "generated-adapters"
        runtime.mkdir(parents=True)
        generated.mkdir(parents=True)
        (runtime / ".agent-foundry-managed").write_text("managed fixture\n", encoding="utf-8")
        (generated / "adapter-publish-manifest.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        skill = runtime / "SKILL.md"
        helper = runtime / "helper.py"
        write(
            skill,
            "\n".join(
                [
                    "---",
                    "name: sample-skill",
                    "---",
                    "",
                    "# Sample Skill",
                    "",
                    "Use this as review evidence only.",
                    "",
                ]
            ),
        )
        write(helper, "#!/usr/bin/env python3\nprint('not executed by import staging')\n")

        init = init_blank(vault)
        errors.extend(expect_contains("init-temp-vault", init, "Blank Vault initialized and validated."))

        source_before = digest_tree(runtime)
        vault_canonical_before = digest_tree(vault / "practices") | digest_tree(vault / "assets")
        adapter_before = digest_tree(generated)

        dry_run = run(
            [
                str(IMPORT),
                "--source",
                str(runtime),
                "--source-runtime",
                "codex",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--quiet-context",
            ],
            ROOT,
        )
        errors.extend(expect_contains("dry-run", dry_run, "Dry-run only. Re-run with --apply to stage records."))
        if list((vault / "imports" / "inbox").glob("runtime-import-*.md")):
            errors.append("dry-run: unexpectedly wrote import records")

        apply = run(
            [
                str(IMPORT),
                "--source",
                str(runtime),
                "--source-runtime",
                "codex",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--apply",
                "--quiet-context",
            ],
            ROOT,
        )
        errors.extend(expect_contains("apply", apply, "write staging root:"))
        staged = sorted((vault / "imports" / "inbox").glob("runtime-import-*.md"))
        if len(staged) != 2:
            errors.append(f"apply: expected 2 staged records, got {len(staged)}")
        combined = "\n".join(path.read_text(encoding="utf-8") for path in staged)
        for expected in [
            "record_type: runtime_import_evidence",
            "source_runtime: codex",
            "source_context: runtime_install_state",
            "license_status: \"unknown-review-required\"",
            "sensitivity: \"unknown-review-required\"",
            "review_required: true",
            "activation_performed: false",
            "runtime_write_performed: false",
            "routing_recommendation: practice_candidate",
            "routing_recommendation: asset_candidate",
            "Script or executable surface present: `yes`",
        ]:
            if expected not in combined:
                errors.append(f"apply: staged record missing {expected!r}")
        if "print('not executed by import staging')" not in combined:
            errors.append("apply: helper source snapshot missing from staged evidence")
        if digest_tree(runtime) != source_before:
            errors.append("apply: runtime source tree changed")
        if digest_tree(vault / "practices") | digest_tree(vault / "assets") != vault_canonical_before:
            errors.append("apply: canonical Vault practices/assets changed")
        if digest_tree(generated) != adapter_before:
            errors.append("apply: generated adapter output changed")

        core_source = run(
            [
                str(IMPORT),
                "--source",
                str(ROOT / "workflows" / "import-external-skills.md"),
                "--source-runtime",
                "codex",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--quiet-context",
            ],
            ROOT,
        )
        errors.extend(expect_contains("core-source-dry-run", core_source, "source context foundry_core_maintenance"))
        core_apply = run(
            [
                str(IMPORT),
                "--source",
                str(ROOT / "workflows" / "import-external-skills.md"),
                "--source-runtime",
                "codex",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--apply",
                "--quiet-context",
            ],
            ROOT,
        )
        errors.extend(expect_contains("core-source-apply", core_apply, "status: rejected"))

        missing = run(
            [
                str(IMPORT),
                "--source",
                str(base / "missing.md"),
                "--source-runtime",
                "codex",
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--quiet-context",
            ],
            ROOT,
        )
        errors.extend(expect_contains("missing-source", missing, "source file does not exist or is not a file"))

    if errors:
        print("Runtime import fixture failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Runtime import fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
