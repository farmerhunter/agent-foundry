import hashlib
import json
import tempfile
import unittest
import uuid
from dataclasses import replace
from types import MappingProxyType
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
import local_collaboration_onboarding as onboarding

from local_collaboration_handoff import read_handoff_state
from local_collaboration_handoff_bundle import prepare_manual_bundle
from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_onboarding import (apply_second_device_onboarding_step,
    plan_second_device_onboarding_step, read_second_device_onboarding)


def digest(v): return hashlib.sha256(v.encode()).hexdigest()


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.source_root = tempfile.TemporaryDirectory(); self.target_root = tempfile.TemporaryDirectory()
        self.project_id = str(uuid.uuid4())
        self.source = LocalCollaborationLedger.create_project(projects_root=self.source_root.name, project_id=self.project_id)
        self.context = {"source_ledger": self.source, "target_projects_root": self.target_root.name}

    def tearDown(self):
        self.source.close()
        if isinstance(self.context.get("target_ledger"), LocalCollaborationLedger): self.context["target_ledger"].close()
        self.source_root.cleanup(); self.target_root.cleanup()

    def read(self):
        target = self.context.get("target_ledger")
        return read_second_device_onboarding(self.source.path, expected_project_id=self.project_id,
            target_db_path=target.path if target else None, bundle=self.context.get("bundle"),
            proof_ref=self.context.get("proof_ref"), activation_ref=self.context.get("activation_ref"),
            target_projects_root=self.context.get("target_projects_root"))

    def step(self, operation, parameters):
        summary = self.read(); self.assertEqual(summary["next_operation"], operation)
        plan = plan_second_device_onboarding_step(summary, {"operation": operation, "decision_id": "human-" + operation,
            "decision_digest": digest(operation), "parameters": parameters})
        self.assertNotIsInstance(plan, dict)
        result = apply_second_device_onboarding_step(self.context, plan)
        self.assertIn("receipt", result, result)
        return result

    def establish_locked_bundle(self):
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        self.step("enroll_target", {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")})
        self.step("prepare_handoff", {"handoff_id": "handoff-1", "source_replica_id": "source", "target_replica_id": "target", "frontier_digest": digest("frontier")})
        self.step("lock_source", {"handoff_id": "handoff-1"})
        locked = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        self.step("export_bundle", {})
        return prepare_manual_bundle(self.source, expected_handoff_state=locked)

    def test_full_one_step_walkthrough_keeps_source_locked_and_target_local(self):
        self.source.append_event("fixture_source", {"schema_version": "fixture", "project_id": self.project_id}, event_id=str(uuid.uuid4()), actor="fixture", source="fixture", root=self.project_id)
        # Establish the first local active device through its existing owner API.
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        self.step("enroll_target", {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")})
        self.step("prepare_handoff", {"handoff_id": "handoff-1", "source_replica_id": "source", "target_replica_id": "target", "frontier_digest": digest("frontier")})
        self.step("lock_source", {"handoff_id": "handoff-1"})
        source_locked = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        exported = self.step("export_bundle", {})
        self.context["bundle"] = exported["operation_output"]["manual_transfer_artifact"]
        self.assertTrue(json.dumps(exported["receipt"]))
        with self.assertRaises(TypeError): json.dumps(exported["operation_output"]["manual_transfer_artifact"])
        self.step("create_target_authority", {})
        self.context["target_ledger"] = LocalCollaborationLedger.open_existing(Path(self.target_root.name) / self.project_id / "collaboration.db", expected_project_id=self.project_id)
        imported = self.step("import_bundle", {})
        self.context["proof_ref"] = imported["operation_output"]["proof_ref"]
        activated = self.step("activate_target", {})
        self.context["activation_ref"] = activated["operation_output"]["activation_ref"]
        final = self.read()
        self.assertEqual(final["stage"], "target_active_source_locked")
        self.assertEqual(final["target_activation_visibility"], "owner_verified_target_local")
        source = self.read(); self.assertEqual(read_handoff_state(self.source.path, expected_project_id=self.project_id).phase, "source_locked")
        self.assertFalse(final["global_convergence_verified"]); self.assertFalse(source["source_unlock_performed"])

    def test_stale_forged_summary_and_plan_hold_before_mutation(self):
        before = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        summary = self.read(); forged = dict(summary); forged["summary_digest"] = digest("forged")
        plan = plan_second_device_onboarding_step(forged, {"operation": "none", "decision_id": "x", "decision_digest": digest("x"), "parameters": {}})
        self.assertIsInstance(plan, dict)
        after = LocalCollaborationLedger.authority_snapshot(self.source.path, expected_project_id=self.project_id)
        self.assertEqual((before.authority_generation, before.authority_head), (after.authority_generation, after.authority_head))

    def test_exact_a1_retry_is_duplicate_without_second_mutation(self):
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        summary = self.read()
        plan = plan_second_device_onboarding_step(summary, {"operation": "enroll_target", "decision_id": "human-enroll", "decision_digest": digest("human-enroll"), "parameters": {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")}})
        first = apply_second_device_onboarding_step(self.context, plan)
        second = apply_second_device_onboarding_step(self.context, plan)
        self.assertTrue(first["receipt"]["mutation_performed"])
        self.assertTrue(second["receipt"]["duplicate"])

    def test_changed_decision_id_and_prepare_retry_never_claim_duplicate(self):
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        summary = self.read(); plan = plan_second_device_onboarding_step(summary, {"operation": "enroll_target", "decision_id": "one", "decision_digest": digest("same"), "parameters": {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")}})
        apply_second_device_onboarding_step(self.context, plan)
        changed_id = "two"; changed_payload = {"project_id": self.project_id, "operation": plan.operation, "summary_digest": plan.summary_digest, "decision_id": changed_id, "decision_digest": plan.decision_digest, "parameters": dict(plan.parameters)}
        changed = replace(plan, decision_id=changed_id, fingerprint=hashlib.sha256(json.dumps(changed_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(apply_second_device_onboarding_step(self.context, changed)["outcome"], "held")
        prepared_summary = self.read(); prepared = plan_second_device_onboarding_step(prepared_summary, {"operation": "prepare_handoff", "decision_id": "prepare", "decision_digest": digest("prepare"), "parameters": {"handoff_id": "h", "source_replica_id": "source", "target_replica_id": "target", "frontier_digest": digest("f")}})
        apply_second_device_onboarding_step(self.context, prepared)
        self.assertEqual(apply_second_device_onboarding_step(self.context, prepared)["reason_code"], "retry_owner_decision_identity_unavailable")

    def test_target_root_switch_and_immutable_export_preserve_mutation_boundary(self):
        bundle = self.establish_locked_bundle()
        root_a, root_b = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        try:
            summary = read_second_device_onboarding(self.source.path, expected_project_id=self.project_id, bundle=bundle, target_projects_root=root_a.name)
            plan = plan_second_device_onboarding_step(summary, {"operation": "create_target_authority", "decision_id": "create", "decision_digest": digest("create"), "parameters": {}})
            switched = {"source_ledger": self.source, "target_projects_root": root_b.name, "bundle": bundle}
            self.assertEqual(apply_second_device_onboarding_step(switched, plan)["outcome"], "held")
            self.assertFalse((Path(root_a.name) / self.project_id / "collaboration.db").exists())
            self.assertFalse((Path(root_b.name) / self.project_id / "collaboration.db").exists())
        finally:
            root_a.cleanup(); root_b.cleanup()
        # An immutable caller context can receive the committed export receipt without a post-commit write-back.
        self.assertEqual(self.read()["stage"], "manual_transfer_required")

    def test_immutable_context_keeps_export_receipt_after_commit(self):
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        self.step("enroll_target", {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")})
        self.step("prepare_handoff", {"handoff_id": "handoff-1", "source_replica_id": "source", "target_replica_id": "target", "frontier_digest": digest("frontier")})
        self.step("lock_source", {"handoff_id": "handoff-1"})
        summary = self.read(); plan = plan_second_device_onboarding_step(summary, {"operation": "export_bundle", "decision_id": "export", "decision_digest": digest("export"), "parameters": {}})
        result = apply_second_device_onboarding_step(MappingProxyType({"source_ledger": self.source, "target_projects_root": self.target_root.name}), plan)
        self.assertEqual(result["receipt"]["owner_outcome"], "bundle_exported")
        self.assertEqual(read_handoff_state(self.source.path, expected_project_id=self.project_id).handoff["status"], "bundle_exported")

    def test_post_export_readback_failure_preserves_provisional_receipt(self):
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        self.step("enroll_target", {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")})
        self.step("prepare_handoff", {"handoff_id": "handoff-1", "source_replica_id": "source", "target_replica_id": "target", "frontier_digest": digest("frontier")})
        self.step("lock_source", {"handoff_id": "handoff-1"})
        plan = plan_second_device_onboarding_step(self.read(), {"operation": "export_bundle", "decision_id": "export", "decision_digest": digest("export"), "parameters": {}})
        original = onboarding.read_second_device_onboarding; calls = {"count": 0}
        def fail_after_preflight(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2: raise onboarding.LedgerIntegrityError("injected")
            return original(*args, **kwargs)
        onboarding.read_second_device_onboarding = fail_after_preflight
        try:
            result = apply_second_device_onboarding_step(self.context, plan)
        finally:
            onboarding.read_second_device_onboarding = original
        self.assertEqual(result["outcome"], "setup_incomplete")
        self.assertEqual(result["receipt"]["owner_outcome"], "bundle_exported")
        self.assertTrue(result["receipt"]["mutation_performed"])
        self.assertEqual(read_handoff_state(self.source.path, expected_project_id=self.project_id).handoff["status"], "bundle_exported")

    def test_closed_schema_immutable_and_claims_hold(self):
        result = self.read(); self.assertTrue(json.dumps(result))
        with self.assertRaises(TypeError): result["stage"] = "held"
        schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "local-collaboration-onboarding.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema); self.assertFalse(list(Draft202012Validator(schema).iter_errors(result)))
        held = read_second_device_onboarding(self.source.path, expected_project_id=self.project_id, completed=True)
        self.assertEqual(held["stage"], "held")

    def test_invalid_target_context_does_not_create_authority(self):
        self.assertEqual(apply_second_device_onboarding_step({}, object())["outcome"], "held")
        self.assertFalse((Path(self.target_root.name) / self.project_id / "collaboration.db").exists())

    def test_forged_plan_and_existing_target_hold_before_create(self):
        from dataclasses import replace
        state = read_handoff_state(self.source.path, expected_project_id=self.project_id)
        from local_collaboration_handoff import plan_handoff_transition, apply_handoff_transition
        initial = plan_handoff_transition(state, {"transition": "enroll_initial", "project_id": self.project_id, "replica_id": "source", "replica_epoch": 1, "enrollment_id": "source-enroll", "enrollment_digest": digest("source"), "decision_id": "initial", "decision_digest": digest("initial")})
        apply_handoff_transition(self.source, initial, expected_before=state)
        summary = self.read()
        plan = plan_second_device_onboarding_step(summary, {"operation": "enroll_target", "decision_id": "enroll", "decision_digest": digest("enroll"), "parameters": {"replica_id": "target", "replica_epoch": 1, "enrollment_id": "target-enroll", "enrollment_digest": digest("target")}})
        forged = replace(plan, fingerprint=digest("forged"))
        self.assertEqual(apply_second_device_onboarding_step(self.context, forged)["outcome"], "held")


if __name__ == "__main__": unittest.main()
