#!/usr/bin/env python3
"""Focused tests for the fixture-only #543-D1 evidence harness."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

import orch04_d1_evidence_harness as harness


ROOT = Path("/private/tmp")
PROJECT = "b21487d3-b1fa-513a-9bb9-927ed5000475"
ALTERNATE_PROJECT = "c3c72601-47ec-4483-8739-f1cd1af0824b"


class D1HarnessTests(unittest.TestCase):
    def root(self, name: str) -> Path:
        return ROOT / ("orch-04-4-test-" + name + "-" + uuid.uuid4().hex)

    def test_success_uses_public_snapshot_fields_and_cleans(self):
        root = self.root("success")
        receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "fixture_evidence_complete")
        self.assertEqual(receipt["cleanup"], "complete")
        self.assertFalse(root.exists())
        self.assertEqual(receipt["stages"]["action"]["appended_count"], 1)
        self.assertEqual(receipt["stages"]["duplicate"]["duplicate_count"], 1)
        self.assertEqual(receipt["stages"]["timestamp_hold"], {
            "outcome": "hold", "appended_count": 0, "duplicate_count": 0,
            "mutation_performed": False, "status": "hold",
            "error": "sqlite_action_timestamp_invalid", "authority_unchanged": True,
        })
        self.assertNotIn("/private/tmp", json.dumps(receipt))
        self.assertNotIn("reason", receipt["stages"]["timestamp_hold"])
        json.dumps(receipt, sort_keys=True, separators=(",", ":"))

    def test_existing_root_rejects_before_onboarding(self):
        root = self.root("existing")
        root.mkdir()
        try:
            with patch.object(harness, "fresh_onboarding") as onboarding:
                receipt = harness.run(root, PROJECT)
            onboarding.assert_not_called()
            self.assertEqual(receipt["outcome"], "held_preflight")
            self.assertEqual(receipt["cleanup"], "not_started")
            self.assertTrue(root.exists())
        finally:
            root.rmdir()

    def test_symlink_rejects_before_onboarding(self):
        root = self.root("symlink")
        target = self.root("target")
        target.mkdir()
        root.symlink_to(target, target_is_directory=True)
        try:
            with patch.object(harness, "fresh_onboarding") as onboarding:
                receipt = harness.run(root, PROJECT)
            onboarding.assert_not_called()
            self.assertEqual(receipt["outcome"], "held_preflight")
        finally:
            root.unlink()
            target.rmdir()

    def test_malformed_snapshot_holds_without_fallback_and_cleans(self):
        root = self.root("bad-snapshot")
        with patch.object(harness, "_snapshot", side_effect=harness._Hold("held_owner_api_contract_mismatch")):
            receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "held_owner_api_contract_mismatch")
        self.assertEqual(receipt["cleanup"], "complete")
        self.assertEqual(receipt["stages"]["onboarding"]["outcome"], "created")

    def test_onboarding_exception_is_entered_typed_hold_and_cleans(self):
        root = self.root("onboarding-exception")
        with patch.object(harness, "fresh_onboarding", side_effect=RuntimeError("raw private failure")):
            receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "held_onboarding")
        self.assertEqual(receipt["stages"]["onboarding"]["outcome"], "held_onboarding")
        self.assertEqual(receipt["cleanup"], "complete")
        self.assertNotIn("raw private failure", json.dumps(receipt))

    def test_malformed_binding_rejects_before_onboarding(self):
        root = self.root("bad-binding")
        with patch.object(harness, "fresh_onboarding") as onboarding:
            receipt = harness.run(root, "not-a-uuid")
        onboarding.assert_not_called()
        self.assertEqual(receipt["outcome"], "held_preflight")
        self.assertEqual(receipt["cleanup"], "not_started")

    def test_any_valid_synthetic_uuid_is_accepted(self):
        root = self.root("alternate-project")
        receipt = harness.run(root, ALTERNATE_PROJECT)
        self.assertEqual(receipt["outcome"], "fixture_evidence_complete")
        self.assertEqual(receipt["cleanup"], "complete")

    def test_entered_owner_failure_is_not_not_run_and_cleans(self):
        root = self.root("action-hold")
        original = harness.local_action_batch
        calls = 0

        def failing(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {"status": "hold", "reason": "integrity", "mutation_performed": False}
            return original(*args, **kwargs)

        with patch.object(harness, "local_action_batch", side_effect=failing):
            receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "held_action_semantics")
        self.assertNotEqual(receipt["stages"]["action"]["outcome"], "not_run")
        self.assertEqual(receipt["cleanup"], "complete")

    def test_unexpected_duplicate_exception_is_privacy_safe_hold(self):
        root = self.root("duplicate-exception")
        original = harness.local_action_batch
        calls = 0

        def failing(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("secret /private/tmp/raw-output")
            return original(*args, **kwargs)

        with patch.object(harness, "local_action_batch", side_effect=failing):
            receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "held_owner_api_contract_mismatch")
        self.assertNotEqual(receipt["stages"]["duplicate"]["outcome"], "not_run")
        self.assertNotIn("secret", json.dumps(receipt))
        self.assertEqual(receipt["cleanup"], "complete")

    def test_receipt_has_no_integration_or_raw_project_binding(self):
        root = self.root("privacy")
        receipt = harness.run(root, PROJECT)
        text = json.dumps(receipt)
        self.assertNotIn(PROJECT, text)
        self.assertNotIn("integration", text)
        self.assertEqual(receipt["source_binding"], "external_execution_preflight_required")

    def test_timestamp_cli_malformed_result_holds_without_mutation(self):
        root = self.root("timestamp-malformed")
        malformed = CompletedProcess(args=["ignored"], returncode=6, stdout='{"status":"hold","error":"wrong","mutation_performed":false}', stderr="")
        with patch.object(harness.subprocess, "run", return_value=malformed):
            receipt = harness.run(root, PROJECT)
        self.assertEqual(receipt["outcome"], "held_timestamp_hold_semantics")
        self.assertEqual(receipt["stages"]["timestamp_hold"]["outcome"], "held_timestamp_hold_semantics")
        self.assertEqual(receipt["cleanup"], "complete")
        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
