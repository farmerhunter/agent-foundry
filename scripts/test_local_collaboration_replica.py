from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import local_collaboration_replica as replica
from local_collaboration_ledger import LocalCollaborationLedger

P1 = "11111111-1111-4111-8111-111111111111"
P2 = "22222222-2222-4222-8222-222222222222"
H = "a" * 64


def identity(replica_id, epoch, sequence, seed):
    return {"replica_id": replica_id, "replica_epoch": epoch, "origin_sequence": sequence,
            "event_id": str(uuid.uuid5(uuid.NAMESPACE_URL, seed))}


def enrollment(project_id, replica_id, epoch):
    return {"project_id": project_id, "replica_id": replica_id, "replica_epoch": epoch,
            "enrollment_receipt": {"receipt_id": f"receipt-{replica_id}", "receipt_digest": hashlib.sha256(replica_id.encode()).hexdigest(), "outcome": "enrollment_accepted"}}


def event(project_id, rid, epoch, seq, seed, *, parents=(), work=None, decision=None, resolution=None, refs=None):
    value = {"project_id": project_id, **identity(rid, epoch, seq, seed), "event_type": "work_resolution" if resolution else "work_decision" if decision else "replica_note", "causal_parents": list(parents)}
    if decision:
        value.update(work_id=work, decision=decision)
    if resolution:
        value.update(work_id=work, resolution=resolution, conflict_references=list(refs or ()), human_decision_receipt={"receipt_id": "human-1", "receipt_digest": H, "outcome": "human_decision_accepted"})
    digest_value = {key: value[key] for key in value}
    value["event_digest"] = replica._digest(digest_value)
    return value


def snapshot(project_id=P1, generation=3, head=H):
    return {"project_id": project_id, "authority_generation": generation, "authority_head": head}


def test_schema_parses_and_closed_export_round_trip():
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-replica.schema.yaml").read_text())
    events = [event(P1, "replica.a", 1, 1, "a")]
    bundle = replica.export_bundle(snapshot(), events, enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "a")])
    Draft202012Validator(schema).validate(bundle)
    assert bundle["outcome"] == "replica_export_ready"
    inspection = replica.inspect_bundle(bundle, [enrollment(P1, "replica.a", 1)])
    Draft202012Validator(schema).validate(inspection)
    assert inspection["outcome"] == "replica_export_ready"


def test_export_consumes_owner_snapshot_without_opening_or_mutating_authority(tmp_path):
    ledger = LocalCollaborationLedger.create_project(projects_root=tmp_path, project_id=P1)
    db_path = ledger.path
    ledger.close()
    owner_snapshot = LocalCollaborationLedger.authority_snapshot(db_path, expected_project_id=P1)
    before = (owner_snapshot.authority_generation, owner_snapshot.authority_head)
    item = event(P1, "replica.a", 1, 1, "owner-api")
    bundle = replica.export_bundle(owner_snapshot, [item], enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "owner-api")])
    after = LocalCollaborationLedger.authority_snapshot(db_path, expected_project_id=P1)
    assert bundle["outcome"] == "replica_export_ready"
    assert before == (after.authority_generation, after.authority_head) == (0, "0" * 64)


def test_shuffled_duplicate_delivery_converges_to_one_digest_and_read_only_plan():
    first = event(P1, "replica.a", 1, 1, "a", work="w1", decision="accept")
    second = event(P1, "replica.b", 1, 1, "b", work="w2", decision="hold")
    one = replica.reduce_converged_view([first, second])
    two = replica.reduce_converged_view([second, first, first])
    assert one["outcome"] == two["outcome"] == "replica_converged"
    assert one["shared_view_digest"] == two["shared_view_digest"]
    bundle = replica.export_bundle(snapshot(), [first, second], enrollment(P1, "replica.b", 1), [identity("replica.b", 1, 1, "b")])
    inspection = replica.inspect_bundle(bundle, [enrollment(P1, "replica.b", 1)])
    plan = replica.plan_import(snapshot(), [first], bundle, inspection)
    assert plan["outcome"] == "replica_import_plan_ready"
    assert plan["accepted_identities"] == [identity("replica.b", 1, 1, "b")]
    duplicate = replica.plan_import(snapshot(), [first, second], bundle, inspection)
    assert duplicate["outcome"] == "replica_duplicate"


def test_import_requires_prior_verified_enrollment_context_not_self_issued_receipt():
    item = event(P1, "replica.unapproved", 1, 1, "unapproved")
    forged = enrollment(P1, "replica.unapproved", 1)
    bundle = replica.export_bundle(snapshot(), [item], forged, [identity("replica.unapproved", 1, 1, "unapproved")])
    assert replica.plan_import(snapshot(), [], bundle)["outcome"] == "hold_replica_identity"
    assert replica.inspect_bundle(bundle, [enrollment(P1, "replica.approved", 1)])["outcome"] == "hold_replica_identity"
    inspection = replica.inspect_bundle(bundle, [forged])
    assert inspection["outcome"] == "replica_export_ready"
    tampered = {**inspection, "enrollment_context_digest": "0" * 64}
    assert replica.plan_import(snapshot(), [], bundle, tampered)["outcome"] == "hold_replica_identity"
    assert replica.plan_import(snapshot(), [], bundle, inspection)["outcome"] == "replica_import_plan_ready"


@pytest.mark.parametrize("mutate,outcome", [
    (lambda bundle: bundle["events"][0].update(event_digest="0" * 64), "hold_transport_integrity"),
    (lambda bundle: bundle.update(project_id=P2), "hold_replica_identity"),
    (lambda bundle: bundle["replica_identity"].update(replica_epoch=2), "hold_transport_integrity"),
])
def test_representative_integrity_identity_and_epoch_holds(mutate, outcome):
    item = event(P1, "replica.a", 1, 1, "a")
    bundle = replica.export_bundle(snapshot(), [item], enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "a")])
    mutate(bundle)
    assert replica.inspect_bundle(bundle, [enrollment(P1, "replica.a", 1)])["outcome"] == outcome


def test_missing_parent_and_cycle_hold():
    missing = event(P1, "replica.a", 1, 1, "a", parents=[identity("replica.b", 1, 1, "missing")])
    assert replica.reduce_converged_view([missing])["outcome"] == "hold_missing_dependency"
    left = event(P1, "replica.a", 1, 1, "a")
    right = event(P1, "replica.b", 1, 1, "b", parents=[identity("replica.a", 1, 1, "a")])
    left["causal_parents"] = [identity("replica.b", 1, 1, "b")]
    left["event_digest"] = replica._digest({key: value for key, value in left.items() if key != "event_digest"})
    assert replica.reduce_converged_view([left, right])["outcome"] == "hold_missing_dependency"


def test_work_variant_schema_runtime_parity_requires_work_and_decision():
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-replica.schema.yaml").read_text())
    missing = event(P1, "replica.a", 1, 1, "missing", work="w", decision="accept")
    missing.pop("work_id")
    missing["event_digest"] = replica._digest({key: value for key, value in missing.items() if key != "event_digest"})
    validator = Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/event"})
    assert list(validator.iter_errors(missing))
    assert replica.reduce_converged_view([missing])["outcome"] == "hold_schema"


def test_conflicting_work_decisions_need_explicit_human_compensation():
    accepted = event(P1, "replica.a", 1, 1, "a", work="work", decision="accept")
    rejected = event(P1, "replica.b", 1, 1, "b", work="work", decision="reject")
    held = replica.reduce_converged_view([accepted, rejected])
    assert held["outcome"] == "hold_semantic_conflict"
    speculative = event(P1, "replica.c", 1, 1, "c", work="work", resolution="accept", refs=[identity("replica.a", 1, 1, "a"), identity("replica.b", 1, 1, "b")])
    assert replica.reduce_converged_view([accepted, rejected, speculative])["outcome"] == "hold_semantic_conflict"
    resolution = event(P1, "replica.c", 1, 1, "c", work="work", resolution="accept", parents=[identity("replica.a", 1, 1, "a"), identity("replica.b", 1, 1, "b")], refs=[identity("replica.a", 1, 1, "a"), identity("replica.b", 1, 1, "b")])
    assert replica.reduce_converged_view([accepted, rejected, resolution])["outcome"] == "replica_converged"
    bad = copy.deepcopy(resolution); bad["conflict_references"] = [identity("replica.a", 1, 1, "a")]; bad["event_digest"] = replica._digest({key: value for key, value in bad.items() if key != "event_digest"})
    assert replica.reduce_converged_view([accepted, rejected, bad])["outcome"] == "hold_semantic_conflict"


def test_privacy_json_size_and_offline_hold_without_hidden_retry_or_io(monkeypatch):
    item = event(P1, "replica.a", 1, 1, "a")
    private = copy.deepcopy(item); private["prompt"] = "private"; private["event_digest"] = replica._digest({key: value for key, value in private.items() if key != "event_digest"})
    assert replica.reduce_converged_view([private])["outcome"] == "hold_privacy"
    assert replica.reduce_converged_view([item] * 101)["outcome"] == "hold_schema"
    bundle = replica.export_bundle(snapshot(), [item], enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "a")])
    result = replica.FakeReplicaTransport(available=False).plan_delivery(snapshot(), [], bundle)
    assert result["outcome"] == "replica_offline"
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network call"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("process call"))
    inspection = replica.inspect_bundle(bundle, [enrollment(P1, "replica.a", 1)])
    assert replica.FakeReplicaTransport().plan_delivery(snapshot(), [], bundle, inspection)["outcome"] == "replica_import_plan_ready"


def test_public_fake_dependency_envelopes_remain_non_confirming():
    item = event(P1, "replica.a", 1, 1, "a")
    result = replica.reduce_converged_view([item])
    assert result["flags"] == {"simulation_only": True, "network_capability": False, "authoritative": False, "confirmation_eligible": False, "remote_mutation_performed": False}
    assert "confirmed" not in result and "remote" not in result
