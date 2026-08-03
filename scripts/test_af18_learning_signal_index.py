#!/usr/bin/env python3
"""Offline regressions for the AF18 static LearningSignal candidate index."""

from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "af18_learning_signal_index.py"
SCHEMA = ROOT / "schemas" / "af18-learning-signal-index.schema.yaml"
SPEC = importlib.util.spec_from_file_location("learning_signal_index", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


def expect(name: str, condition: bool, detail: object) -> list[str]:
    if condition:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def record(identity: str, anchors: list[str] | None = None) -> dict:
    anchors = anchors or ["https://example.test/evidence/a", "https://example.test/evidence/b"]
    return {
        "candidate_key": module.candidate_key(identity, anchors),
        "state": "candidate_hold",
        "source_work_anchor": identity,
        "source_role": "bounded role",
        "lesson_type": "validated_workflow",
        "summary": "compact static evidence intake",
        "applicability": "future bounded offline work",
        "evidence_anchors": anchors,
        "residual_limits": "no formal Harvest or activation",
        "privacy_status": "pass_metadata_only",
        "explicit_exclusions": "no persistent storage",
    }


def held(callable_: object, *args: object) -> bool:
    try:
        callable_(*args)  # type: ignore[operator]
    except module.CandidateError:
        return True
    return False


def main() -> int:
    errors: list[str] = []
    one, two = record("work-2"), record("work-1")
    index = module.LearningSignalIndex([one, two])
    default = index.default_projection()
    errors += expect("default-minimal", set(default) == {"count", "routing_state", "next_cursor"} and default["count"] == 2 and default["routing_state"] == "candidate_hold" and "summary" not in json.dumps(default), default)
    page_cursor = index.default_projection(1)["next_cursor"]
    page_one = index.page(page_cursor, 1)
    page_two = index.page(page_one["next_cursor"], 1)
    expected_refs = [module.opaque_reference(item["candidate_key"]) for item in sorted([one, two], key=lambda item: item["candidate_key"])]
    errors += expect("opaque-stable-pages", page_one["references"] + page_two["references"] == expected_refs and all("work" not in ref and "https" not in ref for ref in expected_refs), (page_one, page_two))
    reversed_anchors = record("work-3", ["https://example.test/evidence/b", "https://example.test/evidence/a"])
    reversed_anchors["candidate_key"] = module.candidate_key("work-3", sorted(reversed_anchors["evidence_anchors"]))
    errors += expect("anchor-order-normalizes", module.validate_candidate(reversed_anchors)["candidate_key"] == reversed_anchors["candidate_key"], reversed_anchors)
    duplicate_anchors = record("work-4", ["https://example.test/evidence/a", "https://example.test/evidence/a"])
    duplicate_anchors["candidate_key"] = module.candidate_key("work-4", duplicate_anchors["evidence_anchors"])
    errors += expect("anchor-duplicate-holds", held(module.validate_candidate, duplicate_anchors), duplicate_anchors)
    mismatch = record("work-5")
    mismatch["candidate_key"] = "af18-ls-v1-" + "0" * 64
    errors += expect("key-mismatch-holds", held(module.validate_candidate, mismatch), mismatch)
    unknown = record("work-6")
    unknown["unexpected"] = "x"
    forbidden = record("work-7")
    forbidden["summary"] = "publish activation intent"
    errors += expect("unknown-and-forbidden-hold", held(module.validate_candidate, unknown) and held(module.validate_candidate, forbidden), (unknown, forbidden))
    selected_vault_source = record("selected-vault/private/path")
    private_vault_source = record("vault/private/path")
    selected_vault_anchor = record("work-8", ["https://example.test/selected-vault/private/path"])
    native_id_anchor = record("work-9", ["https://example.test/evidence/native-id/123"])
    errors += expect("source-and-anchor-private-boundaries-hold", all(held(module.validate_candidate, item) for item in (selected_vault_source, private_vault_source, selected_vault_anchor, native_id_anchor)), (selected_vault_source, private_vault_source, selected_vault_anchor, native_id_anchor))
    double_encoded_markers = ("selected%252Dvault%252Fprivate", "vault%252Fprivate", "content%253Draw", "native%252Did")
    double_encoded_sources = [record(marker) for marker in double_encoded_markers]
    double_encoded_anchors = [record(f"work-double-{number}", [f"https://example.test/evidence/{marker}"]) for number, marker in enumerate(double_encoded_markers)]
    errors += expect("double-encoded-source-and-anchor-hold", all(held(module.validate_candidate, item) for item in double_encoded_sources + double_encoded_anchors), (double_encoded_sources, double_encoded_anchors))
    malformed_encoded_sources = [record("bad%FF"), record("residual%GZ")]
    malformed_encoded_anchors = [record(f"work-malformed-{number}", [f"https://example.test/evidence/{marker}"]) for number, marker in enumerate(("bad%FF", "residual%GZ"))]
    errors += expect("decode-error-and-residual-encoding-hold", all(held(module.validate_candidate, item) for item in malformed_encoded_sources + malformed_encoded_anchors), (malformed_encoded_sources, malformed_encoded_anchors))
    backslash_markers = ("vault\\private", "selected-vault\\private", "vault%5Cprivate", "vault/%5Cprivate")
    backslash_sources = [record(marker) for marker in backslash_markers]
    backslash_anchors = [record(f"work-backslash-{number}", [f"https://example.test/evidence/{marker}"]) for number, marker in enumerate(backslash_markers)]
    backslash_anchors += [record("work-backslash-query", ["https://example.test/evidence/safe?path=vault%5Cprivate"]), record("work-backslash-fragment", ["https://example.test/evidence/safe#vault%5Cprivate"])]
    errors += expect("backslash-source-and-anchor-hold", all(held(module.validate_candidate, item) for item in backslash_sources + backslash_anchors), (backslash_sources, backslash_anchors))
    errors += expect("duplicate-batch-holds", held(module.LearningSignalIndex, [one, copy.deepcopy(one)]), one)
    cursor = default["next_cursor"]
    tampered = cursor[:-1] + ("0" if cursor[-1] != "0" else "1")
    errors += expect("cursor-tamper-holds", index.page(tampered, 1) == {"routing_state": "held_cursor_invalid"}, tampered)
    errors += expect("cursor-missing-holds", index.page(None, 1) == {"routing_state": "held_cursor_invalid"}, None)
    errors += expect("page-bounds-hold", all(index.page(cursor, size) == {"routing_state": "held_cursor_invalid"} for size in (0, -1, 1.5, 26, True, None)), cursor)
    errors += expect("page-size-mismatch-holds", index.page(cursor, 2) == {"routing_state": "held_cursor_invalid"}, cursor)
    restarted = module.LearningSignalIndex([one, two])
    errors += expect("restart-holds", restarted.page(cursor, 25) == {"routing_state": "held_cursor_invalid"}, cursor)
    changed = module.LearningSignalIndex([one])
    errors += expect("batch-change-holds", changed.page(cursor, 25) == {"routing_state": "held_cursor_invalid"}, cursor)
    payload, _ = index._cursors[cursor]
    changed_payload = json.loads(payload)
    changed_payload["cursor_version"] = "wrong"
    version_payload = module.canonical_json(changed_payload)
    version_tag = hmac.new(index._secret, version_payload, hashlib.sha256).hexdigest()
    version_cursor = module.CURSOR_PREFIX + "version." + version_tag
    index._cursors[version_cursor] = (version_payload, version_tag)
    changed_payload["cursor_version"] = module.CURSOR_VERSION
    changed_payload["last_ordered_reference"] = "af18-ls-ref-v1-" + "0" * 64
    order_payload = module.canonical_json(changed_payload)
    order_tag = hmac.new(index._secret, order_payload, hashlib.sha256).hexdigest()
    order_cursor = module.CURSOR_PREFIX + "order." + order_tag
    index._cursors[order_cursor] = (order_payload, order_tag)
    errors += expect("version-and-order-holds", index.page(version_cursor, 25) == {"routing_state": "held_cursor_invalid"} and index.page(order_cursor, 25) == {"routing_state": "held_cursor_invalid"}, (version_cursor, order_cursor))
    schema = SCHEMA.read_text(encoding="utf-8")
    errors += expect("schema-contract", all(value in schema for value in (module.IDENTITY_ALGORITHM, "HMAC-SHA-256", "1..25", "pass_metadata_only", "no detail lookup")), schema)
    with tempfile.TemporaryDirectory() as raw:
        batch_path = Path(raw) / "batch.json"
        batch_path.write_text(json.dumps([one, two]), encoding="utf-8")
        valid = subprocess.run([sys.executable, str(SCRIPT), "--batch-json", str(batch_path)], text=True, capture_output=True)
        invalid_path = Path(raw) / "invalid.json"
        invalid_path.write_text(json.dumps([unknown]), encoding="utf-8")
        invalid = subprocess.run([sys.executable, str(SCRIPT), "--batch-json", str(invalid_path)], text=True, capture_output=True)
        private_paths = []
        private_cases = (("selected-source", selected_vault_source), ("private-source", private_vault_source), ("selected-anchor", selected_vault_anchor), ("native-anchor", native_id_anchor))
        private_cases += tuple((f"double-source-{number}", item) for number, item in enumerate(double_encoded_sources))
        private_cases += tuple((f"double-anchor-{number}", item) for number, item in enumerate(double_encoded_anchors))
        private_cases += tuple((f"malformed-source-{number}", item) for number, item in enumerate(malformed_encoded_sources))
        private_cases += tuple((f"malformed-anchor-{number}", item) for number, item in enumerate(malformed_encoded_anchors))
        private_cases += tuple((f"backslash-source-{number}", item) for number, item in enumerate(backslash_sources))
        private_cases += tuple((f"backslash-anchor-{number}", item) for number, item in enumerate(backslash_anchors))
        for name, item in private_cases:
            path = Path(raw) / f"{name}.json"
            path.write_text(json.dumps([item]), encoding="utf-8")
            private_paths.append(path)
        private_outputs = [subprocess.run([sys.executable, str(SCRIPT), "--batch-json", str(path)], text=True, capture_output=True) for path in private_paths]
        valid_output = json.loads(valid.stdout)
        invalid_output = json.loads(invalid.stdout)
        errors += expect("cli-static-input-only", valid.returncode == 0 and invalid.returncode == 0 and set(valid_output) == {"count", "routing_state", "next_cursor"} and invalid_output == {"routing_state": "held_candidate_invalid"} and all(result.returncode == 0 and json.loads(result.stdout) == {"routing_state": "held_candidate_invalid"} for result in private_outputs) and not any(word in valid.stderr.lower() + invalid.stderr.lower() for word in ("github", "vault", "harvester", "network")), (valid, invalid, private_outputs))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("af18 learning-signal index tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
