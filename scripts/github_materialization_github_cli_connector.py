"""Bounded GitHub CLI label connector.

This module is deliberately separate from :class:`FakeConnector`.  It owns
only one future live capability: adding one already-approved, existing label
to one existing Issue or pull request, followed by a same-target readback.
Tests inject ``runner``; this module never reads tokens or environment auth.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import urllib.parse
import uuid
from collections.abc import Callable, Mapping
from typing import Any


CONNECTOR_ID = "github-cli-issue-label"
CONNECTOR_VERSION = "1"
_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_LABEL = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PRINCIPAL = re.compile(r"^[A-Za-z0-9-]{1,39}$")
_SCOPE = re.compile(r"^[A-Za-z0-9:_-]{1,64}$")
_REASONS = {
    "hold_capability_unavailable", "hold_capability_untrusted",
    "hold_auth_mismatch", "hold_scope_unavailable", "hold_scope_insufficient",
    "hold_target_invalid", "hold_target_type_invalid", "hold_label_absent",
    "hold_preimage_stale", "hold_authority_pair_stale", "hold_duplicate",
    "hold_provider_conflict", "hold_provider_rate_limited", "hold_provider_unavailable",
    "hold_write_failed", "hold_readback_mismatch", "hold_rollback_incomplete",
    "hold_second_forward_attempt", "hold_schema", "hold_output_invalid",
    "hold_capability_broader_or_unobservable",
}


class GitHubCliConnectorHold(ValueError):
    """A privacy-safe, closed connector failure classification."""

    def __init__(self, reason: str):
        self.reason = reason if reason in _REASONS else "hold_schema"
        super().__init__(self.reason)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _validate_target(value: Any) -> dict[str, Any]:
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


def _validate_plan(value: Any) -> dict[str, Any]:
    required = {"schema_version", "human_authorization_ref", "operation", "target", "label", "preimage_digest", "authority_generation", "authority_head", "expected_capability_version", "expected_capability_digest"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise GitHubCliConnectorHold("hold_schema")
    if value.get("schema_version") != "GitHubCliIssueLabelConnector-v1" or value.get("operation") != "add_existing_label":
        raise GitHubCliConnectorHold("hold_schema")
    if not isinstance(value.get("human_authorization_ref"), str) or not value["human_authorization_ref"] or len(value["human_authorization_ref"].encode()) > 256:
        raise GitHubCliConnectorHold("hold_schema")
    if not isinstance(value.get("label"), str) or not _LABEL.fullmatch(value["label"]):
        raise GitHubCliConnectorHold("hold_label_absent")
    if not isinstance(value.get("authority_generation"), int) or isinstance(value["authority_generation"], bool) or value["authority_generation"] < 0:
        raise GitHubCliConnectorHold("hold_authority_pair_stale")
    if not isinstance(value.get("authority_head"), str) or not _DIGEST.fullmatch(value["authority_head"]):
        raise GitHubCliConnectorHold("hold_authority_pair_stale")
    if not isinstance(value.get("preimage_digest"), str) or not _DIGEST.fullmatch(value["preimage_digest"]):
        raise GitHubCliConnectorHold("hold_preimage_stale")
    if value.get("expected_capability_version") != CONNECTOR_VERSION:
        raise GitHubCliConnectorHold("hold_capability_untrusted")
    if not isinstance(value.get("expected_capability_digest"), str) or not _DIGEST.fullmatch(value["expected_capability_digest"]):
        raise GitHubCliConnectorHold("hold_capability_untrusted")
    target = _validate_target(value["target"])
    return {**dict(value), "target": target}


def _scope_list(value: Any) -> bool:
    return (isinstance(value, list) and bool(value) and len(value) <= 10
            and len(set(value)) == len(value) and all(isinstance(scope, str) and _SCOPE.fullmatch(scope) for scope in value))


def capability_digest(value: Mapping[str, Any]) -> str:
    """Digest the closed, connector-owned capability fact for Gate-1 binding."""
    return _digest(value)


class GitHubCliIssueLabelConnector:
    """One-operation connector using the GitHub CLI managed authentication.

    ``runner`` receives a fixed argv tuple and ``shell=False``.  Production
    callers may omit it; tests must inject a deterministic stub.
    """

    network_capability = True
    production_eligibility = True
    trust_domain = "github_cli_managed_auth"

    def __init__(self, *, repository_owner: str, repository: str,
                 runner: Callable[..., Any] | None = None) -> None:
        self._repository = _validate_target({"owner": repository_owner, "repository": repository, "number": 1, "kind": "issue"})
        self._runner = runner or subprocess.run
        self._forward_receipts: dict[str, dict[str, Any]] = {}

    @property
    def repository_binding(self) -> dict[str, str]:
        """The connector-owned operation confinement, without auth facts."""
        return {"owner": self._repository["owner"], "repository": self._repository["repository"]}

    @property
    def repository_capability_required(self) -> bool:
        return True

    def capability_metadata(self) -> dict[str, Any]:
        """Resolve the same normalized capability fact execution will bind."""
        try:
            return self._resolve_repository_capability()
        except GitHubCliConnectorHold:
            return self._unavailable_capability()

    def add_existing_label(self, plan: Mapping[str, Any], *, authority_pair: Mapping[str, Any]) -> dict[str, Any]:
        planned = _validate_plan(plan)
        target = planned["target"]
        if target["owner"] != self._repository["owner"] or target["repository"] != self._repository["repository"]:
            raise GitHubCliConnectorHold("hold_auth_mismatch")
        if authority_pair != {"authority_generation": planned["authority_generation"], "authority_head": planned["authority_head"]}:
            raise GitHubCliConnectorHold("hold_authority_pair_stale")
        capability = self._resolve_repository_capability()
        if capability_digest(capability) != planned["expected_capability_digest"]:
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        receipt_id = _digest({key: planned[key] for key in ("human_authorization_ref", "operation", "target", "label", "preimage_digest", "authority_generation", "authority_head")})
        if receipt_id in self._forward_receipts:
            raise GitHubCliConnectorHold("hold_second_forward_attempt")
        labels = self._read_labels(target)
        if _digest(labels) != planned["preimage_digest"]:
            raise GitHubCliConnectorHold("hold_preimage_stale")
        if planned["label"] in labels:
            return self._result("duplicate_no_mutation", planned, receipt_id, labels, mutation_count=0)
        self._write("POST", target, planned["label"])
        readback = self._read_labels(target)
        if planned["label"] not in readback:
            raise GitHubCliConnectorHold("hold_readback_mismatch")
        receipt = self._result("label_added", planned, receipt_id, readback, mutation_count=1)
        self._forward_receipts[receipt_id] = receipt
        return receipt

    def _unavailable_capability(self) -> dict[str, Any]:
        return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "provider": "github", "host": "github.com", "repository_restriction": f"{self._repository['owner']}/{self._repository['repository']}", "authenticated_principal": "unavailable", "observable_scopes": "unavailable", "minimum_scopes": ["repo"], "network_capability": True, "production_eligibility": True, "available": False}

    def _resolve_capability(self) -> dict[str, Any]:
        # ``hosts`` is the documented JSON field for `gh auth status`; do not
        # rely on unsupported login/scopes fields or token display output.
        result = self._call(("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"))
        if result["returncode"] != 0:
            raise GitHubCliConnectorHold("hold_capability_unavailable")
        try:
            parsed = json.loads(result["stdout"])
        except (TypeError, ValueError):
            raise GitHubCliConnectorHold("hold_capability_untrusted") from None
        if not isinstance(parsed, Mapping) or set(parsed) != {"hosts"} or not isinstance(parsed.get("hosts"), Mapping):
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        host_accounts = parsed["hosts"].get("github.com")
        if not isinstance(host_accounts, list) or len(host_accounts) != 1 or not isinstance(host_accounts[0], Mapping):
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        account = host_accounts[0]
        if set(account) != {"login", "scopes"}:
            raise GitHubCliConnectorHold("hold_capability_untrusted")
        principal, scopes = account.get("login"), account.get("scopes")
        if not isinstance(principal, str) or not _PRINCIPAL.fullmatch(principal):
            raise GitHubCliConnectorHold("hold_auth_mismatch")
        if scopes == "unavailable":
            raise GitHubCliConnectorHold("hold_scope_unavailable")
        if not _scope_list(scopes) or "repo" not in set(scopes):
            raise GitHubCliConnectorHold("hold_scope_insufficient")
        return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "provider": "github", "host": "github.com", "repository_restriction": f"{self._repository['owner']}/{self._repository['repository']}", "authenticated_principal": principal, "observable_scopes": sorted(scopes), "minimum_scopes": ["repo"], "network_capability": True, "production_eligibility": True, "available": True}

    def _resolve_repository_capability(self) -> dict[str, Any]:
        self._resolve_capability()
        # GitHub CLI managed authentication exposes host/account state and
        # OAuth scopes, but no credential-grant repository constraint nor an
        # Issues-metadata permission envelope.  The public bridge must never
        # manufacture that missing fact from a repository constructor value or
        # an API response field that GitHub does not provide.
        raise GitHubCliConnectorHold("hold_capability_broader_or_unobservable")

    def remove_same_label_if_added(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(receipt, Mapping) or receipt.get("outcome") != "label_added" or not isinstance(receipt.get("receipt_id"), str):
            raise GitHubCliConnectorHold("hold_schema")
        stored = self._forward_receipts.get(receipt["receipt_id"])
        if stored != dict(receipt):
            raise GitHubCliConnectorHold("hold_schema")
        target = _validate_target(receipt.get("target"))
        label = receipt.get("label")
        if not isinstance(label, str) or not _LABEL.fullmatch(label):
            raise GitHubCliConnectorHold("hold_schema")
        labels = self._read_labels(target)
        if label not in labels:
            raise GitHubCliConnectorHold("hold_rollback_incomplete")
        self._write("DELETE", target, label)
        readback = self._read_labels(target)
        if label in readback:
            raise GitHubCliConnectorHold("hold_rollback_incomplete")
        return {"schema_version": "GitHubCliIssueLabelConnector-v1", "outcome": "rollback_complete", "operation": "remove_same_label_if_added", "receipt_id": receipt["receipt_id"], "target": target, "label": label, "readback_digest": _digest(readback), "mutation_count": 1, "network_capability": True, "production_eligibility": True, "authoritative": False, "confirmation_eligible": False}

    def _endpoint(self, target: Mapping[str, Any]) -> str:
        return f"repos/{target['owner']}/{target['repository']}/issues/{target['number']}/labels"

    def _read_labels(self, target: Mapping[str, Any]) -> list[str]:
        result = self._call(("gh", "api", "--method", "GET", self._endpoint(target), "--jq", ".[ ].name".replace(" ", "")))
        if result["returncode"] != 0:
            raise self._provider_hold(result["returncode"], result["stderr"])
        labels = [line for line in result["stdout"].splitlines() if line]
        if len(labels) > 100 or any(not _LABEL.fullmatch(label) for label in labels) or len(set(labels)) != len(labels):
            raise GitHubCliConnectorHold("hold_output_invalid")
        return sorted(labels)

    def _write(self, method: str, target: Mapping[str, Any], label: str) -> None:
        endpoint = self._endpoint(target)
        if method == "POST":
            argv = ("gh", "api", "--method", "POST", endpoint, "-f", f"labels[]={label}")
        elif method == "DELETE":
            argv = ("gh", "api", "--method", "DELETE", endpoint + "/" + urllib.parse.quote(label, safe=""))
        else:
            raise GitHubCliConnectorHold("hold_schema")
        result = self._call(argv)
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
        returncode = raw.get("returncode") if isinstance(raw, Mapping) else getattr(raw, "returncode", None)
        stdout = raw.get("stdout", "") if isinstance(raw, Mapping) else getattr(raw, "stdout", "")
        stderr = raw.get("stderr", "") if isinstance(raw, Mapping) else getattr(raw, "stderr", "")
        if not isinstance(returncode, int) or isinstance(returncode, bool) or not isinstance(stdout, str) or not isinstance(stderr, str) or len(stdout.encode()) > 4096 or len(stderr.encode()) > 4096:
            raise GitHubCliConnectorHold("hold_output_invalid")
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}

    @staticmethod
    def _provider_hold(returncode: int, stderr: str, *, write: bool = False) -> GitHubCliConnectorHold:
        # Only fixed HTTP markers affect the classification; raw stderr never
        # leaves this function or becomes part of a receipt/exception.
        if returncode == 409 or "HTTP 409" in stderr: return GitHubCliConnectorHold("hold_provider_conflict")
        if returncode == 429 or "HTTP 429" in stderr: return GitHubCliConnectorHold("hold_provider_rate_limited")
        if write and (returncode == 422 or "HTTP 422" in stderr): return GitHubCliConnectorHold("hold_label_absent")
        return GitHubCliConnectorHold("hold_write_failed" if write else "hold_provider_unavailable")

    @staticmethod
    def _result(outcome: str, plan: Mapping[str, Any], receipt_id: str, labels: list[str], *, mutation_count: int) -> dict[str, Any]:
        return {"schema_version": "GitHubCliIssueLabelConnector-v1", "outcome": outcome, "operation": "add_existing_label", "receipt_id": receipt_id, "target": plan["target"], "label": plan["label"], "preimage_digest": plan["preimage_digest"], "readback_digest": _digest(labels), "mutation_count": mutation_count, "network_capability": True, "production_eligibility": True, "authoritative": False, "confirmation_eligible": False}


__all__ = ["CONNECTOR_ID", "CONNECTOR_VERSION", "GitHubCliConnectorHold", "GitHubCliIssueLabelConnector"]
