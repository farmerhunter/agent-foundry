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
            "enrollment_descriptor": {"descriptor_id": f"descriptor-{replica_id}", "descriptor_digest": hashlib.sha256(replica_id.encode()).hexdigest()}}


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
    inspection = replica.inspect_bundle(bundle, enrollment(P1, "replica.a", 1)["enrollment_descriptor"])
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
    plan = replica.plan_import(snapshot(), [first], bundle, enrollment(P1, "replica.b", 1)["enrollment_descriptor"])
    assert plan["outcome"] == "replica_import_candidate_ready"
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-replica.schema.yaml").read_text())
    Draft202012Validator(schema).validate(plan)
    assert plan["candidate_identities"] == [identity("replica.b", 1, 1, "b")]
    duplicate = replica.plan_import(snapshot(), [first, second], bundle, enrollment(P1, "replica.b", 1)["enrollment_descriptor"])
    assert duplicate["outcome"] == "replica_duplicate"


def test_import_returns_non_authoritative_candidate_after_current_descriptor_validation():
    item = event(P1, "replica.unapproved", 1, 1, "unapproved")
    forged = enrollment(P1, "replica.unapproved", 1)
    bundle = replica.export_bundle(snapshot(), [item], forged, [identity("replica.unapproved", 1, 1, "unapproved")])
    claimed_receipt = {"schema_version": replica.VERSION, "outcome": "replica_export_ready", "project_id": P1, "bundle_digest": bundle["bundle_digest"], "flags": replica.FLAGS}
    assert replica.plan_import(snapshot(), [], bundle, claimed_receipt)["outcome"] == "hold_replica_identity"
    claimed_trust = {**forged["enrollment_descriptor"], "trusted": True}
    assert replica.plan_import(snapshot(), [], bundle, claimed_trust)["outcome"] == "hold_replica_identity"
    assert replica.inspect_bundle(bundle, enrollment(P1, "replica.approved", 1)["enrollment_descriptor"])["outcome"] == "hold_replica_identity"
    plan = replica.plan_import(snapshot(), [], bundle, forged["enrollment_descriptor"])
    assert plan["outcome"] == "replica_import_candidate_ready"
    assert {key: plan[key] for key in ("authority_level", "owner_enrollment_verified", "import_authorized", "requires_owner_verification")} == {"authority_level": "current_validation_only", "owner_enrollment_verified": False, "import_authorized": False, "requires_owner_verification": True}
    assert "accepted_identities" not in plan and plan["candidate_identities"] == [identity("replica.unapproved", 1, 1, "unapproved")]


@pytest.mark.parametrize("mutate,outcome", [
    (lambda bundle: bundle["events"][0].update(event_digest="0" * 64), "hold_transport_integrity"),
    (lambda bundle: bundle.update(project_id=P2), "hold_replica_identity"),
    (lambda bundle: bundle["replica_identity"].update(replica_epoch=2), "hold_transport_integrity"),
])
def test_representative_integrity_identity_and_epoch_holds(mutate, outcome):
    item = event(P1, "replica.a", 1, 1, "a")
    bundle = replica.export_bundle(snapshot(), [item], enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "a")])
    mutate(bundle)
    assert replica.inspect_bundle(bundle, enrollment(P1, "replica.a", 1)["enrollment_descriptor"])["outcome"] == outcome


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
    result = replica.FakeReplicaTransport(available=False).plan_delivery(snapshot(), [], bundle, enrollment(P1, "replica.a", 1)["enrollment_descriptor"])
    assert result["outcome"] == "replica_offline"
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network call"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("process call"))
    assert replica.FakeReplicaTransport().plan_delivery(snapshot(), [], bundle, enrollment(P1, "replica.a", 1)["enrollment_descriptor"])["outcome"] == "replica_import_candidate_ready"


def test_public_fake_dependency_envelopes_remain_non_confirming():
    item = event(P1, "replica.a", 1, 1, "a")
    result = replica.reduce_converged_view([item])
    assert result["flags"] == {"simulation_only": True, "network_capability": False, "authoritative": False, "confirmation_eligible": False, "remote_mutation_performed": False}
    assert "confirmed" not in result and "remote" not in result


def test_every_terminal_receipt_is_schema_closed_and_runtime_closed():
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-replica.schema.yaml").read_text())
    validator = Draft202012Validator(schema)
    ident = identity("replica.a", 1, 1, "terminal")
    common = {"schema_version": replica.VERSION, "project_id": P1, "flags": dict(replica.FLAGS)}
    candidate = {**common, "outcome": "replica_import_candidate_ready", "authority_generation": 1, "authority_head": H,
                 "bundle_digest": H, "candidate_identities": [ident], "authority_level": "current_validation_only",
                 "owner_enrollment_verified": False, "import_authorized": False, "requires_owner_verification": True}
    fixtures = [
        {**common, "outcome": "replica_export_ready", "bundle_digest": H},
        candidate,
        {**common, "outcome": "replica_converged", "shared_view_digest": H, "converged_identities": [ident]},
        {**common, "outcome": "replica_duplicate", "authority_generation": 1, "authority_head": H, "bundle_digest": H, "duplicate_identities": [ident]},
        {**common, "outcome": "replica_offline", "authority_generation": 1, "authority_head": H, "reason_code": "replica_offline"},
        {**common, "outcome": "hold_replica_identity", "reason_code": "replica_identity_invalid"},
        {**common, "outcome": "hold_transport_integrity", "reason_code": "transport_integrity_invalid"},
        {**common, "outcome": "hold_missing_dependency", "reason_code": "missing_dependency"},
        {**common, "outcome": "hold_semantic_conflict", "reason_code": "semantic_conflict", "held_identities": [ident]},
        {**common, "outcome": "hold_privacy", "reason_code": "privacy_rejected"},
        {**common, "outcome": "hold_schema", "reason_code": "schema_invalid"},
        {**common, "outcome": "hold_recovery_readback", "reason_code": "recovery_readback_required"},
    ]
    assert {value["outcome"] for value in fixtures} == replica.OUTCOMES
    for value in fixtures:
        validator.validate(value)
        replica._validate_receipt(value)

    invalid = [
        {key: value for key, value in candidate.items() if key != "requires_owner_verification"},
        {**candidate, "unknown": True},
        {**candidate, "authority_generation": "1"},
        {**fixtures[5], "authority_level": "current_validation_only"},
        {**candidate, "held_identities": [ident]},
    ]
    for value in invalid:
        assert list(validator.iter_errors(value))
        with pytest.raises(replica.ReplicaHold):
            replica._validate_receipt(value)


def test_bundle_count_boundary_is_schema_and_runtime_hold_before_candidate_plan():
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-replica.schema.yaml").read_text())
    item = event(P1, "replica.a", 1, 1, "count")
    bundle = replica.export_bundle(snapshot(), [item], enrollment(P1, "replica.a", 1), [identity("replica.a", 1, 1, "count")])
    over_limit = copy.deepcopy(bundle); over_limit["events"] = [item] * 101
    assert list(Draft202012Validator(schema).iter_errors(over_limit))
    assert replica.plan_import(snapshot(), [], over_limit, enrollment(P1, "replica.a", 1)["enrollment_descriptor"])["outcome"] == "hold_schema"
