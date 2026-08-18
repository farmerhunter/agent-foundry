from __future__ import annotations

import os
from pathlib import Path
import json
import sqlite3
import tempfile
import uuid
import jsonschema
import yaml

import bounded_collaboration_runtime_bridge as bridge
from test_bounded_collaboration_runtime_bridge import _fixture as _bridge_fixture, _request as _bridge_request
from bounded_collaboration_initializer import Owners, initialize
import local_collaboration_control_plane as control
import local_collaboration_scheduler as scheduler
from bounded_collaboration_native_topology_owner import NativeRoleTopologyOwner, TrustedRuntime
from codex_host_rolehub_adapter import ThreadMetadata
from local_collaboration_ledger import LocalCollaborationLedger


class FakeHost:
    def __init__(self, project_id: str): self.project_id = project_id; self.items = {}; self.calls = self.creates = self.names = self.reads = self.lists = 0
    def list_threads(self, cwd: str): self.calls += 1; self.lists += 1; return list(self.items.values())
    def create_thread(self, cwd: str):
        self.calls += 1; self.creates += 1; key = "n" + str(self.calls); self.items[key] = ThreadMetadata(key, cwd, "", self.project_id); return self.items[key]
    def set_thread_name(self, ident: str, title: str):
        self.calls += 1; self.names += 1; old = self.items[ident]; self.items[ident] = ThreadMetadata(ident, old.cwd, title, old.project_id); return self.items[ident]
    def read_thread(self, ident: str, include_turns=False): self.calls += 1; self.reads += 1; return self.items[ident]


def _request(project_id: str) -> dict:
    return {"project_id": project_id, "occurred_at": "2026-08-17T00:00:00Z", "timestamp_provenance": "explicit", "work": {"project_id": project_id, "work_id": "w", "issue": 548, "objective": "x", "stage": "implementation", "phase": "orch-04", "role": "Coordinator", "root_budget_tokens": 1, "remaining_budget_tokens": 1, "issue_anchor": {"issue": 548, "scope": "x", "risk": "low", "acceptance": "x", "durable_anchor": "issue:548", "human_gates": ["none"]}, "durable_anchors": ["issue:548"], "stop_conditions": ["x"]}, "execution_run": {"run_id": "r", "work_id": "w", "role": "Coordinator", "state": "active", "context": {"source_timestamp": "2026-08-17T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 1, "source": "x"}}}, "model": {"name": "x", "reasoning": "low"}}, "dispatch_claim": {"idempotency_key": "k", "work_id": "w", "role": "Coordinator", "decision_boundary": "x", "transition_semantics": "bounded", "durable_anchor": "issue:548"}, "requested_route": "isolated_execution"}


def _fixture():
    return _bridge_fixture()


def test_trusted_two_call_lifecycle_and_exact_retry() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        first = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert first["terminal_classification"] == "native_ready" and host.creates == 2 and host.names == 2 and host.calls > 6
        assert "permit" not in str(first).lower() and "n1" not in str(first)
        before = host.calls
        retry = bridge.trusted_initialize_fixture(root, selected, "key", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "native_ready" and host.calls > before and host.creates == 2 and host.names == 2
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
        context = {"project_id": binding["project_id"], "project_binding_ref": binding["project_binding_ref"], "project_binding_digest": binding["project_binding_digest"], "root_digest": binding["root_digest"], "scheduler_binding_digest": scheduler_binding["scheduler_binding_digest"], "scheduler_binding_ref": scheduler_binding["scheduler_binding_ref"], "work_root_ref": scheduler_binding["work_root_ref"], "scheduler_binding_revision": scheduler_binding["scheduler_binding_revision"], "onboarding_key": "guard", "topology_plan_digest": plan["topology_plan_digest"], "topology_preimage_digest": plan["topology_preimage_digest"], "mapping_digest": identity["mapping_digest"], "create_budget": {"Coordinator": 1, "DurableArchitect": 1}}
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


def test_final_store_symlink_holds_before_sqlite_or_host() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        external = Path(temp.name) / "outside.db"; store = root / project_id / "role-topology.db"; store.symlink_to(external)
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "link", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "partial_hold" and result["attention_reason"] == "project_identity_invalid"
        assert host.calls == 0 and not external.exists()
    finally: temp.cleanup()


def test_same_permit_cannot_bind_a_second_owner_or_project() -> None:
    first_temp, first_root, first_selected, first_id = _fixture(); second_temp, second_root, second_selected, second_id = _fixture()
    try:
        runtime = TrustedRuntime(); permit = runtime.issue_permit(host_digest="sha256:" + "2" * 64)
        first_host = FakeHost(first_id); first_owner = NativeRoleTopologyOwner(first_root, first_selected, first_host, runtime=runtime)
        assert bridge.trusted_initialize_fixture(first_root, first_selected, "first", topology_owner=first_owner, permit=permit)["terminal_classification"] == "native_ready"
        second_host = FakeHost(second_id); second_owner = NativeRoleTopologyOwner(second_root, second_selected, second_host, runtime=runtime)
        second = bridge.trusted_initialize_fixture(second_root, second_selected, "second", topology_owner=second_owner, permit=permit)
        assert second["terminal_classification"] == "partial_hold" and second["attention_reason"] == "authorization_unavailable"
        assert second_host.calls == 0 and not (second_root / second_id / "role-topology.db").exists()
    finally:
        first_temp.cleanup(); second_temp.cleanup()


def test_bound_owner_context_swap_cannot_retarget_same_root_project() -> None:
    temp, root, selected, first_id = _fixture()
    try:
        second_selected = Path(temp.name) / "second-project"; second_selected.mkdir(); os.chmod(second_selected, 0o700); second_selected = second_selected.resolve(); second_id = str(uuid.uuid4())
        ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=second_id); ledger.bind_project("path", str(second_selected)); ledger.bind_project("repo", "second"); ledger.close()
        control.apply_control_request(root, second_id, _bridge_request(second_id)); scheduler.apply_scheduler_request(root, second_id, {"project_id": second_id, "work_id": "work-bridge", "operation": "initialize", "occurred_at": "2026-08-17T00:00:01Z"})
        runtime = TrustedRuntime(); first_host = FakeHost(first_id); first_owner = NativeRoleTopologyOwner(root, selected, first_host, runtime=runtime)
        def make_context(project_root, owner, key):
            project = bridge.ProjectBindingOwner(root, project_root); sched = bridge.SchedulerBindingOwner(root); plan = initialize(Owners(project, sched, owner), onboarding_key=key, apply_authorized=False)["topology_plan"]
            binding = project.read_binding(); scheduler_binding = sched.read_binding(binding); identity, reason = owner._identity(binding); assert reason is None and identity is not None
            return plan, {"project_id": binding["project_id"], "project_binding_ref": binding["project_binding_ref"], "project_binding_digest": binding["project_binding_digest"], "root_digest": binding["root_digest"], "scheduler_binding_digest": scheduler_binding["scheduler_binding_digest"], "scheduler_binding_ref": scheduler_binding["scheduler_binding_ref"], "work_root_ref": scheduler_binding["work_root_ref"], "scheduler_binding_revision": scheduler_binding["scheduler_binding_revision"], "onboarding_key": key, "topology_plan_digest": plan["topology_plan_digest"], "topology_preimage_digest": plan["topology_preimage_digest"], "mapping_digest": identity["mapping_digest"], "create_budget": {"Coordinator": 1, "DurableArchitect": 1}}
        first_plan, first_context = make_context(selected, first_owner, "first")
        bound = first_owner.bind_permit(runtime.issue_permit(host_digest="sha256:" + "2" * 64), first_context); assert bound is not None
        second_host = FakeHost(second_id); second_owner = NativeRoleTopologyOwner(root, second_selected, second_host, runtime=runtime)
        second_plan, second_context = make_context(second_selected, second_owner, "second")
        bound.__dict__["_context"] = second_context
        assert bound.apply_topology(second_plan)["reason"] == "authorization_mismatch"
        assert second_host.calls == 0 and not (root / second_id / "role-topology.db").exists()
    finally: temp.cleanup()


def test_bound_owner_host_and_root_swap_holds_before_either_store_or_host() -> None:
    temp, root, selected, first_id = _fixture()
    try:
        second_selected = Path(temp.name) / "host-target"; second_selected.mkdir(); os.chmod(second_selected, 0o700); second_selected = second_selected.resolve(); second_id = str(uuid.uuid4())
        ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=second_id); ledger.bind_project("path", str(second_selected)); ledger.bind_project("repo", "second"); ledger.close()
        control.apply_control_request(root, second_id, _bridge_request(second_id)); scheduler.apply_scheduler_request(root, second_id, {"project_id": second_id, "work_id": "work-bridge", "operation": "initialize", "occurred_at": "2026-08-17T00:00:01Z"})
        runtime = TrustedRuntime(); first_host = FakeHost(first_id); owner = NativeRoleTopologyOwner(root, selected, first_host, runtime=runtime)
        project = bridge.ProjectBindingOwner(root, selected); sched = bridge.SchedulerBindingOwner(root); plan = initialize(Owners(project, sched, owner), onboarding_key="first", apply_authorized=False)["topology_plan"]
        binding = project.read_binding(); scheduler_binding = sched.read_binding(binding); identity, reason = owner._identity(binding); assert reason is None and identity is not None
        context = {"project_id": binding["project_id"], "project_binding_ref": binding["project_binding_ref"], "project_binding_digest": binding["project_binding_digest"], "root_digest": binding["root_digest"], "scheduler_binding_digest": scheduler_binding["scheduler_binding_digest"], "scheduler_binding_ref": scheduler_binding["scheduler_binding_ref"], "work_root_ref": scheduler_binding["work_root_ref"], "scheduler_binding_revision": scheduler_binding["scheduler_binding_revision"], "onboarding_key": "first", "topology_plan_digest": plan["topology_plan_digest"], "topology_preimage_digest": plan["topology_preimage_digest"], "mapping_digest": identity["mapping_digest"], "create_budget": {"Coordinator": 1, "DurableArchitect": 1}}
        bound = owner.bind_permit(runtime.issue_permit(host_digest="sha256:" + "2" * 64), context); assert bound is not None
        second_host = FakeHost(second_id); bound.__dict__["_project_root"] = second_selected; bound.__dict__["_host"] = second_host
        assert bound.apply_topology(plan)["reason"] == "authorization_mismatch"
        assert first_host.calls == 0 and second_host.calls == 0
        assert not (root / first_id / "role-topology.db").exists() and not (root / second_id / "role-topology.db").exists()
    finally: temp.cleanup()


def test_completed_retry_holds_on_deleted_or_replaced_host_identity() -> None:
    for replacement in (False, True):
        temp, root, selected, project_id = _fixture()
        try:
            host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
            assert bridge.trusted_initialize_fixture(root, selected, "done", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))["terminal_classification"] == "native_ready"
            if replacement:
                native_id = next(iter(host.items)); host.items[native_id] = ThreadMetadata(native_id, str(selected), "AF18 RoleHub", "foreign-project")
            else:
                host.items.clear()
            creates, names, before = host.creates, host.names, host.calls
            retry = bridge.trusted_initialize_fixture(root, selected, "done", topology_owner=owner, permit=object())
            assert retry["terminal_classification"] == "partial_hold" and host.calls > before
            assert host.creates == creates and host.names == names
        finally: temp.cleanup()


def test_completed_retry_uses_protected_direct_reads_not_list_inventory() -> None:
    for kind in ("duplicate", "list_error"):
        temp, root, selected, project_id = _fixture()
        try:
            host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
            assert bridge.trusted_initialize_fixture(root, selected, "done", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))["terminal_classification"] == "native_ready"
            if kind == "duplicate": host.items["duplicate"] = ThreadMetadata("duplicate", str(selected), "AF18 Coordinator", project_id)
            else: host.list_threads = lambda cwd: (_ for _ in ()).throw(RuntimeError("unavailable"))
            creates, names, before = host.creates, host.names, host.calls
            retry = bridge.trusted_initialize_fixture(root, selected, "done", topology_owner=owner, permit=object())
            assert retry["terminal_classification"] == "native_ready" and host.calls > before and host.creates == creates and host.names == names
        finally: temp.cleanup()


def test_fresh_success_does_not_require_post_write_list_visibility() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class DelayedListHost(FakeHost):
            def list_threads(self, cwd):
                self.calls += 1; self.lists += 1
                return [] if self.creates else list(self.items.values())
        host = DelayedListHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "delayed-list", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "native_ready"
        assert host.creates == 2 and host.names == 2 and host.lists == 2
        assert "native_id" not in json.dumps(result).lower() and "n1" not in str(result)
    finally: temp.cleanup()


def test_exact_final_inventory_reconciles_then_retries_without_native_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class InterruptedFinalRead(FakeHost):
            fail_final = True
            def read_thread(self, ident, include_turns=False):
                if self.fail_final and self.reads >= 2:
                    self.calls += 1; self.reads += 1
                    raise RuntimeError("final inventory unavailable")
                return super().read_thread(ident, include_turns)
        host = InterruptedFinalRead(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        first = bridge.trusted_initialize_fixture(root, selected, "reconcile", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert first["terminal_classification"] == "setup_incomplete" and host.creates == 2 and host.names == 2
        host.fail_final = False
        before = (host.creates, host.names)
        reconciled = bridge.trusted_initialize_fixture(root, selected, "reconcile", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert reconciled["terminal_classification"] == "native_ready" and (host.creates, host.names) == before
        refs = tuple(reconciled["initialization"]["operation_receipt_refs"])
        retry = bridge.trusted_initialize_fixture(root, selected, "reconcile", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "native_ready" and (host.creates, host.names) == before
        assert tuple(retry["initialization"]["operation_receipt_refs"]) == refs
    finally: temp.cleanup()


def test_final_inventory_mismatch_holds_before_new_native_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class InterruptedFinalRead(FakeHost):
            fail_final = True
            def read_thread(self, ident, include_turns=False):
                if self.fail_final and self.reads >= 2:
                    self.calls += 1; self.reads += 1
                    raise RuntimeError("final inventory unavailable")
                return super().read_thread(ident, include_turns)
        host = InterruptedFinalRead(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        assert bridge.trusted_initialize_fixture(root, selected, "mismatch", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))["terminal_classification"] == "setup_incomplete"
        host.fail_final = False
        native_id = next(iter(host.items))
        item = host.items[native_id]
        host.items[native_id] = ThreadMetadata(item.id, item.cwd, "wrong-title", item.project_id)
        before = (host.creates, host.names)
        held = bridge.trusted_initialize_fixture(root, selected, "mismatch", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert held["terminal_classification"] == "setup_incomplete" and (host.creates, host.names) == before
    finally: temp.cleanup()


def test_unmanaged_collision_ambiguity_foreign_and_list_failure_hold_pre_store() -> None:
    for kind in ("collision", "ambiguous", "foreign", "error"):
        temp, root, selected, project_id = _fixture()
        try:
            host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
            project = bridge.ProjectBindingOwner(root, selected); sched = bridge.SchedulerBindingOwner(root); plan = initialize(Owners(project, sched, owner), onboarding_key=kind, apply_authorized=False)["topology_plan"]
            binding = project.read_binding(); scheduler_binding = sched.read_binding(binding); identity, reason = owner._identity(binding); assert reason is None and identity is not None
            context = {"project_id": binding["project_id"], "project_binding_ref": binding["project_binding_ref"], "project_binding_digest": binding["project_binding_digest"], "root_digest": binding["root_digest"], "scheduler_binding_digest": scheduler_binding["scheduler_binding_digest"], "scheduler_binding_ref": scheduler_binding["scheduler_binding_ref"], "work_root_ref": scheduler_binding["work_root_ref"], "scheduler_binding_revision": scheduler_binding["scheduler_binding_revision"], "onboarding_key": kind, "topology_plan_digest": plan["topology_plan_digest"], "topology_preimage_digest": plan["topology_preimage_digest"], "mapping_digest": identity["mapping_digest"], "create_budget": {"Coordinator": 1, "DurableArchitect": 1}}
            bound = owner.bind_permit(runtime.issue_permit(host_digest="sha256:" + "2" * 64), context); assert bound is not None
            if kind == "collision": host.items["u"] = ThreadMetadata("u", str(selected), "AF18 Coordinator", project_id)
            elif kind == "ambiguous":
                host.items["u1"] = ThreadMetadata("u1", str(selected), "AF18 Coordinator", project_id); host.items["u2"] = ThreadMetadata("u2", str(selected), "AF18 Coordinator", project_id)
            elif kind == "foreign": host.items["u"] = ThreadMetadata("u", str(selected), "irrelevant", "foreign")
            else:
                host.list_threads = lambda cwd: (_ for _ in ()).throw(RuntimeError("unavailable"))
            held = bound.apply_topology(plan)
            assert held["state"] == "held" and host.creates == 0 and host.names == 0 and not (root / project_id / "role-topology.db").exists()
        finally: temp.cleanup()


def test_public_schema_accepts_actual_ready_and_rejects_private_held_fields() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        assert bridge.trusted_initialize_fixture(root, selected, "schema", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))["terminal_classification"] == "native_ready"
        binding = bridge.ProjectBindingOwner(root, selected).read_binding()
        schema = yaml.safe_load((Path(__file__).resolve().parents[1] / "schemas" / "bounded-collaboration-native-topology-owner.schema.yaml").read_text())
        jsonschema.Draft202012Validator(schema).validate(owner.read_topology(binding)); jsonschema.Draft202012Validator(schema).validate(owner.read_completion("schema", binding))
        assert list(jsonschema.Draft202012Validator(schema).iter_errors({"state": "held", "reason": "x", "rolehub_ref": "leak"}))
    finally: temp.cleanup()


def test_unrelated_rolehub_title_is_ignored_by_two_role_onboarding() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        host = FakeHost(project_id)
        host.items["unmanaged-rolehub"] = ThreadMetadata("unmanaged-rolehub", str(selected), "AF18 RoleHub", project_id)
        runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "ignore-rolehub", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "native_ready"
        assert host.creates == 2 and host.names == 2
        assert "rolehub_ref" not in json.dumps(result).lower()
        assert host.items["unmanaged-rolehub"].name == "AF18 RoleHub"
    finally: temp.cleanup()


def test_legacy_three_role_store_holds_before_permit_or_host() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        store = root / project_id / "role-topology.db"
        con = sqlite3.connect(store)
        con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA synchronous=FULL")
        con.execute("CREATE TABLE topology (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        con.execute("INSERT INTO topology(k,v) VALUES('schema_version',?)", ("bounded-collaboration-native-topology-owner-v1",))
        con.execute("INSERT INTO topology(k,v) VALUES('mapping','legacy')")
        con.execute("INSERT INTO topology(k,v) VALUES('completion',?)", ('{"native_ids":{"RoleHub":"legacy-r","Coordinator":"legacy-c","Architect":"legacy-a"}}',))
        con.commit(); con.close(); os.chmod(store, 0o600)
        host = FakeHost(project_id); runtime = TrustedRuntime(); permit = runtime.issue_permit(host_digest="sha256:" + "2" * 64)
        owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "legacy", topology_owner=owner, permit=permit)
        assert result["terminal_classification"] == "partial_hold"
        assert result["attention_reason"] == "legacy_topology_migration_required"
        assert host.calls == 0 and permit._binding is None
    finally: temp.cleanup()


def test_bridge_surfaces_wrong_project_create_as_retained_partial_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class WrongProject(FakeHost):
            def create_thread(self, cwd):
                item = super().create_thread(cwd); self.items[item.id] = ThreadMetadata(item.id, item.cwd, item.name, "foreign-project"); return self.items[item.id]
        host = WrongProject(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "wrong-project", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert result["initialization"]["operation_receipt_refs"] and "native" not in str(result).lower() and host.creates == 1 and host.names == 0
        before = (host.creates, host.names); retry = bridge.trusted_initialize_fixture(root, selected, "wrong-project", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "partial_hold" and (host.creates, host.names) == before
    finally: temp.cleanup()


def test_bridge_surfaces_invalid_post_name_readback_as_retained_partial_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class InvalidReadback(FakeHost):
            def read_thread(self, ident, include_turns=False):
                item = super().read_thread(ident, include_turns); return ThreadMetadata(item.id, item.cwd, "wrong-name", item.project_id)
        host = InvalidReadback(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "invalid-read", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert result["initialization"]["operation_receipt_refs"] and "native" not in str(result).lower() and host.creates == 1 and host.names == 1
        before = (host.creates, host.names); retry = bridge.trusted_initialize_fixture(root, selected, "invalid-read", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "partial_hold" and (host.creates, host.names) == before
    finally: temp.cleanup()


def test_second_create_exception_retains_first_role_mutation_truthfully() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class SecondCreateFails(FakeHost):
            def create_thread(self, cwd):
                if self.creates >= 1: raise RuntimeError("second create unavailable")
                return super().create_thread(cwd)
        host = SecondCreateFails(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "second-create", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert result["initialization"]["operation_receipt_refs"] and host.creates == 1 and host.names == 1
        before = (host.calls, host.creates, host.names); retry = bridge.trusted_initialize_fixture(root, selected, "second-create", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "partial_hold" and (host.calls, host.creates, host.names) == before
    finally: temp.cleanup()


def test_first_create_exception_has_no_mutation_claim() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class FirstCreateFails(FakeHost):
            def create_thread(self, cwd): raise RuntimeError("unavailable before create")
        host = FirstCreateFails(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "first-create", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["mutation_performed"] is False and host.creates == 0 and host.names == 0
    finally: temp.cleanup()


def test_malformed_create_metadata_retains_unknown_host_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        class MalformedCreate(FakeHost):
            def create_thread(self, cwd):
                super().create_thread(cwd); return {"id": "untrusted"}
        host = MalformedCreate(project_id); runtime = TrustedRuntime(); owner = NativeRoleTopologyOwner(root, selected, host, runtime=runtime)
        result = bridge.trusted_initialize_fixture(root, selected, "malformed-create", topology_owner=owner, permit=runtime.issue_permit(host_digest="sha256:" + "2" * 64))
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert result["initialization"]["operation_receipt_refs"] and host.creates == 1 and host.names == 0 and "untrusted" not in str(result)
        before = (host.calls, host.creates, host.names); retry = bridge.trusted_initialize_fixture(root, selected, "malformed-create", topology_owner=owner, permit=object())
        assert retry["terminal_classification"] == "partial_hold" and (host.calls, host.creates, host.names) == before
    finally: temp.cleanup()


if __name__ == "__main__":
    test_trusted_two_call_lifecycle_and_exact_retry(); test_bad_or_replayed_permit_holds_before_store_or_host(); test_one_shot_guard_is_consumed_before_second_host_attempt(); test_noncanonical_identity_holds_without_host_or_store(); test_final_store_symlink_holds_before_sqlite_or_host(); test_same_permit_cannot_bind_a_second_owner_or_project(); test_bound_owner_context_swap_cannot_retarget_same_root_project(); test_bound_owner_host_and_root_swap_holds_before_either_store_or_host(); test_completed_retry_holds_on_deleted_or_replaced_host_identity(); test_completed_retry_uses_protected_direct_reads_not_list_inventory(); test_fresh_success_does_not_require_post_write_list_visibility(); test_exact_final_inventory_reconciles_then_retries_without_native_mutation(); test_final_inventory_mismatch_holds_before_new_native_mutation(); test_unmanaged_collision_ambiguity_foreign_and_list_failure_hold_pre_store(); test_public_schema_accepts_actual_ready_and_rejects_private_held_fields(); test_unrelated_rolehub_title_is_ignored_by_two_role_onboarding(); test_legacy_three_role_store_holds_before_permit_or_host(); test_bridge_surfaces_wrong_project_create_as_retained_partial_mutation(); test_bridge_surfaces_invalid_post_name_readback_as_retained_partial_mutation(); test_second_create_exception_retains_first_role_mutation_truthfully(); test_first_create_exception_has_no_mutation_claim(); test_malformed_create_metadata_retains_unknown_host_mutation(); print("ok")
