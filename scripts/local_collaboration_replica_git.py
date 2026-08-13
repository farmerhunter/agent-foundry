"""Bounded Git exchange for immutable local-collaboration replica bundles.

The adapter owns only a dedicated Git branch and bundle files.  It never opens
or imports into SQLite: callers retain owner verification and local authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import local_collaboration_replica as replica

VERSION = "LocalCollaborationReplicaGit-v1"
BRANCH = "refs/heads/agent-foundry-replica-v1"
MAX_BUNDLES = 100
PATH_PART = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class GitReplicaTransportHold(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe(value: Any) -> str:
    if not isinstance(value, str) or not PATH_PART.fullmatch(value):
        raise GitReplicaTransportHold("hold_transport_path_invalid")
    return value


class GitReplicaTransport:
    """Exchange validated immutable bundles through one fixed Git branch.

    ``repository`` must already be an isolated clone.  The adapter never runs
    init, changes remotes, or executes arbitrary Git arguments.
    """

    def __init__(self, *, repository: str | Path, remote_name: str = "origin") -> None:
        self._repository = Path(repository)
        self._remote_name = _safe(remote_name)

    def _git(self, *arguments: str, allow_missing_branch: bool = False) -> str:
        try:
            result = subprocess.run(("git", "-C", str(self._repository), *arguments), shell=False,
                                    capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitReplicaTransportHold("hold_transport_unavailable") from exc
        if result.returncode != 0:
            if allow_missing_branch and result.returncode == 2:
                return ""
            raise GitReplicaTransportHold("hold_transport_unavailable")
        if not isinstance(result.stdout, str) or len(result.stdout.encode()) > 1024 * 1024:
            raise GitReplicaTransportHold("hold_transport_invalid")
        return result.stdout

    def _check_clone(self) -> None:
        if not self._repository.is_dir() or self._git("rev-parse", "--is-inside-work-tree").strip() != "true":
            raise GitReplicaTransportHold("hold_transport_unavailable")
        if self._git("status", "--porcelain").strip():
            raise GitReplicaTransportHold("hold_transport_dirty")

    @staticmethod
    def _bundle(bundle: Any) -> tuple[dict[str, Any], str]:
        if not isinstance(bundle, dict):
            raise GitReplicaTransportHold("hold_transport_integrity")
        descriptor = bundle.get("replica_identity", {}).get("enrollment_descriptor") if isinstance(bundle.get("replica_identity"), dict) else None
        inspected = replica.inspect_bundle(bundle, descriptor)
        if inspected.get("outcome") != "replica_export_ready":
            raise GitReplicaTransportHold("hold_transport_integrity")
        project = _safe(bundle["project_id"])
        identity = bundle["replica_identity"]
        replica_id = _safe(identity["replica_id"])
        digest = bundle["bundle_digest"]
        if not isinstance(digest, str) or len(digest) != 64:
            raise GitReplicaTransportHold("hold_transport_integrity")
        return bundle, f"bundles/{project}/{replica_id}/{digest}.json"

    def _remote_branch_exists(self) -> bool:
        return bool(self._git("ls-remote", "--exit-code", self._remote_name, BRANCH, allow_missing_branch=True).strip())

    def _checkout_remote(self, exists: bool) -> None:
        if exists:
            self._git("fetch", "--no-tags", self._remote_name, BRANCH)
            self._git("checkout", "-B", "agent-foundry-replica-v1", "FETCH_HEAD")
        else:
            self._git("checkout", "--orphan", "agent-foundry-replica-v1")

    def publish_bundle(self, bundle: Any) -> dict[str, Any]:
        """Publish one immutable validated bundle; one push and no retry."""
        try:
            bundle, relative = self._bundle(bundle)
            self._check_clone()
            exists = self._remote_branch_exists()
            self._checkout_remote(exists)
            path = self._repository / relative
            encoded = _canonical(bundle)
            if path.exists():
                if path.read_bytes() != encoded:
                    raise GitReplicaTransportHold("hold_transport_integrity")
                return self._receipt("replica_transport_duplicate", bundle, mutation_count=0)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded)
            self._git("add", "--", relative)
            self._git("commit", "--no-gpg-sign", "-m", f"replica bundle {bundle['bundle_digest']}")
            self._git("push", self._remote_name, f"HEAD:{BRANCH}")
            return self._receipt("replica_transport_published", bundle, mutation_count=1)
        except (GitReplicaTransportHold, replica.ReplicaHold) as exc:
            return self._hold(getattr(exc, "reason", "hold_transport_integrity"), bundle if isinstance(bundle, dict) else None)

    def fetch_bundles(self, project_id: str) -> dict[str, Any]:
        """Fetch and validate the complete fixed-branch event-set view."""
        try:
            project_id = _safe(project_id)
            self._check_clone()
            if not self._remote_branch_exists():
                return self._fetch_receipt("replica_transport_offline", project_id, bundles=[])
            self._git("fetch", "--no-tags", self._remote_name, BRANCH)
            names = [name for name in self._git("ls-tree", "-r", "--name-only", "FETCH_HEAD", "--", f"bundles/{project_id}").splitlines() if name]
            if len(names) > MAX_BUNDLES or any(not name.endswith(".json") for name in names):
                raise GitReplicaTransportHold("hold_transport_integrity")
            bundles = []
            for name in sorted(names):
                raw = self._git("show", f"FETCH_HEAD:{name}")
                try:
                    bundle = json.loads(raw)
                except (TypeError, ValueError) as exc:
                    raise GitReplicaTransportHold("hold_transport_integrity") from exc
                checked, expected = self._bundle(bundle)
                if expected != name:
                    raise GitReplicaTransportHold("hold_transport_integrity")
                bundles.append(checked)
            return self._fetch_receipt("replica_transport_fetched", project_id, bundles=bundles)
        except (GitReplicaTransportHold, replica.ReplicaHold) as exc:
            return self._fetch_hold(getattr(exc, "reason", "hold_transport_integrity"), project_id)

    def converge(self, project_id: str) -> dict[str, Any]:
        fetched = self.fetch_bundles(project_id)
        if fetched["outcome"] != "replica_transport_fetched":
            return fetched
        events = [event for bundle in fetched["bundles"] for event in bundle["events"]]
        view = replica.reduce_converged_view(events)
        return {"schema_version": VERSION, "outcome": "replica_transport_converged" if view.get("outcome") == "replica_converged" else "replica_transport_hold",
                "project_id": project_id, "bundle_digests": [bundle["bundle_digest"] for bundle in fetched["bundles"]],
                "view": view, "authoritative": False, "remote_mutation_performed": False}

    @staticmethod
    def _receipt(outcome: str, bundle: dict[str, Any], *, mutation_count: int) -> dict[str, Any]:
        return {"schema_version": VERSION, "outcome": outcome, "project_id": bundle["project_id"], "bundle_digest": bundle["bundle_digest"],
                "mutation_count": mutation_count, "retries": 0, "authoritative": False, "confirmation_eligible": False}

    @staticmethod
    def _fetch_receipt(outcome: str, project_id: str, *, bundles: list[dict[str, Any]]) -> dict[str, Any]:
        return {"schema_version": VERSION, "outcome": outcome, "project_id": project_id, "bundles": bundles,
                "authoritative": False, "confirmation_eligible": False}

    @staticmethod
    def _hold(reason: str, bundle: dict[str, Any] | None) -> dict[str, Any]:
        return {"schema_version": VERSION, "outcome": "replica_transport_hold", "reason": reason,
                "project_id": bundle.get("project_id") if bundle else None, "authoritative": False, "confirmation_eligible": False}

    @staticmethod
    def _fetch_hold(reason: str, project_id: str) -> dict[str, Any]:
        return {"schema_version": VERSION, "outcome": "replica_transport_hold", "reason": reason,
                "project_id": project_id, "authoritative": False, "confirmation_eligible": False}


__all__ = ["BRANCH", "GitReplicaTransport", "GitReplicaTransportHold", "VERSION"]
