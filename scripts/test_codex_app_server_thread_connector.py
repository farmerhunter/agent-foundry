"""Fake-transport checks for the owner-bound Codex App Server connector."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

import pytest

from codex_app_server_thread_connector import (
    BinaryIdentity,
    CodexAppServerThreadConnector,
    ConnectorHold,
    PostDispatchHold,
    SOURCE_KINDS,
    StdioJsonRpcTransport,
    verify_codex_binary,
)


INITIALIZED = {"userAgent": "codex-test", "platformFamily": "unix", "platformOs": "macos", "codexHome": "/private"}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.notifications = []
        self.closed = False

    def request(self, method, params):
        self.calls.append((method, dict(params)))
        if not self.responses:
            raise AssertionError("unexpected request")
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def notify(self, method, params):
        self.notifications.append((method, dict(params)))

    def close(self):
        self.closed = True


def _thread(ident: str, root: str, name: str | None = None) -> dict:
    return {"id": ident, "cwd": root, "name": name, "preview": "private content", "turns": [{"private": True}]}


def test_handshake_full_pagination_create_name_and_read_use_only_stable_surface() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = str(Path(directory).resolve())
        transport = FakeTransport([
            INITIALIZED,
            {"data": [_thread("old", root, "unmanaged")], "nextCursor": "page-2"},
            {"data": [], "nextCursor": None},
            {"thread": _thread("new", root)},
            {},
            {"thread": _thread("new", root, "AF18 RoleHub")},
            {"thread": _thread("new", root, "AF18 RoleHub")},
        ])
        connector = CodexAppServerThreadConnector(transport, project_id="owner-project", project_root=root)
        assert connector.list_threads(root)[0].project_id == "owner-project"
        created = connector.create_thread(root)
        assert created.id == "new" and created.project_id == "owner-project"
        named = connector.set_thread_name("new", "AF18 RoleHub")
        assert named.name == "AF18 RoleHub"
        assert connector.read_thread("new", include_turns=False).id == "new"
        assert transport.notifications == [("initialized", {})]
        assert [method for method, _ in transport.calls] == [
            "initialize", "thread/list", "thread/list", "thread/start",
            "thread/name/set", "thread/read", "thread/read",
        ]
        first_page, second_page = transport.calls[1][1], transport.calls[2][1]
        assert first_page["cwd"] == [root] and first_page["sourceKinds"] == list(SOURCE_KINDS)
        assert second_page["cursor"] == "page-2"
        assert transport.calls[3][1] == {"cwd": root, "ephemeral": False}
        assert transport.calls[5][1]["includeTurns"] is False
        assert set(SOURCE_KINDS) == {"cli", "vscode", "exec", "appServer", "subAgent", "subAgentReview", "subAgentCompact", "subAgentThreadSpawn", "subAgentOther", "unknown"}


def test_cwd_drift_loop_and_forged_method_locator_hold_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = str(Path(directory).resolve())
        drift = FakeTransport([INITIALIZED, {"data": [_thread("x", "/foreign", "x")], "nextCursor": None}])
        connector = CodexAppServerThreadConnector(drift, project_id="owner", project_root=root)
        with pytest.raises(ConnectorHold):
            connector.list_threads(root)
        with pytest.raises(ConnectorHold):
            connector.list_threads("/caller-forged")

        loop = FakeTransport([INITIALIZED, {"data": [], "nextCursor": "same"}, {"data": [], "nextCursor": "same"}])
        connector = CodexAppServerThreadConnector(loop, project_id="owner", project_root=root)
        with pytest.raises(ConnectorHold):
            connector.list_threads(root)
        with pytest.raises(NotImplementedError):
            connector.navigate_to_thread("x")


def test_post_dispatch_start_ambiguity_returns_invalid_metadata_for_owner_truth() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = str(Path(directory).resolve())
        transport = FakeTransport([INITIALIZED, PostDispatchHold("response_lost")])
        connector = CodexAppServerThreadConnector(transport, project_id="owner", project_root=root)
        result = connector.create_thread(root)
        assert result.id == "" and result.cwd == root and result.project_id == "owner"


def test_stdio_parser_matches_id_ignores_notifications_and_rejects_server_requests() -> None:
    transport = object.__new__(StdioJsonRpcTransport)
    transport._next_id = 1
    transport._closed = False
    sent = []
    transport._send = lambda envelope, dispatched_error: sent.append((envelope, dispatched_error))
    lines = iter([
        '{"jsonrpc":"2.0","method":"thread/started","params":{}}\n',
        '{"jsonrpc":"2.0","id":1,"result":{"data":[],"nextCursor":null}}\n',
    ])
    transport._line = lambda: next(lines)
    assert transport.request("thread/list", {})["data"] == []
    assert sent[0][1] is True

    transport._next_id = 2
    transport._line = lambda: '{"jsonrpc":"2.0","id":9,"method":"account/login/start","params":{}}\n'
    with pytest.raises(PostDispatchHold):
        transport.request("thread/read", {"threadId": "x", "includeTurns": False})
    with pytest.raises(ConnectorHold):
        transport.request("turn/start", {})


def test_binary_identity_is_exact_and_checked_without_starting_transport() -> None:
    with tempfile.TemporaryDirectory() as directory:
        binary = Path(directory) / "codex"
        binary.write_bytes(b"fixture executable")
        os.chmod(binary, 0o700)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        identity = verify_codex_binary(binary, digest, "codex-cli fixture", releases={digest: "codex-cli fixture"})
        assert identity == BinaryIdentity(str(binary.resolve()), digest, "codex-cli fixture")
        with pytest.raises(ConnectorHold):
            verify_codex_binary(binary, "0" * 64, "codex-cli fixture", releases={digest: "codex-cli fixture"})
        with pytest.raises(ConnectorHold):
            verify_codex_binary(binary, digest, "wrong", releases={digest: "codex-cli fixture"})
        link = Path(directory) / "link"
        link.symlink_to(binary)
        assert verify_codex_binary(link, digest, "codex-cli fixture", releases={digest: "codex-cli fixture"}).path == str(binary.resolve())
