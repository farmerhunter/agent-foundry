import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import (
    apply_owner_import, inspect_manual_bundle, plan_owner_import,
    prepare_manual_bundle, verify_owner_import_proof,
)
from local_collaboration_ledger import LocalCollaborationLedger


def digest(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()


class ManualBundleTests(unittest.TestCase):
    def setUp(self):
        self.source_root = tempfile.TemporaryDirectory()
        self.target_root = tempfile.TemporaryDirectory()
        self.project_id = str(uuid.uuid4())
        self.source = LocalCollaborationLedger.create_project(projects_root=self.source_root.name, project_id=self.project_id)
        self.target = LocalCollaborationLedger.create_project(projects_root=self.target_root.name, project_id=self.project_id)

    def tearDown(self):
        self.source.close(); self.target.close()
        self.source_root.cleanup(); self.target_root.cleanup()

    def request(self, transition, **more):
        return {"transition": transition, "project_id": self.project_id, **more}

    def apply(self, request):
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, request)
        self.assertNotIsInstance(plan, dict)
        return apply_handoff_transition(self.source, plan, expected_before=state)

    def locked(self):
        self.apply(self.request("enroll_initial", replica_id="source", replica_epoch=1, enrollment_id="enroll-source", enrollment_digest=digest("source"), decision_id="d-source", decision_digest=digest("d-source")))
        self.apply(self.request("enroll_target", replica_id="target", replica_epoch=1, enrollment_id="enroll-target", enrollment_digest=digest("target"), decision_id="d-target", decision_digest=digest("d-target")))
        self.apply(self.request("prepare", handoff_id="handoff-1", source_replica_id="source", target_replica_id="target", frontier_digest=digest("frontier")))
        self.apply(self.request("source_lock", handoff_id="handoff-1"))
        return read_handoff_state(self.source.path, expected_project_id=self.project_id)

    def exported(self):
        state = self.locked()
        bundle = prepare_manual_bundle(self.source, expected_handoff_state=state)
        self.assertNotIn("outcome", bundle)
        with self.assertRaises(TypeError):
            bundle["bundle_id"] = "mutate"
        self.assertTrue(json.dumps(bundle))
        self.assertEqual(inspect_manual_bundle(bundle)["outcome"], "import_candidate")
        return bundle

    def test_roundtrip_import_exact_retry_and_verified_locator(self):
        bundle = self.exported()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        plan = plan_owner_import(before, bundle)
        self.assertNotIsInstance(plan, dict)
        proof = apply_owner_import(self.target, plan, expected_before=before)
        self.assertEqual(proof["outcome"], "owner_import_committed")
        self.assertTrue(proof["owner_import_performed"])
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        verified = verify_owner_import_proof(self.target.path, expected_project_id=self.project_id, proof_ref=locator)
        self.assertEqual(verified["outcome"], "owner_import_verified")
        self.assertFalse(verified["target_activation_authorized"])
        retry = apply_owner_import(self.target, plan, expected_before=before)
        self.assertEqual(retry["outcome"], "owner_import_committed")
        self.assertFalse(retry["owner_import_performed"])
        self.target.close()
        self.target = LocalCollaborationLedger.open_existing(Path(self.target_root.name) / self.project_id / "collaboration.db", expected_project_id=self.project_id)
        self.assertEqual(verify_owner_import_proof(self.target.path, expected_project_id=self.project_id, proof_ref=locator)["outcome"], "owner_import_verified")

    def test_exact_source_export_receipt_loss_retry_reconstructs_same_package(self):
        locked = self.locked()
        first = prepare_manual_bundle(self.source, expected_handoff_state=locked)
        retry = prepare_manual_bundle(self.source, expected_handoff_state=locked)
        self.assertEqual(first["package_digest"], retry["package_digest"])
        self.assertEqual(read_handoff_state(self.source.path, expected_project_id=self.project_id).authority_generation, locked.authority_generation + 1)

    def test_exact_prefix_and_divergent_target(self):
        bundle = self.exported()
        records = list(bundle["events"]) + [bundle["export_marker"]]
        prefix = records[:2]
        self.target.conditional_append_batch([{key: record[key] for key in ("event_type", "event_id", "payload", "actor", "source", "root")} for record in prefix], expected_generation=0, expected_head="0" * 64)
        plan = plan_owner_import(LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id), bundle)
        self.assertNotIsInstance(plan, dict)
        self.assertEqual(apply_owner_import(self.target, plan, expected_before=LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id))["outcome"], "owner_import_committed")
        other = LocalCollaborationLedger.create_project(projects_root=tempfile.mkdtemp(), project_id=self.project_id)
        try:
            other.conditional_append_batch([{"event_type": "other", "event_id": str(uuid.uuid4()), "payload": {"n": 1}, "actor": "owner", "source": "fixture", "root": self.project_id}], expected_generation=0, expected_head="0" * 64)
            held = plan_owner_import(LocalCollaborationLedger.authority_snapshot(other.path, expected_project_id=self.project_id), bundle)
            self.assertEqual(held["outcome"], "hold_target_not_prefix")
        finally:
            other.close()

    def test_export_marker_blocks_unreleased_cancel_and_forgery_holds(self):
        bundle = self.exported()
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        cancel = plan_handoff_transition(state, self.request("cancel", handoff_id="handoff-1", cancellation_evidence="bundle_not_released", decision_id="d-cancel", decision_digest=digest("d-cancel")))
        self.assertEqual(cancel["outcome"], "hold_cancellation_unproven")
        forged = dict(bundle); forged["source_head"] = digest("forged")
        self.assertEqual(inspect_manual_bundle(forged)["outcome"], "hold_package_integrity")
        private = dict(bundle); private["events"] = [dict(bundle["events"][0], payload={"prompt": "private"})] + list(bundle["events"][1:])
        self.assertEqual(inspect_manual_bundle(private)["outcome"], "hold_privacy")

    def test_cross_project_stale_proof_and_activation_stay_held(self):
        bundle = self.exported()
        before = LocalCollaborationLedger.authority_snapshot(self.target.path, expected_project_id=self.project_id)
        proof = apply_owner_import(self.target, plan_owner_import(before, bundle), expected_before=before)
        locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        self.target.append_event("later", {"n": 1}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        self.assertEqual(verify_owner_import_proof(self.target.path, expected_project_id=self.project_id, proof_ref=locator)["outcome"], "hold_proof_missing_or_stale")
        other = dict(locator); other["project_id"] = str(uuid.uuid4())
        self.assertEqual(verify_owner_import_proof(self.target.path, expected_project_id=self.project_id, proof_ref=other)["outcome"], "hold_project_identity")
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        activation = plan_handoff_transition(state, self.request("target_activate", handoff_id="handoff-1", target_replica_id="target", decision_id="d-a", decision_digest=digest("d-a"), import_readback_generation=1, import_readback_head=digest("h")))
        self.assertEqual(activation["outcome"], "hold_a2_owner_proof_unavailable")

    def test_schema_and_no_db_file_copy(self):
        bundle = self.exported()
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff-bundle.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(json.loads(json.dumps(bundle)))))
        self.assertEqual({path.name for path in Path(self.source_root.name).rglob("*") if path.is_file() if path.suffix in {".db", ".wal", ".shm"}}, {"collaboration.db"})


if __name__ == "__main__":
    unittest.main()
