"""Deterministic, disposable evidence collector for ORCH-05 A4-P1R.

This is deliberately an orchestration harness, not a product API.  It only
composes the public owner facades in isolated authorities below ``/private/tmp``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import (
    apply_owner_import, apply_owner_target_activation, plan_owner_import,
    plan_owner_target_activation, prepare_manual_bundle,
)
from local_collaboration_handoff_experience import read_handoff_experience
from local_collaboration_ledger import LocalCollaborationLedger
from local_collaboration_recovery import apply_recovery_action, plan_recovery_action, read_recovery_summary


VERSION = "ORCH05-A4-EH1-v1"
INTEGRATION = "codex/orch-05-single-active-handoff-integration@f7e6340afb61e1a025cfb957f9160eb9a99c9019"
S1_EVIDENCE_REF = "5284481954"
_ROOT_NAME = re.compile(r"^orch05-a4-eh1-[A-Za-z0-9_-]+$")


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs):
        raise TypeError("immutable fixture evidence")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


class _FixtureHold(Exception):
    def __init__(self, terminal: str):
        self.terminal = terminal


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pair(snapshot) -> tuple[int, str]:
    return snapshot.authority_generation, snapshot.authority_head


def _root_or_hold(private_root: str | Path) -> Path:
    root = Path(private_root)
    expected_parent = Path("/private/tmp").resolve()
    if (not _ROOT_NAME.fullmatch(root.name) or root.parent.resolve() != expected_parent
            or root.exists() or root.is_symlink()):
        raise _FixtureHold("held_privacy_or_cleanup")
    return root


def _transition(ledger: LocalCollaborationLedger, project_id: str, transition: str, **fields: Any) -> Mapping[str, Any]:
    state = read_handoff_state(ledger.path, expected_project_id=project_id)
    plan = plan_handoff_transition(state, {"transition": transition, "project_id": project_id, **fields})
    if isinstance(plan, Mapping):
        raise _FixtureHold("held_public_api_gap")
    result = apply_handoff_transition(ledger, plan, expected_before=state)
    if not isinstance(result, Mapping) or result.get("outcome", "").startswith("hold_"):
        raise _FixtureHold("held_public_api_gap")
    return result


def _imported(root: Path, label: str, ledgers: list[LocalCollaborationLedger]) -> tuple[str, LocalCollaborationLedger, LocalCollaborationLedger, Mapping[str, Any], Mapping[str, Any], Any, Any]:
    """Build one source-locked, owner-imported pair through public APIs."""
    project_id = str(uuid.uuid4())
    source = LocalCollaborationLedger.create_project(projects_root=root / (label + "-source"), project_id=project_id)
    target = LocalCollaborationLedger.create_project(projects_root=root / (label + "-target"), project_id=project_id)
    ledgers.extend((source, target))
    _transition(source, project_id, "enroll_initial", replica_id="source", replica_epoch=1,
                enrollment_id="source-enroll", enrollment_digest=_digest(label + "-source"),
                decision_id="source-decision", decision_digest=_digest(label + "-source-decision"))
    _transition(source, project_id, "enroll_target", replica_id="target", replica_epoch=1,
                enrollment_id="target-enroll", enrollment_digest=_digest(label + "-target"),
                decision_id="target-decision", decision_digest=_digest(label + "-target-decision"))
    _transition(source, project_id, "prepare", handoff_id="handoff-" + label,
                source_replica_id="source", target_replica_id="target", frontier_digest=_digest(label + "-frontier"))
    _transition(source, project_id, "source_lock", handoff_id="handoff-" + label)
    bundle = prepare_manual_bundle(source, expected_handoff_state=read_handoff_state(source.path, expected_project_id=project_id))
    if not isinstance(bundle, Mapping) or "outcome" in bundle:
        raise _FixtureHold("held_public_api_gap")
    before = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    plan = plan_owner_import(before, bundle)
    if isinstance(plan, Mapping):
        raise _FixtureHold("held_public_api_gap")
    proof = apply_owner_import(target, plan, expected_before=before)
    if proof.get("outcome") != "owner_import_committed" or not proof.get("owner_import_performed"):
        raise _FixtureHold("held_public_api_gap")
    locator = {key: proof[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
    return project_id, source, target, bundle, locator, plan, before


def _s2(root: Path, ledgers: list[LocalCollaborationLedger]) -> Mapping[str, Any]:
    project_id, source, target, bundle, locator, plan, import_before = _imported(root, "s2", ledgers)
    before = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    duplicate = apply_owner_import(target, plan, expected_before=import_before)
    after = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    status = read_handoff_experience(target.path, expected_project_id=project_id, bundle=bundle, proof_ref=locator)
    status_ok = (status.get("owner_import_verified") is True and status.get("target_activation_authorized") is False
                 and (status.get("target_generation"), status.get("target_head")) == _pair(after))
    if not (duplicate.get("outcome") == "owner_import_committed" and duplicate.get("owner_import_performed") is False
            and _pair(before) == _pair(after) and len(before.events) == len(after.events) and status_ok):
        raise _FixtureHold("held_s2_duplicate_evidence")
    return {"status": "complete", "scenario_calls": 1, "duplicate_calls": 1, "owner_import_calls": 2,
            "pair_unchanged": True, "event_count_unchanged": True, "owner_status_accepted": True,
            "source_locked": read_handoff_state(source.path, expected_project_id=project_id).phase == "source_locked"}


def _s3(root: Path, ledgers: list[LocalCollaborationLedger]) -> Mapping[str, Any]:
    project_id, source, target, bundle, locator, _, _ = _imported(root, "s3-drift", ledgers)
    decision = {"decision_id": "activation-decision", "decision_digest": _digest("activation-decision")}
    activation = plan_owner_target_activation(target.path, expected_project_id=project_id, bundle=bundle, proof_ref=locator, decision=decision)
    if isinstance(activation, Mapping):
        raise _FixtureHold("held_s3_fixture_safety_defect")
    target.append_event("fixture_tail", {"kind": "drift"}, event_id=str(uuid.uuid4()), actor="fixture", source="eh1", root=project_id)
    before_drift = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    drift = apply_owner_target_activation(target, activation, bundle=bundle, proof_ref=locator, decision=decision)
    after_drift = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    drift_ok = (isinstance(drift, Mapping) and str(drift.get("outcome", "")).startswith("hold_")
                and _pair(before_drift) == _pair(after_drift))

    project_id2, _, target2, bundle2, locator2, _, _ = _imported(root, "s3-forged", ledgers)
    decision2 = {"decision_id": "forged-decision", "decision_digest": _digest("forged-decision")}
    activation2 = plan_owner_target_activation(target2.path, expected_project_id=project_id2, bundle=bundle2, proof_ref=locator2, decision=decision2)
    if isinstance(activation2, Mapping):
        raise _FixtureHold("held_s3_fixture_safety_defect")
    bad_locator = dict(locator2); bad_locator["receipt_event_hash"] = "0" * 64
    before_bad = LocalCollaborationLedger.authority_snapshot(target2.path, expected_project_id=project_id2)
    forged = apply_owner_target_activation(target2, activation2, bundle=bundle2, proof_ref=bad_locator, decision=decision2)
    after_bad = LocalCollaborationLedger.authority_snapshot(target2.path, expected_project_id=project_id2)
    forged_ok = str(forged.get("outcome", "")).startswith("hold_") and _pair(before_bad) == _pair(after_bad)

    project_id3 = str(uuid.uuid4())
    source3 = LocalCollaborationLedger.create_project(projects_root=root / "s3-overlap-source", project_id=project_id3)
    target3 = LocalCollaborationLedger.create_project(projects_root=root / "s3-overlap-target", project_id=project_id3)
    ledgers.extend((source3, target3))
    target3.append_event("fixture_overlap", {"kind": "frontier"}, event_id=str(uuid.uuid4()), actor="fixture", source="eh1", root=project_id3)
    _transition(source3, project_id3, "enroll_initial", replica_id="source", replica_epoch=1, enrollment_id="source-enroll", enrollment_digest=_digest("overlap-source"), decision_id="source-decision", decision_digest=_digest("overlap-source-decision"))
    _transition(source3, project_id3, "enroll_target", replica_id="target", replica_epoch=1, enrollment_id="target-enroll", enrollment_digest=_digest("overlap-target"), decision_id="target-decision", decision_digest=_digest("overlap-target-decision"))
    _transition(source3, project_id3, "prepare", handoff_id="handoff-overlap", source_replica_id="source", target_replica_id="target", frontier_digest=_digest("overlap-frontier"))
    _transition(source3, project_id3, "source_lock", handoff_id="handoff-overlap")
    bundle3 = prepare_manual_bundle(source3, expected_handoff_state=read_handoff_state(source3.path, expected_project_id=project_id3))
    before_overlap = LocalCollaborationLedger.authority_snapshot(target3.path, expected_project_id=project_id3)
    overlap = plan_owner_import(before_overlap, bundle3)
    after_overlap = LocalCollaborationLedger.authority_snapshot(target3.path, expected_project_id=project_id3)
    overlap_ok = isinstance(overlap, Mapping) and str(overlap.get("outcome", "")).startswith("hold_") and _pair(before_overlap) == _pair(after_overlap)
    if not (drift_ok and forged_ok and overlap_ok):
        raise _FixtureHold("held_s3_fixture_safety_defect")
    return {"status": "complete", "scenario_calls": 1, "negative_count": 3, "all_holds": True, "wrongful_activation": False,
            "tail_drift_hold_class": drift["outcome"], "tail_drift_mutations": 0,
            "forgery_hold_class": forged["outcome"], "forgery_mutations": 0,
            "overlap_hold_class": overlap["outcome"], "overlap_mutations": 0}


def _s4(root: Path, ledgers: list[LocalCollaborationLedger]) -> Mapping[str, Any]:
    project_id, source, target, bundle, locator, _, _ = _imported(root, "s4", ledgers)
    summary = read_recovery_summary(target.path, expected_project_id=project_id, bundle=bundle, proof_ref=locator)
    if summary.get("outcome") != "target_import_recovery_ready":
        raise _FixtureHold("held_s4_recovery_evidence")
    decision = {"decision_id": "recovery-decision", "decision_digest": _digest("recovery-decision")}
    backup_path = str(root / "s4-backup.db")
    backup_plan = plan_recovery_action(target.path, expected_project_id=project_id, action="fresh_backup", decision=decision, backup_locator=backup_path)
    backup = apply_recovery_action(target, backup_plan, decision=decision, backup_locator=backup_path)
    restored_root = str(root / "s4-restored")
    restore_plan = plan_recovery_action(target.path, expected_project_id=project_id, action="fresh_target_restore", decision=decision, restore_locator=backup_path, fresh_target_locator=restored_root)
    restore = apply_recovery_action(target, restore_plan, decision=decision, restore_locator=backup_path, fresh_target_locator=restored_root)
    takeover_plan = plan_recovery_action(target.path, expected_project_id=project_id, action="target_takeover", decision=decision, bundle=bundle, proof_ref=locator)
    if isinstance(takeover_plan, Mapping):
        raise _FixtureHold("held_s4_recovery_evidence")
    first = apply_recovery_action(target, takeover_plan, decision=decision, bundle=bundle, proof_ref=locator)
    pair = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    duplicate = apply_recovery_action(target, takeover_plan, decision=decision, bundle=bundle, proof_ref=locator)
    after_duplicate = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id)
    stale = plan_recovery_action(target.path, expected_project_id=project_id, action="target_takeover", decision=decision, bundle=bundle, proof_ref=locator)
    target_status = read_handoff_experience(target.path, expected_project_id=project_id)
    restored_pair_matches_backup = ((backup.get("generation"), backup.get("head"))
                                    == (restore.get("generation"), restore.get("head")))
    valid = (backup.get("outcome") == "fresh_backup_created" and restore.get("outcome") == "fresh_target_restored"
             and restored_pair_matches_backup
             and first.get("outcome") == "recovery_action_applied" and first.get("active_replica_id") == "target"
             and duplicate.get("outcome") == "recovery_action_applied" and duplicate.get("flags", {}).get("mutation_performed") is False
             and _pair(pair) == _pair(after_duplicate) and isinstance(stale, Mapping) and str(stale.get("outcome", "")).startswith("hold_")
             and target_status.get("experience_state") in {"taken_over", "target_active"}
             and read_handoff_state(source.path, expected_project_id=project_id).phase == "source_locked")
    if not valid:
        raise _FixtureHold("held_s4_recovery_evidence")
    return {"status": "complete", "scenario_calls": 1, "backup_created": True, "restore_created": True, "takeover_applied": True,
            "takeover_duplicate_calls": 1, "takeover_duplicate_zero_mutation": True, "stale_hold": True,
            "target_status_active": True, "source_locked": True,
            "restored_pair_matches_backup": True}


def _not_run() -> Mapping[str, Any]:
    return {"status": "not_run", "scenario_calls": 0}


def _stopped_scenario(*, terminal: str, unexpected: bool) -> Mapping[str, Any]:
    return {"status": "fail" if unexpected else "hold", "reason_code": "unexpected_exception" if unexpected else terminal,
            "scenario_calls": 1, "counters_complete": False}


def _receipt(*, terminal: str, cleanup: bool, s2: Mapping[str, Any] | None = None,
             s3: Mapping[str, Any] | None = None, s4: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return _freeze({"contract_version": VERSION, "integration": INTEGRATION, "run_id": uuid.uuid4().hex,
                    "prior_s1_evidence_ref": S1_EVIDENCE_REF, "s1_rerun": False,
                    "fixture_only": True, "live_data": False, "network": False, "transport": False,
                    "s2": dict(s2 or _not_run()), "s3": dict(s3 or _not_run()),
                    "s4": dict(s4 or _not_run()), "cleanup_complete": cleanup, "terminal_outcome": terminal})


def collect_missing_fixture_evidence(*, private_root: str | Path) -> Mapping[str, Any]:
    """Collect the missing A4-P1R fixture evidence once, then delete all artifacts."""
    root: Path | None = None
    ledgers: list[LocalCollaborationLedger] = []
    s2 = s3 = s4 = None
    active: str | None = None
    terminal = "held_evidence_incomplete"
    try:
        root = _root_or_hold(private_root)
        root.mkdir(mode=0o700)
        active = "s2"; s2 = _s2(root, ledgers)
        active = "s3"; s3 = _s3(root, ledgers)
        active = "s4"; s4 = _s4(root, ledgers)
        terminal = "fixture_evidence_complete_for_live_a4_hdc_preparation"
    except _FixtureHold as exc:
        terminal = exc.terminal
        if active == "s2": s2 = _stopped_scenario(terminal=terminal, unexpected=False)
        elif active == "s3": s3 = _stopped_scenario(terminal=terminal, unexpected=False)
        elif active == "s4": s4 = _stopped_scenario(terminal=terminal, unexpected=False)
    except Exception:
        terminal = "held_evidence_incomplete"
        if active == "s2": s2 = _stopped_scenario(terminal=terminal, unexpected=True)
        elif active == "s3": s3 = _stopped_scenario(terminal=terminal, unexpected=True)
        elif active == "s4": s4 = _stopped_scenario(terminal=terminal, unexpected=True)
    finally:
        for ledger in reversed(ledgers):
            try:
                ledger.close()
            except Exception:
                terminal = "held_privacy_or_cleanup"
        cleanup = root is not None and not root.exists()
        if root is not None and root.exists():
            try:
                shutil.rmtree(root)
                cleanup = not root.exists()
            except Exception:
                cleanup = False
        if not cleanup:
            terminal = "held_privacy_or_cleanup"
    return _receipt(terminal=terminal, cleanup=cleanup, s2=s2, s3=s3, s4=s4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(collect_missing_fixture_evidence(private_root=args.private_root), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
