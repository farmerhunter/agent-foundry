#!/usr/bin/env python3
"""Owner-bound Codex App Server connector for local role topology."""
from __future__ import annotations

import hashlib
import json
import os
import selectors
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from codex_host_rolehub_adapter import ThreadMetadata


CLIENT_VERSION = "orch04-i2-cx1"
SOURCE_KINDS = (
    "cli", "vscode", "exec", "appServer", "subAgent",
    "subAgentReview", "subAgentCompact", "subAgentThreadSpawn",
    "subAgentOther", "unknown",
)
SUPPORTED_RELEASES = {
    "531957aaf16c742232ce6ea495ddc0208d959ea156b84a89cffad3f1b4d07efc": "codex-cli 0.133.0",
}


class ConnectorHold(RuntimeError):
    pass


class PostDispatchHold(ConnectorHold):
    pass


class JsonRpcTransport(Protocol):
    def request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def notify(self, method: str, params: Mapping[str, Any]) -> None: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class BinaryIdentity:
    path: str
    sha256: str
    version: str


def verify_codex_binary(
    path: str | Path,
    expected_sha256: str,
    expected_version: str,
    *,
    releases: Mapping[str, str] = SUPPORTED_RELEASES,
) -> BinaryIdentity:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ConnectorHold("binary_identity_mismatch")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ConnectorHold("binary_identity_mismatch") from exc
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ConnectorHold("binary_identity_mismatch")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or expected_sha256.lower() != expected_sha256:
        raise ConnectorHold("binary_identity_mismatch")
    actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if actual != expected_sha256 or releases.get(actual) != expected_version:
        raise ConnectorHold("binary_identity_mismatch")
    return BinaryIdentity(str(resolved), actual, expected_version)


class StdioJsonRpcTransport:
    """One sequential, bounded JSON-RPC connection over stdio."""

    def __init__(self, binary: BinaryIdentity, *, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds
        self._next_id = 1
        self._closed = False
        try:
            self._process = subprocess.Popen(
                [binary.path, "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
                shell=False,
            )
        except OSError as exc:
            raise ConnectorHold("transport_start_unavailable") from exc
        if self._process.stdin is None or self._process.stdout is None:
            self.close()
            raise ConnectorHold("transport_start_unavailable")

    def _send(self, envelope: Mapping[str, Any], *, dispatched_error: bool) -> None:
        if self._closed or self._process.poll() is not None:
            raise ConnectorHold("transport_unavailable")
        try:
            assert self._process.stdin is not None
            self._process.stdin.write(json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as exc:
            error = PostDispatchHold if dispatched_error else ConnectorHold
            raise error("transport_unavailable") from exc

    def _line(self) -> str:
        if self._closed or self._process.poll() is not None:
            raise ConnectorHold("transport_unavailable")
        assert self._process.stdout is not None
        selector = selectors.DefaultSelector()
        try:
            selector.register(self._process.stdout, selectors.EVENT_READ)
            if not selector.select(self._timeout):
                raise ConnectorHold("transport_timeout")
            line = self._process.stdout.readline()
        finally:
            selector.close()
        if not line:
            raise ConnectorHold("transport_unavailable")
        return line

    def request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        if method not in {"initialize", "thread/list", "thread/read", "thread/start", "thread/name/set"}:
            raise ConnectorHold("unsupported_method")
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)}, dispatched_error=True)
        try:
            for _ in range(101):
                try:
                    value = json.loads(self._line())
                except (json.JSONDecodeError, UnicodeError, TypeError, ValueError) as exc:
                    raise PostDispatchHold("malformed_response") from exc
                if not isinstance(value, Mapping) or value.get("jsonrpc") != "2.0":
                    raise PostDispatchHold("malformed_response")
                if "method" in value:
                    if "id" in value:
                        raise PostDispatchHold("unsupported_server_request")
                    continue
                if value.get("id") != request_id or ("result" in value) == ("error" in value):
                    raise PostDispatchHold("response_identity_mismatch")
                if "error" in value or not isinstance(value.get("result"), Mapping):
                    raise PostDispatchHold("server_request_failed")
                return value["result"]
            raise PostDispatchHold("notification_budget_exceeded")
        except PostDispatchHold:
            raise
        except ConnectorHold as exc:
            raise PostDispatchHold("transport_unavailable") from exc

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        if method != "initialized":
            raise ConnectorHold("unsupported_method")
        self._send({"jsonrpc": "2.0", "method": method, "params": dict(params)}, dispatched_error=False)

    def close(self) -> None:
        if getattr(self, "_closed", True):
            return
        self._closed = True
        process = self._process
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


class CodexAppServerThreadConnector:
    """Projects owner-attested identity onto exact-cwd host metadata."""

    def __init__(self, transport: JsonRpcTransport, *, project_id: str, project_root: str):
        root = Path(project_root)
        if not root.is_absolute() or root.is_symlink():
            raise ConnectorHold("sealed_owner_context_invalid")
        try:
            resolved = root.resolve(strict=True)
        except OSError as exc:
            raise ConnectorHold("sealed_owner_context_invalid") from exc
        if resolved != root or not root.is_dir() or not isinstance(project_id, str) or not project_id:
            raise ConnectorHold("sealed_owner_context_invalid")
        self._transport = transport
        self._project_id = project_id
        self._root = str(resolved)
        result = transport.request("initialize", {
            "clientInfo": {"name": "agent-foundry-orch04", "version": CLIENT_VERSION},
            "capabilities": {"experimentalApi": False},
        })
        if not all(isinstance(result.get(key), str) and result[key] for key in ("userAgent", "platformFamily", "platformOs")):
            raise ConnectorHold("initialize_failed")
        transport.notify("initialized", {})

    @classmethod
    def open(
        cls,
        binary: BinaryIdentity,
        *,
        project_id: str,
        project_root: str,
        transport_factory: Callable[[BinaryIdentity], JsonRpcTransport] | None = None,
    ) -> "CodexAppServerThreadConnector":
        transport = (transport_factory or StdioJsonRpcTransport)(binary)
        try:
            return cls(transport, project_id=project_id, project_root=project_root)
        except Exception:
            transport.close()
            raise

    def _cwd(self, value: str) -> None:
        if value != self._root:
            raise ConnectorHold("sealed_cwd_mismatch")

    def _metadata(self, value: Any) -> ThreadMetadata:
        if not isinstance(value, Mapping):
            raise ConnectorHold("malformed_thread")
        ident, cwd, name = value.get("id"), value.get("cwd"), value.get("name")
        if not isinstance(ident, str) or not ident or not isinstance(cwd, str):
            raise ConnectorHold("malformed_thread")
        self._cwd(cwd)
        if name is not None and not isinstance(name, str):
            raise ConnectorHold("malformed_thread")
        return ThreadMetadata(ident, cwd, name or "", self._project_id)

    def list_threads(self, cwd: str) -> list[ThreadMetadata]:
        self._cwd(cwd)
        cursor: str | None = None
        seen_cursors: set[str] = set()
        seen_ids: set[str] = set()
        output: list[ThreadMetadata] = []
        while True:
            params: dict[str, Any] = {"cwd": [self._root], "limit": 100, "sourceKinds": list(SOURCE_KINDS)}
            if cursor is not None:
                params["cursor"] = cursor
            result = self._transport.request("thread/list", params)
            data, next_cursor = result.get("data"), result.get("nextCursor")
            if not isinstance(data, list) or (next_cursor is not None and (not isinstance(next_cursor, str) or not next_cursor)):
                raise ConnectorHold("malformed_list")
            for value in data:
                item = self._metadata(value)
                if item.id in seen_ids:
                    raise ConnectorHold("duplicate_thread_identity")
                seen_ids.add(item.id)
                output.append(item)
            if next_cursor is None:
                return output
            if next_cursor in seen_cursors:
                raise ConnectorHold("pagination_loop")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def read_thread(self, id: str, include_turns: bool = False) -> ThreadMetadata:
        if not isinstance(id, str) or not id or include_turns is not False:
            raise ConnectorHold("invalid_read_request")
        result = self._transport.request("thread/read", {"threadId": id, "includeTurns": False})
        metadata = self._metadata(result.get("thread"))
        if metadata.id != id:
            raise ConnectorHold("thread_identity_mismatch")
        return metadata

    def create_thread(self, cwd: str) -> ThreadMetadata:
        self._cwd(cwd)
        try:
            result = self._transport.request("thread/start", {"cwd": self._root, "ephemeral": False})
        except PostDispatchHold:
            return ThreadMetadata("", self._root, "", self._project_id)
        try:
            return self._metadata(result.get("thread"))
        except ConnectorHold:
            return ThreadMetadata("", self._root, "", self._project_id)

    def set_thread_name(self, id: str, title: str) -> ThreadMetadata:
        if not isinstance(id, str) or not id or not isinstance(title, str) or not title:
            raise ConnectorHold("invalid_name_request")
        result = self._transport.request("thread/name/set", {"threadId": id, "name": title})
        if result:
            raise ConnectorHold("malformed_name_response")
        return self.read_thread(id, include_turns=False)

    def navigate_to_thread(self, id: str) -> Any:
        raise NotImplementedError("navigation_not_supported")

    def close(self) -> None:
        self._transport.close()


__all__ = [
    "BinaryIdentity", "CodexAppServerThreadConnector", "ConnectorHold",
    "JsonRpcTransport", "PostDispatchHold", "SOURCE_KINDS",
    "StdioJsonRpcTransport", "SUPPORTED_RELEASES", "verify_codex_binary",
]
