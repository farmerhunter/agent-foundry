import os
import math
import json
import stat
import sqlite3
import subprocess
import sys
import signal
import tempfile
import threading
import time
import unittest
from pathlib import Path

from local_collaboration_ledger import LedgerBackupError, LedgerBusyError, LedgerConflictError, LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError, LocalCollaborationLedger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = LocalCollaborationLedger.create_project(projects_root=self.tmp.name)

    def tearDown(self):
        self.ledger.close(); self.tmp.cleanup()

    def test_storage_and_pragmas(self):
        self.assertEqual(stat.S_IMODE(Path(self.ledger.directory).stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.ledger.path.stat().st_mode), 0o600)
        self.assertEqual(self.ledger._conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.ledger._conn.execute("PRAGMA synchronous").fetchone()[0], 2)
        self.assertEqual(self.ledger.pragma_receipt(), {"journal_mode": "wal", "synchronous": "2", "foreign_keys": "1", "trusted_schema": "0", "busy_timeout": "5000", "wal_autocheckpoint": "1000"})

    def test_fresh_close_read_only_probe_preserves_wal_and_mtime(self):
        path = self.ledger.path
        self.ledger.close()
        sidecars = [Path(str(path) + suffix) for suffix in ("-wal", "-shm")]
        self.assertFalse(any(sidecar.exists() for sidecar in sidecars))
        self.assertEqual(path.read_bytes()[18:20], b"\x02\x02")
        before = path.stat().st_mtime_ns
        reopened = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name, create=False)
        try:
            self.assertEqual(reopened.pragma_receipt()["journal_mode"], "wal")
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertFalse(any(sidecar.exists() for sidecar in sidecars))
        finally:
            reopened.close()

    def test_read_only_probe_has_independent_no_mutation_receipt(self):
        path = self.ledger.path
        self.ledger.close()
        sidecars = {suffix: Path(str(path) + suffix) for suffix in ("-wal", "-shm")}
        before = {"db": path.stat().st_mtime_ns, **{suffix: (p.exists(), p.stat().st_mtime_ns if p.exists() else None) for suffix, p in sidecars.items()}}
        reopened = LocalCollaborationLedger(db_path=path, create=False)
        reopened.close()
        after = {"db": path.stat().st_mtime_ns, **{suffix: (p.exists(), p.stat().st_mtime_ns if p.exists() else None) for suffix, p in sidecars.items()}}
        self.assertEqual(before, after)

    def test_binding_and_projection_checkpoint(self):
        self.ledger.bind_project("path", "/tmp/project")
        self.assertEqual(self.ledger.resolve_binding("path"), "/tmp/project")
        with self.assertRaises(LedgerConflictError): self.ledger.bind_project("path", "/tmp/other")
        self.ledger.bind_project("path", "/tmp/other", rebind=True)
        self.assertEqual(self.ledger.resolve_binding("path"), "/tmp/other")
        self.ledger.append_event("work.accepted", {"id": 1})
        self.ledger.checkpoint_projection("board", 1, {"open": 1})
        self.assertEqual(self.ledger.load_projection("board")["sequence"], 1)
        self.assertTrue(self.ledger.verify_projection("board"))
        self.ledger.rebuild_projection("board", lambda events: {"count": len(events)})
        self.assertEqual(self.ledger.load_projection("board")["payload"], {"count": 1})
        self.assertTrue(self.ledger.delete_projection("board")); self.assertFalse(self.ledger.verify_projection("board"))

    def test_append_sequence_chain_and_idempotency(self):
        event_id = "11111111-1111-1111-1111-111111111111"
        first = self.ledger.append_event("work.accepted", {"title": "x"}, event_id=event_id)
        same = self.ledger.append_event("work.accepted", {"title": "x"}, event_id=event_id)
        self.assertEqual(first, same); self.assertEqual(self.ledger.list_events()[0].sequence, 1)
        self.ledger.append_batch([{"event_type": "candidate.accepted", "payload": {"id": 1}}, {"event_type": "work.closed", "payload": {"id": 2}}])
        self.assertTrue(self.ledger.verify()); self.assertEqual(len(self.ledger.list_events()), 3)

    def test_divergent_duplicate_is_held_and_atomic(self):
        event_id = "22222222-2222-2222-2222-222222222222"
        self.ledger.append_event("x", {"a": 1}, event_id=event_id)
        with self.assertRaises(LedgerConflictError): self.ledger.append_event("x", {"a": 2}, event_id=event_id)
        self.assertEqual(len(self.ledger.list_events()), 1)
        with self.assertRaises(LedgerConflictError): self.ledger.append_event("x", {"a": 1}, event_id=event_id)
        self.ledger.close()
        reopened = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)
        with self.assertRaises(LedgerConflictError): reopened.append_event("x", {"a": 2}, event_id=event_id)
        self.assertEqual(reopened._conn.execute("SELECT COUNT(*) FROM holds WHERE event_id=?", (event_id,)).fetchone()[0], 1)
        reopened.close()

    def test_duplicate_identity_includes_event_fields_and_root(self):
        event_id = "33333333-3333-3333-3333-333333333333"
        self.ledger.append_event("x", {"a": 1}, event_id=event_id, actor="a", source="local")
        with self.assertRaises(LedgerConflictError): self.ledger.append_event("x", {"a": 1}, event_id=event_id, actor="b", source="local")
        with self.assertRaises(ValueError): self.ledger.append_event("x", {"a": 1}, event_id="44444444-4444-4444-4444-444444444444", source="tool_output")
        with self.assertRaises(LedgerConflictError): self.ledger.append_event("x", {"a": 1}, root=str(__import__('uuid').uuid4()))

    def test_privacy_and_batch_rollback(self):
        with self.assertRaises(ValueError): self.ledger.append_event("x", {"raw_transcript": "secret"})
        for field in ("prompt", "tool_output", "raw_transcript", "secret", "native_history"):
            with self.assertRaises(ValueError):
                self.ledger.append_event("x", {"meta": {"items": [{field: "secret"}]}})
        self.ledger.append_event("x", {"meta": {"labels": ["safe"], "source": "local"}})
        with self.assertRaises(ValueError): self.ledger.append_batch([{"event_type": "ok", "payload": {}}, {"event_type": "bad", "payload": {"prompt": "x"}}])
        self.assertEqual(len(self.ledger.list_events()), 1)

    def test_strict_json_payloads(self):
        with self.assertRaises(ValueError): self.ledger.append_event("x", {1: "non-string-key"})
        with self.assertRaises(ValueError): self.ledger.append_event("x", {"value": math.nan})
        with self.assertRaises(ValueError): self.ledger.append_event("x", {"value": math.inf})

    def test_tamper_and_backup(self):
        self.ledger.append_event("x", {"a": 1})
        backup = Path(self.tmp.name) / "backup.db"
        self.ledger.backup(backup)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertTrue((Path(str(backup) + ".receipt.json")).exists())
        with self.assertRaises(LedgerConflictError): self.ledger.backup(backup)
        restored_path = Path(self.tmp.name) / "restored" / "collaboration.db"
        restored = LocalCollaborationLedger.restore(backup, restored_path, expected_project_id=self.ledger.project_id)
        self.assertEqual(restored.project_id, self.ledger.project_id)
        restored.close()
        self.ledger._conn.execute("UPDATE events SET payload='{}' WHERE sequence=1")
        with self.assertRaises(LedgerIntegrityError): self.ledger.verify()

    def test_backup_receipt_tamper_is_backup_hold(self):
        self.ledger.append_event("x", {"a": 1})
        backup = Path(self.tmp.name) / "tamper-backup.db"
        self.ledger.backup(backup)
        receipt = Path(str(backup) + ".receipt.json")
        receipt.write_text("not-json")
        with self.assertRaises(LedgerBackupError):
            LocalCollaborationLedger.restore(backup, Path(self.tmp.name) / "tamper-restore" / "collaboration.db", expected_project_id=self.ledger.project_id)

    def test_subprocess_crash_rolls_back_uncommitted_batch(self):
        path = str(self.ledger.path)
        prior = self.ledger.append_event("prior", {"ok": True}, event_id="99999999-9999-9999-9999-999999999999")
        prior_head = prior.event_hash
        self.ledger.close()
        code = (
            "import os,signal,sys; from local_collaboration_ledger import LocalCollaborationLedger; "
            "l=LocalCollaborationLedger.open_existing(sys.argv[1], expected_project_id=sys.argv[2]); "
            "l._conn.create_function('crash_now',0,lambda: os.kill(os.getpid(),signal.SIGKILL)); "
            "l._conn.execute(\"CREATE TEMP TRIGGER kill_after_first AFTER INSERT ON events BEGIN SELECT crash_now(); END\"); "
            "l.append_batch([{'event_type':'crash.one','payload':{'n':1},'event_id':'66666666-6666-6666-6666-666666666666'}, {'event_type':'crash.two','payload':{'n':2},'event_id':'77777777-7777-7777-7777-777777777777'}])"
        )
        result = subprocess.run([sys.executable, "-c", code, path, self.ledger.project_id], env={**os.environ, "PYTHONPATH": "scripts"}, capture_output=True)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        reopened = LocalCollaborationLedger.open_existing(path, expected_project_id=self.ledger.project_id)
        try:
            events = reopened.list_events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_hash, prior_head)
            self.assertTrue(reopened.verify())
            self.assertEqual(reopened._conn.execute("SELECT COUNT(*) FROM holds").fetchone()[0], 0)
            self.assertEqual(reopened._conn.execute("SELECT COUNT(*) FROM projections").fetchone()[0], 0)
        finally:
            reopened.close()

    def test_subprocess_post_commit_receipt_loss_is_idempotent(self):
        path = str(self.ledger.path)
        project_id = self.ledger.project_id
        self.ledger.close()
        code = (
            "import os,sys; from local_collaboration_ledger import LocalCollaborationLedger; "
            "l=LocalCollaborationLedger.open_existing(sys.argv[1], expected_project_id=sys.argv[2]); "
            "l.append_event('receipt.loss', {'ok': True}, event_id='88888888-8888-8888-8888-888888888888'); os._exit(0)"
        )
        result = subprocess.run([sys.executable, "-c", code, path, project_id], env={**os.environ, "PYTHONPATH": "scripts"}, capture_output=True)
        self.assertEqual(result.returncode, 0)
        reopened = LocalCollaborationLedger.open_existing(path, expected_project_id=project_id)
        try:
            before = len(reopened.list_events())
            same = reopened.append_event("receipt.loss", {"ok": True}, event_id="88888888-8888-8888-8888-888888888888")
            self.assertEqual(len(reopened.list_events()), before)
            self.assertEqual(same.event_id, "88888888-8888-8888-8888-888888888888")
        finally:
            reopened.close()

    def test_backup_snapshot_remains_coherent_during_append(self):
        self.ledger.append_event("before", {"n": 0})
        backup = Path(self.tmp.name) / "concurrent-backup.db"
        done = threading.Event()

        def append_during_backup():
            writer = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
            try:
                writer.append_event("during", {"n": 1})
            finally:
                writer.close(); done.set()

        worker = threading.Thread(target=append_during_backup)
        worker.start()
        self.ledger.backup(backup)
        worker.join(timeout=5)
        self.assertTrue(done.is_set())
        restored_path = Path(self.tmp.name) / "snapshot" / "collaboration.db"
        restored = LocalCollaborationLedger.restore(backup, restored_path, expected_project_id=self.ledger.project_id)
        try:
            self.assertTrue(restored.verify())
            receipt = json.loads(Path(str(backup) + ".receipt.json").read_text())
            events = restored.list_events()
            head = events[-1].event_hash if events else "0" * 64
            self.assertEqual(len(events), receipt["generation"])
            self.assertEqual(head, receipt["source_head"])
        finally:
            restored.close()

    def test_permission_and_schema_fail_closed(self):
        self.ledger.close()
        os.chmod(Path(self.tmp.name) / self.ledger.project_id, 0o755)
        with self.assertRaises(Exception):
            LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)

    def test_registry_discovery_and_input_caps(self):
        self.ledger.bind_project("path", "/tmp/discover")
        self.assertEqual(LocalCollaborationLedger.discover_by_binding(self.tmp.name, "path", "/tmp/discover"), [self.ledger.project_id])
        with self.assertRaises(ValueError): self.ledger.append_batch([{"event_type": "x", "payload": {}, "unknown": 1}])
        nested = value = {}
        for _ in range(14): value["x"] = {}; value = value["x"]
        with self.assertRaises(ValueError): self.ledger.append_event("x", nested)
        os.chmod(Path(self.tmp.name) / self.ledger.project_id, 0o700)
        reopened = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)
        reopened._conn.execute("UPDATE ledger_metadata SET value='9.9.9' WHERE key='schema_version'")
        reopened.close()
        with self.assertRaises(LedgerIntegrityError):
            LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)

    def test_discovery_preserves_schema_and_permission_holds(self):
        self.ledger.bind_project("repo", "schema-case")
        self.ledger.close()
        db = Path(self.tmp.name) / self.ledger.project_id / "collaboration.db"
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE ledger_metadata SET value='9.9.9' WHERE key='schema_version'")
        with self.assertRaises(LedgerSchemaError):
            LocalCollaborationLedger.discover_by_binding(self.tmp.name, "repo", "schema-case")
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE ledger_metadata SET value=? WHERE key='schema_version'", ("1.0.0",))
        directory = db.parent
        os.chmod(directory, 0o755)
        try:
            with self.assertRaises(LedgerPermissionError):
                LocalCollaborationLedger.discover_by_binding(self.tmp.name, "repo", "schema-case")
        finally:
            os.chmod(directory, 0o700)

    def test_discovery_preserves_truncated_database_integrity_hold(self):
        self.ledger.close()
        source = Path(self.tmp.name) / self.ledger.project_id / "collaboration.db"
        corrupt_root = Path(self.tmp.name) / "corrupt-root" / self.ledger.project_id
        corrupt_root.mkdir(parents=True)
        os.chmod(corrupt_root, 0o700)
        corrupt = corrupt_root / "collaboration.db"
        data = source.read_bytes()
        corrupt.write_bytes(data[:64])
        os.chmod(corrupt, 0o600)
        with self.assertRaises(LedgerIntegrityError):
            LocalCollaborationLedger.discover_by_binding(Path(self.tmp.name) / "corrupt-root", "repo", "missing")

    def test_existing_rw_never_recreates_or_changes_identity(self):
        path = self.ledger.path
        project_id = self.ledger.project_id
        self.ledger.close()
        opened = LocalCollaborationLedger.open_existing(path, expected_project_id=project_id)
        opened.append_event("restart", {"ok": True})
        opened.close()
        reopened = LocalCollaborationLedger.open_existing(path, expected_project_id=project_id)
        try:
            self.assertEqual(reopened.project_id, project_id)
        finally:
            reopened.close()
        with self.assertRaises(LedgerIntegrityError):
            LocalCollaborationLedger.open_existing(Path(self.tmp.name) / "missing" / "collaboration.db", expected_project_id=project_id)

    def test_restart_replay_and_post_commit_retry_are_deterministic(self):
        event_id = "55555555-5555-5555-5555-555555555555"
        first = self.ledger.append_event("restart", {"n": 1}, event_id=event_id)
        self.ledger.close()
        reopened = LocalCollaborationLedger.open_existing(Path(self.tmp.name) / self.ledger.project_id / "collaboration.db", expected_project_id=self.ledger.project_id)
        try:
            self.assertEqual(reopened.append_event("restart", {"n": 1}, event_id=event_id), first)
            self.assertTrue(reopened.verify())
        finally:
            reopened.close()

    def test_precommit_invalid_batch_rolls_back_without_partial_event(self):
        with self.assertRaises(ValueError):
            self.ledger.append_batch([{"event_type": "ok", "payload": {"a": 1}}, {"event_type": "bad", "payload": {"prompt": "x"}}])
        self.assertEqual(self.ledger.list_events(), [])

    def test_busy_writer_is_bounded_and_classified(self):
        lock = sqlite3.connect(self.ledger.path, timeout=0, isolation_level=None)
        lock.execute("BEGIN IMMEDIATE")
        writer = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
        started = time.monotonic()
        try:
            with self.assertRaises(LedgerBusyError):
                writer.append_event("busy", {"ok": True})
        finally:
            writer.close()
            lock.execute("ROLLBACK"); lock.close()
        self.assertLess(time.monotonic() - started, 8)

    def test_subprocess_missing_authority_does_not_create(self):
        missing = Path(self.tmp.name) / "missing.db"
        code = "from local_collaboration_ledger import LocalCollaborationLedger; LocalCollaborationLedger.open_existing(%r, expected_project_id='00000000-0000-0000-0000-000000000000')" % str(missing)
        result = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": "scripts"}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(missing.exists())


if __name__ == "__main__": unittest.main()
