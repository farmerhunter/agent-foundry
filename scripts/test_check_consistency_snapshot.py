#!/usr/bin/env python3
"""Static synthetic-only consumer fixtures for consistency pinned catalogs."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_consistency
import practice_catalog_snapshot as catalog


def main() -> int:
    files = {
        "indexes/practice_index.yaml": "schema_version: 1\npractices:\n  - id: SYN-001\n    path: practices/synthetic/SYN-001.md\n  - id: SYN-002\n    path: practices/synthetic/SYN-002.md\n",
        "practices/synthetic/SYN-001.md": "---\nid: SYN-001\n---\nSynthetic one.\n",
        "practices/synthetic/SYN-002.md": "---\nid: SYN-002\n---\nSynthetic two.\n",
    }
    manifest = {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": path, "sha256": hashlib.sha256(text.encode()).hexdigest()} for path, text in files.items()]}
    value = catalog.snapshot("synthetic-consistency", manifest, files)
    store = catalog.PointerStore(value["manifest_sha256"])
    errors = check_consistency.validate_injected_pinned_catalog(store, {value["manifest_sha256"]: value})
    if errors or store.read_calls != 1:
        print(f"pinned-consistency-consumer: FAIL {errors} read_calls={store.read_calls}")
        return 1
    print("pinned-consistency-consumer: ok")
    if check_consistency.validate_injected_pinned_catalog(object(), {value["manifest_sha256"]: value}):
        print("unknown-capability: ok")
    else:
        print("unknown-capability: FAIL")
        return 1
    for label, path, body in [
        ("non-markdown-path", "practices/synthetic/SYN-001.txt", "---\nid: SYN-001\n---\nSynthetic.\n"),
        ("body-only-id", "practices/synthetic/SYN-001.md", "body\nid: SYN-001\n"),
        ("fake-frontmatter-delimiter", "practices/synthetic/SYN-001.md", "---\nid: SYN-001\n---not-a-delimiter\nSynthetic.\n"),
        ("duplicate-frontmatter-id", "practices/synthetic/SYN-001.md", "---\nid: SYN-001\nid: SYN-999\n---\nSynthetic.\n"),
    ]:
        altered_files = dict(files)
        altered_files.pop("practices/synthetic/SYN-001.md")
        altered_files[path] = body
        altered_manifest = {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": item, "sha256": hashlib.sha256(text.encode()).hexdigest()} for item, text in altered_files.items()]}
        altered = catalog.snapshot(label, altered_manifest, altered_files)
        if check_consistency.validate_injected_pinned_catalog(catalog.PointerStore(altered["manifest_sha256"]), {altered["manifest_sha256"]: altered}):
            print(f"{label}: ok")
        else:
            print(f"{label}: FAIL")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
