"""Static contract evidence for the local collaboration lifecycle front door."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "workflows" / "local-collaboration-lifecycle.md"
GUIDE = ROOT / "docs" / "multi-agent-collaboration.md"


class LocalCollaborationFrontDoorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.guide = GUIDE.read_text(encoding="utf-8")
        cls.combined = cls.workflow + "\n" + cls.guide

    def test_both_intent_aliases_resolve_to_the_same_workflow(self):
        self.assertIn("开启本地多-agent协作", self.workflow)
        self.assertIn("start local collaboration", self.workflow)
        self.assertIn("local-collaboration-lifecycle.md", self.guide)

    def test_supported_owner_lanes_and_read_only_board_are_explicit(self):
        for module in (
            "sqlite_collaboration_workflow.py",
            "local_collaboration_onboarding.py",
            "local_collaboration_handoff_experience.py",
            "local_collaboration_recovery.py",
        ):
            self.assertIn(module, self.workflow)
        self.assertIn("`supported`", self.combined)
        self.assertIn("local read-only", self.combined)
        self.assertIn("does not access GitHub Project", self.combined)

    def test_experimental_and_deferred_lanes_are_honest(self):
        self.assertIn("experimental_same_host_manual_custody", self.combined)
        self.assertIn("manual immutable bundle custody", self.combined)
        self.assertIn("source remains locked", self.combined)
        self.assertIn("recovery and cleanup", self.combined)
        self.assertIn("held_real_second_device_deferred", self.combined)
        self.assertIn("only safe next action", self.workflow)
        self.assertIn("No mutation", self.combined)

    def test_mutations_holds_and_prohibited_claims_remain_bounded(self):
        self.assertIn("explicit Human decision", self.combined)
        self.assertIn("never auto-repair", self.combined)
        self.assertIn("JSONL fallback", self.workflow)
        self.assertIn("target-local", self.combined)
        forbidden = (
            "automatic cross-device sync",
            "device sync",
            "automatic handoff",
            "transport resilience",
            "global convergence",
        )
        for phrase in forbidden:
            self.assertIn(phrase, self.combined)
        self.assertIn("not automatic", self.combined)

    def test_result_shape_and_human_walkthrough_are_discoverable(self):
        for field in (
            "capability_lane", "support_level", "lifecycle_state", "authority_mode",
            "project_binding_status", "attention_reason", "safe_next_action",
            "mutation_required", "human_gate_required", "receipt_refs",
            "unsupported_or_deferred",
        ):
            self.assertIn(field, self.workflow)
        self.assertIn("discoverability", self.workflow)
        self.assertIn("authority clarity", self.workflow)
        self.assertIn("recovery clarity", self.workflow)
        self.assertIn("boundary honesty", self.workflow)


if __name__ == "__main__":
    unittest.main()
