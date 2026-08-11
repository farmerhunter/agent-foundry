from __future__ import annotations
import os, sys, tempfile, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from local_collaboration_ledger import LocalCollaborationLedger
from github_evidence_cache import *

class Producer:
    def __init__(self, entries, **extra): self.entries, self.calls, self.extra = entries, 0, extra
    def fetch_evidence(self, binding, selectors, capability_receipt):
        self.calls += 1
        return {"trust_domain":"same_process_reference", "production_eligibility":False,
                "producer_id":"fake", "producer_version":"1", "entries":self.entries, **self.extra}

def setup():
    root=tempfile.mkdtemp(prefix="evidence-cache-"); pid=str(uuid.uuid4())
    ledger=LocalCollaborationLedger.create_project(projects_root=root, project_id=pid)
    ledger.bind_project("github_repository", "repo-opaque"); ledger.close()
    initialize_cache(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator")
    return root,pid

def entry(revision="r1", summary="bounded"):
    return {"evidence_kind":"issue_metadata", "opaque_object_ref":"123", "selector_digest":"0"*64,
            "representation_version":"1", "facts":{"state":"open"}, "summary":summary,
            "anchors":["issue:123"], "source_revision":revision, "fetched_at":"2026-08-11T00:00:00Z",
            "coverage":"complete", "privacy_class":"metadata_only"}

def test_miss_is_non_mutating():
    root,pid=setup(); path=Path(root)/pid/"github-evidence-cache.db"; before=path.stat().st_mtime_ns
    result=read_cache(projects_root=root,project_id=pid,evaluated_at="2026-08-11T00:00:01Z",max_age_seconds=10)
    assert result["outcome"] == "cache_hit" and result["entries"] == [] and path.stat().st_mtime_ns == before

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

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"): fn()
    print("github evidence cache tests: PASS")
