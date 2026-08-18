#!/usr/bin/env python3
"""Focused fixtures for deterministic adapter publish manifests."""

from __future__ import annotations

import hashlib
import os
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import publish_adapters


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_vault(root: Path, practice_updated: str = "2026-08-11", asset_updated: str = "2026-07-06") -> None:
    write(
        root / ".agent-foundry-vault.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "layout_kind: vault",
                "layout_version: 1",
                "identity: user-vault",
                "supported_modes: [combined, split]",
                "supported_core_layout_versions: [1]",
                "privacy_boundary: private_by_default",
                "",
            ]
        ),
    )
    write(
        root / "indexes" / "practice_index.yaml",
        f"schema_version: 1\nupdated: {practice_updated}\n\ndomains: {{}}\n\npractices: []\n",
    )
    write(
        root / "indexes" / "asset_index.yaml",
        f"schema_version: 1\nupdated: {asset_updated}\n\nasset_types: {{}}\n\nassets: []\n",
    )
    write(root / "usage" / "usage-aggregate.yaml", "schema_version: 1\nupdated: 2026-08-11\n\naggregates: []\n")


def digest_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file())
    }


@contextmanager
def simulated_clock(fake_date: type[date], timezone: str):
    previous_timezone = os.environ.get("TZ")
    os.environ["TZ"] = timezone
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        with patch.object(publish_adapters, "date", fake_date):
            yield
    finally:
        if previous_timezone is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_timezone
        if hasattr(time, "tzset"):
            time.tzset()


class EarlyDate(date):
    @classmethod
    def today(cls) -> date:
        return cls(2001, 1, 1)


class LateDate(date):
    @classmethod
    def today(cls) -> date:
        return cls(2099, 12, 31)


def test_identical_inputs_ignore_wall_clock_and_timezone(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_vault(vault)

    with simulated_clock(EarlyDate, "Pacific/Honolulu"):
        assert publish_adapters.publish(ROOT, vault, first, True) == 0
    with simulated_clock(LateDate, "Pacific/Kiritimati"):
        assert publish_adapters.publish(ROOT, vault, second, True) == 0

    assert digest_tree(first) == digest_tree(second)
    manifest = (first / "adapter-publish-manifest.yaml").read_text(encoding="utf-8")
    assert "updated: 2026-08-11\n" in manifest


def test_later_index_date_changes_only_manifest_date(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_vault(vault)
    assert publish_adapters.publish(ROOT, vault, first, True) == 0

    asset_index = vault / "indexes" / "asset_index.yaml"
    asset_index.write_text(
        asset_index.read_text(encoding="utf-8").replace("updated: 2026-07-06", "updated: 2026-08-12"),
        encoding="utf-8",
    )
    assert publish_adapters.publish(ROOT, vault, second, True) == 0

    first_manifest = (first / "adapter-publish-manifest.yaml").read_text(encoding="utf-8")
    second_manifest = (second / "adapter-publish-manifest.yaml").read_text(encoding="utf-8")
    assert first_manifest.replace("updated: 2026-08-11", "updated: 2026-08-12") == second_manifest
    first_tree = digest_tree(first)
    second_tree = digest_tree(second)
    del first_tree["adapter-publish-manifest.yaml"]
    del second_tree["adapter-publish-manifest.yaml"]
    assert first_tree == second_tree


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "updated: 2026-08-11\nupdated: 2026-08-12\n",
        "updated: 2026-13-40\n",
        "updated: 20260811\n",
    ],
    ids=["missing", "duplicate", "malformed", "noncanonical"],
)
def test_invalid_index_date_fails_before_output_mutation(tmp_path: Path, replacement: str) -> None:
    vault = tmp_path / "vault"
    make_vault(vault)
    index = vault / "indexes" / "practice_index.yaml"
    index.write_text(
        index.read_text(encoding="utf-8").replace("updated: 2026-08-11\n", replacement),
        encoding="utf-8",
    )

    absent = tmp_path / "absent"
    assert publish_adapters.publish(ROOT, vault, absent, True) == 1
    assert not absent.exists()

    existing = tmp_path / "existing"
    write(existing / "sentinel", "unchanged\n")
    before = digest_tree(existing)
    assert publish_adapters.publish(ROOT, vault, existing, True) == 1
    assert digest_tree(existing) == before


def test_unreadable_index_fails_before_output_mutation(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    absent = tmp_path / "absent"
    existing = tmp_path / "existing"
    make_vault(vault)
    write(existing / "sentinel", "unchanged\n")
    before = digest_tree(existing)
    original_read = publish_adapters.read

    def unreadable_practice_index(path: Path) -> str:
        if path == vault / "indexes" / "practice_index.yaml":
            raise OSError("fixture unreadable")
        return original_read(path)

    with patch.object(publish_adapters, "read", unreadable_practice_index):
        assert publish_adapters.publish(ROOT, vault, absent, True) == 1
        assert publish_adapters.publish(ROOT, vault, existing, True) == 1
    assert not absent.exists()
    assert digest_tree(existing) == before
