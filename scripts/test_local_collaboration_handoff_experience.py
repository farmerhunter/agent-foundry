import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import apply_owner_import, plan_owner_import, prepare_manual_bundle
from local_collaboration_handoff_experience import project_handoff_experience
from local_collaboration_ledger import LocalCollaborationLedger


def digest(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()


class HandoffExperienceTests(unittest.TestCase):
    def setUp(self):
        self.source_root = tempfile.TemporaryDirectory()
        self.target_root = tempfile.TemporaryDirectory()
        self.project_id = str(uuid.uuid4())
        self.source = LocalCollaborationLedger.create_project(projects_root=self.source_root.name, project_id=self.project_id)
        self.target = LocalCollaborationLedger.create_project(projects_root=self.target_root.name, project_id=self.project_id)

    def tearDown(self):
        self.source.close(); self.target.close()
        self.source_root.cleanup(); self.target_root.cleanup()

    def req(self, transition, **more):
        return {"transition": transition, "project_id": self.project_id, **more}

    def apply(self, transition, **more):
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, self.req(transition, **more))
        self.assertNotIsInstance(plan, dict)
        return apply_handoff_transition(self.source, plan, expected_before=state)

    def enroll(self):
        self.apply("enroll_initial", replica_id="source", replica_epoch=1, enrollment_id="source-enroll",
                   enrollment_digest=digest("source"), decision_id="source-decision", decision_digest=digest("source-decision"))
        self.apply("enroll_target", replica_id="target", replica_epoch=1, enrollment_id="target-enroll",
                   enrollment_digest=digest("target"), decision_id="target-decision", decision_digest=digest("target-decision"))

    def locked_bundle(self):
        self.enroll()
        self.apply("prepare", handoff_id="handoff-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("frontier"))
        self.apply("source_lock", handoff_id="handoff-1")
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        bundle = prepare_manual_bundle(self.source, expected_handoff_state=state)
        self.assertNotIn("outcome", bundle)
        return bundle

    def local(self):
        return project_handoff_experience(self.source.path, expected_project_id=self.project_id, mode="local_source")

    def test_local_uninitialized_active_preparing_locked_and_exported_statuses(self):
        self.assertEqual((self.local()["status"], self.local()["next_action"]), ("local_enrollment_required", "enroll_active_device"))
        self.enroll()
        self.assertEqual(self.local()["status"], "local_active")
        self.apply("prepare", handoff_id="handoff-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("frontier"))
        self.assertEqual(self.local()["status"], "handoff_preparing")
        self.apply("source_lock", handoff_id="handoff-1")
        self.assertEqual(self.local()["status"], "source_locked_export_bundle")
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        self.assertNotIn("outcome", prepare_manual_bundle(self.source, expected_handoff_state=state))
        result = self.local()
        self.assertEqual((result["status"], result["next_action"]), ("source_locked_bundle_exported", "retain_bundle_and_resolve_handoff"))
        self.assertFalse(result["target_activation_authorized"])

    def test_cancel_takeover_and_held_conflict_are_explicit(self):
        self.enroll()
        self.apply("prepare", handoff_id="cancel-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("cancel"))
        self.apply("cancel", handoff_id="cancel-1", cancellation_evidence="bundle_not_released", decision_id="cancel-decision", decision_digest=digest("cancel-decision"))
        self.assertEqual(self.local()["status"], "handoff_cancelled_active")
        self.apply("takeover", target_replica_id="target", prior_frontier_digest=digest("prior"), decision_id="takeover-decision", decision_digest=digest("takeover-decision"))
        self.assertEqual(self.local()["status"], "handoff_taken_over_active")
        self.source.append_event("handoff_target_activated", {"schema_version": "LocalCollaborationHandoff-v1", "transition": "target_activate", "project_id": self.project_id, "request_digest": digest("bad"), "before_state_digest": read_handoff_state(self.source.path, expected_project_id=self.project_id).state_digest}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        result = self.local()
        self.assertEqual((result["outcome"], result["status"], result["next_action"]), ("hold_conflict", "held", "human_conflict_resolution_required"))

    def test_imported_target_uses_owner_reconstruction_and_stays_inactive(self):
        bundle = self.locked_bundle()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        result = project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target", bundle=bundle, proof_ref=locator)
        self.assertEqual(result["outcome"], "target_import_verified_activation_deferred")
        self.assertEqual(result["status"], "target_import_verified_activation_deferred")
        self.assertEqual(result["next_action"], "keep_target_inactive")
        self.assertFalse(result["target_activation_authorized"])
        self.assertTrue(result["flags"]["owner_import_verified"])
        self.assertNotEqual((result["source_generation"], result["source_head"]), (result["target_generation"], result["target_head"]))

    def test_imported_requires_bundle_and_locator_and_caller_claims_do_not_help(self):
        self.assertEqual(project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target")["outcome"], "hold_schema")
        self.enroll()
        bare = project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target", bundle={"project_id": self.project_id}, proof_ref={"project_id": self.project_id, "trusted": True})
        self.assertEqual(bare["outcome"], "hold_import_proof")
        self.assertFalse(bare["target_activation_authorized"])

    def test_stale_cross_project_and_private_bundle_hold_without_activation(self):
        bundle = self.locked_bundle()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        stale = dict(locator); stale["receipt_event_hash"] = digest("forged")
        self.assertEqual(project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target", bundle=bundle, proof_ref=stale)["outcome"], "hold_import_proof")
        cross = dict(locator); cross["project_id"] = str(uuid.uuid4())
        self.assertEqual(project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target", bundle=bundle, proof_ref=cross)["outcome"], "hold_import_proof")
        private = json.loads(json.dumps(bundle)); private["events"][0]["payload"]["prompt"] = "private"
        self.assertEqual(project_handoff_experience(self.target.path, expected_project_id=self.project_id, mode="imported_target", bundle=private, proof_ref=locator)["outcome"], "hold_import_proof")

    def test_local_does_not_accept_import_inputs_or_mutate_business_rows(self):
        before = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        result = project_handoff_experience(self.source.path, expected_project_id=self.project_id, mode="local_source", bundle={}, proof_ref={})
        after = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        self.assertEqual(result["outcome"], "hold_schema")
        self.assertEqual((before.authority_generation, before.authority_head), (after.authority_generation, after.authority_head))

    def test_closed_schema_and_json_safe_outputs(self):
        result = self.local()
        self.assertTrue(json.dumps(result))
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff-experience.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        self.assertFalse(list(validator.iter_errors(result)))
        self.assertTrue(list(validator.iter_errors({**result, "claim": True})))


if __name__ == "__main__":
    unittest.main()
