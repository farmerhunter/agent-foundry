import json
import tempfile
import unittest
import uuid
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

from local_collaboration_handoff import (
    HandoffHold, HandoffState, apply_handoff_transition, plan_handoff_transition,
    read_handoff_state, reduce_handoff_events, verify_a2_import_seam,
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

    def test_enrollment_prepare_lock_and_a2_candidate_only(self):
        locked = self.ready_locked()
        self.assertEqual(locked["outcome"], "source_locked")
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        header = {key: state.handoff[key] for key in ("handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch", "target_replica_epoch", "source_generation", "source_head", "frontier_digest")}
        header["project_id"] = self.project_id
        seam = verify_a2_import_seam(state, header)
        self.assertEqual(seam["outcome"], "a2_import_candidate")
        activation = plan_handoff_transition(state, self.request("target_activate", handoff_id="handoff-1", target_replica_id="replica-target", **self.decision("activate")))
        self.assertEqual(activation["outcome"], "hold_a2_owner_proof_unavailable")
        self.assertEqual(read_handoff_state(self.ledger.path, expected_project_id=self.project_id).authority_generation, state.authority_generation)

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
        calls = 0
        original = self.ledger.conditional_append_batch
        def forbidden(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)
        self.ledger.conditional_append_batch = forbidden
        self.assertEqual(apply_handoff_transition(self.ledger, plan, expected_before=before)["outcome"], "hold_stale_snapshot")
        self.assertEqual(calls, 0)

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
                             plan.after_state_digest, plan.expected_outcome, plan.request_digest, {**plan.event, "event_id": str(uuid.uuid4())})
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

    def test_historical_duplicate_and_crafted_activation_hold(self):
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        plan = plan_handoff_transition(state, self.enrollment("enroll_initial", "replica-source", 1, "source"))
        self.assertEqual(apply_handoff_transition(self.ledger, plan, expected_before=state)["cas_status"], "appended")
        after = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.ledger.conditional_append_batch([{"event_type": "unrelated", "event_id": str(uuid.uuid4()), "payload": {"n": 1}, "actor": "owner", "source": "fixture", "root": self.project_id}], expected_generation=after.authority_generation, expected_head=after.authority_head)
        self.assertEqual(apply_handoff_transition(self.ledger, plan, expected_before=state)["outcome"], "hold_stale_snapshot")
        current = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        crafted = type(plan)("target_activate", plan.project_id, current.authority_generation, current.authority_head,
                             current.state_digest, current.state_digest, "target_active", plan.request_digest, plan.event)
        self.assertEqual(apply_handoff_transition(self.ledger, crafted, expected_before=current)["outcome"], "hold_a2_owner_proof_unavailable")

    def test_unverified_activation_event_replays_to_held_not_active(self):
        self.ready_locked()
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        payload = {"schema_version": "LocalCollaborationHandoff-v1", "transition": "target_activate", "project_id": self.project_id,
                   "request_digest": digest("crafted"), "before_state_digest": state.state_digest}
        self.ledger.conditional_append_batch([{"event_type": "handoff_target_activated", "event_id": str(uuid.uuid4()), "payload": payload,
                                                "actor": "owner", "source": "orch05_handoff", "root": self.project_id}],
                                               expected_generation=state.authority_generation, expected_head=state.authority_head)
        replayed = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual((replayed.phase, replayed.active_replica_id), ("held", "replica-source"))

    def test_bundle_export_marker_is_purely_reducible_and_blocks_unreleased_cancel(self):
        self.ready_locked()
        state = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        marker = self.apply(self.request("bundle_exported", handoff_id="handoff-1", bundle_id="bundle-1",
                                         content_manifest_digest=digest("manifest")))
        self.assertEqual(marker["outcome"], "bundle_exported")
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        reduced = reduce_handoff_events(self.project_id, snapshot.events, snapshot.authority_generation, snapshot.authority_head)
        self.assertEqual((reduced.phase, reduced.handoff["status"]), ("source_locked", "bundle_exported"))
        cancel = plan_handoff_transition(reduced, self.request("cancel", handoff_id="handoff-1", cancellation_evidence="bundle_not_released", **self.decision("blocked")))
        self.assertEqual(cancel["outcome"], "hold_cancellation_unproven")

    def test_prepare_persists_only_owner_derived_source_frontier(self):
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        before = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        forged = self.request("prepare", handoff_id="handoff-frontier", source_replica_id="replica-source",
                              target_replica_id="replica-target", frontier_digest=digest("frontier"),
                              source_generation=0, source_head="0" * 64)
        self.assertEqual(plan_handoff_transition(before, forged)["outcome"], "hold_schema")
        receipt = self.apply(self.request("prepare", handoff_id="handoff-frontier", source_replica_id="replica-source",
                                           target_replica_id="replica-target", frontier_digest=digest("frontier")))
        self.assertEqual(receipt["outcome"], "prepared")
        event = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id).events[-1]
        self.assertEqual((event.payload["source_generation"], event.payload["source_head"], event.payload["source_prefix_identity"]),
                         (before.authority_generation, before.authority_head, before.portable_prefix_identity))
        self.assertEqual(read_handoff_state(self.ledger.path, expected_project_id=self.project_id).handoff["source_head"], before.authority_head)
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-handoff.schema.yaml").read_text())
        payload_schema = {"$schema": schema["$schema"], "$defs": schema["$defs"], **schema["$defs"]["durable_prepare_payload"]}
        self.assertFalse(list(Draft202012Validator(payload_schema).iter_errors(dict(event.payload))))

    def test_pure_reducer_requires_prepare_event_local_source_frontier(self):
        self.assertEqual(self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        self.assertEqual(self.apply(self.request("prepare", handoff_id="handoff-prefix", source_replica_id="replica-source",
                                                 target_replica_id="replica-target", frontier_digest=digest("frontier")))["outcome"], "prepared")
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        event = snapshot.events[-1]
        altered = type(event)(event.sequence, event.event_id, event.event_type,
                              {**event.payload, "source_generation": 0, "source_head": "0" * 64,
                               "source_prefix_identity": "0" * 64},
                              event.payload_hash, event.previous_hash, event.event_hash, event.created_at,
                              event.actor, event.source, event.root)
        with self.assertRaises(HandoffHold):
            reduce_handoff_events(self.project_id, list(snapshot.events[:-1]) + [altered],
                                  snapshot.authority_generation, snapshot.authority_head)

    def test_unrelated_verified_events_advance_the_replay_pair_without_changing_handoff_state(self):
        self.ledger.conditional_append_batch([{"event_type": "unrelated", "event_id": str(uuid.uuid4()),
                                               "payload": {"n": 1}, "actor": "owner", "source": "fixture",
                                               "root": self.project_id}], expected_generation=0, expected_head="0" * 64)
        initial = self.apply(self.enrollment("enroll_initial", "replica-source", 1, "source"))
        self.assertEqual(initial["outcome"], "enrolled")
        self.assertEqual(self.apply(self.enrollment("enroll_target", "replica-target", 1, "target"))["outcome"], "enrolled")
        self.ledger.append_event("unrelated", {"n": 2}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        before_prepare = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual(before_prepare.phase, "active")
        self.assertEqual(self.apply(self.request("prepare", handoff_id="handoff-unrelated", source_replica_id="replica-source",
                                                  target_replica_id="replica-target", frontier_digest=digest("frontier")))["outcome"], "prepared")
        self.ledger.append_event("unrelated", {"n": 3}, event_id=str(uuid.uuid4()), actor="owner", source="fixture", root=self.project_id)
        self.assertEqual(self.apply(self.request("source_lock", handoff_id="handoff-unrelated"))["outcome"], "source_locked")
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.project_id)
        replayed = read_handoff_state(self.ledger.path, expected_project_id=self.project_id)
        self.assertEqual((replayed.authority_generation, replayed.authority_head),
                         (snapshot.authority_generation, snapshot.authority_head))


if __name__ == "__main__":
    unittest.main()
