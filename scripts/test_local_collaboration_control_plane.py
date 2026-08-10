import tempfile
import uuid
from pathlib import Path

from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_control_plane import *

def request(pid):
    return {"project_id":pid,"occurred_at":"2026-08-10T00:00:00Z","timestamp_provenance":"explicit","work":{"project_id":pid,"work_id":"w1","issue":1,"objective":"bounded control","stage":"s","phase":"p","role":"Implementer","root_budget_tokens":100,"remaining_budget_tokens":100,"issue_anchor":{"issue":1,"durable_anchor":"https://github.com/x/y/issues/1","scope":"s","risk":"low","acceptance":"a","human_gates":["none"]},"durable_anchors":["https://github.com/x/y/issues/1"],"stop_conditions":["none"]},"execution_run":{"run_id":"r1","work_id":"w1","role":"Implementer","state":"active","context":{"source_timestamp":"2026-08-10T00:00:00Z","threshold_band":"implementer_small_scoped_implementation","resource_observations":{"context_tokens":{"provenance":"estimated","tokens":10,"source":"test"}}},"model":{"name":"gpt-5.5","reasoning":"medium"}},"dispatch_claim":{"idempotency_key":"k","work_id":"w1","role":"Implementer","decision_boundary":"b","transition_semantics":"t","durable_anchor":"https://github.com/x/y/issues/1"},"requested_route":"isolated_execution"}

def test_roundtrip():
    pid=str(uuid.uuid4()); result=plan_control_request(request(pid), {})
    assert result["event_batch"] and result["decision"] == "allow"
    state=reduce_control_events([{"event_type":x["event_type"],"payload":x["payload"]} for x in result["event_batch"]])
    assert state["initialized"] and state["work"]["work_id"] == "w1"

def test_existing_append_and_retry():
    pid=str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as d:
        ledger=LocalCollaborationLedger.create_project(projects_root=d, project_id=pid); ledger.close()
        first=apply_control_request(d,pid,request(pid)); second=apply_control_request(d,pid,request(pid))
        assert first["mutation_performed"] and not second["mutation_performed"]

def test_reject_caller_claims():
    try: plan_control_request({**request(str(uuid.uuid4())),"active_runs":[]}, {})
    except ControlPlaneError as exc: assert str(exc)=="hold_untrusted_observation"
    else: assert False

if __name__ == "__main__":
    test_roundtrip(); test_reject_caller_claims(); test_existing_append_and_retry(); print("ok")
