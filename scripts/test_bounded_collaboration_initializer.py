#!/usr/bin/env python3
"""Fixture-only regressions for owner-composed onboarding completion."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load((ROOT / "schemas" / "bounded-collaboration-initialization.schema.yaml").read_text(encoding="utf-8"))
spec = importlib.util.spec_from_file_location("initializer", ROOT / "scripts" / "bounded_collaboration_initializer.py")
initializer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = initializer
spec.loader.exec_module(initializer)


class Project:
    def __init__(self): self.calls = 0; self.state = self.value()
    @staticmethod
    def value(): return {"state": "bound", "project_binding_ref": "project:opaque", "project_binding_digest": "sha256:project", "project_id": "opaque-project", "repository_digest": "sha256:repo", "root_digest": "sha256:root"}
    def read_binding(self): self.calls += 1; return dict(self.state)


class Scheduler:
    def __init__(self, state="bound"): self.calls = 0; self.state = state
    def read_binding(self, project):
        self.calls += 1
        if self.state != "bound": return {"state": self.state}
        return {"state": "bound", "scheduler_binding_ref": "scheduler:opaque", "work_root_ref": "work:opaque", "scheduler_binding_revision": "rev-1", "scheduler_binding_digest": "sha256:scheduler", "project_binding_digest": project["project_binding_digest"]}


class Topology:
    def __init__(self, project, state="ready"):
        self.calls = 0; self.apply_calls = 0; self.completion_calls = 0; self.project = project; self.state = state; self.post_apply_error = False; self.completions = {}
    def read_topology(self, project):
        self.calls += 1
        if self.post_apply_error: raise RuntimeError("unshown")
        if self.state == "missing": return {"state": "missing"}
        if self.state == "duplicate": return {"state": "ready", "rolehub_ref": "hub:opaque", "coordinator_ref": "role:c", "architect_ref": "role:a", "topology_readback_digest": "sha256:topology", "project_binding_digest": project["project_binding_digest"], "coordinator_count": 2, "architect_count": 1}
        foreign = getattr(self, "foreign_after_apply", False)
        value = {"state": "ready", "rolehub_ref": "hub:foreign" if foreign else "hub:opaque", "coordinator_ref": "role:foreign-c" if foreign else "role:c", "architect_ref": "role:foreign-a" if foreign else "role:a", "topology_readback_digest": "sha256:foreign-topology" if foreign else "sha256:topology", "project_binding_digest": project["project_binding_digest"], "coordinator_count": 1, "architect_count": 1}
        if hasattr(self, "binding"):
            value["topology_apply_binding_ref"] = self.binding["topology_apply_binding_ref"]
            value["topology_apply_binding_digest"] = self.binding["topology_apply_binding_digest"]
            value["topology_apply_binding"] = dict(self.binding)
        return value
    def apply_topology(self, plan):
        self.apply_calls += 1
        assert plan["requested_roles"] == ("Coordinator", "Architect")
        self.state = "ready"
        refs = ["receipt:coordinator", "receipt:architect"]
        self.binding = {"topology_apply_binding_ref": "binding:opaque", "onboarding_key": plan["onboarding_key"], "project_binding_digest": plan["project_binding_digest"], "scheduler_binding_digest": plan["scheduler_binding_digest"], "requested_roles": list(plan["requested_roles"]), "topology_plan_digest": plan["topology_plan_digest"], "operation_receipt_refs": refs, "operation_receipt_refs_digest": initializer._digest(refs), "rolehub_ref": "hub:opaque", "coordinator_ref": "role:c", "architect_ref": "role:a", "topology_readback_digest": "sha256:topology"}
        self.binding["topology_apply_binding_digest"] = initializer._binding_digest(self.binding)
        self.completions[plan["onboarding_key"]] = {"state": "ready", "completion_receipt_ref": "completion:opaque", **initializer._completion_identity(plan["onboarding_key"], {"project_binding_ref": plan["project_binding_ref"], "project_binding_digest": plan["project_binding_digest"]}, {"scheduler_binding_ref": "scheduler:opaque", "work_root_ref": "work:opaque", "scheduler_binding_revision": "rev-1", "scheduler_binding_digest": plan["scheduler_binding_digest"]}, {"rolehub_ref": "hub:opaque", "coordinator_ref": "role:c", "architect_ref": "role:a", "topology_readback_digest": "sha256:topology"}, self.binding)}
        return {"state": "applied", "mutation_performed": getattr(self, "apply_mutation", True), "operation_receipt_refs": refs, "topology_apply_binding": dict(self.binding), "topology_plan_digest": plan["topology_plan_digest"]}
    def read_completion(self, onboarding_key, project):
        self.completion_calls += 1
        return dict(self.completions.get(onboarding_key, {"state": "absent"}))


def owners(scheduler_state="bound", topology_state="ready"):
    project = Project(); scheduler = Scheduler(scheduler_state); topology = Topology(project, topology_state)
    return initializer.Owners(project, scheduler, topology), project, scheduler, topology


def check(name, condition, value):
    if not condition: raise AssertionError(f"{name}: {value}")
    print(f"{name}: ok")


def schema(name, value):
    wire_value = json.loads(json.dumps(value, sort_keys=True))
    jsonschema.Draft202012Validator(SCHEMA).validate(wire_value)
    print(f"schema-{name}: ok")


def main():
    own, project, scheduler, topology = owners()
    success = initializer.initialize(own, onboarding_key="onboard-1")
    check("valid-composite-ready", success["completion_state"] == "native_ready" and success["mutation_performed"] is False and topology.apply_calls == 0, success)
    check("immutable-json-safe", isinstance(success["operation_receipt_refs"], tuple) and json.loads(json.dumps(success))["completion_state"] == "native_ready", success)
    try: success["completion_state"] = "forged"; raise AssertionError("receipt mutation accepted")
    except TypeError: print("immutable-receipt: ok")
    schema("ready", success)

    own, _, scheduler, topology = owners("missing", "missing")
    missing_scheduler = initializer.initialize(own, onboarding_key="onboard-2", apply_authorized=True)
    check("549-no-scheduler-work-root", missing_scheduler["completion_state"] == "repo_contract_only" and topology.apply_calls == 0 and topology.calls == 0, missing_scheduler)
    schema("scheduler-hold", missing_scheduler)

    own, _, scheduler, topology = owners("bound", "missing")
    repo_only = initializer.initialize(own, onboarding_key="onboard-3")
    check("548-absent-role-not-ready", repo_only["completion_state"] == "topology_plan_ready" and topology.apply_calls == 0, repo_only)
    schema("plan", repo_only)
    applied = initializer.initialize(own, onboarding_key="onboard-3", apply_authorized=True)
    check("ordered-apply-and-bound-readback", applied["completion_state"] == "native_ready" and applied["mutation_performed"] and applied["topology_apply_binding_ref"] == "binding:opaque" and topology.apply_calls == 1, applied)
    retried = initializer.initialize(own, onboarding_key="onboard-3", apply_authorized=True)
    check("exact-retry-no-topology-mutation", retried["completion_state"] == "native_ready" and retried["mutation_performed"] is False and topology.apply_calls == 1 and topology.binding["topology_apply_binding_ref"] == "binding:opaque", retried)

    topology.foreign_after_apply = True
    topology.binding["rolehub_ref"] = "hub:foreign"; topology.binding["coordinator_ref"] = "role:foreign-c"; topology.binding["architect_ref"] = "role:foreign-a"; topology.binding["topology_readback_digest"] = "sha256:foreign-topology"; topology.binding["topology_apply_binding_digest"] = initializer._binding_digest(topology.binding)
    foreign_retry = initializer.initialize(own, onboarding_key="onboard-3", apply_authorized=True)
    check("same-key-retry-rereads-self-consistent-foreign-topology-holds", foreign_retry["completion_state"] == "partial_hold" and foreign_retry["attention_reason"] == "original_completion_identity_drift" and topology.apply_calls == 1 and topology.completion_calls >= 2, foreign_retry)

    own, project, scheduler, topology = owners("bound", "missing")
    old_apply = topology.apply_topology
    def apply_then_replace(plan):
        value = old_apply(plan)
        topology.foreign_after_apply = True
        return value
    topology.apply_topology = apply_then_replace
    foreign = initializer.initialize(own, onboarding_key="onboard-foreign", apply_authorized=True)
    check("same-binding-foreign-final-topology-replacement-holds", foreign["completion_state"] == "setup_incomplete" and foreign["attention_reason"] == "topology_apply_readback_identity_mismatch", foreign)

    own, project, scheduler, topology = owners("bound", "missing")
    topology.apply_mutation = False
    reused = initializer.initialize(own, onboarding_key="onboard-reuse", apply_authorized=True)
    check("zero-mutation-apply-still-validates-binding", reused["completion_state"] == "native_ready" and reused["mutation_performed"] is False and "topology_apply_binding_digest" in reused, reused)

    own, project, scheduler, topology = owners("bound", "missing")
    old_apply = topology.apply_topology
    def apply_forged_binding(plan):
        value = old_apply(plan)
        value["topology_apply_binding"]["topology_apply_binding_digest"] = "sha256:forged"
        return value
    topology.apply_topology = apply_forged_binding
    forged_binding = initializer.initialize(own, onboarding_key="onboard-forged-binding", apply_authorized=True)
    check("forged-apply-binding-holds", forged_binding["completion_state"] == "setup_incomplete" and forged_binding["attention_reason"] == "topology_apply_readback_binding_forged", forged_binding)

    own, project, scheduler, topology = owners("bound", "missing")
    old_apply = topology.apply_topology
    def apply_without_binding(plan):
        value = old_apply(plan)
        value.pop("topology_apply_binding")
        return value
    topology.apply_topology = apply_without_binding
    absent_binding = initializer.initialize(own, onboarding_key="onboard-absent-binding", apply_authorized=True)
    check("absent-apply-binding-holds", absent_binding["completion_state"] == "setup_incomplete" and absent_binding["attention_reason"] == "topology_apply_incomplete", absent_binding)

    own, project, scheduler, topology = owners("bound", "missing")
    old_apply = topology.apply_topology
    def apply_mutation_without_receipt(plan):
        value = old_apply(plan)
        value["operation_receipt_refs"] = []
        return value
    topology.apply_topology = apply_mutation_without_receipt
    missing_receipt = initializer.initialize(own, onboarding_key="onboard-missing-receipt", apply_authorized=True)
    check("mutation-true-without-receipt-holds", missing_receipt["completion_state"] == "setup_incomplete" and missing_receipt["attention_reason"] == "topology_apply_incomplete", missing_receipt)

    own, _, scheduler, topology = owners("bound", "duplicate")
    duplicate = initializer.initialize(own, onboarding_key="onboard-4", apply_authorized=True)
    check("duplicate-topology-holds-preapply", duplicate["completion_state"] == "partial_hold" and topology.apply_calls == 0, duplicate)

    own, project, scheduler, topology = owners("bound", "missing")
    forged = initializer.initialize(own, onboarding_key="onboard-5", apply_authorized=True, caller_claims={"scheduler_binding_digest": "sha256:forged", "completion_receipt": "forged"})
    check("forged-caller-claims-hold-after-owner-reads", forged["completion_state"] == "partial_hold" and project.calls == scheduler.calls == topology.calls == 1 and topology.apply_calls == 0, forged)

    own, project, scheduler, topology = owners("bound", "missing")
    original = scheduler.read_binding
    def drift(binding):
        value = original(binding)
        if scheduler.calls > 1: value["scheduler_binding_revision"] = "rev-2"
        return value
    scheduler.read_binding = drift
    stale = initializer.initialize(own, onboarding_key="onboard-6", apply_authorized=True)
    check("postcommit-scheduler-drift-setup-incomplete", stale["completion_state"] == "setup_incomplete" and stale["mutation_performed"] is True, stale)

    own, project, scheduler, topology = owners("bound", "missing")
    topology.post_apply_error = False
    old_apply = topology.apply_topology
    def apply_then_unreadable(plan):
        result = old_apply(plan); topology.post_apply_error = True; return result
    topology.apply_topology = apply_then_unreadable
    partial = initializer.initialize(own, onboarding_key="onboard-7", apply_authorized=True)
    check("postcommit-readback-unavailable", partial["completion_state"] == "setup_incomplete" and partial["attention_reason"] == "post_commit_readback_unavailable", partial)

    own, project, scheduler, topology = owners()
    project.state["path"] = "/private/secret"
    privacy = initializer.initialize(own, onboarding_key="onboard-8")
    check("privacy-hold-before-scheduler-topology", privacy["completion_state"] == "partial_hold" and scheduler.calls == topology.calls == 0, privacy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
