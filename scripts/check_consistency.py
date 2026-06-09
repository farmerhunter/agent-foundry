#!/usr/bin/env python3
"""Consistency checks for Agent Foundry.

No third-party dependencies. Intended to be callable by any local agent.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}
INACTIVE_PRACTICE_STATUSES = {"candidate", "proposed", "superseded", "archived"}
INACTIVE_ASSET_STATUSES = {"candidate", "proposed", "deprecated", "retired", "archived"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> dict[str, str]:
    text = read(path)
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def simple_yaml_entries(index_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in index_text.splitlines():
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
            continue
        if current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def scan_yaml_status(path: Path) -> str | None:
    for line in read(path).splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return None


def extract_yaml_list(text: str, key: str, limit_to_frontmatter: bool = False) -> list[str]:
    values: list[str] = []
    lines = text.splitlines()
    end = len(lines)
    if limit_to_frontmatter and text.startswith("---\n"):
        fm_end = text.find("\n---", 4)
        if fm_end != -1:
            end = text[:fm_end].count("\n") + 1
    for i in range(end):
        stripped = lines[i].strip()
        if stripped.startswith(f"{key}:"):
            rest = stripped.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1]
                return [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
            elif rest:
                return [rest.strip().strip('"').strip("'")]
            else:
                j = i + 1
                while j < end:
                    next_stripped = lines[j].strip()
                    if not next_stripped:
                        j += 1
                        continue
                    if next_stripped.startswith("- "):
                        values.append(next_stripped[2:].strip().strip('"').strip("'"))
                    elif not lines[j].startswith(" ") and not lines[j].startswith("\t"):
                        break
                    j += 1
                return values
    return values


def load_adapter_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "adapters").iterdir():
        if path.is_dir():
            names.add(path.name)
    return names


def check_index_paths(index_path: Path, label: str) -> list[str]:
    errors: list[str] = []
    for entry in simple_yaml_entries(read(index_path)):
        rel = entry.get("path")
        if not rel:
            errors.append(f"{label} {entry.get('id')} has no path")
            continue
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{label} {entry.get('id')} path missing: {rel}")
    return errors


def check_practice_frontmatter() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "practices").glob("*/*.md")):
        fm = frontmatter(path)
        if not fm:
            errors.append(f"Practice missing frontmatter: {path.relative_to(ROOT)}")
            continue
        pid = fm.get("id")
        if not pid:
            errors.append(f"Practice missing id: {path.relative_to(ROOT)}")
        elif not path.name.startswith(pid):
            errors.append(f"Practice filename/id mismatch: {path.relative_to(ROOT)} has id {pid}")
        status = fm.get("status")
        if status not in ACTIVE_STATUSES | INACTIVE_PRACTICE_STATUSES:
            errors.append(f"Practice {pid} has invalid status: {status}")
    return errors


def check_asset_files() -> list[str]:
    errors: list[str] = []
    required = [
        "id:",
        "title:",
        "asset_type:",
        "status:",
        "purpose:",
        "responsibility:",
        "non_responsibility:",
        "inputs:",
        "process:",
        "outputs:",
        "canonical_practices:",
        "published_to:",
        "usage_triggers:",
        "success_criteria:",
    ]
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        asset_id = None
        for line in text.splitlines():
            if line.startswith("id:"):
                asset_id = line.split(":", 1)[1].strip()
                break
        if not asset_id:
            errors.append(f"Asset missing id: {path.relative_to(ROOT)}")
        elif not path.name.startswith(asset_id):
            errors.append(f"Asset filename/id mismatch: {path.relative_to(ROOT)} has id {asset_id}")
        status = scan_yaml_status(path)
        if status not in ACTIVE_STATUSES | INACTIVE_ASSET_STATUSES:
            errors.append(f"Asset {asset_id} has invalid status: {status}")
        for key in required:
            if key not in text:
                errors.append(f"Asset {asset_id} missing required field {key.rstrip(':')}")
    return errors


def check_no_inactive_leakage() -> list[str]:
    errors: list[str] = []
    adapter_files = [p for p in (ROOT / "adapters").rglob("*") if p.is_file()]
    bad_statuses = {"proposed", "candidate", "superseded", "archived", "deprecated", "retired"}
    for path in adapter_files:
        for line in read(path).splitlines():
            match = re.match(r"^\s*status:\s*([A-Za-z_-]+)\s*$", line)
            if match and match.group(1) in bad_statuses:
                errors.append(
                    f"Inactive status leaked into adapter {path.relative_to(ROOT)}: status {match.group(1)}"
                )
    return errors


def check_adapter_id_references() -> list[str]:
    errors: list[str] = []
    valid_ids: set[str] = set()
    for entry in simple_yaml_entries(read(ROOT / "indexes" / "practice_index.yaml")):
        pid = entry.get("id")
        if pid:
            valid_ids.add(pid)
    for entry in simple_yaml_entries(read(ROOT / "indexes" / "asset_index.yaml")):
        aid = entry.get("id")
        if aid:
            valid_ids.add(aid)
    valid_prefixes = {vid.split("-")[0] for vid in valid_ids}
    id_pattern = re.compile(r"\b(?:ASSET-[A-Z]{2,}-\d{3,}|[A-Z]{2,}-\d{3,})\b")
    for path in (ROOT / "adapters").rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"adapter_profiles.yaml", ".agent-foundry-managed"}:
            continue
        text = read(path)
        for match in id_pattern.finditer(text):
            candidate = match.group(0)
            prefix = candidate.split("-")[0]
            if prefix not in valid_prefixes:
                continue
            if candidate not in valid_ids:
                errors.append(
                    f"Adapter {path.relative_to(ROOT)} references unknown ID: {candidate}"
                )
    return errors


def check_no_deepseek_direct_adapter() -> list[str]:
    if (ROOT / "adapters" / "deepseek").exists():
        return ["Direct DeepSeek adapter exists; DeepSeek should be an underlying model provider only"]
    return []


def check_usage_aggregate() -> list[str]:
    path = ROOT / "usage" / "usage-aggregate.yaml"
    if not path.exists():
        return ["Missing usage/usage-aggregate.yaml"]
    text = read(path)
    if "aggregates:" not in text:
        return ["usage-aggregate.yaml missing aggregates"]
    for line in text.splitlines():
        if line.strip().startswith("machine_hash:") and "hostname" in line.lower():
            return ["usage-aggregate.yaml appears to contain an unhashed machine name"]
    return []


def check_foundry_roots_script() -> list[str]:
    script = ROOT / "scripts" / "check_foundry_roots.py"
    if not script.exists():
        return ["Missing scripts/check_foundry_roots.py"]
    result = subprocess.run(
        ["python3", str(script), "--core-root", str(ROOT), "--vault-root", str(ROOT)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout + result.stderr).strip()
    if not output:
        return ["Foundry root validation failed without output"]
    return output.splitlines()


def parse_simple_targets(text: str) -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_targets = False
    for line in text.splitlines():
        if line == "targets:":
            in_targets = True
            continue
        if not in_targets:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current = line.strip().removesuffix(":")
            targets[current] = {}
            continue
        if current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            targets[current][key] = value.strip().strip('"')
    return targets


def check_runtime_manifest() -> list[str]:
    errors: list[str] = []
    path = ROOT / "runtime" / "templates" / "runtime_manifest.template.yaml"
    if not path.exists():
        return ["Missing runtime/templates/runtime_manifest.template.yaml"]
    targets = parse_simple_targets(read(path))
    if not targets:
        return ["runtime_manifest.yaml has no targets"]
    adapter_text = read(ROOT / "adapters" / "adapter_profiles.yaml")
    for target, config in targets.items():
        adapter = config.get("adapter")
        status = config.get("status")
        if status not in {"enabled", "disabled", "missing", "manual"}:
            errors.append(f"Runtime target {target} has invalid status: {status}")
        if not adapter:
            errors.append(f"Runtime target {target} has no adapter")
        elif f"  {adapter}:" not in adapter_text:
            errors.append(f"Runtime target {target} references unknown adapter: {adapter}")
        if status == "enabled" and not config.get("install_path"):
            errors.append(f"Enabled runtime target {target} has no install_path")
    return errors


def check_cross_references() -> list[str]:
    errors: list[str] = []
    practice_ids: set[str] = set()
    for entry in simple_yaml_entries(read(ROOT / "indexes" / "practice_index.yaml")):
        pid = entry.get("id")
        if pid:
            practice_ids.add(pid)

    asset_ids: set[str] = set()
    for entry in simple_yaml_entries(read(ROOT / "indexes" / "asset_index.yaml")):
        aid = entry.get("id")
        if aid:
            asset_ids.add(aid)

    adapter_names = load_adapter_names()

    for path in sorted((ROOT / "practices").glob("*/*.md")):
        text = read(path)
        fm = frontmatter(path)
        pid = fm.get("id")
        if not pid:
            continue
        for ref in extract_yaml_list(text, "related", limit_to_frontmatter=True):
            if ref not in practice_ids:
                errors.append(f"Practice {pid} references unknown practice in related: {ref}")
        for ref in extract_yaml_list(text, "supersedes", limit_to_frontmatter=True):
            if ref not in practice_ids:
                errors.append(f"Practice {pid} references unknown practice in supersedes: {ref}")
        for ref in extract_yaml_list(text, "superseded_by", limit_to_frontmatter=True):
            if ref not in practice_ids:
                errors.append(f"Practice {pid} references unknown practice in superseded_by: {ref}")

    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        asset_id = None
        for line in text.splitlines():
            if line.startswith("id:"):
                asset_id = line.split(":", 1)[1].strip()
                break
        if not asset_id:
            continue
        for ref in extract_yaml_list(text, "canonical_practices"):
            if ref not in practice_ids:
                errors.append(f"Asset {asset_id} references unknown practice in canonical_practices: {ref}")
        for adapter in extract_yaml_list(text, "published_to"):
            if adapter not in adapter_names:
                errors.append(f"Asset {asset_id} references unknown adapter in published_to: {adapter}")
        for ref in extract_yaml_list(text, "related_assets"):
            if ref not in asset_ids:
                errors.append(f"Asset {asset_id} references unknown asset in related_assets: {ref}")
        for ref in extract_yaml_list(text, "supersedes"):
            if ref not in asset_ids:
                errors.append(f"Asset {asset_id} references unknown asset in supersedes: {ref}")
        for ref in extract_yaml_list(text, "superseded_by"):
            if ref not in asset_ids:
                errors.append(f"Asset {asset_id} references unknown asset in superseded_by: {ref}")

    return errors


def check_supersede_bidirectional() -> list[str]:
    errors: list[str] = []
    superseded_by_map: dict[str, str] = {}
    supersedes_map: dict[str, list[str]] = {}

    for path in sorted((ROOT / "practices").glob("*/*.md")):
        text = read(path)
        fm = frontmatter(path)
        pid = fm.get("id")
        if not pid:
            continue
        for ref in extract_yaml_list(text, "superseded_by", limit_to_frontmatter=True):
            superseded_by_map[pid] = ref
        supersedes_map[pid] = extract_yaml_list(text, "supersedes", limit_to_frontmatter=True)

    for pid, refs in supersedes_map.items():
        for ref in refs:
            if superseded_by_map.get(ref) != pid:
                errors.append(
                    f"Practice {pid} supersedes {ref}, but {ref} does not list {pid} in superseded_by"
                )

    asset_superseded_by_map: dict[str, str] = {}
    asset_supersedes_map: dict[str, list[str]] = {}
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        asset_id = None
        for line in text.splitlines():
            if line.startswith("id:"):
                asset_id = line.split(":", 1)[1].strip()
                break
        if not asset_id:
            continue
        for ref in extract_yaml_list(text, "superseded_by"):
            asset_superseded_by_map[asset_id] = ref
        asset_supersedes_map[asset_id] = extract_yaml_list(text, "supersedes")

    for aid, refs in asset_supersedes_map.items():
        for ref in refs:
            if asset_superseded_by_map.get(ref) != aid:
                errors.append(
                    f"Asset {aid} supersedes {ref}, but {ref} does not list {aid} in superseded_by"
                )

    return errors


def check_claude_managed_block_integrity() -> list[str]:
    errors: list[str] = []
    user_claude = Path.home() / ".claude" / "CLAUDE.md"
    if not user_claude.exists():
        return errors
    text = read(user_claude)
    start_count = text.count("<!-- AGENT-FOUNDRY-START -->")
    end_count = text.count("<!-- AGENT-FOUNDRY-END -->")
    if start_count == 0 and end_count == 0:
        return errors
    if start_count != 1:
        errors.append(
            f"Claude managed block integrity: expected 1 AGENT-FOUNDRY-START block, found {start_count} in ~/.claude/CLAUDE.md"
        )
    if end_count != 1:
        errors.append(
            f"Claude managed block integrity: expected 1 AGENT-FOUNDRY-END block, found {end_count} in ~/.claude/CLAUDE.md"
        )
    if start_count == 1 and end_count == 1:
        start_idx = text.find("<!-- AGENT-FOUNDRY-START -->")
        end_idx = text.find("<!-- AGENT-FOUNDRY-END -->")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            block = text[start_idx:end_idx + len("<!-- AGENT-FOUNDRY-END -->")]
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("@"):
                    import_path = Path(stripped[1:].strip()).expanduser()
                    if not import_path.exists():
                        errors.append(
                            f"Claude managed block integrity: import target does not exist: {import_path}"
                        )
                    break
            else:
                errors.append(
                    "Claude managed block integrity: managed block does not contain an @import path"
                )
        else:
            errors.append(
                "Claude managed block integrity: AGENT-FOUNDRY-START/END blocks are malformed or out of order"
            )
    return errors


def check_obsidian_compatibility() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "practices").glob("*/*.md")):
        text = read(path)
        fm = frontmatter(path)
        pid = fm.get("id")
        if not pid:
            continue

        # Check that id is the first alias for stable Obsidian wikilinks.
        aliases = extract_yaml_list(text, "aliases", limit_to_frontmatter=True)
        if not aliases:
            errors.append(f"Practice {pid} missing aliases (Obsidian wikilink): {path.relative_to(ROOT)}")
        elif aliases[0] != pid:
            errors.append(
                f"Practice {pid} must have id as first alias (Obsidian wikilink): {path.relative_to(ROOT)}"
            )

        # Check that related IDs have a Related Practices section with wikilinks
        related = extract_yaml_list(text, "related", limit_to_frontmatter=True)
        if related:
            if "## Related Practices" not in text:
                errors.append(
                    f"Practice {pid} has related entries but no '## Related Practices' section: {path.relative_to(ROOT)}"
                )
            else:
                # Extract wikilinks from Related Practices section
                section_match = re.search(
                    r"## Related Practices\n+(.*?)(?=\n## |\Z)", text, re.DOTALL
                )
                if section_match:
                    section_text = section_match.group(1)
                    wikilinks = re.findall(r"\[\[([A-Z]{2,}-\d{3,})\]\]", section_text)
                    missing = [r for r in related if r not in wikilinks]
                    extra = [w for w in wikilinks if w not in related]
                    if missing:
                        errors.append(
                            f"Practice {pid} Related Practices missing wikilinks: {missing} in {path.relative_to(ROOT)}"
                        )
                    if extra:
                        errors.append(
                            f"Practice {pid} Related Practices has extra wikilinks: {extra} in {path.relative_to(ROOT)}"
                        )
                else:
                    errors.append(
                        f"Practice {pid} '## Related Practices' section malformed: {path.relative_to(ROOT)}"
                    )
    return errors


def check_adapter_quality_script() -> list[str]:
    script = ROOT / "scripts" / "check_adapter_quality.py"
    if not script.exists():
        return ["Missing scripts/check_adapter_quality.py"]
    result = subprocess.run(
        ["python3", str(script)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout + result.stderr).strip()
    if not output:
        return ["Adapter quality check failed without output"]
    return output.splitlines()


def check_activation_script() -> list[str]:
    script = ROOT / "scripts" / "check_activation.py"
    if not script.exists():
        return ["Missing scripts/check_activation.py"]
    result = subprocess.run(
        ["python3", str(script)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout + result.stderr).strip()
    if not output:
        return ["Activation check failed without output"]
    return output.splitlines()


def main() -> int:
    errors: list[str] = []
    errors += check_index_paths(ROOT / "indexes" / "practice_index.yaml", "Practice")
    errors += check_index_paths(ROOT / "indexes" / "asset_index.yaml", "Asset")
    errors += check_practice_frontmatter()
    errors += check_asset_files()
    errors += check_no_inactive_leakage()
    errors += check_adapter_id_references()
    errors += check_no_deepseek_direct_adapter()
    errors += check_usage_aggregate()
    errors += check_foundry_roots_script()
    errors += check_runtime_manifest()
    errors += check_claude_managed_block_integrity()
    errors += check_cross_references()
    errors += check_supersede_bidirectional()
    errors += check_obsidian_compatibility()
    errors += check_adapter_quality_script()
    errors += check_activation_script()

    if errors:
        print("Consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
