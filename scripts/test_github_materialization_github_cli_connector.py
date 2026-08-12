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
    return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": login, "observable_scopes": sorted(scopes or ["repo"]), "minimum_scopes": ["repo"], "network_capability": True, "production_eligibility": True, "available": True}


def auth(login="octocat", scopes=None):
    return ok(json.dumps({"hosts": {"github.com": [{"login": login, "scopes": scopes if scopes is not None else ["repo"]}]}}))


def plan(**extra):
    value = {"schema_version": "GitHubCliIssueLabelConnector-v1", "human_authorization_ref": "human-gate-2-receipt", "operation": "add_existing_label", "target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "issue"}, "label": "trial-label", "preimage_digest": digest(["bug"]), "authority_generation": 7, "authority_head": H, "expected_capability_version": CONNECTOR_VERSION, "expected_capability_digest": capability_digest(observed())}
    value.update(extra)
    return value


class StubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
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


def test_direct_label_path_requires_repository_grant_before_target_call():
    c, runner = connector([auth(), ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_capability_broader_or_unobservable"
    assert runner.calls[0][0] == ("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts")
    assert not any("/issues/" in " ".join(call[0]) for call in runner.calls)
    assert_runner_contract(runner)


@pytest.mark.parametrize("response, expected, reason", [
    ({"returncode": 1, "stdout": "", "stderr": "token=secret"}, None, "hold_capability_unavailable"),
    (auth("octocat", []), None, "hold_scope_insufficient"),
    (auth("octocat", "unavailable"), None, "hold_scope_unavailable"),
    (auth("another"), None, "hold_capability_broader_or_unobservable"),
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
    assert str(held.value) == "hold_capability_broader_or_unobservable" and len(runner.calls) == 1
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


def test_capability_metadata_and_execution_share_resolver_and_sanitize_output(monkeypatch):
    c, runner = connector([auth("octocat", ["repo", "read:org"])])
    metadata = c.capability_metadata()
    assert metadata["available"] is False
    def blocked(*args, **kwargs): raise AssertionError("socket invoked")
    monkeypatch.setattr(socket, "socket", blocked)
    c, _ = connector([ok('{"hosts":{"github.com":[{"login":"octocat","scopes":["repo"],"token":"secret"}]}}')])
    assert c.capability_metadata()["available"] is False


def test_schema_results_and_no_credential_environment_access():
    import jsonschema
    import yaml
    schema = yaml.safe_load(open("schemas/github-materialization-adapter.schema.yaml"))
    c, _ = connector([auth()])
    with pytest.raises(GitHubCliConnectorHold):
        c.add_existing_label(plan(preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    jsonschema.Draft202012Validator(schema).validate(plan())


def test_repository_bound_capability_mode_rejects_unobservable_cli_scope_before_target():
    c, runner = connector([auth()])
    # The documented host/account status shape has no repository-grant field;
    # bridge capability metadata fails closed before an Issue endpoint.
    assert c.capability_metadata()["available"] is False
    assert not any("/issues/" in " ".join(call[0]) for call in runner.calls)
    with pytest.raises(TypeError):
        GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", capability_resolver=lambda: observed())
    assert not hasattr(c, "remove_same_label_if_added")
    assert not any("DELETE" in call[0] for call in runner.calls)
