import hashlib
import json
import socket

import pytest

from github_materialization_github_cli_connector import GitHubCliConnectorHold, GitHubCliIssueLabelConnector


H = "a" * 64


def digest(labels):
    return hashlib.sha256(json.dumps(sorted(labels), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def plan(**extra):
    value = {
        "schema_version": "GitHubCliIssueLabelConnector-v1",
        "human_authorization_ref": "human-gate-2-receipt",
        "operation": "add_existing_label",
        "target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "issue"},
        "label": "trial-label",
        "preimage_digest": digest(["bug"]),
        "authority_generation": 7,
        "authority_head": H,
        "capability": {"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "octocat", "observable_scopes": ["repo"], "minimum_scopes": ["repo"], "available": True},
    }
    value.update(extra)
    return value


class StubRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
        if not self.responses:
            raise AssertionError("unexpected subprocess call")
        return self.responses.pop(0)


def connector(responses):
    runner = StubRunner(responses)
    return GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner), runner


def ok(stdout=""):
    return {"returncode": 0, "stdout": stdout, "stderr": ""}


def test_add_uses_fixed_argv_shell_false_and_returns_non_confirming_receipt():
    c, runner = connector([ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    result = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert result["outcome"] == "label_added" and result["mutation_count"] == 1
    assert result["network_capability"] is True and result["production_eligibility"] is True
    assert result["authoritative"] is False and result["confirmation_eligible"] is False
    assert runner.calls[0][0] == ("gh", "api", "--method", "GET", "repos/octo-org/demo/issues/12/labels", "--jq", ".[ ].name".replace(" ", ""))
    assert runner.calls[1][0] == ("gh", "api", "--method", "POST", "repos/octo-org/demo/issues/12/labels", "-f", "labels[]=trial-label")
    assert all(call[1] == {"shell": False, "capture_output": True, "text": True, "timeout": 10} for call in runner.calls)


def test_duplicate_is_no_mutation_and_second_forward_attempt_holds():
    c, runner = connector([ok("bug\ntrial-label\n")])
    duplicate = c.add_existing_label(plan(preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    assert duplicate["outcome"] == "duplicate_no_mutation" and duplicate["mutation_count"] == 0
    assert len(runner.calls) == 1
    c, _ = connector([ok("bug\n"), ok(), ok("bug\ntrial-label\n")])
    result = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_second_forward_attempt" and result["outcome"] == "label_added"


@pytest.mark.parametrize("changed, reason", [
    ({"target": {"owner": "octo-org", "repository": "demo", "number": 0, "kind": "issue"}}, "hold_target_invalid"),
    ({"target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "discussion"}}, "hold_target_type_invalid"),
    ({"label": ""}, "hold_label_absent"),
    ({"preimage_digest": "bad"}, "hold_preimage_stale"),
])
def test_invalid_target_or_label_holds_before_subprocess(changed, reason):
    c, runner = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(**changed), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == reason and not runner.calls


def test_repository_and_authority_binding_hold_before_subprocess():
    c, runner = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(target={"owner": "other", "repository": "demo", "number": 12, "kind": "issue"}, capability={**plan()["capability"], "repository_restriction": "other/demo"}), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_auth_mismatch"
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 8, "authority_head": H})
    assert str(held.value) == "hold_authority_pair_stale" and not runner.calls


@pytest.mark.parametrize("capability, reason", [
    ({"connector_id": "other", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "octocat", "observable_scopes": ["repo"], "minimum_scopes": ["repo"], "available": True}, "hold_capability_untrusted"),
    ({"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "other/demo", "authenticated_principal": "octocat", "observable_scopes": ["repo"], "minimum_scopes": ["repo"], "available": True}, "hold_capability_untrusted"),
    ({"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "octocat", "observable_scopes": ["repo"], "minimum_scopes": ["repo"], "available": False}, "hold_capability_unavailable"),
    ({"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "octocat", "observable_scopes": "unavailable", "minimum_scopes": ["repo"], "available": True}, "hold_scope_unavailable"),
    ({"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "octocat", "observable_scopes": ["read:org"], "minimum_scopes": ["repo"], "available": True}, "hold_scope_insufficient"),
])
def test_capability_binding_holds_before_pre_read(capability, reason):
    c, runner = connector([])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(capability=capability), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == reason and not runner.calls


def test_preimage_drift_provider_failures_and_readback_mismatch_are_typed_and_private():
    c, runner = connector([ok("other\n")])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_preimage_stale"
    for response, reason in (({"returncode": 429, "stdout": "", "stderr": "token=sensitive"}, "hold_provider_rate_limited"), ({"returncode": 1, "stdout": "", "stderr": "credential=secret"}, "hold_write_failed")):
        c, _ = connector([ok("bug\n"), response])
        with pytest.raises(GitHubCliConnectorHold) as held:
            c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
        assert str(held.value) == reason and "token" not in str(held.value) and "secret" not in str(held.value)
    c, _ = connector([ok("bug\n"), ok(), ok("bug\n")])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_readback_mismatch"


def test_bounded_rollback_only_for_own_added_receipt():
    c, runner = connector([ok("bug\n"), ok(), ok("bug\ntrial-label\n"), ok("bug\ntrial-label\n"), ok(), ok("bug\n")])
    forward = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    rollback = c.remove_same_label_if_added(forward)
    assert rollback["outcome"] == "rollback_complete" and rollback["operation"] == "remove_same_label_if_added"
    assert runner.calls[4][0] == ("gh", "api", "--method", "DELETE", "repos/octo-org/demo/issues/12/labels/trial-label")
    with pytest.raises(GitHubCliConnectorHold):
        c.remove_same_label_if_added({**forward, "receipt_id": "b" * 64})


def test_capability_metadata_is_sanitized_and_scope_unavailable():
    c, runner = connector([ok("logged in as someone with token=secret")])
    metadata = c.capability_metadata()
    assert metadata == {"connector_id": "github-cli-issue-label", "connector_version": "1", "provider": "github", "host": "github.com", "repository_restriction": "octo-org/demo", "authenticated_principal": "available", "observable_scopes": "unavailable", "network_capability": True, "production_eligibility": True, "available": True}
    assert runner.calls[0][0] == ("gh", "auth", "status", "--hostname", "github.com")
    assert "secret" not in repr(metadata)


def test_output_limit_timeout_and_no_socket_or_environment_auth(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("socket invoked")
    monkeypatch.setattr(socket, "socket", blocked)
    c, _ = connector([{ "returncode": 0, "stdout": "x" * 4097, "stderr": "" }])
    with pytest.raises(GitHubCliConnectorHold) as held:
        c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    assert str(held.value) == "hold_output_invalid"


def test_connector_results_match_closed_schema_variants():
    import jsonschema
    import yaml
    schema = yaml.safe_load(open("schemas/github-materialization-adapter.schema.yaml"))
    c, _ = connector([ok("bug\ntrial-label\n")])
    duplicate = c.add_existing_label(plan(preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    jsonschema.Draft202012Validator(schema).validate(duplicate)
    c, _ = connector([ok("bug\n"), ok(), ok("bug\ntrial-label\n"), ok("bug\ntrial-label\n"), ok(), ok("bug\n")])
    forward = c.add_existing_label(plan(), authority_pair={"authority_generation": 7, "authority_head": H})
    jsonschema.Draft202012Validator(schema).validate(forward)
    jsonschema.Draft202012Validator(schema).validate(c.remove_same_label_if_added(forward))
