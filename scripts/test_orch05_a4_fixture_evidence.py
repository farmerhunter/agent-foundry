import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import orch05_a4_fixture_evidence as evidence


class FixtureEvidenceTests(unittest.TestCase):
    def root(self, suffix="run"):
        return Path("/private/tmp") / ("orch05-a4-eh1-test-" + suffix)

    def test_complete_public_fixture_run_is_sanitized_immutable_and_cleaned(self):
        root = self.root("complete")
        receipt = evidence.collect_missing_fixture_evidence(private_root=root)
        self.assertEqual(receipt["terminal_outcome"], "fixture_evidence_complete_for_live_a4_hdc_preparation")
        self.assertTrue(receipt["cleanup_complete"])
        self.assertFalse(root.exists())
        self.assertFalse(receipt["s1_rerun"])
        self.assertEqual(receipt["s2"]["duplicate_calls"], 1)
        self.assertTrue(receipt["s2"]["owner_status_accepted"])
        self.assertEqual(receipt["s3"]["negative_count"], 3)
        self.assertTrue(receipt["s3"]["all_holds"])
        self.assertTrue(receipt["s4"]["backup_created"])
        self.assertTrue(receipt["s4"]["takeover_duplicate_zero_mutation"])
        self.assertTrue(json.dumps(receipt))
        with self.assertRaises(TypeError):
            receipt["network"] = True
        self.assertEqual(set(receipt), {"contract_version", "integration", "run_id", "prior_s1_evidence_ref", "s1_rerun", "fixture_only", "live_data", "network", "transport", "s2", "s3", "s4", "cleanup_complete", "terminal_outcome"})
        rendered = json.dumps(receipt)
        self.assertNotIn(str(root), rendered)
        self.assertNotIn("project_id", rendered)

    def test_existing_symlink_and_escaping_roots_fail_before_owner_calls(self):
        existing = self.root("existing")
        existing.mkdir(exist_ok=False)
        try:
            receipt = evidence.collect_missing_fixture_evidence(private_root=existing)
            self.assertEqual(receipt["terminal_outcome"], "held_privacy_or_cleanup")
            self.assertTrue(existing.exists())
        finally:
            existing.rmdir()
        outside = Path("/private/var/orch05-a4-eh1-test-outside")
        self.assertEqual(evidence.collect_missing_fixture_evidence(private_root=outside)["terminal_outcome"], "held_privacy_or_cleanup")
        link = self.root("link")
        link.symlink_to("/private/tmp")
        try:
            self.assertEqual(evidence.collect_missing_fixture_evidence(private_root=link)["terminal_outcome"], "held_privacy_or_cleanup")
        finally:
            link.unlink()

    def test_fail_fast_and_cleanup_when_s2_holds(self):
        root = self.root("hold")
        with patch.object(evidence, "_s2", side_effect=evidence._FixtureHold("held_s2_duplicate_evidence")) as s2, \
             patch.object(evidence, "_s3") as s3, patch.object(evidence, "_s4") as s4:
            receipt = evidence.collect_missing_fixture_evidence(private_root=root)
        self.assertEqual(receipt["terminal_outcome"], "held_s2_duplicate_evidence")
        self.assertEqual(s2.call_count, 1)
        s3.assert_not_called(); s4.assert_not_called()
        self.assertTrue(receipt["cleanup_complete"])
        self.assertFalse(root.exists())

    def test_unexpected_exception_is_sanitized_and_cleaned(self):
        root = self.root("exception")
        with patch.object(evidence, "_s2", side_effect=RuntimeError("secret path /nope")):
            receipt = evidence.collect_missing_fixture_evidence(private_root=root)
        self.assertEqual(receipt["terminal_outcome"], "held_evidence_incomplete")
        self.assertTrue(receipt["cleanup_complete"])
        self.assertNotIn("secret", json.dumps(receipt))
        self.assertFalse(root.exists())

    def test_cli_accepts_only_private_root_and_emits_one_json_receipt(self):
        root = self.root("cli")
        with patch.object(evidence, "collect_missing_fixture_evidence", return_value={"terminal_outcome": "held_evidence_incomplete"}) as collect, \
             patch("sys.stdout.write") as write:
            self.assertEqual(evidence.main(["--private-root", str(root)]), 0)
        collect.assert_called_once_with(private_root=str(root))
        self.assertTrue(write.called)


if __name__ == "__main__":
    unittest.main()
