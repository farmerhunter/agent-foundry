#!/usr/bin/env python3
import copy
import unittest

from codex_rolehub_runner import CodexRoleHubRunner, START_CONTRACT, diagnose_thread_start_contract


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
            self.threads[tid] = {"name": "", "cwd": params["cwd"]}
            return {"thread": {"id": tid, "cwd": params["cwd"], "name": ""}}
        if method == "thread/read":
            tid = params["threadId"]
            if tid not in self.threads:
                raise RuntimeError("foreign")
            return {"thread": {"id": tid, "cwd": self.threads[tid]["cwd"], "name": self.threads[tid]["name"], "turns": [{"message": "secret"}]}}
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
    def start_sample(self):
        thread = {"id": "t1", "cwd": "/tmp/tiny-ipa", "name": "Coordinator"}
        response = {field: ("x" if field not in {"cwd", "thread"} else ("/tmp/tiny-ipa" if field == "cwd" else thread)) for field in START_CONTRACT["start_response"]["required"]}
        return {"cli_version": "codex-cli 0.133.0", "protocol_variant": "v2", "start_method": "thread/start", "read_method": "thread/read", "start_request": {"cwd": "/tmp/tiny-ipa"}, "start_response": response, "readback": {"thread": copy.deepcopy(thread)}}

    def test_static_start_contract_valid_and_privacy_safe(self):
        sample = self.start_sample(); sample["start_response"]["turns"] = [{"prompt": "secret"}]
        result = diagnose_thread_start_contract(sample)
        self.assertEqual(result["status"], "setup_incomplete")
        self.assertNotIn("secret", str(result))

    def test_static_start_contract_valid(self):
        self.assertEqual(diagnose_thread_start_contract(self.start_sample())["status"], "ready")

    def test_static_contract_missing_required_and_unknown_type(self):
        sample = self.start_sample(); del sample["start_request"]["cwd"]
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "start_required_cwd_missing")
        sample = self.start_sample(); sample["start_request"]["cwd"] = 7
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "start_required_cwd_missing")
        sample = self.start_sample(); sample["start_request"]["unexpected"] = True
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "start_request_unknown_field")

    def test_static_contract_protocol_and_response_failures(self):
        sample = self.start_sample(); sample["protocol_variant"] = "v1"
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "version_or_protocol_mismatch")
        sample = self.start_sample(); sample["start_response"] = {"error": {"message": "secret"}}
        result = diagnose_thread_start_contract(sample)
        self.assertEqual(result["reason"], "protocol_error"); self.assertNotIn("secret", str(result))
        sample = self.start_sample(); del sample["start_response"]["thread"]
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "start_response_required_missing")
        sample = self.start_sample(); sample["start_response"]["thread"]["id"] = None
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "nested_thread_id_missing")

    def test_static_contract_correlation_and_readback(self):
        sample = self.start_sample(); sample["start_response"]["thread"]["cwd"] = "/foreign"
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "foreign_cwd")
        sample = self.start_sample(); sample["readback"]["thread"]["id"] = "other"
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "readback_correlation_mismatch")
        sample = self.start_sample(); sample.pop("readback")
        self.assertEqual(diagnose_thread_start_contract(sample)["reason"], "readback_missing")

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

    def test_stale_preimage_holds_before_mutation(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        runner.apply(plan(op("create", title="old")))
        result = runner.apply(plan(op("name", key="k2", title="new", preimage_digest="sha256:stale")))
        self.assertEqual(result["reason"], "stale_preimage")
        self.assertEqual(rpc.threads["t1"]["name"], "old")

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

    def test_rpc_error_is_structured_and_private(self):
        class Broken(FakeRPC):
            def __call__(self, method, params):
                if method == "thread/start":
                    raise RuntimeError("secret prompt payload")
                return super().__call__(method, params)
        result = CodexRoleHubRunner(Broken(), runtime_id="rt-1").apply(plan(op()))
        self.assertEqual(result["status"], "setup_incomplete")
        self.assertEqual(result["operations"][0]["status"], "setup_incomplete")

    def test_nested_start_requires_thread_metadata(self):
        class MissingThread(FakeRPC):
            def __call__(self, method, params):
                if method == "thread/start":
                    return {"thread": {"id": "t1", "name": ""}}
                return super().__call__(method, params)
        result = CodexRoleHubRunner(MissingThread(), runtime_id="rt-1").apply(plan(op()))
        self.assertEqual(result["status"], "setup_incomplete")
        self.assertEqual(result["operations"][0]["status"], "setup_incomplete")
        self.assertNotIn("threadId", str(result))

    def test_nested_read_rejects_foreign_cwd(self):
        class ForeignRead(FakeRPC):
            def __call__(self, method, params):
                value = super().__call__(method, params)
                if method == "thread/read":
                    value["thread"]["cwd"] = "/foreign"
                return value
        rpc = ForeignRead(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        result = runner.apply(plan(op()))
        self.assertEqual(result["status"], "partial_hold")
        self.assertNotIn("/foreign", str(result))

    def test_new_thread_failure_is_setup_incomplete_with_receipt(self):
        class Broken(FakeRPC):
            def __call__(self, method, params):
                if method == "thread/start":
                    raise RuntimeError("private native error")
                return super().__call__(method, params)
        result = CodexRoleHubRunner(Broken(), runtime_id="rt-1").apply(plan(op()))
        self.assertEqual(result["status"], "setup_incomplete")
        self.assertEqual(result["operations"][0]["status"], "setup_incomplete")
        self.assertNotIn("private", str(result))

    def test_mid_plan_failure_preserves_applied_evidence(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        result = runner.apply(plan(op("create", key="first"), op("name", key="second", role="Reviewer")))
        self.assertEqual(result["status"], "partial_hold")
        self.assertEqual(result["operations"][0]["status"], "applied")

    def test_forged_rollback_receipt_is_rejected(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        runner.apply(plan(op("create", title="old")))
        result = runner.apply(plan(op("name", title="new", key="named")))
        forged = copy.deepcopy(result["operations"][0])
        forged["readback"]["previous_title"] = "forged"
        rollback = runner.rollback([forged])
        self.assertEqual(rollback["status"], "rollback_incomplete")
        self.assertEqual(rpc.threads["t1"]["name"], "new")

    def test_forged_digest_and_external_rename_are_rejected(self):
        rpc = FakeRPC(); runner = CodexRoleHubRunner(rpc, runtime_id="rt-1")
        runner.apply(plan(op("create", title="old")))
        result = runner.apply(plan(op("name", title="new", key="named")))
        forged = copy.deepcopy(result["operations"][0])
        forged["readback"]["digest"] = "sha256:forged"
        self.assertEqual(runner.rollback([forged])["status"], "rollback_incomplete")
        rpc.threads["t1"]["name"] = "changed-externally"
        self.assertEqual(runner.rollback([result["operations"][0]])["reason"], "current_preimage_changed")
        self.assertEqual(rpc.threads["t1"]["name"], "changed-externally")

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
