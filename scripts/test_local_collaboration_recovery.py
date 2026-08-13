import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from jsonschema import Draft202012Validator

from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
import local_collaboration_recovery as recovery
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
    def test_backup_and_selected_replica_success_outputs_match_closed_schema(self):
        schema = yaml.safe_load(Path("schemas/local-collaboration-recovery.schema.yaml").read_text())
        validator = Draft202012Validator(schema)
        dest = Path(self.root.name) / "canonical-backup.db"
        backup = apply_recovery_action({"ledger": self.ledger, "destination": str(dest)}, self.plan("create_backup", {"destination": str(dest)}))
        self.assertEqual(list(validator.iter_errors(dict(backup))), [])
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        target = plan_handoff_transition(state, {"transition": "enroll_target", "project_id": self.project_id, "replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-e", "enrollment_digest": digest("target"), "decision_id": "target", "decision_digest": digest("target")})
        apply_handoff_transition(self.ledger, target, expected_before=state)
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id, intent="revoke_inactive_replica", selected_replica_id="target")
        plan = plan_recovery_action(summary, {"operation": "revoke_inactive_replica", "decision_id": "human-2", "decision_digest": digest("human2"), "parameters": {}})
        result = apply_recovery_action({"ledger": self.ledger, "selected_replica_id": "target"}, plan)
        self.assertEqual(result["receipt"]["selected_replica_id"], "target")
        self.assertEqual(list(validator.iter_errors(dict(result))), [])
        self.assertIn("destination_digest", backup["receipt"]["locator_digests"])
    def test_active_revoke_holds_before_mutation(self):
        before = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id, intent="revoke_inactive_replica", selected_replica_id="source")
        self.assertEqual(summary["state"], "held")
        after = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(before.authority_generation, after.authority_generation)
    def test_takeover_target_pair_drift_holds_before_any_a1_call(self):
        bundle = {"fixture": "bundle"}; proof = {"fixture": "proof"}
        projection = {"outcome": "owner_import_verified", "target_activation_authorized": False,
                      "target_generation": 4, "target_head": digest("four"), "target_replica_id": "target",
                      "frontier_digest": digest("frontier")}
        summary = recovery._summary(self.project_id, "recovery_action_ready", "takeover_from_accepted_frontier",
            bundle_locator_digest=recovery._digest(bundle), proof_locator_digest=recovery._digest(proof),
            projection_digest=recovery._digest(projection), target_generation=4, target_head=digest("four"),
            frontier_digest=digest("frontier"), before_generation=4, before_head=digest("four"), before_state_digest=digest("state"))
        plan = plan_recovery_action(summary, {"operation": "takeover_from_accepted_frontier", "decision_id": "human-1",
            "decision_digest": digest("human"), "parameters": {"bundle": bundle, "proof_ref": proof, "rpo_warning_digest": digest("rpo")}})
        drifted = SimpleNamespace(authority_generation=5, authority_head=digest("five"))
        with patch.object(recovery, "read_recovery_summary", return_value=summary), \
             patch.object(recovery, "read_handoff_state", return_value=drifted), \
             patch.object(recovery, "read_owner_imported_handoff_projection", return_value=projection), \
             patch.object(recovery, "plan_handoff_transition") as owner_plan, \
             patch.object(recovery, "apply_handoff_transition") as owner_apply:
            result = apply_recovery_action({"ledger": self.ledger, "bundle": bundle, "proof_ref": proof}, plan)
        self.assertEqual(result["reason_code"], "target_authority_pair_drift")
        owner_plan.assert_not_called(); owner_apply.assert_not_called()
        snap = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(snap.authority_generation, 1)
    def test_schema(self):
        schema = yaml.safe_load(Path(__file__).with_name("..").resolve() / "schemas/local-collaboration-recovery.schema.yaml") if False else yaml.safe_load(Path("schemas/local-collaboration-recovery.schema.yaml").read_text())
        summary = read_recovery_summary(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(dict(summary))), [])


if __name__ == "__main__": unittest.main()
