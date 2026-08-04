#!/usr/bin/env python3
from thread_harvest_contract import review

def main():
    errors=[]
    base={"human_intent_confirmed":True,"thread_ref":"opaque-1","coverage":"complete","adapter_history":"available"}
    if review(base)["outcome"] != "candidate_hold": errors.append("valid")
    for coverage, reason in (("complete", "validated_bounded_request"), ("partial", "thread_harvest_partial"), ("unavailable", "held_thread_history_unavailable"), ("privacy_held", "held_thread_history_privacy")):
        checked = review({**base, "coverage": coverage})
        expected_outcome = "candidate_hold" if coverage == "complete" else "deferred"
        if checked["coverage"] != coverage or checked["reason"] != reason or checked["outcome"] != expected_outcome or (coverage != "complete" and checked["terminal"] is not True): errors.append(coverage)
    for key in ("page_size","cursor","cross_thread","raw_transcript","prompt","tool_output","identity","secret"):
        if review({**base,key:1})["outcome"] != "rejected": errors.append(key)
    if review({**base,"coverage":"unknown"})["outcome"] != "rejected": errors.append("coverage")
    if review({**base,"output":"proposed"})["outcome"] != "rejected": errors.append("promotion")
    if review({**base,"output":"active"})["outcome"] != "rejected": errors.append("active-promotion")
    print("thread harvest tests passed." if not errors else f"failed: {errors}")
    return 1 if errors else 0
if __name__ == "__main__": raise SystemExit(main())
