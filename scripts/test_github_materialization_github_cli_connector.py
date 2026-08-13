import hashlib
import json

import pytest

from github_materialization_github_cli_connector import (
    CONFINEMENT, CONNECTOR_ID, CONNECTOR_VERSION, GitHubCliConnectorHold,
    GitHubCliIssueLabelConnector, capability_digest,
)

H = "a" * 64


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def auth(login="octocat", scopes=None):
    return {"returncode": 0, "stdout": json.dumps({"hosts": {"github.com": [{"login": login, "scopes": scopes or ["repo"]}]}}), "stderr": ""}


class StubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
        return self.responses.pop(0)


def plan(capability, **extra):
    value = {"schema_version": "GitHubCliIssueLabelConnector-v1", "human_authorization_ref": "hdc-ref",
             "operation": "add_existing_label", "target": {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "issue"},
             "label": "trial-label", "preimage_digest": digest(["bug"]), "authority_generation": 7,
             "authority_head": H, "expected_capability_digest": capability_digest(capability)}
    value.update(extra); return value


def test_owner_resolution_and_exact_label_sequence_are_nonattesting():
    runner = StubRunner([auth(), auth(), {"returncode": 0, "stdout": "bug\n", "stderr": ""},
                         {"returncode": 0, "stdout": "", "stderr": ""}, {"returncode": 0, "stdout": "bug\ntrial-label\n", "stderr": ""}])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    capability = connector.capability_metadata()
    result = connector.add_existing_label(plan(capability), authority_pair={"authority_generation": 7, "authority_head": H})
    assert result["outcome"] == "label_added" and result["mutation_count"] == 1
    for key, value in {"credential_grant_attested": False, "operation_confinement": CONFINEMENT, "authoritative": False, "confirmation_eligible": False}.items(): assert result[key] is value if isinstance(value, bool) else result[key] == value
    assert runner.calls[0][0] == ("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts")
    assert runner.calls[2][0] == ("gh", "api", "--method", "GET", "repos/octo-org/demo/issues/12/labels", "--jq", ".[ ].name".replace(" ", ""))
    assert runner.calls[3][0] == ("gh", "api", "--method", "POST", "repos/octo-org/demo/issues/12/labels", "-f", "labels[]=trial-label")
    assert all(kwargs == {"shell": False, "capture_output": True, "text": True, "timeout": 10} for _, kwargs in runner.calls)


def test_duplicate_has_no_post_and_allows_no_rollback_or_delete():
    runner = StubRunner([auth(), auth(), {"returncode": 0, "stdout": "bug\ntrial-label\n", "stderr": ""}])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    capability = connector.capability_metadata()
    result = connector.add_existing_label(plan(capability, preimage_digest=digest(["bug", "trial-label"])), authority_pair={"authority_generation": 7, "authority_head": H})
    assert result["outcome"] == "duplicate_no_mutation" and result["mutation_count"] == 0
    assert not any("POST" in argv or "DELETE" in argv for argv, _ in runner.calls)
    assert not hasattr(connector, "remove_same_label_if_added")


@pytest.mark.parametrize("response", [{"returncode": 1, "stdout": "", "stderr": "token=x"}, auth("bad user"), {"returncode": 0, "stdout": "{}", "stderr": ""}])
def test_malformed_or_unavailable_auth_holds_without_target(response):
    runner = StubRunner([response])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    with pytest.raises(GitHubCliConnectorHold): connector.add_existing_label(plan({"bad": True}), authority_pair={"authority_generation": 7, "authority_head": H})
    assert not any("/issues/" in " ".join(argv) for argv, _ in runner.calls)


def test_capability_drift_and_caller_injection_are_rejected_before_target():
    runner = StubRunner([auth()])
    connector = GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner)
    with pytest.raises(GitHubCliConnectorHold): connector.add_existing_label(plan({"connector_id": "x"}), authority_pair={"authority_generation": 7, "authority_head": H})
    assert not any("/issues/" in " ".join(argv) for argv, _ in runner.calls)
    with pytest.raises(TypeError): GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", capability_resolver=lambda: {})
