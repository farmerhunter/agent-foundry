"""One bounded GitHub CLI label-add connector.

The Human execution HDC owns credential selection.  This connector observes
only active host-level authentication and confines its one possible operation
to its constructor's exact repository, Issue and label plan.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping
from typing import Any

CONNECTOR_ID = "github-cli-issue-label"
CONNECTOR_VERSION = "1"
CONFINEMENT = "exact_repo_issue_label"
_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_LABEL = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PRINCIPAL = re.compile(r"^[A-Za-z0-9-]{1,39}$")
_SCOPE = re.compile(r"^[A-Za-z0-9:_-]{1,64}$")
_TOKEN_SOURCE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_REASONS = {"hold_capability_unavailable", "hold_capability_untrusted", "hold_auth_mismatch",
            "hold_scope_unavailable", "hold_scope_insufficient", "hold_target_invalid",
            "hold_target_type_invalid", "hold_label_absent", "hold_preimage_stale",
            "hold_authority_pair_stale", "hold_provider_conflict", "hold_provider_rate_limited",
            "hold_provider_unavailable", "hold_write_failed", "hold_readback_mismatch",
            "hold_second_forward_attempt", "hold_schema", "hold_output_invalid"}


class GitHubCliConnectorHold(ValueError):
    def __init__(self, reason: str):
        self.reason = reason if reason in _REASONS else "hold_schema"
        super().__init__(self.reason)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def capability_digest(value: Mapping[str, Any]) -> str:
    return _digest(value)


def _target(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"owner", "repository", "number", "kind"}:
        raise GitHubCliConnectorHold("hold_target_invalid")
    owner, repository, number, kind = value.get("owner"), value.get("repository"), value.get("number"), value.get("kind")
    if not isinstance(owner, str) or not _OWNER.fullmatch(owner) or not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise GitHubCliConnectorHold("hold_target_invalid")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise GitHubCliConnectorHold("hold_target_invalid")
    if kind not in {"issue", "pull_request"}:
        raise GitHubCliConnectorHold("hold_target_type_invalid")
    return {"owner": owner, "repository": repository, "number": number, "kind": kind}


def _plan(value: Any) -> dict[str, Any]:
    required = {"schema_version", "human_authorization_ref", "operation", "target", "label", "preimage_digest",
                "authority_generation", "authority_head", "expected_capability_digest"}
    if not isinstance(value, Mapping) or set(value) != required or value.get("schema_version") != "GitHubCliIssueLabelConnector-v1" or value.get("operation") != "add_existing_label":
        raise GitHubCliConnectorHold("hold_schema")
    if not isinstance(value.get("human_authorization_ref"), str) or not value["human_authorization_ref"] or len(value["human_authorization_ref"].encode()) > 256:
        raise GitHubCliConnectorHold("hold_schema")
    if not isinstance(value.get("label"), str) or not _LABEL.fullmatch(value["label"]):
        raise GitHubCliConnectorHold("hold_label_absent")
    if not isinstance(value.get("authority_generation"), int) or isinstance(value["authority_generation"], bool) or value["authority_generation"] < 0 or not isinstance(value.get("authority_head"), str) or not _DIGEST.fullmatch(value["authority_head"]):
        raise GitHubCliConnectorHold("hold_authority_pair_stale")
    for key, reason in (("preimage_digest", "hold_preimage_stale"), ("expected_capability_digest", "hold_capability_untrusted")):
        if not isinstance(value.get(key), str) or not _DIGEST.fullmatch(value[key]):
            raise GitHubCliConnectorHold(reason)
    return {**dict(value), "target": _target(value["target"])}


class GitHubCliIssueLabelConnector:
    network_capability = True
    production_eligibility = True
    trust_domain = "github_cli_managed_auth"

    def __init__(self, *, repository_owner: str, repository: str, runner: Callable[..., Any] | None = None) -> None:
        self._repository = _target({"owner": repository_owner, "repository": repository, "number": 1, "kind": "issue"})
        self._runner = runner or subprocess.run
        self._forward_receipts: set[str] = set()

    @property
    def repository_binding(self) -> dict[str, str]:
        return {"owner": self._repository["owner"], "repository": self._repository["repository"]}

    def capability_metadata(self) -> dict[str, Any]:
        try:
            return self._public_capability(self._resolve_capability())
        except GitHubCliConnectorHold:
            return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "host": "github.com",
                    "available": False, "credential_grant_attested": False, "operation_confinement": CONFINEMENT,
                    "authoritative": False, "confirmation_eligible": False}

    def _add_existing_label(self, plan: Mapping[str, Any], *, authority_pair: Mapping[str, Any]) -> dict[str, Any]:
        planned = _plan(plan)
        target = planned["target"]
        if self.repository_binding != {"owner": target["owner"], "repository": target["repository"]}:
            raise GitHubCliConnectorHold("hold_auth_mismatch")
        pair = {"authority_generation": planned["authority_generation"], "authority_head": planned["authority_head"]}
        if authority_pair != pair:
            raise GitHubCliConnectorHold("hold_authority_pair_stale")
        if self._execution_binding_digest() != planned["expected_capability_digest"]:
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        receipt_id = _digest({key: planned[key] for key in ("human_authorization_ref", "operation", "target", "label", "preimage_digest", "authority_generation", "authority_head")})
        if receipt_id in self._forward_receipts:
            raise GitHubCliConnectorHold("hold_second_forward_attempt")
        labels = self._read_labels(target)
        if _digest(labels) != planned["preimage_digest"]:
            raise GitHubCliConnectorHold("hold_preimage_stale")
        if planned["label"] in labels:
            return self._result("duplicate_no_mutation", planned, receipt_id, labels, 0)
        self._write(target, planned["label"])
        labels = self._read_labels(target)
        if planned["label"] not in labels:
            raise GitHubCliConnectorHold("hold_readback_mismatch")
        self._forward_receipts.add(receipt_id)
        return self._result("label_added", planned, receipt_id, labels, 1)

    def _resolve_capability(self) -> dict[str, Any]:
        result = self._call(("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"))
        if result["returncode"] != 0:
            raise GitHubCliConnectorHold("hold_capability_unavailable")
        try:
            parsed = json.loads(result["stdout"])
            accounts = parsed["hosts"]["github.com"]
        except (KeyError, TypeError, ValueError):
            raise GitHubCliConnectorHold("hold_capability_untrusted") from None
        if not isinstance(parsed, Mapping) or set(parsed) != {"hosts"} or not isinstance(accounts, list) or len(accounts) != 1:
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        principal, scopes = self._parse_auth_account(accounts[0])
        return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "host": "github.com",
                "active_principal": principal, "observable_host_scopes": sorted(scopes), "available": True,
                "credential_grant_attested": False, "operation_confinement": CONFINEMENT,
                "authoritative": False, "confirmation_eligible": False}

    @staticmethod
    def _parse_auth_account(value: Any) -> tuple[str, list[str]]:
        """Accept only the documented CLI shape or the prior sanitized fixture."""
        if not isinstance(value, Mapping):
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        legacy_keys = {"login", "scopes"}
        official_required = {"state", "active", "host", "login", "tokenSource", "gitProtocol"}
        official_allowed = official_required | {"scopes", "error"}
        keys = set(value)
        if keys == legacy_keys:
            principal, raw_scopes = value.get("login"), value.get("scopes")
            scopes = GitHubCliIssueLabelConnector._legacy_scopes(raw_scopes)
        elif official_required <= keys <= official_allowed:
            if value.get("state") != "success" or value.get("active") is not True or value.get("host") != "github.com":
                raise GitHubCliConnectorHold("hold_capability_untrusted")
            if "error" in value or not isinstance(value.get("tokenSource"), str) or not _TOKEN_SOURCE.fullmatch(value["tokenSource"]) or value.get("gitProtocol") != "https":
                raise GitHubCliConnectorHold("hold_capability_untrusted")
            principal, raw_scopes = value.get("login"), value.get("scopes")
            scopes = GitHubCliIssueLabelConnector._official_scopes(raw_scopes)
        else:
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        if not isinstance(principal, str) or not _PRINCIPAL.fullmatch(principal):
            raise GitHubCliConnectorHold("hold_auth_mismatch")
        if not scopes:
            raise GitHubCliConnectorHold("hold_scope_unavailable")
        if len(scopes) > 10 or len(set(scopes)) != len(scopes) or any(not _SCOPE.fullmatch(scope) for scope in scopes) or "repo" not in scopes:
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        return principal, sorted(scopes)

    @staticmethod
    def _legacy_scopes(value: Any) -> list[str]:
        if value == "unavailable":
            return []
        if not isinstance(value, list) or any(not isinstance(scope, str) for scope in value):
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        return value

    @staticmethod
    def _official_scopes(value: Any) -> list[str]:
        if not isinstance(value, str):
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        if not value or len(value.encode()) > 512:
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        scopes = [scope.strip() for scope in value.split(",")]
        if any(not scope for scope in scopes):
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        return scopes

    @staticmethod
    def _public_capability(value: Mapping[str, Any]) -> dict[str, Any]:
        """Return binding-safe metadata without the active auth identity."""
        return {"connector_id": value["connector_id"], "connector_version": value["connector_version"],
                "host": value["host"], "available": value["available"],
                "credential_grant_attested": False, "operation_confinement": CONFINEMENT,
                "authoritative": False, "confirmation_eligible": False}

    def _execution_binding_digest(self) -> str:
        """Private digest of the full fresh resolver fact, never returned."""
        return capability_digest(self._resolve_capability())

    def _endpoint(self, target: Mapping[str, Any]) -> str:
        return f"repos/{target['owner']}/{target['repository']}/issues/{target['number']}/labels"

    def _read_labels(self, target: Mapping[str, Any]) -> list[str]:
        result = self._call(("gh", "api", "--method", "GET", self._endpoint(target), "--jq", ".[ ].name".replace(" ", "")))
        if result["returncode"] != 0:
            raise self._provider_hold(result["returncode"], result["stderr"])
        labels = [item for item in result["stdout"].splitlines() if item]
        if len(labels) > 100 or len(set(labels)) != len(labels) or any(not _LABEL.fullmatch(label) for label in labels):
            raise GitHubCliConnectorHold("hold_output_invalid")
        return sorted(labels)

    def _write(self, target: Mapping[str, Any], label: str) -> None:
        result = self._call(("gh", "api", "--method", "POST", self._endpoint(target), "-f", f"labels[]={label}"))
        if result["returncode"] != 0:
            raise self._provider_hold(result["returncode"], result["stderr"], write=True)

    def _call(self, argv: tuple[str, ...]) -> dict[str, Any]:
        try:
            raw = self._runner(argv, shell=False, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            raise GitHubCliConnectorHold("hold_provider_unavailable") from None
        except OSError:
            raise GitHubCliConnectorHold("hold_capability_unavailable") from None
        except Exception:
            raise GitHubCliConnectorHold("hold_provider_unavailable") from None
        code = raw.get("returncode") if isinstance(raw, Mapping) else getattr(raw, "returncode", None)
        stdout = raw.get("stdout", "") if isinstance(raw, Mapping) else getattr(raw, "stdout", "")
        stderr = raw.get("stderr", "") if isinstance(raw, Mapping) else getattr(raw, "stderr", "")
        if not isinstance(code, int) or isinstance(code, bool) or not isinstance(stdout, str) or not isinstance(stderr, str) or len(stdout.encode()) > 4096 or len(stderr.encode()) > 4096:
            raise GitHubCliConnectorHold("hold_output_invalid")
        return {"returncode": code, "stdout": stdout, "stderr": stderr}

    @staticmethod
    def _provider_hold(code: int, stderr: str, *, write: bool = False) -> GitHubCliConnectorHold:
        if code == 409 or "HTTP 409" in stderr: return GitHubCliConnectorHold("hold_provider_conflict")
        if code == 429 or "HTTP 429" in stderr: return GitHubCliConnectorHold("hold_provider_rate_limited")
        if write and (code == 422 or "HTTP 422" in stderr): return GitHubCliConnectorHold("hold_label_absent")
        return GitHubCliConnectorHold("hold_write_failed" if write else "hold_provider_unavailable")

    @staticmethod
    def _result(outcome: str, plan: Mapping[str, Any], receipt_id: str, labels: list[str], mutation_count: int) -> dict[str, Any]:
        return {"schema_version": "GitHubCliIssueLabelConnector-v1", "outcome": outcome, "operation": "add_existing_label",
                "receipt_id": receipt_id, "target": plan["target"], "label": plan["label"], "readback_digest": _digest(labels),
                "mutation_count": mutation_count, "credential_grant_attested": False, "operation_confinement": CONFINEMENT,
                "authoritative": False, "confirmation_eligible": False}


__all__ = ["CONNECTOR_ID", "CONNECTOR_VERSION", "CONFINEMENT", "GitHubCliConnectorHold", "GitHubCliIssueLabelConnector", "capability_digest"]
