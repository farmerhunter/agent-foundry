import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_recovery import apply_recovery_action, plan_recovery_action, read_recovery_summary


def digest(value): return hashlib.sha256(value.encode()).hexdigest()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory(); self.project_id = str(uuid.uuid4())
        self.ledger = LocalCollaborationLedger.create_project(projects_root=self.root.name, project_id=self.project_id)
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        p = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-e", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.ledger, p, expected_before=state)
    def tearDown(self): self.ledger.close(); self.root.cleanup()
    def plan(self, intent, params):
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id, intent=intent)
        return plan_recovery_action(summary, {"operation": intent, "decision_id": "human-1", "decision_digest": digest("human"), "parameters": params})
    def test_summary_is_json_safe_immutable_and_read_only(self):
        before = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(summary["state"], "healthy_active"); json.dumps(summary)
        with self.assertRaises(TypeError): summary["state"] = "held"
        after = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual((before.authority_generation, before.authority_head), (after.authority_generation, after.authority_head))
    def test_backup_once_then_existing_destination_holds(self):
        dest = Path(self.root.name) / "backup.db"; plan = self.plan("create_backup", {"destination": str(dest)})
        result = apply_recovery_action({"ledger": self.ledger, "destination": str(dest)}, plan)
        self.assertTrue(result["receipt"]["mutation_performed"]); self.assertTrue(dest.exists())
        plan2 = self.plan("create_backup", {"destination": str(dest)})
        held = apply_recovery_action({"ledger": self.ledger, "destination": str(dest)}, plan2)
        self.assertEqual(held["outcome"], "held")
    def test_active_revoke_holds_before_mutation(self):
        before = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id, intent="revoke_inactive_replica", selected_replica_id="source")
        self.assertEqual(summary["state"], "held")
        after = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(before.authority_generation, after.authority_generation)
    def test_schema(self):
        schema = yaml.safe_load(Path(__file__).with_name("..").resolve() / "schemas/local-collaboration-recovery.schema.yaml") if False else yaml.safe_load(Path("schemas/local-collaboration-recovery.schema.yaml").read_text())
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(dict(summary))), [])


if __name__ == "__main__": unittest.main()
