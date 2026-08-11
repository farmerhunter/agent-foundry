import json
import tempfile
import uuid
from pathlib import Path

from local_collaboration_ledger import LocalCollaborationLedger
import local_collaboration_control_plane as cp
import local_collaboration_scheduler as sc

def _control_request(pid):
    return {"project_id": pid, "occurred_at": "2026-08-11T00:00:00Z", "timestamp_provenance": "explicit",
      "work": {"project_id": pid, "work_id": "w1", "issue": 404, "objective": "local scheduler", "stage": "implementation", "phase": "orch-03", "role": "Implementer", "root_budget_tokens": 100, "remaining_budget_tokens": 100, "issue_anchor": {"issue": 404, "scope": "local scheduler", "risk": "low", "acceptance": "bounded", "durable_anchor": "issue:404", "human_gates": ["none"]}, "durable_anchors": ["issue:404"], "stop_conditions": ["scope drift"]},
      "execution_run": {"run_id": "r1", "work_id": "w1", "role": "Implementer", "state": "active", "context": {"source_timestamp": "2026-08-11T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 100, "source": "test"}}}, "model": {"name": "gpt-5.5", "reasoning": "low"}},
      "dispatch_claim": {"idempotency_key": "k1", "work_id": "w1", "role": "Implementer", "decision_boundary": "local", "transition_semantics": "bounded", "durable_anchor": "issue:404"}, "requested_route": "isolated_execution"}


def _setup(root):
    pid = str(uuid.uuid4()); ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=pid); ledger.close(); cp.apply_control_request(root, pid, _control_request(pid)); return pid


def test_initialize_and_offline_transitions():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); first = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        assert first["mutation_performed"]
        for n, (a, b) in enumerate((("registered", "queued"), ("queued", "claimed"), ("claimed", "active")), 1):
            req = {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": a, "to_state": b, "transition_sequence": n, "occurred_at": f"2026-08-11T00:00:0{n+1}Z"}
            result = sc.apply_scheduler_request(root, pid, req)
            assert result["mutation_performed"]
            assert sc.apply_scheduler_request(root, pid, req)["decision"] == "duplicate"
        state = sc.replay_scheduler_state(root, pid); assert state["local_state"] == "active"


def test_exact_retry_and_divergence_hold():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); req = {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"}; assert sc.apply_scheduler_request(root, pid, req)["mutation_performed"]; assert sc.apply_scheduler_request(root, pid, req)["decision"] == "duplicate"
        bad = {**req, "occurred_at": "2026-08-11T00:00:02Z"}
        try: sc.apply_scheduler_request(root, pid, bad)
        except sc.SchedulerHold as exc: assert str(exc) in {"hold_duplicate_or_divergent", "hold_scheduler_not_enabled"}
        else: raise AssertionError("divergence must hold")


def test_replay_uses_one_authority_snapshot_and_receipts_expose_pair():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        original = LocalCollaborationLedger.authority_snapshot
        calls = []

        def counted(db_path, *, expected_project_id):
            snapshot = original(db_path, expected_project_id=expected_project_id)
            calls.append(snapshot)
            return snapshot

        LocalCollaborationLedger.authority_snapshot = counted
        try:
            first = sc.replay_scheduler_state(root, pid)
        finally:
            LocalCollaborationLedger.authority_snapshot = original
        assert len(calls) == 1
        assert (first["authority_generation"], first["authority_head"]) == (calls[0].authority_generation, calls[0].authority_head)
        reducer_events = sc._snapshot_events_for_reducer(calls[0].events)
        assert json.loads(json.dumps(reducer_events, ensure_ascii=False, sort_keys=True))
        assert cp.reduce_control_events([event for event in reducer_events if event["event_type"].startswith("control.")])["initialized"]
        request = {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"}
        applied = sc.apply_scheduler_request(root, pid, request)
        assert applied["replay"]["authority_generation"] > first["authority_generation"]
        assert applied["replay"]["authority_head"] != first["authority_head"]
        duplicate = sc.apply_scheduler_request(root, pid, request)
        assert duplicate["decision"] == "duplicate"
        assert (duplicate["replay"]["authority_generation"], duplicate["replay"]["authority_head"]) == (applied["replay"]["authority_generation"], applied["replay"]["authority_head"])
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "registered", "to_state": "queued", "transition_sequence": 1, "occurred_at": "2026-08-11T00:00:02Z"})
        changed = sc.replay_scheduler_state(root, pid)
        assert changed["authority_generation"] > applied["replay"]["authority_generation"]
        assert changed["authority_head"] != applied["replay"]["authority_head"]


def test_remote_never_confirmed_by_observation():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"}); result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": str(uuid.uuid4()), "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"}); assert result["mutation_performed"]; state = sc.replay_scheduler_state(root, pid); assert state["remote_intent_state"] == "accepted_local"


def test_remote_predecessor_guards():
    """Remote outcomes require the explicit pending materialization step."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        for operation, extra in (("observe", {"observed_remote_state": "open"}), ("failure", {}), ("conflict", {}), ("cancel", {})):
            try:
                sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": operation, "intent_id": intent, **extra, "occurred_at": "2026-08-11T00:00:03Z"})
            except sc.SchedulerHold as exc:
                assert str(exc) == "hold_transition_order"
            else:
                raise AssertionError(f"{operation} must require pending materialization")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:04Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:05Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:06Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_transition_order"
        else:
            raise AssertionError("observed state must not silently re-enter pending")


def test_observation_and_terminal_use_current_attempt():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:03Z"})
        observed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
        assert observed["event_batch"][0]["payload"]["payload"]["attempt_sequence"] == 1
        terminal = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "conflict", "intent_id": intent, "occurred_at": "2026-08-11T00:00:05Z"})
        assert terminal["event_batch"][0]["payload"]["payload"]["attempt_sequence"] == 1
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "conflict"


def test_retry_requires_receipt_and_advances_only_after_failed_attempt():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:03Z"})
        # An outcome belongs to attempt 1; an arbitrary attempt 2 is not a retry.
        ledger_path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        before = len(ledger.list_events()); ledger.close()
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "attempt_sequence": 2, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_transition_order"
        else:
            raise AssertionError("observation cannot invent a new attempt")
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        assert len(ledger.list_events()) == before
        ledger.close()
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "failure", "intent_id": intent, "classification": "hold_readback_unavailable", "occurred_at": "2026-08-11T00:00:04Z"})
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "readback_unavailable"
        retry = {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "attempt_sequence": 2, "occurred_at": "2026-08-11T00:00:05Z"}
        try:
            sc.apply_scheduler_request(root, pid, retry)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_retry_receipt_required"
        else:
            raise AssertionError("retry without authorization must hold")
        retry.update({"retry_receipt_ref": "issue:404/retry-1", "retry_receipt_digest": "a" * 64, "retry_authority": "Human"})
        result = sc.apply_scheduler_request(root, pid, retry)
        assert result["mutation_performed"]
        assert sc.replay_scheduler_state(root, pid)["attempt_sequence"] == 2


def test_readback_future_attempt_holds_before_append():
    """A readback for attempt N+1 cannot mutate an attempt-N authority."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        expected = {"kind": "issue", "ref": "opaque-issue", "digest": "a" * 64, "version": "v1"}
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "expected_remote_kind": expected["kind"], "expected_remote_ref": expected["ref"], "expected_remote_digest": expected["digest"], "expected_remote_version": expected["version"], "occurred_at": "2026-08-11T00:00:03Z"})
        ledger_path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        before = ledger.list_events(); before_head = before[-1].event_hash
        ledger.close()

        class Adapter:
            def readback(self, request):
                return {"project_id": pid, "intent_id": intent, "confirmed": True,
                    "adapter_id": "test-adapter", "adapter_version": "1",
                    "expected_remote_kind": expected["kind"], "expected_remote_ref": expected["ref"],
                    "expected_remote_digest": expected["digest"], "expected_remote_version": expected["version"],
                    "readback_digest": "b" * 64, "opaque_receipt_ref": "receipt:1",
                    "occurred_at": "2026-08-11T00:00:04Z", "read_timestamp": "2026-08-11T00:00:04Z",
                    "readback_nonce": "nonce-1", "request_digest": request["request_digest"],
                    "desired_effect_digest": desired}

        request = {"project_id": pid, "work_id": "w1", "operation": "readback", "intent_id": intent,
            "attempt_sequence": 2, "request_digest": "c" * 64, "occurred_at": "2026-08-11T00:00:04Z"}
        try:
            sc.apply_remote_readback(root, pid, intent, Adapter(), request)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_readback_binding_conflict"
        else:
            raise AssertionError("future readback attempt must hold")
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        after = ledger.list_events(); assert len(after) == len(before); assert after[-1].event_hash == before_head
        ledger.close()


def test_closed_payload_and_resume_gate():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        try:
            sc._validate_envelope({"version": sc.VERSION, "project_id": pid, "kind": "scheduler_initialized", "occurred_at": "2026-08-11T00:00:01Z", "timestamp_provenance": "explicit", "payload": {"work_id": "w1", "unknown": True}})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_schema_or_version"
        else:
            raise AssertionError("unknown scheduler payload must hold")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        for n, (a, b) in enumerate((("registered", "queued"), ("queued", "claimed"), ("claimed", "active"), ("active", "hold")), 1):
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": a, "to_state": b, "transition_sequence": n, "occurred_at": f"2026-08-11T00:00:0{n+1}Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "hold", "to_state": "queued", "transition_sequence": 5, "occurred_at": "2026-08-11T00:00:06Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_resume_receipt_required"
        else:
            raise AssertionError("resume without receipt must hold")


def test_caller_project_binding_and_disabled_gate():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); other = str(uuid.uuid4())
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": other, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_control_plane_unready"
        else:
            raise AssertionError("caller/project mismatch must hold")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "disable", "occurred_at": "2026-08-11T00:00:02Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "enable", "occurred_at": "2026-08-11T00:00:03Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_disabled_enable_gate"
        else:
            raise AssertionError("disabled enable without gate must hold")

def _remote_setup(root, expected):
    pid = _setup(root)
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
    intent = str(uuid.uuid4())
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, **expected, "occurred_at": "2026-08-11T00:00:03Z"})
    return pid, intent


def _canonical_fake_readback(pid, intent, expected, desired, request, **changes):
    """The accepted #403 hermetic result shape; it remains non-authoritative."""
    response = {
        "schema_version": "GitHubMaterializationAdapter-v1", "operation": "issue_create",
        "outcome": "materialization_readback_verified", "simulation_only": True,
        "remote_mutation_performed": False, "authoritative": False,
        "confirmation_eligible": False, "classification": "must_publish",
        "project_id": pid, "intent_id": intent, "attempt_sequence": 1,
        "idempotency_key": "fixture-1", "readback_digest": "b" * 64,
        "opaque_receipt_ref": "fake:fixture-1", "confirmed": True,
        "adapter_id": "github-materialization-hermetic", "adapter_version": "1",
        "expected_remote_kind": expected["expected_remote_kind"],
        "expected_remote_ref": expected["expected_remote_ref"],
        "expected_remote_digest": expected["expected_remote_digest"],
        "expected_remote_version": expected["expected_remote_version"],
        "desired_effect_digest": desired, "request_digest": request["request_digest"],
        "occurred_at": "2026-08-11T00:00:04Z", "read_timestamp": "2026-08-11T00:00:04Z",
        "readback_nonce": "2026-08-11T00:00:04Z"}
    response.update(changes)
    return response


def _business_snapshot(path, root, pid):
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        events = ledger.list_events()
        table_counts = tuple(ledger._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                             for table in ("holds", "project_bindings", "projections"))
        return len(events), events[-1].sequence if events else 0, events[-1].event_hash if events else None, table_counts, sc.replay_scheduler_state(root, pid)
    finally:
        ledger.close()


def test_hermetic_readback_never_confirms_and_invalid_envelopes_do_not_call_adapter():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        path = Path(root) / pid / "collaboration.db"
        desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        request = {"project_id": pid, "work_id": "w1", "operation": "readback", "intent_id": intent,
                   "attempt_sequence": 1, "request_digest": "c" * 64, "occurred_at": "2026-08-11T00:00:04Z",
                   **expected, "desired_effect_digest": desired}
        before = _business_snapshot(path, root, pid)

        class Adapter:
            calls = 0
            def readback(self, received):
                self.calls += 1
                return _canonical_fake_readback(pid, intent, expected, desired, request)

        adapter = Adapter()
        try:
            sc.apply_remote_readback(root, pid, intent, adapter, request)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_untrusted_readback"
        else:
            raise AssertionError("hermetic #403 result must never confirm")
        assert adapter.calls == 1 and _business_snapshot(path, root, pid) == before

        # Closed request validation happens before the fake boundary is invoked.
        invalid_overlays = [{"unknown": "x"}, {"request_digest": "not-a-digest"},
            {"expected_remote_ref": "other"}, {"attempt_sequence": 2},
            {"desired_effect_digest": None}, {"expected_remote_ref": None},
            {"desired_effect_digest": 1}, {"expected_remote_ref": 1}]
        invalid_requests = [{**request, **bad} for bad in invalid_overlays]
        for field in ("desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
            missing = dict(request); del missing[field]; invalid_requests.append(missing)
        for candidate in invalid_requests:
            try:
                sc.apply_remote_readback(root, pid, intent, adapter, candidate)
            except sc.SchedulerHold:
                pass
            else:
                raise AssertionError("invalid request must hold")
            assert adapter.calls == 1 and _business_snapshot(path, root, pid) == before


def test_readback_response_closed_parity_and_self_attestation_never_mutate():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-2", "expected_remote_digest": "d" * 64, "expected_remote_version": "v2"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        path = Path(root) / pid / "collaboration.db"
        desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        request = {"project_id": pid, "work_id": "w1", "operation": "confirm", "intent_id": intent,
                   "attempt_sequence": 1, "request_digest": "e" * 64, "occurred_at": "2026-08-11T00:00:04Z",
                   **expected, "desired_effect_digest": desired}
        before = _business_snapshot(path, root, pid)
        variants = [
            lambda r: {**r, "unknown": "x"},
            lambda r: {k: v for k, v in r.items() if k != "readback_nonce"},
            lambda r: {**r, "attempt_sequence": "1"},
            lambda r: {**r, "observed_remote_state": "open"},
            lambda r: {**r, "authoritative": True, "confirmation_eligible": True},
            lambda r: {**r, "readback_digest": "f" * 64, "readback_nonce": "other", "opaque_receipt_ref": "fake:other"},
        ]
        for build in variants:
            class Adapter:
                def readback(self, received):
                    return build(_canonical_fake_readback(pid, intent, expected, desired, request))
            try:
                sc.apply_remote_readback(root, pid, intent, Adapter(), request)
            except sc.SchedulerHold as exc:
                assert str(exc) in {"hold_schema_or_version", "hold_readback_binding_conflict", "hold_untrusted_readback"}
            else:
                raise AssertionError("untrusted or malformed response must hold")
            assert _business_snapshot(path, root, pid) == before


def test_historical_schema_valid_confirmation_still_replays():
    """The repair blocks new untrusted transitions without rewriting history."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-history", "expected_remote_digest": "9" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        try:
            existing = ledger.list_events()
            cstate = cp.reduce_control_events([event for event in existing if event.event_type.startswith("control.")])
            sstate = sc.reduce_scheduler_state(cstate, [event for event in existing if event.event_type.startswith("scheduler.")])
            payload = {"work_id": "w1", **sc._binding_payload({}, cstate, sstate), "intent_id": intent,
                "desired_effect_digest": sstate["desired_effect_digest"], "attempt_sequence": 1,
                **expected, "adapter_id": "historical-trusted-adapter", "adapter_version": "1",
                "readback_digest": "8" * 64, "read_timestamp": "2026-08-11T00:00:04Z",
                "readback_nonce": "history-nonce", "request_digest": "7" * 64,
                "opaque_receipt_ref": "receipt:history", "classification": "confirmed", "next_action": "none"}
            ledger.append_batch([sc._event(pid, "remote_confirmation_recorded", payload, "2026-08-11T00:00:04Z")])
        finally:
            ledger.close()
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "confirmed"


def test_reducer_version_mismatch_is_preappend_hold():
    """Reducer binding rejects a changed version without changing business state."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        before_events = ledger.list_events(); before_head = before_events[-1].event_hash
        control_state = cp.reduce_control_events([e for e in before_events if e.event_type.startswith("control.")])
        scheduler_events = [e for e in before_events if e.event_type.startswith("scheduler.")]
        pending = scheduler_events[-1]
        altered = sc._event(pid, "remote_observation_recorded", {**pending.payload["payload"], "expected_remote_version": "v2", "observed_remote_state": "open", "classification": "observed_unverified"}, "2026-08-11T00:00:04Z")
        ledger.close()
        try:
            sc.reduce_scheduler_state(control_state, scheduler_events + [altered])
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_readback_binding_conflict"
        else:
            raise AssertionError("reducer version mismatch must hold")
        check = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        after_events = check.list_events(); check.close()
        assert len(after_events) == len(before_events) and after_events[-1].event_hash == before_head


def test_planner_observation_version_mismatch_is_preappend_hold():
    """Observation planning rejects a changed expected version before append."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", **{**expected, "expected_remote_version": "v2"}, "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc: assert str(exc) == "hold_readback_binding_conflict"
        else: raise AssertionError("planner version mismatch must hold")
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()


def test_privacy_binding_mismatch_is_preappend_hold():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        for bad in ({"intent_id": str(uuid.uuid4())}, {"attempt_sequence": 2}, {"expected_remote_version": "v2"}, {"unknown": "x"}):
            request = {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, **expected, "occurred_at": "2026-08-11T00:00:04Z", **bad}
            try: sc.apply_scheduler_request(root, pid, request)
            except sc.SchedulerHold: pass
            else: raise AssertionError("invalid privacy payload must hold")
            ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()


def test_adapter_version_mismatch_is_preappend_hold():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"; desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        class Adapter:
            def readback(self, request):
                return _canonical_fake_readback(pid, intent, expected, desired, request, expected_remote_version="v2")
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        try: sc.apply_remote_readback(root, pid, intent, Adapter(), {"project_id": pid, "work_id": "w1", "operation": "readback", "intent_id": intent, "attempt_sequence": 1, "request_digest": "c" * 64, "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc: assert str(exc) == "hold_readback_binding_conflict"
        else: raise AssertionError("adapter version mismatch must hold")
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()


def test_observed_unverified_to_privacy_hold_preserves_all_bindings():
    """A valid observed attempt can become a durable privacy hold."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        observed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", **expected, "occurred_at": "2026-08-11T00:00:04Z"})
        assert observed["mutation_performed"]
        state = sc.replay_scheduler_state(root, pid)
        assert state["remote_intent_state"] == "observed_unverified"
        assert state["attempt_sequence"] == 1
        desired = state["desired_effect_digest"]
        result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, "attempt_sequence": 1, "desired_effect_digest": desired, **expected, "occurred_at": "2026-08-11T00:00:05Z"})
        assert result["mutation_performed"]
        state = sc.replay_scheduler_state(root, pid)
        assert state["remote_intent_state"] == "privacy_held"
        assert state["local_state"] == "hold"
        assert state["intent_id"] == intent and state["attempt_sequence"] == 1
        assert state["desired_effect_digest"] == desired
        assert all(state[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        privacy = [event for event in ledger.list_events() if event.event_type == "scheduler.privacy_hold_recorded"][-1]
        payload = privacy.payload["payload"]
        assert payload["intent_id"] == intent and payload["attempt_sequence"] == 1 and payload["desired_effect_digest"] == desired
        assert all(payload[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        ledger.close()


def test_pending_materialization_to_privacy_hold_preserves_all_bindings():
    """A pending attempt can become a durable privacy hold without observation."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-2", "expected_remote_digest": "c" * 64, "expected_remote_version": "v2"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        pending_state = sc.replay_scheduler_state(root, pid)
        assert pending_state["remote_intent_state"] == "pending_materialization"
        desired = pending_state["desired_effect_digest"]
        result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, "attempt_sequence": 1, "desired_effect_digest": desired, **expected, "occurred_at": "2026-08-11T00:00:04Z"})
        assert result["mutation_performed"]
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        privacy = [event for event in ledger.list_events() if event.event_type == "scheduler.privacy_hold_recorded"][-1]
        payload = privacy.payload["payload"]
        assert payload["intent_id"] == intent
        assert payload["attempt_sequence"] == 1
        assert payload["desired_effect_digest"] == desired
        assert all(payload[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        ledger.close()
        replayed = sc.replay_scheduler_state(root, pid)
        assert replayed["remote_intent_state"] == "privacy_held"
        assert replayed["local_state"] == "hold"
        assert replayed["intent_id"] == intent
        assert replayed["attempt_sequence"] == 1
        assert replayed["desired_effect_digest"] == desired
        assert all(replayed[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))


if __name__ == "__main__":
    test_initialize_and_offline_transitions(); test_exact_retry_and_divergence_hold(); test_replay_uses_one_authority_snapshot_and_receipts_expose_pair(); test_remote_never_confirmed_by_observation(); test_remote_predecessor_guards(); test_observation_and_terminal_use_current_attempt(); test_closed_payload_and_resume_gate(); test_caller_project_binding_and_disabled_gate(); test_hermetic_readback_never_confirms_and_invalid_envelopes_do_not_call_adapter(); test_readback_response_closed_parity_and_self_attestation_never_mutate(); test_historical_schema_valid_confirmation_still_replays(); test_reducer_version_mismatch_is_preappend_hold(); test_planner_observation_version_mismatch_is_preappend_hold(); test_privacy_binding_mismatch_is_preappend_hold(); test_adapter_version_mismatch_is_preappend_hold(); test_observed_unverified_to_privacy_hold_preserves_all_bindings(); test_pending_materialization_to_privacy_hold_preserves_all_bindings(); print("ok")
