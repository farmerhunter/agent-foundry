import json

import pytest

from github_materialization_github_cli_connector import CONFINEMENT, GitHubCliIssueLabelConnector


class StubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs)); return self.responses.pop(0)


def auth(login="octocat", scopes=None):
    return {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"login": login, "scopes": scopes or ["repo"]}]}}), "stderr": ""}


def test_connector_only_exposes_metadata_and_private_execution():
    runner = StubRunner([auth()])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    metadata = connector.capability_metadata()
    assert metadata["available"] is True
    assert metadata["credential_grant_attested"] is False
    assert metadata["operation_confinement"] == CONFINEMENT
    assert not hasattr(connector, "add_existing_label")
    assert not hasattr(connector, "remove_same_label_if_added")
    assert runner.calls[0][0] == ("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts")
    assert runner.calls[0][1] == {"shell": False, "capture_output": True, "text": True, "timeout": 10}


@pytest.mark.parametrize("response", [{"returncode": 1, "stdout": "", "stderr": "token=x"}, auth("bad user"), {"returncode": 0, "stdout": "{}", "stderr": ""}])
def test_metadata_failure_is_nonattesting_and_never_calls_target(response):
    runner = StubRunner([response])
    metadata = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner).capability_metadata()
    assert metadata["available"] is False and metadata["credential_grant_attested"] is False
    assert not any("/issues/" in " ".join(argv) or "POST" in argv or "DELETE" in argv for argv, _ in runner.calls)


def test_constructor_rejects_caller_capability_or_runner_arguments_beyond_stub_runner():
    with pytest.raises(TypeError):
        GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", capability_resolver=lambda: {})
