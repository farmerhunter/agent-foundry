#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_host_rolehub_adapter import CodexHostRoleHubAdapter, ThreadMetadata, apply_rolehub, CONTRACT

class FakeHost:
    def __init__(self, threads=None, navigation=True):
        self.project_id = "tiny-ipa"
        self.threads = {t.id: ThreadMetadata(t.id, t.cwd, t.name, t.project_id or self.project_id) for t in (threads or [])}; self.navigation = navigation
        self.calls = []
    def list_threads(self, cwd): self.calls.append(("list", cwd)); return [t for t in self.threads.values() if t.cwd == cwd]
    def read_thread(self, id, include_turns=False):
        self.calls.append(("read", id, include_turns)); return self.threads[id]
    def create_thread(self, cwd):
        self.calls.append(("create", cwd)); ident = "native-new"; t = ThreadMetadata(ident, cwd, "", self.project_id)
        self.threads[ident] = t; return t
    def set_thread_name(self, id, title):
        self.calls.append(("name", id, title)); t = self.threads[id]; self.threads[id] = ThreadMetadata(t.id, t.cwd, title, t.project_id); return self.threads[id]
    def navigate_to_thread(self, id):
        self.calls.append(("navigate", id))
        if not self.navigation: raise NotImplementedError

def plan(*ops):
    return {"contract_version": CONTRACT, "project_id": "tiny-ipa", "project_root": "/p/tiny-ipa", "logical_rolehub_id": "rh-1", "operations": list(ops)}
def op(i, action, **kw): return {"operation_id": i, "action": action, "idempotency_key": i, **kw}

class AdapterTests(unittest.TestCase):
    def test_create_name_readback_and_opaque_receipt(self):
        h = FakeHost(); r = apply_rolehub(plan(op("c", "create", role="Coordinator", title="AF18 Coordinator")), h)
        self.assertEqual(r["status"], "ready"); self.assertEqual(r["operations"][0]["status"], "applied")
        self.assertNotIn("native-new", str(r)); self.assertTrue(any(x[0] == "read" and x[2] is False for x in h.calls))
    def test_reuse_requires_one_unambiguous_match(self):
        h = FakeHost([ThreadMetadata("a", "/p/tiny-ipa", "Coordinator")])
        self.assertEqual(apply_rolehub(plan(op("r", "reuse", role="Coordinator", title="Coordinator")), h)["status"], "ready")
        h.threads["b"] = ThreadMetadata("b", "/p/tiny-ipa", "Coordinator")
        self.assertEqual(apply_rolehub(plan(op("r2", "reuse", role="Coordinator", title="Coordinator")), h)["status"], "setup_incomplete")
    def test_link_is_logical_only(self):
        r = apply_rolehub(plan(op("l", "link", target_ref="opaque")), FakeHost())
        self.assertTrue(r["operations"][0]["logical_link"]); self.assertFalse(r["operations"][0]["native_link"])
    def test_navigation_fallback_is_explicit(self):
        h = FakeHost([ThreadMetadata("a", "/p/tiny-ipa", "A")], navigation=False)
        r = apply_rolehub(plan(op("n", "navigate", target_ref="a")), h)
        self.assertEqual(r["operations"][0]["navigation"], "client_fallback")
    def test_idempotency_and_conflict(self):
        h = FakeHost(); a = CodexHostRoleHubAdapter(h); p = plan(op("c", "create", title="A")); first = a.apply(p); second = a.apply(p)
        self.assertEqual(first, second)
        bad = plan(op("c", "create", title="B")); self.assertEqual(a.apply(bad)["status"], "setup_incomplete")
    def test_ambiguous_or_foreign_transport_holds(self):
        class Bad(FakeHost):
            def create_thread(self, cwd): return {"id": "leak", "cwd": cwd}
        r = apply_rolehub(plan(op("c", "create", title="A")), Bad())
        self.assertEqual(r["status"], "setup_incomplete"); self.assertNotIn("leak", str(r))
    def test_create_external_rename_never_ready(self):
        class Renaming(FakeHost):
            def set_thread_name(self, id, title):
                return super().set_thread_name(id, "external")
        r = apply_rolehub(plan(op("c", "create", title="requested")), Renaming())
        self.assertEqual(r["status"], "partial_hold")
        self.assertEqual(r["reason"], "readback_name_mismatch")
    def test_name_external_rename_never_ready(self):
        class Renaming(FakeHost):
            def set_thread_name(self, id, title):
                return super().set_thread_name(id, "external")
        h = Renaming([ThreadMetadata("a", "/p/tiny-ipa", "old")])
        r = apply_rolehub(plan(op("n", "name", title="requested", target_ref="a")), h)
        self.assertEqual(r["status"], "partial_hold")
    def test_no_turns_or_forbidden_operations(self):
        h = FakeHost([ThreadMetadata("a", "/p/tiny-ipa", "A")]); apply_rolehub(plan(op("n", "navigate", target_ref="a")), h)
        self.assertFalse(any(len(x) > 2 and x[0] == "read" and x[2] for x in h.calls))
        self.assertFalse(hasattr(h, "send_message"))
    def test_project_binding_mismatch_holds(self):
        h = FakeHost([ThreadMetadata("a", "/p/tiny-ipa", "A", "foreign")])
        self.assertEqual(apply_rolehub(plan(op("n", "navigate", target_ref="a")), h)["status"], "setup_incomplete")

if __name__ == "__main__": unittest.main()
