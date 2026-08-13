import json
import tempfile
import unittest
import uuid
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

from local_collaboration_handoff import (
    HandoffState, apply_handoff_transition, plan_handoff_transition,
    read_handoff_state, verify_a2_import_seam,
)
from local_collaboration_ledger import LocalCollaborationLedger


def opaque(name):
    return name.replace("_", "-")


def digest(name):
    import hashlib
    return hashlib.sha256(name.encode()).hexdigest()


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = LocalCollaborationLedger.create_project(projects_root=self.tmp.name)
        self.project_id = self.ledger.project_id

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def request(self, transition, **extra):
        return {"transition": transition, "project_id": self.project_id, **extra}

    def decision(self, key):
        return {"decision_id": opaque("decision-" + key), "decision_digest": digest("decision-" + key)}

    def enrollment(self, transition, replica, epoch, key):
        return self.request(transition, replica_id=opaque(replica), replica_epoch=epoch,
                            enrollment_id=opaque("enrollment-" + key), enrollment_digest=digest("enrollment-" + key),
                            **self.decision(key))

    def apply(self, request):
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, request)
        self.assertNotIsInstance(plan, dict)
        return apply_handoff_transition(self.ledger, plan, expected_before=state)

    def ready_locked(self):
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        prepared = self.apply(self.request("prepare", handoff_id="handoff-1", source_replica_id="replica-source",
                                           target_replica_id="replica-target", frontier_digest=digest("frontier")))
        self.assertEqual(prepared["outcome"], "prepared")
        return self.apply(self.request("source_lock", handoff_id="handoff-1"))

    def test_enrollment_prepare_lock_a2_and_activation(self):
        locked = self.ready_locked()
        self.assertEqual(locked["outcome"], "source_locked")
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        header = {key: state.handoff[key] for key in ("handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch", "target_replica_epoch", "source_generation", "source_head", "frontier_digest")}
        header["project_id"] = self.project_id
        seam = verify_a2_import_seam(state, header)
        self.assertEqual(seam["outcome"], "a2_import_candidate")
        receipt = self.apply(self.request("target_activate", handoff_id="handoff-1", target_replica_id="replica-target",
                                          import_readback_generation=state.authority_generation,
                                          import_readback_head=state.authority_head, **self.decision("activate")))
        self.assertEqual(receipt["outcome"], "target_active")
        final = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual((final.active_replica_id, final.active_epoch, final.phase), ("replica-target", 2, "active"))

    def test_cancel_and_takeover(self):
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        self.apply(self.request("prepare", handoff_id="handoff-c", source_replica_id="replica-source", target_replica_id="replica-target", frontier_digest=digest("frontier")))
        cancelled = self.apply(self.request("cancel", handoff_id="handoff-c", cancellation_evidence="bundle_not_released", **self.decision("cancel")))
        self.assertEqual(cancelled["outcome"], "cancelled")
        takeover = self.apply(self.request("takeover", target_replica_id="replica-target", prior_frontier_digest=digest("rpo"), **self.decision("takeover")))
        self.assertEqual(takeover["outcome"], "taken_over")
        self.assertEqual(read_handoff_state(self.ledger.path, expected_project_id=self.project_id).active_replica_id, "replica-target")

    def test_holds_before_writable_open_for_closed_privacy_and_state_failures(self):
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        bad = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "r", "replica_epoch": 1, "enrollment_id": "e", "enrollment_digest": digest("e"), **self.decision("e"), "prompt": "private"})
        self.assertEqual(bad["outcome"], "hold_privacy")
        self.assertEqual(state.authority_generation, read_handoff_state(self.ledger.path, expected_project_id=self.project_id).authority_generation)
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        wrong = plan_handoff_transition(read_handoff_state(self.ledger.path, expected_project_id=self.project_id), self.enrollment("enroll_initial", "replica-target", 1, "target"))
        self.assertEqual(wrong["outcome"], "hold_transition")

    def test_revoked_cross_project_stale_and_duplicate(self):
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        revoked = self.apply(self.request("revoke_inactive", replica_id="replica-target", **self.decision("revoke")))
        self.assertEqual(revoked["outcome"], "enrolled")
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        no_target = plan_handoff_transition(state, self.request("prepare", handoff_id="handoff-r", source_replica_id="replica-source", target_replica_id="replica-target", frontier_digest=digest("f")))
        self.assertEqual(no_target["outcome"], "hold_enrollment")
        cross = plan_handoff_transition(state, {**self.enrollment("enroll_target", "replica-x", 1, "x"), "project_id": str(uuid.uuid4())})
        self.assertEqual(cross["outcome"], "hold_project_identity")
        fresh = self.enrollment("enroll_target", "replica-target", 2, "target2")
        first = self.apply(fresh)
        self.assertEqual(first["outcome"], "enrolled")
        before = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(before, self.request("prepare", handoff_id="handoff-d", source_replica_id="replica-source", target_replica_id="replica-target", frontier_digest=digest("d")))
        self.ledger.conditional_append_batch([{"event_type": "unrelated", "event_id": str(uuid.uuid4()), "payload": {"n": 1}, "actor": "owner", "source": "fixture", "root": self.project_id}], expected_generation=before.authority_generation, expected_head=before.authority_head)
        self.assertEqual(apply_handoff_transition(self.ledger, plan, expected_before=before)["outcome"], "hold_stale_snapshot")

    def test_exact_post_commit_duplicate_and_fresh_process_replay(self):
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, self.enrollment("enroll_initial", "replica-source", 1, "source"))
        first = apply_handoff_transition(self.ledger, plan, expected_before=state)
        self.assertEqual(first["outcome"], "enrolled")
        after = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        retry = apply_handoff_transition(self.ledger, plan, expected_before=state)
        self.assertEqual(retry["cas_status"], "duplicate")
        self.assertEqual(retry["after_state_digest"], first["after_state_digest"])
        self.assertEqual(after.state_digest, read_handoff_state(self.ledger.path, expected_project_id=self.project_id).state_digest)
        self.ledger.close()
        reopened = LocalCollaborationLedger.open_existing(Path(self.tmp.name) / self.project_id / "collaboration.db", expected_project_id=self.project_id)
        try:
            replayed = read_handoff_state(reopened.path, expected_project_id=self.project_id)
            self.assertEqual(replayed.active_replica_id, "replica-source")
        finally:
            self.ledger = reopened

    def test_event_ref_mismatch_holds_without_success(self):
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, self.enrollment("enroll_initial", "replica-source", 1, "source"))
        altered = type(plan)(plan.transition, plan.project_id, plan.expected_generation, plan.expected_head, plan.before_state_digest,
                             plan.after_state_digest, plan.request_digest, {**plan.event, "event_id": str(uuid.uuid4())})
        self.assertEqual(apply_handoff_transition(self.ledger, altered, expected_before=state)["outcome"], "hold_readback_ambiguous")

    def test_no_external_io_and_json_safe_receipts(self):
        self.ready_locked()
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.assertTrue(json.dumps({"state": state.state_digest}))
        self.assertEqual(verify_a2_import_seam(state, {"project_id": self.project_id}), {"schema_version": "LocalCollaborationHandoff-v1", "outcome": "hold_schema", "project_id": self.project_id, "reason_code": "bundle_header_invalid", "flags": {"owner_persisted": False, "owner_readback_verified": False, "bundle_exported": False, "owner_import_performed": False, "transport_performed": False}})

    def test_closed_schema_accepts_canonical_request_and_receipt(self):
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        request = self.enrollment("enroll_initial", "replica-source", 1, "source")
        self.assertFalse(list(validator.iter_errors(request)))
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        receipt = apply_handoff_transition(self.ledger, plan_handoff_transition(state, request), expected_before=state)
        self.assertFalse(list(validator.iter_errors(receipt)))
        self.assertTrue(list(validator.iter_errors({**request, "unknown": True})))


if __name__ == "__main__":
    unittest.main()
