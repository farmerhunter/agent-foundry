from __future__ import annotations

import os
from pathlib import Path
import tempfile
import uuid

import bounded_collaboration_runtime_bridge as bridge
from test_bounded_collaboration_runtime_bridge import _fixture as _bridge_fixture
from bounded_collaboration_initializer import Owners, initialize
import local_collaboration_control_plane as control
import local_collaboration_scheduler as scheduler
from bounded_collaboration_native_topology_owner import NativeRoleTopologyOwner, TrustedRuntime
from codex_host_rolehub_adapter import ThreadMetadata
from local_collaboration_ledger import LocalCollaborationLedger


class FakeHost:
    def __init__(self, project_id: str): self.project_id = project_id; self.items = {}; self.calls = 0
    def create_thread(self, cwd: str):
        self.calls += 1; key = "n" + str(self.calls); self.items[key] = ThreadMetadata(key, cwd, "", self.project_id); return self.items[key]
    def set_thread_name(self, ident: str, title: str):
        self.calls += 1; old = self.items[ident]; self.items[ident] = ThreadMetadata(ident, old.cwd, title, old.project_id); return self.items[ident]
    def read_thread(self, ident: str, include_turns=False): self.calls += 1; return self.items[ident]


def _request(project_id: str) -> dict:
    return {"project_id": project_id, "occurred_at": "2026-08-17T00:00:00Z", "timestamp_provenance": "explicit", "work": {"project_id": project_id, "work_id": "w", "issue": 548, "objective": "x", "stage": "implementation", "phase": "orch-04", "role": "Coordinator", "root_budget_tokens": 1, "remaining_budget_tokens": 1, "issue_anchor": {"issue": 548, "scope": "x", "risk": "low", "acceptance": "x", "durable_anchor": "issue:548", "human_gates": ["none"]}, "durable_anchors": ["issue:548"], "stop_conditions": ["x"]}, "execution_run": {"run_id": "r", "work_id": "w", "role": "Coordinator", "state": "active", "context": {"source_timestamp": "2026-08-17T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 1, "source": "x"}}}, "model": {"name": "x", "reasoning": "low"}}, "dispatch_claim": {"idempotency_key": "k", "work_id": "w", "role": "Coordinator", "decision_boundary": "x", "transition_semantics": "bounded", "durable_anchor": "issue:548"}, "requested_route": "isolated_execution"}


def _fixture():
    return _bridge_fixture()


def test_trusted_two_call_lifecycle_and_exact_retry() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        first = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert first["terminal_classification"] == "native_ready" and host.calls == 9
        assert "permit" not in str(first).lower() and "n1" not in str(first)
        retry = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "native_ready" and host.calls == 9
    finally: temp.cleanup()


def test_bad_or_replayed_permit_holds_before_store_or_host() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        bad = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit={"runtime_digest": runtime.runtime_digest})
        assert bad["terminal_classification"] == "partial_hold" and host.calls == 0
        permit = runtime.issue_permit(host_digest="sha256:" + "2" * 64, expires_at=0)
        expired = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit=permit)
        assert expired["terminal_classification"] == "partial_hold" and host.calls == 0
    finally: temp.cleanup()


def test_one_shot_guard_is_consumed_before_second_host_attempt() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        project = bridge.ProjectBindingOwner(root, selected); scheduler_owner = bridge.SchedulerBindingOwner(root)
        plan = initialize(Owners(project, scheduler_owner, owner), onboarding_key="guard", apply_authorized=False)["topology_plan"]
        binding = project.read_binding(); scheduler_binding = scheduler_owner.read_binding(binding); identity, reason = owner._identity(binding)
        assert reason is None and identity is not None
        context = {"project_id": binding["project_id"], "project_binding_ref": binding["project_binding_ref"], "project_binding_digest": binding["project_binding_digest"], "root_digest": binding["root_digest"], "scheduler_binding_digest": scheduler_binding["scheduler_binding_digest"], "scheduler_binding_ref": scheduler_binding["scheduler_binding_ref"], "work_root_ref": scheduler_binding["work_root_ref"], "scheduler_binding_revision": scheduler_binding["scheduler_binding_revision"], "onboarding_key": "guard", "topology_plan_digest": plan["topology_plan_digest"], "topology_preimage_digest": plan["topology_preimage_digest"], "mapping_digest": identity["mapping_digest"], "create_budget": {"RoleHub": 1, "Coordinator": 1, "DurableArchitect": 1}}
        bound = owner.bind_permit(runtime.issue_permit(host_digest="sha256:" + "2" * 64), context); assert bound is not None
        assert bound.apply_topology(plan)["state"] == "applied"; calls = host.calls
        assert bound.apply_topology(plan)["reason"] == "authorization_unavailable" and host.calls == calls
    finally: temp.cleanup()


def test_noncanonical_identity_holds_without_host_or_store() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); owner = NativeRoleTopologyOwner(root, selected, host)
        assert owner.read_topology({"project_id": project_id.upper(), "project_binding_digest": "sha256:" + "1" * 64, "root_digest": "sha256:" + "2" * 64})["state"] == "held"
        assert host.calls == 0 and not (root / project_id / "role-topology.db").exists()
    finally: temp.cleanup()


if __name__ == "__main__":
    test_trusted_two_call_lifecycle_and_exact_retry(); test_bad_or_replayed_permit_holds_before_store_or_host(); test_one_shot_guard_is_consumed_before_second_host_attempt(); test_noncanonical_identity_holds_without_host_or_store(); print("ok")
