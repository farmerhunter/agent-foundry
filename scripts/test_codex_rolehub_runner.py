#!/usr/bin/env python3
import copy
import unittest

from codex_rolehub_runner import CodexRoleHubRunner


class FakeRPC:
    def __init__(self):
        self.calls = []
        self.threads = {}
        self.next_id = 1

    def __call__(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == "initialize":
            return {"protocolVersion": "1", "capabilities": {"thread": True}}
        if method == "initialized":
            return {}
        if method == "thread/list":
            return {"threads": [{"id": k, "name": v["name"]} for k, v in self.threads.items()]}
        if method == "thread/start":
            tid = f"t{self.next_id}"; self.next_id += 1
            self.threads[tid] = {"name": ""}
            return {"threadId": tid}
        if method == "thread/read":
            tid = params["threadId"]
            if tid not in self.threads:
                raise RuntimeError("foreign")
            return {"id": tid, "name": self.threads[tid]["name"], "turns": [{"message": "secret"}]}
        if method == "thread/name/set":
            self.threads[params["threadId"]]["name"] = params["name"]
            return {"ok": True}
        raise AssertionError(method)


def plan(*ops):
    return {"contract_version": "AF18-codex-rolehub-runner-v1", "project_id": "tiny-ipa", "logical_rolehub_id": "tiny-ipa:rolehub", "runtime_id": "rt-1", "capability_evidence": {"trusted": True, "runtime_id": "rt-1", "methods": ["initialize", "initialized", "thread/list", "thread/read", "thread/start", "thread/name/set"], "cwd": "/tmp/tiny-ipa"}, "operations": list(ops)}


def op(action="create", key="k1", role="Coordinator", **kwargs):
    item = {"operation_id": key, "action": action, "idempotency_key": key, "role": role}
    item.update(kwargs)
    return item


class RunnerTests(unittest.TestCase):
    def test_preflight_and_create_name_readback(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        self.assertEqual(runner.preflight()["status"], "ready")
        result = runner.apply(plan(op(title="coord")))
        self.assertEqual(result["status"], "ready")
        self.assertTrue(all("includeTurns" not in p or p["includeTurns"] is False for m, p in rpc.calls if m == "thread/read"))
        self.assertTrue(all("secret" not in str(x) for x in result.values()))

    def test_duplicate_and_foreign_idempotency(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        first = runner.apply(plan(op()))
        second = runner.apply(plan(op()))
        self.assertEqual(first, second)
        self.assertEqual(runner.apply(plan(op(title="other")))["reason"], "foreign_idempotency_key")

    def test_schema_drift_and_forbidden_rpc(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        bad = plan(op()); bad["unexpected"] = True
        self.assertEqual(runner.apply(bad)["reason"], "schema_drift")
        with self.assertRaises(Exception):
            runner._call("turn/start", {})

    def test_no_cwd_fails_closed(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        without_cwd = plan(op()); del without_cwd["capability_evidence"]["cwd"]
        self.assertEqual(runner.apply(without_cwd)["reason"], "cwd_unproven")
        self.assertNotIn("thread/start", [method for method, _ in rpc.calls])

    def test_logical_link_and_navigation_hold(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        result = runner.apply(plan(op("link", target_ref="github:issue:501"), op("navigate", key="k2")))
        self.assertEqual(result["status"], "ready")
        self.assertTrue(all(item["status"] == "partial_hold" for item in result["operations"]))
        self.assertEqual(len(rpc.calls), 0)

    def test_title_rollback(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        runner.apply(plan(op("create", title="new")))
        receipt = runner.apply(plan(op("name", title="renamed", key="k2")))
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(runner.rollback(receipt["operations"])["status"], "complete")
        # No delete is attempted when setup cannot be completed.
        self.assertNotIn("thread/delete", [m for m, _ in rpc.calls])


if __name__ == "__main__":
    unittest.main()
