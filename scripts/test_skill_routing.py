#!/usr/bin/env python3
"""Focused regressions for canonical discovery and conditional reference projection."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_adapters as publisher
import sync_adapters
import check_adapter_quality as quality


class SkillRoutingTests(unittest.TestCase):
    def record(self, **changes):
        record = {
            "id": "ASSET-COLLAB-001", "slug": "agent-collaboration",
            "title": "Agent Collaboration", "purpose": "Deliver a bounded Work.",
            "source_path": "assets/skills/example.asset.yaml",
            "canonical_practices": ["COLLAB-001", "COLLAB-009"],
            "published_to": ["codex"], "usage_triggers": ["Issue or PR delivery"],
            "process": ["Respect explicit holds and load applicable guidance before action."],
        }
        record.update(changes)
        return record

    def test_complete_discovery_is_not_truncated(self):
        description = "Use for explicit dispatch. " + "Preserve narrow scope. " * 14 + "Not for ordinary PR review."
        body = publisher.generated_skill_body(self.record(discovery_description=description), "codex", [])
        self.assertIn(description, body)
        self.assertIn("Not for ordinary PR review.", body.split("---")[1])

    def test_legacy_metadata_remains_compatible(self):
        record = self.record(purpose="x" * 300)
        body = publisher.generated_skill_body(record, "codex", [])
        self.assertIn("x" * 257 + "...", body)
        self.assertEqual(publisher.asset_routing("purpose: legacy\n", []), {})
        self.assertEqual(publisher.semantic_route_condition("ARCH-008"), "when_planning_cross_owner_migration_or_scope_freeze")
        self.assertEqual(publisher.semantic_route_condition("ARCH-010"), "when_execution_evidence_can_authorize_transition")

    def test_route_membership_and_discovery_validation(self):
        valid = 'discovery_description: "Use for delivery, not unrelated text."\npractice_routes:\n  COLLAB-001: always_for_declared_asset\n  COLLAB-009: when_executing_Work\n'
        fields = publisher.asset_routing(valid, ["COLLAB-001", "COLLAB-009"])
        self.assertEqual(fields["practice_routes"]["COLLAB-009"], "when_executing_Work")
        for invalid in (
            valid.replace("  COLLAB-009: when_executing_Work\n", ""),
            valid + "  COLLAB-099: when_other\n",
            valid + "  COLLAB-001: when_other\n",
            valid.replace("when_executing_Work", "not_applicable"),
            valid.replace("when_executing_Work", "before: write"),
            'discovery_description: "' + "x" * 1025 + '"\n',
            "discovery_description: >\n  hidden multiline\n",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    publisher.asset_routing(invalid, ["COLLAB-001", "COLLAB-009"])

    def test_projection_preserves_membership_and_relative_reachability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = {}
            for identifier in ("COLLAB-001", "COLLAB-009"):
                path = root / f"{identifier}.md"
                path.write_text(f"# {identifier}\nApplicable full canonical content.\n")
                records[identifier] = {"path": path.name}
            asset = self.record(practice_routes={"COLLAB-001": "always_for_declared_asset", "COLLAB-009": "when_executing_Work"})
            routes = publisher.semantic_reachability_routes(root, [asset], records)
            self.assertEqual({r["practice_id"] for r in routes}, set(records))
            self.assertTrue(all(r["declared_required"] == "true" for r in routes))
            body = publisher.generated_skill_body(asset, "codex", routes)
            self.assertIn("`references/COLLAB-009.md` when when_executing_Work", body)
            self.assertNotIn("`codex/skills/agent-collaboration/references/", body)
            reference = publisher.generated_practice_reference(root, routes[0])
            self.assertIn((root / routes[0]["source_path"]).read_text().strip(), reference)

    def test_invalid_source_stops_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(publisher, "print_operation_context"), patch.object(publisher, "validate", return_value=[]), patch.object(publisher, "active_entries", return_value=[{"id": "ASSET-COLLAB-001"}]), patch.object(publisher, "manifest_updated_date", return_value="2026-08-31"), patch.object(publisher, "skill_asset_records", side_effect=ValueError("invalid route")), patch.object(publisher, "write_adapter_outputs") as write:
                (root / "adapters").mkdir()
                (root / "adapters" / "adapter_profiles.yaml").touch()
                self.assertEqual(publisher.publish(root, root, root / "output", True), 1)
                write.assert_not_called()
                self.assertFalse((root / "output").exists())

    def test_manifest_date_comes_from_source_not_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "indexes").mkdir()
            (root / "indexes" / "practice_index.yaml").write_text("updated: 2026-08-27\n")
            (root / "indexes" / "asset_index.yaml").write_text("updated: 2026-08-31\n")
            self.assertEqual(publisher.manifest_updated_date(root), "2026-08-31")
            self.assertEqual(publisher.manifest_text([], [], [], "2026-08-31"), publisher.manifest_text([], [], [], publisher.manifest_updated_date(root)))
            (root / "indexes" / "asset_index.yaml").write_text("updated: yesterday\n")
            with self.assertRaises(ValueError):
                publisher.manifest_updated_date(root)

    def test_managed_update_and_restore_preserve_unrelated_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            skill = runtime / "example"
            skill.mkdir(parents=True)
            (skill / sync_adapters.MANAGED_MARKER).write_text("managed-by: agent-foundry\n")
            (skill / "user-local.txt").write_text("retain user material")
            for version in ("old", "new"):
                source = root / version / "codex" / "skills" / "example"
                (source / "references").mkdir(parents=True)
                (source / "SKILL.md").write_text(version + " guidance")
                (source / "references" / "COLLAB-001.md").write_text(version + " permission")
            with patch.object(sync_adapters, "ROOT", root):
                for version in ("old", "new", "old"):
                    sync_adapters.sync_codex(root / version, runtime, True, False)
                    self.assertEqual((skill / "SKILL.md").read_text(), version + " guidance")
                    self.assertEqual((skill / "references" / "COLLAB-001.md").read_text(), version + " permission")
                    self.assertEqual((skill / "user-local.txt").read_text(), "retain user material")

    def test_quality_rejects_wrong_condition_and_missing_canonical_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "COLLAB-001.md"
            source.write_text("# COLLAB-001\nExplicit holds remain binding.\n")
            asset = self.record(canonical_practices=["COLLAB-001"], practice_routes={"COLLAB-001": "before_action"})
            routes = publisher.semantic_reachability_routes(root, [asset], {"COLLAB-001": {"path": source.name}})
            generated = root / "generated"
            generated.mkdir()
            publisher.write_semantic_manifest(generated, routes, True)
            publisher.write_generated_skill_outputs(generated, [asset], routes, True)
            publisher.write_semantic_reference_outputs(root, generated, routes, True)
            manifest = generated / "adapter-publish-manifest.yaml"
            manifest.write_text("semantic_reachability_manifest: semantic-reachability-manifest.yaml\n")
            expected = {(r["target"], r["asset_id"], r["practice_id"]): r for r in routes}
            with patch.object(quality, "expected_semantic_routes", return_value=expected):
                self.assertEqual(quality.check_semantic_reachability(generated, root, manifest), [])
                router = generated / routes[0]["router_path"]
                original = router.read_text()
                router.write_text(original.replace("when before_action.", "when never.") + "\nbefore_action\n")
                self.assertTrue(any("condition binding" in e for e in quality.check_semantic_reachability(generated, root, manifest)))
                router.write_text(original)
                reference = generated / routes[0]["target_path"]
                reference.write_text(reference.read_text().replace("Explicit holds remain binding.", ""))
                self.assertTrue(any("reference content differs" in e for e in quality.check_semantic_reachability(generated, root, manifest)))


if __name__ == "__main__":
    unittest.main()
