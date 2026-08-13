import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import apply_owner_import, apply_owner_target_activation, plan_owner_import, plan_owner_target_activation, prepare_manual_bundle
from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_recovery import apply_recovery_action, plan_recovery_action, read_recovery_summary


def digest(value): return hashlib.sha256(value.encode()).hexdigest()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.a_root, self.b_root = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.project_id = str(uuid.uuid4())
        self.source = LocalCollaborationLedger.create_project(projects_root=self.a_root.name, project_id=self.project_id)
        self.target = LocalCollaborationLedger.create_project(projects_root=self.b_root.name, project_id=self.project_id)

    def tearDown(self):
        self.source.close(); self.target.close(); self.a_root.cleanup(); self.b_root.cleanup()

    def transition(self, ledger, name, **more):
        state = read_handoff_state(ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, {"transition": name, "project_id": self.project_id, **more})
        self.assertNotIsInstance(plan, dict)
        return apply_handoff_transition(ledger, plan, expected_before=state)

    def imported_target(self):
        self.transition(self.source, "enroll_initial", replica_id="source", replica_epoch=1, enrollment_id="source-e", enrollment_digest=digest("source"), decision_id="source-d", decision_digest=digest("source-d"))
        self.transition(self.source, "enroll_target", replica_id="target", replica_epoch=1, enrollment_id="target-e", enrollment_digest=digest("target"), decision_id="target-d", decision_digest=digest("target-d"))
        self.transition(self.source, "prepare", handoff_id="handoff-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("frontier"))
        self.transition(self.source, "source_lock", handoff_id="handoff-1")
        bundle = prepare_manual_bundle(self.source, expected_handoff_state=read_handoff_state(self.source.path, expected_project_id=self.project_id))
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        return bundle, locator

    def test_public_owner_e2e_import_to_takeover(self):
        bundle, proof = self.imported_target()
        decision = {"decision_id": "human-takeover", "decision_digest": digest("human-takeover")}
        summary = read_recovery_summary(self.target.path, expected_project_id=self.project_id, bundle=bundle, proof_ref=proof)
        self.assertEqual(summary["outcome"], "target_import_recovery_ready")
        plan = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="target_takeover", decision=decision, bundle=bundle, proof_ref=proof)
        self.assertNotIsInstance(plan, dict)
        result = apply_recovery_action(self.target, plan, decision=decision, bundle=bundle, proof_ref=proof)
        self.assertEqual((result["outcome"], result["active_replica_id"]), ("recovery_action_applied", "target"))
        duplicate = apply_recovery_action(self.target, plan, decision=decision, bundle=bundle, proof_ref=proof)
        self.assertFalse(duplicate["flags"]["mutation_performed"])
        self.assertEqual(read_handoff_state(self.source.path, expected_project_id=self.project_id).phase, "source_locked")

    def test_stale_and_forged_proof_hold_before_takeover(self):
        bundle, proof = self.imported_target()
        bad = dict(proof); bad["receipt_event_hash"] = digest("forged")
        held = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="target_takeover", decision={"decision_id": "d", "decision_digest": digest("d")}, bundle=bundle, proof_ref=bad)
        self.assertEqual(held["outcome"], "hold_owner_proof_unavailable")
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        self.target.append_event("later", {"n": 1}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        held = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="target_takeover", decision={"decision_id": "d", "decision_digest": digest("d")}, bundle=bundle, proof_ref=proof)
        self.assertEqual(held["outcome"], "hold_owner_proof_unavailable")
        self.assertEqual(before.authority_generation + 1, LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id).authority_generation)

    def test_fresh_backup_restore_and_post_export_cancel_boundaries(self):
        bundle, proof = self.imported_target()
        decision = {"decision_id": "d", "decision_digest": digest("d")}
        destination = str(Path(self.b_root.name) / "fresh-backup.db")
        backup = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="fresh_backup", decision=decision, backup_locator=destination)
        backup_receipt = apply_recovery_action(self.target, backup, decision=decision, backup_locator=destination)
        self.assertEqual(backup_receipt["outcome"], "fresh_backup_created")
        self.assertTrue(Path(destination).is_file())
        restored_root = str(Path(self.b_root.name) / "restored")
        restore = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="fresh_target_restore", decision=decision, restore_locator=destination, fresh_target_locator=restored_root)
        restore_receipt = apply_recovery_action(self.target, restore, decision=decision, restore_locator=destination, fresh_target_locator=restored_root)
        self.assertEqual(restore_receipt["outcome"], "fresh_target_restored")
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-recovery.schema.yaml").read_text())
        validator = Draft202012Validator(schema)
        self.assertFalse(list(validator.iter_errors(backup_receipt)))
        self.assertFalse(list(validator.iter_errors(restore_receipt)))
        self.assertEqual(plan_recovery_action(self.source.path, expected_project_id=self.project_id, action="pre_export_cancel", decision=decision)["outcome"], "hold_cancellation_unproven")

    def test_schema_closed_and_private_input_holds(self):
        result = read_recovery_summary(self.target.path, expected_project_id=self.project_id)
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-recovery.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(result)))
        self.assertTrue(list(Draft202012Validator(schema).iter_errors({**result, "claim": True})))
        held = plan_recovery_action(self.target.path, expected_project_id=self.project_id, action="target_takeover", decision={"decision_id": "d", "decision_digest": digest("d"), "token": "no"})
        self.assertEqual(held["outcome"], "hold_privacy")
        self.assertTrue(json.dumps(held))


if __name__ == "__main__": unittest.main()
