import hashlib
import json
import socket

import pytest

from github_materialization_github_cli_connector import (
    CONNECTOR_ID, CONNECTOR_VERSION, GitHubCliConnectorHold,
    GitHubCliIssueLabelConnector, capability_digest,
)

H = "a" * 64


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def observed(login="octocat", scopes=None):
    return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": login, "observable_scopes": sorted(scopes or ["repo"]), "minimum_scopes": ["issues:metadata"], "repository_permission": {"repository": "octo-org/demo", "issues": "metadata"}, "network_capability": True, "production_eligibility": True, "available": True}


def auth(login="octocat", scopes=None):
    return ok(json.dumps({"login": login, "scopes": scopes if scopes is not None else ["repo"]}))


def plan(**extra):
    value = {"schema_version": "GitHubCliIssueLabelConnector-v1", "human_authorization_ref": "human-gate-2-receipt", "operation": "add_existing_label", "target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "issue"}, "label": "trial-label", "preimage_digest": digest(["bug"]), "authority_generation": 7, "authority_head": H, "expected_capability_version": CONNECTOR_VERSION, "expected_capability_digest": capability_digest(observed())}
    value.update(extra)
    return value


class StubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
        if tuple(argv) == ("gh", "api", "--method", "GET", "repos/octo-org/demo", "--jq", ".permissions.issues"):
            return ok("metadata\n")
        if not self.responses: raise AssertionError("unexpected subprocess call")
        return self.responses.pop(0)


def connector(responses):
    runner = StubRunner(responses)
    return GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner), runner


def ok(stdout=""): return {"returncode": 0, "stdout": stdout, "stderr": ""}


def assert_runner_contract(runner):
    assert all(call[1] == {"shell": False, "capture_output": True, "text": True, "timeout": 10} for call in runner.calls)


def assert_no_target_calls(runner):
    assert all("/issues/" not in " ".join(call[0]) for call in runner.calls)


def test_matching_owner_resolved_capability_uses_fixed_argv_and_nonconfirming_receipt():
    c, runner = connector([auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    result = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert result["outcome"] == "label_added" and result["mutation_count"] == 1
    assert result["network_capability"] is True and result["production_eligibility"] is True
    assert result["authoritative"] is False and result["confirmation_eligible"] is False
    assert runner.calls[0][0] == ("gh", "auth", "status", "--hostname", "github.com", "--json", "login,scopes")
    assert runner.calls[1][0] == ("gh", "api", "--method", "GET", "repos/octo-org/demo", "--jq", ".permissions.issues")
    assert runner.calls[2][0] == ("gh", "api", "--method", "GET", "repos/octo-org/demo/issues/12/labels", "--jq", ".[ ].name".replace(" ", ""))
    assert runner.calls[3][0] == ("gh", "api", "--method", "POST", "repos/octo-org/demo/issues/12/labels", "-f", "labels[]=trial-label")
    assert_runner_contract(runner)


@pytest.mark.parametrize("response, expected, reason", [
    ({"returncode": 1, "stdout": "", "stderr": "token=secret"}, None, "hold_capability_unavailable"),
    (ok(json.dumps({"login": "octocat", "scopes": []})), None, "hold_scope_insufficient"),
    (ok(json.dumps({"login": "octocat", "scopes": "unavailable"})), None, "hold_scope_unavailable"),
    (auth("another"), None, "hold_capability_untrusted"),
])
def test_forged_or_unavailable_caller_capability_cannot_reach_target(response, expected, reason):
    c, runner = connector([response])
    forged = plan(expected_capability_digest=capability_digest(observed("forged")))
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(forged, authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == reason
    assert_no_target_calls(runner)
    assert "secret" not in str(held.value)


def test_capability_digest_drift_and_extra_caller_claim_hold_before_target():
    c, runner = connector([auth()])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(expected_capability_digest="b" * 64), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_capability_untrusted" and len(runner.calls) == 2
    c, runner = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label({**plan(), "capability": {"observable_scopes": ["repo"]}}, authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_schema" and not runner.calls


@pytest.mark.parametrize("changed, reason", [
    ({"target": {"owner": "octo-org", "repository": "demo", "number": 0, "kind": "issue"}}, "hold_target_invalid"),
    ({"target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "discussion"}}, "hold_target_type_invalid"),
    ({"label": ""}, "hold_label_absent"), ({"preimage_digest": "bad"}, "hold_preimage_stale"),
])
def test_invalid_plan_holds_before_capability_resolution(changed, reason):
    c, runner = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(**changed), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == reason and not runner.calls


def test_duplicate_second_forward_preimage_provider_and_readback_holds():
    c, runner = connector([auth(), ok("bug\ntrial-label\n")])
    duplicate = c.add_existing_label(plan(preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    assert duplicate["outcome"] == "duplicate_no_mutation" and duplicate["mutation_count"] == 0
    c, _ = connector([auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n"), auth()])
    c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_second_forward_attempt"
    c, _ = connector([auth(), ok("other\n")])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_preimage_stale"
    c, _ = connector([auth(), ok("bug\n"), {"returncode": 429, "stdout": "", "stderr": "token=sensitive"}])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_provider_rate_limited" and "token" not in str(held.value)
    c, _ = connector([auth(), ok("bug\n"), ok(), ok("bug\n")])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_readback_mismatch"


def test_bounded_rollback_and_process_loss_remain_incomplete_not_recovered():
    c, runner = connector([auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n"), ok("bug\ntrial-label\n"), ok(), ok("bug\n")])
    forward = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    rollback = c.remove_same_label_if_added(forward)
    assert rollback["outcome"] == "rollback_complete"
    assert runner.calls[6][0] == ("gh", "api", "--method", "DELETE", "repos/octo-org/demo/issues/12/labels/trial-label")
    c, _ = connector([auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    result = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    fresh, _ = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        fresh.remove_same_label_if_added(result)
    assert str(held.value) == "hold_schema"


def test_capability_metadata_and_execution_share_resolver_and_sanitize_output(monkeypatch):
    c, runner = connector([auth("octocat", ["repo", "read:org"]), auth("octocat", ["repo", "read:org"]), ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    metadata = c.capability_metadata()
    assert metadata == observed("octocat", ["repo", "read:org"])
    result = c.add_existing_label(plan(expected_capability_digest=capability_digest(metadata)), authority_pair={"authority_generation": 7, "authority_head": H})
    assert result["outcome"] == "label_added"
    def blocked(*args, **kwargs): raise AssertionError("socket invoked")
    monkeypatch.setattr(socket, "socket", blocked)
    c, _ = connector([ok('{"login":"octocat","scopes":["repo"],"token":"secret"}')])
    assert c.capability_metadata()["available"] is False


def test_schema_results_and_no_credential_environment_access():
    import jsonschema
    import yaml
    schema = yaml.safe_load(open("schemas/github-materialization-adapter.schema.yaml"))
    c, _ = connector([auth(), ok("bug\ntrial-label\n")])
    duplicate = c.add_existing_label(plan(preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    jsonschema.Draft202012Validator(schema).validate(plan())
    jsonschema.Draft202012Validator(schema).validate(duplicate)


def test_repository_bound_capability_mode_rejects_unobservable_cli_scope_before_target():
    c, runner = connector([auth()])
    def no_permission(argv, **kwargs):
        runner.calls.append((tuple(argv), kwargs))
        if tuple(argv) == ("gh", "api", "--method", "GET", "repos/octo-org/demo", "--jq", ".permissions.issues"):
            return {"returncode": 0, "stdout": "write\n", "stderr": ""}
        return runner.responses.pop(0)
    c._runner = no_permission
    # A fixed owner query that does not return the literal metadata permission
    # cannot reach the Issue endpoint.
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_capability_broader_or_unobservable" and not any("/issues/" in " ".join(call[0]) for call in runner.calls)

    bound = observed()
    c, runner = connector([auth(), auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    actual = c.capability_metadata()
    assert actual == bound and c.repository_binding == {"owner": "octo-org", "repository": "demo"}
    receipt = c.add_existing_label(plan(expected_capability_digest=capability_digest(bound)), authority_pair={"authority_generation": 7, "authority_head": H})
    assert receipt["outcome"] == "label_added" and any("/issues/" in " ".join(call[0]) for call in runner.calls)
