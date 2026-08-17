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
from dataclasses import FrozenInstanceError
from pathlib import Path

from local_collaboration_ledger import GENESIS, LedgerBackupError, LedgerBusyError, LedgerConflictError, LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError, LedgerStaleSnapshotError, LocalCollaborationLedger


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

    def test_active_path_repo_binding_snapshot_is_same_view_and_sanitized(self):
        project_root = Path(self.tmp.name) / "canonical-project"; project_root.mkdir(mode=0o700)
        self.ledger.bind_project("path", str(project_root.resolve()))
        self.ledger.bind_project("repo", "repo-opaque")
        self.ledger.append_event("work.accepted", {"id": 1})
        expected = self.ledger.list_events()[-1]
        self.ledger.close()
        view = LocalCollaborationLedger.active_path_repo_binding_snapshot(self.tmp.name, project_root.resolve())
        self.assertEqual(view.project_id, self.ledger.project_id)
        self.assertEqual((view.authority_generation, view.authority_head), (expected.sequence, expected.event_hash))
        self.assertNotIn(str(project_root), repr(view)); self.assertNotIn("repo-opaque", repr(view))
        self.ledger = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)

    def test_active_path_repo_binding_snapshot_holds_for_unreadable_candidate(self):
        project_root = Path(self.tmp.name) / "shared-project"; project_root.mkdir(mode=0o700)
        self.ledger.bind_project("path", str(project_root.resolve())); self.ledger.bind_project("repo", "repo-primary")
        primary_path = self.ledger.path; self.ledger.close()
        duplicate = LocalCollaborationLedger.create_project(projects_root=self.tmp.name)
        duplicate.bind_project("path", str(project_root.resolve())); duplicate.bind_project("repo", "repo-duplicate")
        duplicate_path = duplicate.path; duplicate.close()
        duplicate_path.write_bytes(b"not a sqlite authority")
        os.chmod(duplicate_path, 0o600)
        before = primary_path.read_bytes()
        with self.assertRaises((LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError, LedgerBusyError)):
            LocalCollaborationLedger.active_path_repo_binding_snapshot(self.tmp.name, project_root.resolve())
        self.assertEqual(primary_path.read_bytes(), before)
        self.ledger = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)

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
        with self.assertRaises(LedgerPermissionError):
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

    def test_conditional_append_commits_at_exact_empty_and_nonempty_pairs(self):
        first = self.ledger.conditional_append_batch(
            [{"event_type": "handoff.prepared", "payload": {"epoch": 1}, "event_id": "12121212-1212-1212-1212-121212121212"}],
            expected_generation=0, expected_head=GENESIS)
        self.assertEqual((first.status, first.generation, first.head, first.mutation_performed), ("appended", 1, first.event_refs[0][3], True))
        second = self.ledger.conditional_append_batch(
            [{"event_type": "handoff.locked", "payload": {"epoch": 1}, "event_id": "13131313-1313-1313-1313-131313131313"}],
            expected_generation=first.generation, expected_head=first.head)
        self.assertEqual((second.status, second.generation, second.mutation_performed), ("appended", 2, True))
        with self.assertRaises(TypeError):
            second.event_refs[0][0] = 9
        with self.assertRaises(FrozenInstanceError):
            second.event_refs += ((9, "x", "y", "z"),)
        self.assertEqual(json.loads(json.dumps(second.event_refs)), [list(second.event_refs[0])])
        self.assertTrue(self.ledger.verify())

    def test_conditional_append_stale_does_not_mutate_any_business_table(self):
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        other = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
        try:
            other.append_event("other.commit", {"n": 1}, event_id="14141414-1414-1414-1414-141414141414")
        finally:
            other.close()
        before = self._business_rows()
        with self.assertRaises(LedgerStaleSnapshotError) as caught:
            self.ledger.conditional_append_batch(
                [{"event_type": "handoff.prepared", "payload": {"epoch": 2}, "event_id": "15151515-1515-1515-1515-151515151515"}],
                expected_generation=snapshot.authority_generation, expected_head=snapshot.authority_head)
        self.assertEqual(caught.exception.classification, "stale_snapshot")
        self.assertEqual(before, self._business_rows())
        self.assertEqual(self.ledger._conn.execute("SELECT COUNT(*) FROM events WHERE event_id='15151515-1515-1515-1515-151515151515'").fetchone()[0], 0)

    def test_conditional_append_exact_retry_is_duplicate_without_mutation(self):
        batch = [
            {"event_type": "handoff.prepared", "payload": {"epoch": 3}, "event_id": "16161616-1616-1616-1616-161616161616"},
            {"event_type": "handoff.locked", "payload": {"epoch": 3}, "event_id": "17171717-1717-1717-1717-171717171717"},
        ]
        first = self.ledger.conditional_append_batch(batch, expected_generation=0, expected_head=GENESIS)
        before = self._business_rows()
        retry = self.ledger.conditional_append_batch(batch, expected_generation=0, expected_head=GENESIS)
        self.assertEqual((retry.status, retry.generation, retry.head, retry.mutation_performed), ("duplicate", first.generation, first.head, False))
        self.assertEqual(retry.event_refs, first.event_refs)
        self.assertEqual(before, self._business_rows())

    def test_conditional_append_stale_mixed_and_divergent_batches_hold_without_side_effects(self):
        batch = [
            {"event_type": "handoff.prepared", "payload": {"epoch": 4}, "event_id": "18181818-1818-1818-1818-181818181818"},
            {"event_type": "handoff.locked", "payload": {"epoch": 4}, "event_id": "19191919-1919-1919-1919-191919191919"},
        ]
        self.ledger.conditional_append_batch(batch, expected_generation=0, expected_head=GENESIS)
        before = self._business_rows()
        mixed = [batch[0], {"event_type": "handoff.active", "payload": {"epoch": 4}, "event_id": "20202020-2020-2020-2020-202020202020"}]
        divergent = [{**batch[0], "payload": {"epoch": 99}}, batch[1]]
        for candidate in (mixed, divergent):
            with self.assertRaises(LedgerStaleSnapshotError):
                self.ledger.conditional_append_batch(candidate, expected_generation=0, expected_head=GENESIS)
            self.assertEqual(before, self._business_rows())

    def test_conditional_append_exact_current_mixed_or_duplicate_request_has_zero_mutation(self):
        first = self.ledger.conditional_append_batch(
            [{"event_type": "handoff.prepared", "payload": {"epoch": 41}, "event_id": "26262626-2626-2626-2626-262626262626"}],
            expected_generation=0, expected_head=GENESIS)
        before = self._business_rows()
        mixed = [
            {"event_type": "handoff.prepared", "payload": {"epoch": 41}, "event_id": "26262626-2626-2626-2626-262626262626"},
            {"event_type": "handoff.locked", "payload": {"epoch": 41}, "event_id": "27272727-2727-2727-2727-272727272727"},
        ]
        repeated_id = [mixed[0], mixed[0]]
        for candidate in (mixed, repeated_id):
            with self.assertRaises(LedgerStaleSnapshotError):
                self.ledger.conditional_append_batch(candidate, expected_generation=first.generation, expected_head=first.head)
            self.assertEqual(before, self._business_rows())

    def test_conditional_append_noncontiguous_existing_batch_has_zero_mutation(self):
        first = self.ledger.append_event("other.first", {"n": 1}, event_id="28282828-2828-2828-2828-282828282828")
        self.ledger.append_event("other.middle", {"n": 2}, event_id="29292929-2929-2929-2929-292929292929")
        self.ledger.append_event("other.last", {"n": 3}, event_id="30303030-3030-3030-3030-303030303030")
        before = self._business_rows()
        with self.assertRaises(LedgerStaleSnapshotError):
            self.ledger.conditional_append_batch([
                {"event_type": "other.first", "payload": {"n": 1}, "event_id": first.event_id},
                {"event_type": "other.last", "payload": {"n": 3}, "event_id": "30303030-3030-3030-3030-303030303030"},
            ], expected_generation=0, expected_head=GENESIS)
        self.assertEqual(before, self._business_rows())

    def test_conditional_append_concurrent_writers_allow_exactly_one_winner(self):
        results, failures = [], []
        def writer(event_id):
            ledger = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
            try:
                results.append(ledger.conditional_append_batch(
                    [{"event_type": "handoff.prepared", "payload": {"event": event_id}, "event_id": event_id}],
                    expected_generation=0, expected_head=GENESIS).status)
            except LedgerStaleSnapshotError:
                failures.append("stale_snapshot")
            finally:
                ledger.close()
        first = threading.Thread(target=writer, args=("21212121-2121-2121-2121-212121212121",))
        second = threading.Thread(target=writer, args=("22222222-2222-2222-2222-222222222222",))
        first.start(); second.start(); first.join(); second.join()
        self.assertEqual(results, ["appended"])
        self.assertEqual(failures, ["stale_snapshot"])
        self.assertEqual(len(self.ledger.list_events()), 1)

    def test_conditional_append_rejects_invalid_pair_and_preserves_append_regression(self):
        event = {"event_type": "handoff.prepared", "payload": {"epoch": 5}, "event_id": "23232323-2323-2323-2323-232323232323"}
        for generation, head in ((True, GENESIS), (-1, GENESIS), (0, "x" * 64), (1, GENESIS), (0, "A" * 64)):
            with self.assertRaises(ValueError):
                self.ledger.conditional_append_batch([event], expected_generation=generation, expected_head=head)
        self.ledger.append_event("ordinary.append", {"ok": True}, event_id="24242424-2424-2424-2424-242424242424")
        ordinary = self.ledger.list_events()[0]
        self.assertEqual(ordinary.event_type, "ordinary.append")
        self.assertIsInstance(ordinary.payload, dict)
        self.assertEqual(json.loads(json.dumps(ordinary.payload)), {"ok": True})

    def test_conditional_append_busy_is_bounded_and_has_no_mutation(self):
        lock = sqlite3.connect(self.ledger.path, timeout=0, isolation_level=None)
        lock.execute("BEGIN IMMEDIATE")
        writer = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
        started = time.monotonic()
        try:
            with self.assertRaises(LedgerBusyError):
                writer.conditional_append_batch(
                    [{"event_type": "handoff.prepared", "payload": {"epoch": 6}, "event_id": "25252525-2525-2525-2525-252525252525"}],
                    expected_generation=0, expected_head=GENESIS)
        finally:
            writer.close()
            lock.execute("ROLLBACK"); lock.close()
        self.assertLess(time.monotonic() - started, 8)
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

    def _business_rows(self):
        tables = ("ledger_metadata", "events", "holds", "project_bindings", "binding_decisions", "projections")
        return {table: [tuple(row) for row in self.ledger._conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                for table in tables}

    def test_authority_snapshot_is_wal_aware_and_does_not_change_business_rows(self):
        self.ledger.bind_project("path", "/tmp/snapshot")
        self.ledger.append_event("snapshot.probe", {"safe": True}, event_id="66666666-6666-6666-6666-666666666666")
        self.ledger.checkpoint_projection("snapshot", 1, {"ok": True})
        self.assertTrue(Path(str(self.ledger.path) + "-wal").exists())
        self.assertTrue(Path(str(self.ledger.path) + "-shm").exists())
        before = self._business_rows()
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual(snapshot.project_id, self.ledger.project_id)
        self.assertEqual(snapshot.schema_version, "1.0.0")
        self.assertEqual(snapshot.authority_generation, 1)
        self.assertEqual(snapshot.authority_head, snapshot.events[-1].event_hash)
        self.assertEqual(before, self._business_rows())
        self.ledger.close()
        # A clean WAL authority remains readable without immutable mode.  Its
        # SQLite coordination sidecars are intentionally not an assertion.
        self.assertFalse(Path(str(self.ledger.path) + "-wal").exists())
        self.assertFalse(Path(str(self.ledger.path) + "-shm").exists())
        fresh = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual((fresh.authority_generation, fresh.authority_head), (1, snapshot.authority_head))
        self.ledger = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)

    def test_authority_snapshot_isolation_duplicate_and_restart(self):
        first = self.ledger.append_event("snapshot.before", {"n": 1}, event_id="77777777-7777-7777-7777-777777777777")
        started = []

        def append_after_snapshot_start():
            writer = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)
            try:
                writer.append_event("snapshot.after", {"n": 2}, event_id="88888888-8888-8888-8888-888888888888")
            finally:
                writer.close()
            started.append(True)

        snapshot = LocalCollaborationLedger._authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id, _after_started=append_after_snapshot_start)
        self.assertTrue(started)
        self.assertEqual(snapshot.authority_generation, 1)
        self.assertEqual(snapshot.authority_head, first.event_hash)
        next_snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual(next_snapshot.authority_generation, 2)
        duplicate = self.ledger.append_event("snapshot.before", {"n": 1}, event_id="77777777-7777-7777-7777-777777777777")
        unchanged = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual(duplicate.event_hash, first.event_hash)
        self.assertEqual((unchanged.authority_generation, unchanged.authority_head), (next_snapshot.authority_generation, next_snapshot.authority_head))
        self.ledger.close()
        restart = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual((restart.authority_generation, restart.authority_head), (unchanged.authority_generation, unchanged.authority_head))
        self.ledger = LocalCollaborationLedger.open_existing(self.ledger.path, expected_project_id=self.ledger.project_id)

    def test_authority_snapshot_events_are_deeply_immutable(self):
        event_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        original = {"nested": {"value": 1}, "items": [{"value": 2}]}
        self.ledger.append_event("snapshot.immutable", original, event_id=event_id)
        snapshot = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        payload = snapshot.events[0].payload
        with self.assertRaises(TypeError):
            payload["new"] = True
        with self.assertRaises(TypeError):
            payload["nested"]["value"] = 9
        with self.assertRaises(TypeError):
            payload["items"][0]["value"] = 9
        with self.assertRaises(AttributeError):
            payload["items"].append({"value": 3})
        with self.assertRaises(TypeError):
            dict.__setitem__(payload, "escaped", True)
        with self.assertRaises(TypeError):
            dict.__setitem__(payload["nested"], "value", 9)
        with self.assertRaises(TypeError):
            list.append(payload["items"], {"value": 3})
        with self.assertRaises(TypeError):
            list.__setitem__(payload["items"], 0, {"value": 4})
        future = LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        self.assertEqual(future.events[0].payload["nested"]["value"], original["nested"]["value"])
        self.assertEqual(future.events[0].payload["items"][0]["value"], original["items"][0]["value"])
        self.assertEqual((future.authority_generation, future.authority_head), (snapshot.authority_generation, snapshot.authority_head))

    def test_authority_snapshot_maps_project_schema_integrity_and_permission_holds(self):
        with self.assertRaises(LedgerIdentityError):
            LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=str(__import__("uuid").uuid4()))
        with sqlite3.connect(self.ledger.path) as conn:
            conn.execute("UPDATE ledger_metadata SET value='9.9.9' WHERE key='schema_version'")
        with self.assertRaises(LedgerSchemaError):
            LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        with sqlite3.connect(self.ledger.path) as conn:
            conn.execute("UPDATE ledger_metadata SET value='1.0.0' WHERE key='schema_version'")
            conn.execute("INSERT INTO events VALUES(1, '99999999-9999-9999-9999-999999999999', 'snapshot.bad', '{}', 'x', '0', 'x', '2026-08-11T00:00:00Z', NULL, NULL, ?)", (self.ledger.project_id,))
        with self.assertRaises(LedgerIntegrityError):
            LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        os.chmod(self.ledger.path, 0o644)
        try:
            with self.assertRaises(LedgerPermissionError):
                LocalCollaborationLedger.authority_snapshot(self.ledger.path, expected_project_id=self.ledger.project_id)
        finally:
            os.chmod(self.ledger.path, 0o600)

    def test_authority_snapshot_busy_is_bounded_and_classified(self):
        path, project_id = self.ledger.path, self.ledger.project_id
        self.ledger.close()
        lock = sqlite3.connect(path, timeout=0, isolation_level=None)
        lock.execute("PRAGMA locking_mode=EXCLUSIVE")
        lock.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        try:
            with self.assertRaises(LedgerBusyError):
                LocalCollaborationLedger.authority_snapshot(path, expected_project_id=project_id)
        finally:
            lock.execute("ROLLBACK")
            lock.close()
        self.assertLess(time.monotonic() - started, 8)
        self.ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=project_id)


if __name__ == "__main__": unittest.main()
