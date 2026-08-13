import json

import pytest

from github_materialization_github_cli_connector import CONFINEMENT, GitHubCliIssueLabelConnector


class StubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs)); return self.responses.pop(0)


def auth(login="octocat", scopes=None):
    return {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"login": login, "scopes": scopes or ["repo"]}]}}), "stderr": ""}


def official_auth(login="octocat", scopes="repo", *, token_source="keyring", git_protocol="https", error=None, extra_hosts=None):
    account = {"state": "success", "active": True, "host": "github.com", "login": login,
               "tokenSource": token_source, "gitProtocol": git_protocol, "scopes": scopes}
    if error is not None:
        account["error"] = error
    hosts = {"github.com": [account]}
    hosts.update(extra_hosts or {})
    return {"returncode": 0, "stdout": json.dumps({"hosts": hosts}), "stderr": ""}


def test_connector_only_exposes_metadata_and_private_execution():
    runner = StubRunner([official_auth()])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    metadata = connector.capability_metadata()
    assert metadata["available"] is True
    assert metadata["credential_grant_attested"] is False
    assert metadata["operation_confinement"] == CONFINEMENT
    assert "active_principal" not in metadata and "observable_host_scopes" not in metadata
    assert not hasattr(connector, "add_existing_label")
    assert not hasattr(connector, "remove_same_label_if_added")
    assert runner.calls[0][0] == ("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts")
    assert runner.calls[0][1] == {"shell": False, "capture_output": True, "text": True, "timeout": 10}


def test_connector_retains_explicit_legacy_sanitized_fixture_shape():
    runner = StubRunner([auth()])
    assert GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()["available"] is True


@pytest.mark.parametrize("response", [
    official_auth(token_source="/Library/Application Support/GitHub CLI/secure-store"),
    official_auth(git_protocol="ssh"),
    official_auth(error=""),
])
def test_current_auth_shape_accepts_documented_private_source_ssh_and_empty_error(response):
    runner = StubRunner([response])
    metadata = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()
    assert metadata["available"] is True
    assert len(runner.calls) == 1


@pytest.mark.parametrize("response", [
    {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"state": "success", "active": True, "host": "github.com", "login": "octocat", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "repo", "token": "forbidden"}]}}), "stderr": ""},
    {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"state": "success", "active": False, "host": "github.com", "login": "octocat", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "repo"}]}}), "stderr": ""},
    {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"state": "success", "active": True, "host": "github.com", "login": "octocat", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "gist"}]}}), "stderr": ""},
    {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"state": "success", "active": True, "host": "github.com", "login": "octocat", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "repo", "error": "unavailable"}]}}), "stderr": ""},
    official_auth(extra_hosts={"enterprise.example": []}),
    {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [
        {"state": "success", "active": True, "host": "github.com", "login": "octocat", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "repo"},
        {"state": "success", "active": True, "host": "github.com", "login": "other", "tokenSource": "keyring", "gitProtocol": "https", "scopes": "repo"}]}}), "stderr": ""},
])
def test_current_auth_shape_invalid_classes_hold_before_target(response):
    runner = StubRunner([response])
    metadata = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()
    assert metadata["available"] is False
    assert len(runner.calls) == 1


def test_c1_control_token_source_is_publicly_unavailable_before_any_target_call():
    runner = StubRunner([official_auth(token_source="keyring\u0085")])
    metadata = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()
    assert metadata["available"] is False
    assert len(runner.calls) == 1
    assert not any("/issues/" in " ".join(argv) for argv, _ in runner.calls)


@pytest.mark.parametrize("response", [{"returncode": 1, "stdout": "", "stderr": "token=x"}, auth("bad user"), {"returncode": 0, "stdout": "{}", "stderr": ""}])
def test_metadata_failure_is_nonattesting_and_never_calls_target(response):
    runner = StubRunner([response])
    metadata = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()
    assert metadata["available"] is False and metadata["credential_grant_attested"] is False
    assert "active_principal" not in metadata and "observable_host_scopes" not in metadata
    assert not any("/issues/" in " ".join(argv) or "POST" in argv or "DELETE" in argv for argv, _ in runner.calls)


def test_constructor_rejects_caller_capability_or_runner_arguments_beyond_stub_runner():
    with pytest.raises(TypeError):
        GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", capability_resolver=lambda: {})
