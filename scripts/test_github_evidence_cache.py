from __future__ import annotations
import os, sys, tempfile, uuid, sqlite3, json, subprocess, time, signal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from local_collaboration_ledger import LocalCollaborationLedger
from github_evidence_cache import *

class Producer:
    def __init__(self, entries, **extra): self.entries, self.calls, self.extra = entries, 0, extra
    def fetch_evidence(self, binding, selectors, capability_receipt):
        self.calls += 1
        return {"trust_domain":"same_process_reference", "production_eligibility":False,
                "producer_id":"fake", "producer_version":"1", "coverage":"complete", "entries":self.entries, **self.extra}

def setup():
    root=tempfile.mkdtemp(prefix="evidence-cache-"); pid=str(uuid.uuid4())
    ledger=LocalCollaborationLedger.create_project(projects_root=root, project_id=pid)
    ledger.bind_project("github_repository", "repo-opaque"); ledger.close()
    initialize_cache(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator")
    return root,pid

def entry(revision="r1", summary="bounded", coverage="complete", ref="123"):
    return {"evidence_kind":"issue_metadata", "opaque_object_ref":ref, "selector_digest":"0"*64,
            "representation_version":"1", "facts":{"state":"open"}, "summary":summary,
            "anchors":["issue:123"], "source_revision":revision, "fetched_at":"2026-08-11T00:00:00Z",
            "coverage":coverage, "privacy_class":"metadata_only"}

def test_miss_is_non_mutating():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; before=path.stat().st_mtime_ns
    result=read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:01Z",max_age_seconds=10)
    assert result["outcome"] == "cache_hit" and result["entries"] == [] and path.stat().st_mtime_ns == before

def test_closed_nested_model_and_prewrite_rejection():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; before=path.read_bytes(); before_mtime=path.stat().st_mtime_ns
    for bad, classification in [({**entry(), "facts":{"unknown": "x"}}, "hold_cache_schema"), ({**entry(), "facts":{"raw_body": "x"}}, "hold_cache_privacy"), ({**entry(), "fetched_at":"2026-08-11T00:00:02Z"}, "hold_cache_clock_or_freshness")]:
        try:
            refresh_cache(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:01Z",max_age_seconds=10,producer=Producer([bad]))
        except CacheHold as exc: assert exc.classification == classification
        else: raise AssertionError("invalid entry must hold")
    assert path.read_bytes() == before and path.stat().st_mtime_ns == before_mtime

def test_duplicate_is_zero_mutation_and_metrics_are_separate():
    root,pid=setup(); producer=Producer([entry()]); kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=producer)
    first=refresh_cache(**kwargs); path=Path(root)/pid/"github-evidence-cache.db"; snapshot=path.read_bytes(); second=refresh_cache(**kwargs)
    assert first["outcome"] == "cache_refreshed" and second["outcome"] == "cache_duplicate" and second["receipt_id"] is None and path.read_bytes() == snapshot

def test_read_future_and_binding_holds():
    root,pid=setup(); producer=Producer([entry()]); kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=producer)
    refresh_cache(**kwargs)
    try: read_cache(projects_root=root,project_id=pid,evaluated_at="2025-01-01T00:00:00Z",max_age_seconds=10)
    except CacheHold as exc: assert exc.classification == "hold_cache_clock_or_freshness"
    else: raise AssertionError("future cache age must hold")
    try: read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:01Z",max_age_seconds=10,repository_id="other",repository_locator_digest="repo-locator")
    except CacheHold as exc: assert exc.classification == "hold_cache_binding_mismatch"
    else: raise AssertionError("wrong repository must hold")

def test_corrupt_cache_is_fail_closed_without_delete():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; path.write_bytes(b"not sqlite"); before=path.read_bytes()
    try: read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:01Z",max_age_seconds=10)
    except CacheHold as exc: assert exc.classification in {"hold_cache_integrity", "hold_cache_schema"}
    else: raise AssertionError("corrupt cache must hold")
    assert path.read_bytes() == before

def test_rebuild_and_invalidate_require_existing_cache():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; path.unlink()
    try: invalidate_cache_entries(projects_root=root,project_id=pid,entry_keys=[],reason="x",evaluated_at="2026-08-11T00:00:00Z")
    except CacheHold as exc: assert exc.classification == "hold_cache_authority_unready"
    else: raise AssertionError("invalidate must not create cache")

def test_refresh_once_duplicate_and_divergence():
    root,pid=setup(); p=Producer([entry()]); kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=p)
    assert refresh_cache(**kwargs)["outcome"] == "cache_refreshed"; assert p.calls == 1
    assert refresh_cache(**kwargs)["outcome"] == "cache_duplicate"; assert p.calls == 2
    p.entries=[entry(summary="changed")]
    try: refresh_cache(**kwargs)
    except CacheHold as exc: assert exc.classification == "hold_cache_divergent_revision"
    else: raise AssertionError("divergent revision must hold")

def test_freshness_and_privacy():
    root,pid=setup(); p=Producer([entry()]); refresh_cache(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=p)
    rows=read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:11Z",max_age_seconds=10)["entries"]
    assert rows[0]["freshness"] == "stale" and rows[0]["authoritative"] is False and rows[0]["confirmation_eligible"] is False
    bad=Producer([{**entry(), "opaque_object_ref":"124", "facts":{"raw_body":"secret"}}])
    try: refresh_cache(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=bad)
    except CacheHold as exc: assert exc.classification == "hold_cache_privacy"
    else: raise AssertionError("privacy input must hold")

def test_authority_mismatch_no_orphan():
    root=tempfile.mkdtemp(); pid=str(uuid.uuid4())
    try: initialize_cache(projects_root=root,project_id=pid,repository_id="r",repository_locator_digest="l")
    except CacheHold as exc: assert exc.classification == "hold_cache_authority_unready"
    else: raise AssertionError("missing authority must hold")
    assert not (Path(root)/pid/"github-evidence-cache.db").exists()

def test_cleanup_is_explicit_and_local():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; plan=plan_cache_cleanup(projects_root=root,project_id=pid,disposal_reason="test",owner_receipt="owner")
    assert plan["exists"] is True
    out=apply_cache_cleanup(projects_root=root,project_id=pid,cache_path_digest=plan["cache_path_digest"],disposal_reason="test",owner_receipt="owner")
    assert out["outcome"] == "cache_cleaned" and not path.exists() and (Path(root)/pid/"collaboration.db").exists()

def test_producer_coverage_is_explicit_and_terminal():
    root,pid=setup(); kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)
    try: refresh_cache(**kwargs, producer=Producer([], coverage=None))
    except CacheHold as exc: assert exc.classification == "hold_cache_schema"
    else: raise AssertionError("missing coverage must hold")
    unavailable=refresh_cache(**kwargs, producer=Producer([], coverage="unavailable"))
    private=refresh_cache(**kwargs, producer=Producer([], coverage="privacy_held"))
    assert unavailable["outcome"] == "cache_unavailable" and private["outcome"] == "cache_privacy_held" and unavailable["receipt_id"] and private["receipt_id"]

def test_partial_cannot_replace_complete_and_receipts_validate():
    root,pid=setup(); kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)
    refresh_cache(**kwargs, producer=Producer([entry(revision="complete")]))
    partial=refresh_cache(**kwargs, producer=Producer([entry(revision="partial",coverage="partial")], coverage="partial"))
    read=read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)
    assert partial["outcome"] == "cache_partial_preserved" and read["entries"][0]["source_revision"] == "complete"
    path=Path(root)/pid/"github-evidence-cache.db"
    db=sqlite3.connect(path); db.execute("UPDATE receipts SET payload='{}' WHERE operation='refresh'"); db.commit(); db.close()
    try: read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)
    except CacheHold as exc: assert exc.classification == "hold_cache_integrity"
    else: raise AssertionError("tampered receipt must hold")

def test_closed_runtime_limits_and_preflight_do_not_touch_cache():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; before=path.read_bytes(); mtime=path.stat().st_mtime_ns
    kwargs=dict(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)
    for bad in [entry(summary="two\nlines"), entry(ref="124", summary="x", coverage="complete", revision="r2") | {"anchors":["x"]*17}, entry(ref="125", summary="x", coverage="complete", revision="r3") | {"facts":{"title":"x"*257}}]:
        try: refresh_cache(**kwargs, producer=Producer([bad]))
        except CacheHold: pass
        else: raise AssertionError("runtime limits must hold")
    try: invalidate_cache_entries(projects_root=root,project_id=pid,entry_keys=["bad"],reason="x",evaluated_at="2026-08-11T00:00:00Z")
    except CacheHold as exc: assert exc.classification == "hold_cache_schema"
    else: raise AssertionError("invalid invalidate key must hold")
    try: rebuild_cache(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",entries=[{**entry(),"summary":"bad\nsummary"}],evaluated_at="2026-08-11T00:00:00Z")
    except CacheHold: pass
    else: raise AssertionError("invalid rebuild must hold")
    assert path.read_bytes() == before and path.stat().st_mtime_ns == mtime

def test_cache_metadata_declares_durability_and_reopen_validates():
    root,pid=setup(); meta=project_cache_readout(projects_root=root,project_id=pid)["metadata"]
    assert meta["durability"] == "wal_synchronous_normal"
    path=Path(root)/pid/"github-evidence-cache.db"; db=sqlite3.connect(path); db.execute("UPDATE metadata SET value='FULL' WHERE key='durability'"); db.commit(); db.close()
    try: project_cache_readout(projects_root=root,project_id=pid)
    except CacheHold as exc: assert exc.classification in {"hold_cache_schema","hold_cache_integrity"}
    else: raise AssertionError("tampered durability must hold")

def _subprocess_cache(root, pid, summary, sleep_seconds=0):
    code = '''import os,sys,time; sys.path.insert(0,sys.argv[1]); from github_evidence_cache import refresh_cache
class P:
 def fetch_evidence(self,b,s,c):
  time.sleep(float(sys.argv[6])); return {"trust_domain":"same_process_reference","production_eligibility":False,"producer_id":"race","producer_version":"1","coverage":"complete","entries":[{"evidence_kind":"issue_metadata","opaque_object_ref":"123","selector_digest":"0"*64,"representation_version":"1","facts":{"state":"open"},"summary":sys.argv[5],"anchors":["issue:123"],"source_revision":"race","fetched_at":"2026-08-11T00:00:00Z","coverage":"complete","privacy_class":"metadata_only"}]}
try: print(refresh_cache(projects_root=sys.argv[2],project_id=sys.argv[3],repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["123"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=P()))
except Exception as e: print(type(e).__name__, getattr(e,"classification","")); raise
'''
    return subprocess.Popen([sys.executable,"-c",code,str(Path(__file__).parent),root,pid,"unused",summary,str(sleep_seconds)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def test_two_process_race_busy_and_crash_recovery():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; ledger_path=Path(root)/pid/"collaboration.db"; ledger_before=ledger_path.read_bytes()
    one=_subprocess_cache(root,pid,"one",0.2); two=_subprocess_cache(root,pid,"two",0.2); a=one.communicate(timeout=15); b=two.communicate(timeout=15)
    successes=sum("cache_refreshed" in output for output in (a[0],b[0])); holds=sum("hold_cache_" in output for output in (a[0]+a[1],b[0]+b[1]))
    assert successes == 1 and holds == 1 and ledger_path.read_bytes() == ledger_before
    locker = subprocess.Popen([sys.executable,"-c","import sqlite3,sys,time; d=sqlite3.connect(sys.argv[1],isolation_level=None); d.execute('BEGIN IMMEDIATE'); time.sleep(6)",str(path)])
    time.sleep(.2)
    try: refresh_cache(projects_root=root,project_id=pid,repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["124"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=Producer([entry(ref="124",revision="busy")]))
    except CacheHold as exc: assert exc.classification == "hold_cache_busy"
    else: raise AssertionError("bounded busy must hold")
    locker.wait(timeout=10)
    crash_code = '''import os,signal,sys; sys.path.insert(0,sys.argv[1]); import github_evidence_cache as m
def kill(self,*a,**kw): os.kill(os.getpid(),signal.SIGKILL)
m.GitHubEvidenceCache._receipt=kill
class P:
 def fetch_evidence(self,b,s,c): return {"trust_domain":"same_process_reference","production_eligibility":False,"producer_id":"crash","producer_version":"1","coverage":"complete","entries":[{"evidence_kind":"issue_metadata","opaque_object_ref":"126","selector_digest":"0"*64,"representation_version":"1","facts":{"state":"open"},"summary":"crash-before-commit","anchors":["issue:126"],"source_revision":"crash","fetched_at":"2026-08-11T00:00:00Z","coverage":"complete","privacy_class":"metadata_only"}]}
m.refresh_cache(projects_root=sys.argv[2],project_id=sys.argv[3],repository_id="repo-opaque",repository_locator_digest="repo-locator",selectors=["126"],evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10,producer=P())'''
    crash = subprocess.run([sys.executable,"-c",crash_code,str(Path(__file__).parent),root,pid])
    assert crash.returncode == -signal.SIGKILL
    out=project_cache_readout(projects_root=root,project_id=pid)
    assert ledger_path.read_bytes() == ledger_before and read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:00Z",max_age_seconds=10)["entries"][0]["opaque_object_ref"] == "123"

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"): fn()
    print("github evidence cache tests: PASS")
