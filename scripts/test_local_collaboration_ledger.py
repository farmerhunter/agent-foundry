import os
import stat
import tempfile
import unittest
from pathlib import Path

from local_collaboration_ledger import LedgerConflictError, LedgerIntegrityError, LocalCollaborationLedger


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
        self.assertEqual(self.ledger.append_event("x", {"a": 1}, event_id=event_id).sequence, 1)
        self.ledger.close()
        reopened = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)
        with self.assertRaises(LedgerConflictError): reopened.append_event("x", {"a": 2}, event_id=event_id)
        self.assertEqual(reopened._conn.execute("SELECT COUNT(*) FROM holds WHERE event_id=?", (event_id,)).fetchone()[0], 1)
        reopened.close()

    def test_privacy_and_batch_rollback(self):
        with self.assertRaises(ValueError): self.ledger.append_event("x", {"raw_transcript": "secret"})
        with self.assertRaises(ValueError): self.ledger.append_batch([{"event_type": "ok", "payload": {}}, {"event_type": "bad", "payload": {"prompt": "x"}}])
        self.assertEqual(self.ledger.list_events(), [])

    def test_tamper_and_backup(self):
        self.ledger.append_event("x", {"a": 1})
        backup = Path(self.tmp.name) / "backup.db"
        self.ledger.backup(backup)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.ledger._conn.execute("UPDATE events SET payload='{}' WHERE sequence=1")
        with self.assertRaises(LedgerIntegrityError): self.ledger.verify()

    def test_permission_and_schema_fail_closed(self):
        self.ledger.close()
        os.chmod(Path(self.tmp.name) / self.ledger.project_id, 0o755)
        with self.assertRaises(Exception):
            LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)
        os.chmod(Path(self.tmp.name) / self.ledger.project_id, 0o700)
        reopened = LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)
        reopened._conn.execute("UPDATE ledger_metadata SET value='9.9.9' WHERE key='schema_version'")
        reopened.close()
        with self.assertRaises(LedgerIntegrityError):
            LocalCollaborationLedger(self.ledger.project_id, projects_root=self.tmp.name)


if __name__ == "__main__": unittest.main()
