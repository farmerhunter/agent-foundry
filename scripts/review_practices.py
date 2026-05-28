#!/usr/bin/env python3
"""Generate an Agent Foundry practice anti-rot review report."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}
ALWAYS_PREFLIGHT_SOFT_LIMIT = 8
MISSED_ACTIVATION_PROMOTE_THRESHOLD = 3


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter_text(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    if end == -1:
        return ""
    return text[4:end]


def extract_scalar(fm: str, key: str) -> str:
    for line in fm.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def extract_list(fm: str, key: str) -> list[str]:
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            rest = line.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                return [v.strip().strip('"').strip("'") for v in rest[1:-1].split(",") if v.strip()]
            if rest:
                return [rest.strip().strip('"').strip("'")]
            values: list[str] = []
            for follow in lines[i + 1 :]:
                stripped = follow.strip()
                if stripped.startswith("- "):
                    values.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not follow.startswith(" "):
                    break
            return values
    return []


def load_practices() -> list[dict[str, object]]:
    practices: list[dict[str, object]] = []
    for path in sorted((ROOT / "practices").glob("*/*.md")):
        text = read(path)
        fm = frontmatter_text(text)
        tier = ""
        match = re.search(r"- Tier:\s*([^\n]+)", text)
        if match:
            tier = match.group(1).strip()
        practices.append(
            {
                "id": extract_scalar(fm, "id"),
                "title": extract_scalar(fm, "title"),
                "domain": extract_scalar(fm, "domain"),
                "type": extract_scalar(fm, "type"),
                "status": extract_scalar(fm, "status"),
                "created": extract_scalar(fm, "created"),
                "updated": extract_scalar(fm, "updated"),
                "aliases": extract_list(fm, "aliases"),
                "related": extract_list(fm, "related"),
                "tier": tier,
                "path": str(path.relative_to(ROOT)),
            }
        )
    return practices


def load_missed_evidence() -> dict[str, int]:
    path = ROOT / "usage" / "local" / "usage-log.yaml"
    missed: dict[str, int] = {}
    if not path.exists():
        return missed
    current_type = ""
    current_id = ""
    evidence_type = ""
    for line in read(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("- subject_type:"):
            if current_type == "practice" and evidence_type == "missed" and current_id:
                missed[current_id] = missed.get(current_id, 0) + 1
            current_type = stripped.split(":", 1)[1].strip()
            current_id = ""
            evidence_type = ""
        elif stripped.startswith("subject_id:"):
            current_id = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("evidence_type:"):
            evidence_type = stripped.split(":", 1)[1].strip()
    if current_type == "practice" and evidence_type == "missed" and current_id:
        missed[current_id] = missed.get(current_id, 0) + 1
    return missed


def load_asset_coverage() -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        asset_id = ""
        for line in text.splitlines():
            if line.startswith("id:"):
                asset_id = line.split(":", 1)[1].strip()
                break
        if not asset_id:
            continue
        for practice_id in extract_list(text, "canonical_practices"):
            coverage.setdefault(practice_id, []).append(asset_id)
    return coverage


def load_asset_ids() -> set[str]:
    asset_ids: set[str] = set()
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        for line in read(path).splitlines():
            if line.startswith("id:"):
                asset_ids.add(line.split(":", 1)[1].strip())
                break
    return asset_ids


def infer_adapter_asset_candidates(asset_ids: set[str]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    practice_pattern = re.compile(r"\b[A-Z]+-\d{3}\b")
    for path in sorted((ROOT / "adapters").rglob("SKILL.md")):
        text = read(path)
        asset_match = re.search(r"Asset ID:\s*(ASSET-[A-Z]+-\d{3})", text)
        if not asset_match:
            continue
        asset_id = asset_match.group(1)
        if asset_id in asset_ids:
            continue
        practice_ids = sorted({
            pid for pid in practice_pattern.findall(text)
            if not pid.startswith("ASSET-")
        })
        if len(practice_ids) < 2:
            continue
        title = path.parent.name.replace("-", " ").title()
        candidates.append(
            {
                "asset_id": asset_id,
                "title": title,
                "adapter_path": str(path.relative_to(ROOT)),
                "practice_ids": practice_ids,
            }
        )
    return candidates


def build_recommendations(
    practices: list[dict[str, object]],
    missed: dict[str, int],
    coverage: dict[str, list[str]],
    proposals: list[dict[str, object]],
    alias_issues: list[dict[str, object]],
    always_preflight: list[dict[str, object]],
    adapter_asset_candidates: list[dict[str, object]],
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    by_id = {str(p["id"]): p for p in practices}

    for practice in proposals:
        recommendations.append(
            {
                "subject": str(practice["id"]),
                "action": "needs_human_review",
                "reason": "candidate or proposed practice is older than the review threshold",
                "proposed_change": "approve, revise, defer, or archive the candidate",
                "requires_approval": "yes",
            }
        )

    for practice in alias_issues:
        recommendations.append(
            {
                "subject": str(practice["id"]),
                "action": "revise_metadata",
                "reason": "aliases do not start with the stable practice ID",
                "proposed_change": "move the stable ID to the first alias position",
                "requires_approval": "no for mechanical metadata repair; yes if meaning changes",
            }
        )

    for pid, count in sorted(missed.items()):
        practice = by_id.get(pid, {})
        tier = str(practice.get("tier", ""))
        if count >= MISSED_ACTIVATION_PROMOTE_THRESHOLD and tier != "always_preflight":
            action = "consider_promote_activation"
            proposed = "consider stronger activation signals or promotion after human review"
        else:
            action = "revise_activation"
            proposed = "strengthen Activation signals, adapter trigger text, or workflow coverage"
        recommendations.append(
            {
                "subject": pid,
                "action": action,
                "reason": f"missed activation evidence count is {count}",
                "proposed_change": proposed,
                "requires_approval": "yes",
            }
        )

    if len(always_preflight) > ALWAYS_PREFLIGHT_SOFT_LIMIT:
        recommendations.append(
            {
                "subject": "always_preflight",
                "action": "review_preflight_budget",
                "reason": f"always_preflight count is {len(always_preflight)}, above soft limit {ALWAYS_PREFLIGHT_SOFT_LIMIT}",
                "proposed_change": "demote noisy or narrow entries to task_router or workflow_embedded",
                "requires_approval": "yes",
            }
        )

    covered_by_missing_adapter_asset: set[str] = set()
    for candidate in adapter_asset_candidates:
        practice_ids = [str(pid) for pid in candidate["practice_ids"]]
        covered_by_missing_adapter_asset.update(practice_ids)
        recommendations.append(
            {
                "subject": str(candidate["asset_id"]),
                "action": "create_asset_record",
                "reason": (
                    f"adapter skill {candidate['adapter_path']} references "
                    f"{', '.join(practice_ids)} but has no canonical asset record"
                ),
                "proposed_change": "create or approve an asset record covering the referenced practices",
                "requires_approval": "yes",
            }
        )

    for practice in practices:
        pid = str(practice["id"])
        if practice["status"] not in ACTIVE_STATUSES or practice["tier"] or coverage.get(pid):
            continue
        if pid in covered_by_missing_adapter_asset:
            continue
        recommendations.append(
            {
                "subject": pid,
                "action": "needs_human_review",
                "reason": "active practice has no Activation section and is not covered by an asset record",
                "proposed_change": "add asset coverage, add Activation, or mark as reference-only by intent",
                "requires_approval": "yes",
            }
        )
    return recommendations


def parse_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Agent Foundry practices for rot and activation gaps.")
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.today)

    practices = load_practices()
    missed = load_missed_evidence()
    coverage = load_asset_coverage()
    asset_ids = load_asset_ids()
    adapter_asset_candidates = infer_adapter_asset_candidates(asset_ids)

    print("# Practice Review")
    print(f"date: {today}")
    print(f"practices: {len(practices)}")
    print()

    proposals = [
        p for p in practices
        if p["status"] in {"candidate", "proposed"}
        and (parse_date(str(p["created"])) or today) <= today - dt.timedelta(days=30)
    ]
    alias_issues = [p for p in practices if not p["aliases"] or p["aliases"][0] != p["id"]]
    no_activation = [p for p in practices if p["status"] in ACTIVE_STATUSES and not p["tier"]]
    always_preflight = [p for p in practices if p["tier"] == "always_preflight"]
    uncovered_no_activation = [p for p in no_activation if not coverage.get(str(p["id"]))]
    recommendations = build_recommendations(
        practices,
        missed,
        coverage,
        proposals,
        alias_issues,
        always_preflight,
        adapter_asset_candidates,
    )

    print("## Summary")
    print(f"- stale_candidate_or_proposed: {len(proposals)}")
    print(f"- alias_id_first_issues: {len(alias_issues)}")
    print(f"- active_without_activation_section: {len(no_activation)}")
    print(f"- active_without_activation_or_asset_coverage: {len(uncovered_no_activation)}")
    print(f"- always_preflight_count: {len(always_preflight)}")
    print(f"- missed_activation_subjects: {len(missed)}")
    print(f"- missing_adapter_asset_records: {len(adapter_asset_candidates)}")
    print(f"- recommendations: {len(recommendations)}")

    if missed:
        print()
        print("## Missed Activation Evidence")
        for pid, count in sorted(missed.items()):
            print(f"- {pid}: {count}")

    if proposals:
        print()
        print("## Stale Candidate Or Proposed")
        for practice in proposals:
            print(f"- {practice['id']} {practice['title']} ({practice['path']})")

    if alias_issues:
        print()
        print("## Alias ID-First Issues")
        for practice in alias_issues:
            print(f"- {practice['id']} {practice['path']}")

    if uncovered_no_activation:
        print()
        print("## Active Without Activation Or Asset Coverage")
        for practice in uncovered_no_activation:
            print(f"- {practice['id']} {practice['title']} ({practice['path']})")

    if adapter_asset_candidates:
        print()
        print("## Missing Adapter Asset Records")
        for candidate in adapter_asset_candidates:
            print(f"- {candidate['asset_id']} {candidate['title']} ({candidate['adapter_path']})")
            print(f"  practices: {', '.join(candidate['practice_ids'])}")

    if recommendations:
        print()
        print("## Recommendations")
        for i, item in enumerate(recommendations, 1):
            print(f"{i}. {item['subject']}")
            print(f"   action: {item['action']}")
            print(f"   reason: {item['reason']}")
            print(f"   proposed_change: {item['proposed_change']}")
            print(f"   requires_approval: {item['requires_approval']}")

    print()
    print("## Review Notes")
    print("- Treat recommendations as review input; do not mutate lifecycle or activation tiers without approval.")
    print("- After approval, apply selected canonical changes, publish adapters, run checks, and install supported runtimes.")
    print("- Active practices without Activation sections may be acceptable when covered by a task asset or kept as reference.")
    print("- Missed activation evidence suggests investigation, not automatic promotion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
