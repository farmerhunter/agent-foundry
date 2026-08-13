import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
import local_collaboration_handoff_experience as experience

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import apply_owner_import, plan_owner_import, prepare_manual_bundle
from local_collaboration_handoff_experience import read_handoff_experience
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
        return read_handoff_experience(self.source.path, expected_project_id=self.project_id)

    def test_local_uninitialized_active_preparing_locked_and_exported_statuses(self):
        self.assertEqual((self.local()["experience_state"], self.local()["next_action"]), ("held", "resolve_conflict_or_recover_owner_state"))
        self.enroll()
        self.assertEqual(self.local()["experience_state"], "single_device_active")
        self.apply("prepare", handoff_id="handoff-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("frontier"))
        self.assertEqual(self.local()["experience_state"], "handoff_preparing")
        self.apply("source_lock", handoff_id="handoff-1")
        self.assertEqual(self.local()["experience_state"], "source_locked")
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        self.assertNotIn("outcome", prepare_manual_bundle(self.source, expected_handoff_state=state))
        result = self.local()
        self.assertEqual((result["experience_state"], result["next_action"]), ("bundle_ready_for_manual_transfer", "transfer_and_owner_import_bundle"))
        self.assertFalse(result["target_activation_performed"])

    def test_cancel_takeover_and_held_conflict_are_explicit(self):
        self.enroll()
        self.apply("prepare", handoff_id="cancel-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("cancel"))
        self.apply("cancel", handoff_id="cancel-1", cancellation_evidence="bundle_not_released", decision_id="cancel-decision", decision_digest=digest("cancel-decision"))
        self.assertEqual(self.local()["experience_state"], "cancelled")
        self.apply("takeover", target_replica_id="target", prior_frontier_digest=digest("prior"), decision_id="takeover-decision", decision_digest=digest("takeover-decision"))
        self.assertEqual(self.local()["experience_state"], "taken_over")
        self.source.append_event("handoff_target_activated", {"schema_version": "LocalCollaborationHandoff-v1", "transition": "target_activate", "project_id": self.project_id, "request_digest": digest("bad"), "before_state_digest": read_handoff_state(self.source.path, expected_project_id=self.project_id).state_digest}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        result = self.local()
        self.assertEqual((result["experience_state"], result["next_action"]), ("held", "resolve_conflict_or_recover_owner_state"))

    def test_imported_target_uses_owner_reconstruction_and_stays_inactive(self):
        bundle = self.locked_bundle()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        result = read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle=bundle, proof_ref=locator)
        self.assertEqual(result["experience_state"], "target_import_verified_activation_deferred")
        self.assertEqual(result["next_action"], "request_later_target_activation_gate")
        self.assertFalse(result["target_activation_performed"])
        self.assertTrue(result["owner_import_verified"])
        self.assertNotEqual((result["source_generation"], result["source_head"]), (result["target_generation"], result["target_head"]))
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff-experience.schema.yaml").read_text())
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(result)))

    def test_imported_requires_bundle_and_locator_and_caller_claims_do_not_help(self):
        self.assertEqual(read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle={})["experience_state"], "held")
        self.enroll()
        bare = read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle={"project_id": self.project_id}, proof_ref={"project_id": self.project_id, "trusted": True})
        self.assertEqual(bare["experience_state"], "held")
        self.assertFalse(bare["target_activation_performed"])

    def test_stale_cross_project_and_private_bundle_hold_without_activation(self):
        bundle = self.locked_bundle()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        stale = dict(locator); stale["receipt_event_hash"] = digest("forged")
        self.assertEqual(read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle=bundle, proof_ref=stale)["experience_state"], "held")
        cross = dict(locator); cross["project_id"] = str(uuid.uuid4())
        self.assertEqual(read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle=bundle, proof_ref=cross)["experience_state"], "held")
        private = json.loads(json.dumps(bundle)); private["events"][0]["payload"]["prompt"] = "private"
        self.assertEqual(read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle=private, proof_ref=locator)["experience_state"], "held")

    def test_local_does_not_accept_import_inputs_or_mutate_business_rows(self):
        before = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        result = read_handoff_experience(self.source.path, expected_project_id=self.project_id, bundle={}, proof_ref={})
        after = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        self.assertEqual(result["experience_state"], "held")
        self.assertEqual((before.authority_generation, before.authority_head), (after.authority_generation, after.authority_head))

    def test_closed_schema_and_json_safe_outputs(self):
        result = self.local()
        self.assertTrue(json.dumps(result))
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff-experience.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        self.assertFalse(list(validator.iter_errors(result)))
        self.assertTrue(list(validator.iter_errors({**result, "claim": True})))
        with self.assertRaises(TypeError):
            result["next_action"] = "none"

    def test_malformed_locator_and_caller_claim_hold_before_any_activation(self):
        result = read_handoff_experience(self.target.path, expected_project_id=self.project_id, bundle={}, proof_ref={
            "project_id": self.project_id, "receipt_event_id": "not-a-uuid", "receipt_event_hash": digest("h"), "package_digest": digest("p")})
        self.assertEqual(result["experience_state"], "held")
        self.assertFalse(result["mutation_performed"])
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff-experience.schema.yaml").read_text())
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(result)))
        claimed = read_handoff_experience(self.source.path, expected_project_id=self.project_id, activation=True)
        self.assertEqual(claimed["experience_state"], "held")

    def test_invalid_selection_and_closed_envelopes_do_not_call_either_owner(self):
        calls = {"a1": 0, "a2": 0}
        original_a1, original_a2 = experience.read_handoff_state, experience.read_owner_imported_handoff_projection
        def a1(*args, **kwargs):
            calls["a1"] += 1
            raise AssertionError("A1 must not run")
        def a2(*args, **kwargs):
            calls["a2"] += 1
            raise AssertionError("A2 must not run")
        experience.read_handoff_state, experience.read_owner_imported_handoff_projection = a1, a2
        locator = {"project_id": self.project_id, "receipt_event_id": str(uuid.uuid4()),
                   "receipt_event_hash": digest("receipt"), "package_digest": digest("package")}
        try:
            invalids = [
                {"bundle": {}, "proof_ref": locator},
                {"bundle": {}, "proof_ref": {**locator, "unknown": True}},
                {"bundle": {}, "proof_ref": {**locator, "receipt_event_id": "not-a-uuid"}},
                {"bundle": {}, "proof_ref": None},
                {"bundle": None, "proof_ref": None, "claims": {"mode": "imported_target"}},
            ]
            for item in invalids:
                result = read_handoff_experience(self.source.path, expected_project_id=self.project_id,
                                                 bundle=item["bundle"], proof_ref=item["proof_ref"], **item.get("claims", {}))
                self.assertEqual(result["experience_state"], "held")
            self.assertEqual(calls, {"a1": 0, "a2": 0})
        finally:
            experience.read_handoff_state, experience.read_owner_imported_handoff_projection = original_a1, original_a2


if __name__ == "__main__":
    unittest.main()
