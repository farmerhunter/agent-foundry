from __future__ import annotations

import hashlib
import subprocess
import uuid
from pathlib import Path

import local_collaboration_replica as core
from local_collaboration_replica_git import GitReplicaTransport, GitReplicaTransportHold

P = "11111111-1111-4111-8111-111111111111"
H = "a" * 64


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def ident(replica_id, sequence, name):
    return {"replica_id": replica_id, "replica_epoch": 1, "origin_sequence": sequence, "event_id": str(uuid.uuid5(uuid.NAMESPACE_URL, name))}


def event(replica_id, sequence, name, *, work):
    value = {"project_id": P, **ident(replica_id, sequence, name), "event_type": "work_decision", "work_id": work,
             "decision": "accept", "causal_parents": []}
    value["event_digest"] = core._digest(value)
    return value


def bundle(replica_id, item):
    identity = {"project_id": P, "replica_id": replica_id, "replica_epoch": 1,
                "enrollment_descriptor": {"descriptor_id": f"descriptor-{replica_id}", "descriptor_digest": hashlib.sha256(replica_id.encode()).hexdigest()}}
    frontier = {key: item[key] for key in ("replica_id", "replica_epoch", "origin_sequence", "event_id")}
    return core.export_bundle({"project_id": P, "authority_generation": 1, "authority_head": H}, [item], identity, [frontier])


def clone_pair(tmp_path):
    remote = tmp_path / "remote.git"; run("git", "init", "--bare", str(remote))
    paths = []
    for name in ("a", "b"):
        path = tmp_path / name; run("git", "clone", str(remote), str(path)); run("git", "config", "user.email", f"{name}@example.test", cwd=path); run("git", "config", "user.name", name, cwd=path); paths.append(path)
    return paths


def test_two_isolated_clones_publish_fetch_and_converge(tmp_path):
    left, right = clone_pair(tmp_path)
    first, second = bundle("replica.a", event("replica.a", 1, "first", work="w1")), bundle("replica.b", event("replica.b", 1, "second", work="w2"))
    assert GitReplicaTransport(repository=left).publish_bundle(first)["outcome"] == "replica_transport_published"
    assert GitReplicaTransport(repository=right).publish_bundle(second)["outcome"] == "replica_transport_published"
    one, two = GitReplicaTransport(repository=left).converge(P), GitReplicaTransport(repository=right).converge(P)
    assert one["outcome"] == two["outcome"] == "replica_transport_converged"
    assert one["view"]["shared_view_digest"] == two["view"]["shared_view_digest"]
    assert one["view"]["flags"]["remote_mutation_performed"] is False


def test_duplicate_is_no_push_and_tampered_or_dirty_clone_holds(tmp_path):
    left, right = clone_pair(tmp_path)
    item = bundle("replica.a", event("replica.a", 1, "first", work="w1"))
    adapter = GitReplicaTransport(repository=left)
    assert adapter.publish_bundle(item)["mutation_count"] == 1
    before = run("git", "ls-remote", "origin", "refs/heads/agent-foundry-replica-v1", cwd=left).stdout
    assert adapter.publish_bundle(item)["outcome"] == "replica_transport_duplicate"
    assert run("git", "ls-remote", "origin", "refs/heads/agent-foundry-replica-v1", cwd=left).stdout == before
    (right / "untracked").write_text("x")
    assert GitReplicaTransport(repository=right).fetch_bundles(P)["outcome"] == "replica_transport_hold"


def test_missing_branch_is_offline_and_push_failure_holds_without_retry(tmp_path):
    left, right = clone_pair(tmp_path)
    assert GitReplicaTransport(repository=left).fetch_bundles(P)["outcome"] == "replica_transport_offline"
    first, second = bundle("replica.a", event("replica.a", 1, "first", work="w1")), bundle("replica.b", event("replica.b", 1, "second", work="w2"))
    assert GitReplicaTransport(repository=left).publish_bundle(first)["outcome"] == "replica_transport_published"
    adapter = GitReplicaTransport(repository=right)
    calls, original = [], adapter._git
    def one_failed_push(*args, **kwargs):
        calls.append(args)
        if args and args[0] == "push":
            raise GitReplicaTransportHold("hold_transport_unavailable")
        return original(*args, **kwargs)
    adapter._git = one_failed_push
    outcome = adapter.publish_bundle(second)
    assert outcome["outcome"] == "replica_transport_hold"
    assert sum(call[0] == "push" for call in calls) == 1
