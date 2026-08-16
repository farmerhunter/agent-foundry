# Local Collaboration Lifecycle

Use this workflow when the intent is **“开启本地多-agent协作”** or
**“start local collaboration”**.  It is a portable guidance front door, not an
executable API and not a replacement for the owner modules it names.

## Capability boundary

| Capability lane | Status | Owner surface |
| --- | --- | --- |
| Fresh or existing single-machine onboarding | `supported` | `sqlite_collaboration_workflow.py` and `local_collaboration_onboarding.py` |
| Authority/status/hold visibility and one safe next action | `supported` | `local_collaboration_handoff_experience.py` |
| Local backup, restore, takeover and recovery guidance | `supported` | `local_collaboration_recovery.py` |
| Same-host manual bundle custody between two isolated authorities | `experimental_same_host_manual_custody` | `local_collaboration_handoff.py`, `local_collaboration_handoff_bundle.py`, and `local_collaboration_handoff_experience.py` |
| Real second device, cross-host operation, device-loss resilience, independent credentials, transport or convergence | `held_real_second_device_deferred` | no supported owner surface |

`experimental_same_host_manual_custody` is opt-in. It is not device sync, not
automatic cross-device sync, not automatic handoff, not transport resilience,
and not evidence of independent-device continuity.

## Front-door result

Present a closed, privacy-safe, non-authoritative result with these fields:

```text
capability_lane
support_level
lifecycle_state
authority_mode
project_binding_status
attention_reason
safe_next_action
mutation_required
human_gate_required
receipt_refs
unsupported_or_deferred
```

Do not expose raw ledger events, prompts, transcripts, tool output,
credentials, or unapproved paths. Caller claims are not owner evidence.

## Supported single-machine path

1. Run a **read-only preflight** using the existing owner surface. Establish
   project binding, whether the SQLite authority exists, lifecycle status, and
   any hold. Do not create or repair anything during preflight.
2. For a fresh project, explain the proposed authority creation. For an
   existing candidate, explain the reuse or accepted-backfill decision. Every
   create, accepted backfill, recovery, activation, retention, or disposal is
   a separate Human decision before its owner API can mutate state.
3. After an accepted owner operation, reopen or freshly read the authority and
   show the authority/status result. Where available, the Board is an optional
   **local read-only** view; it is not required proof and never performs a
   Board-backed mutation or GitHub Project access.
4. Daily local work goes through the existing LedgerStore-backed owner
   surfaces. State the timestamp and idempotency/duplicate receipt supplied by
   the owner. Do not replay manually or create JSONL fallback state.
5. For a hold, show exactly one safe next action from the relevant owner
   surface. Never auto-repair, silently retry, fall back to another store, or
   claim a successful mutation without fresh owner readback.
6. For recovery, use the existing recovery owner receipt/proof path. Explain
   backup, restore, conflict, source-lock and cleanup consequences before any
   Human-approved recovery action.

## A0-Lite experimental same-host path

Only after a Human explicitly opts in, use two isolated local authorities on
the same host. The sequence is: enrollment and epoch receipt; prepare and lock
the source; create an immutable manual bundle; transfer it by explicit manual
custody; owner-verify atomic target import; then perform target-local
activation only through its owner proof/decision path.

- The source remains locked without a trusted return channel.
- Manual custody means a named staging/custody step and a digest/readback, not
  automatic transport.
- Interruption, overlap, forged proof, stale state and duplicate requests must
  remain typed holds or exact idempotent owner receipts.
- Recovery and cleanup remain explicit owner-guided actions. Do not silently
  unlock the source, dispose the bundle, or infer a global result.
- `target_active` is target-local only; it does not claim global convergence.

## Deferred real-second-device request

A request for a real second device, cross-host handoff, device-loss recovery,
independent credentials, transport, or convergence returns:

```text
held_real_second_device_deferred
```

It performs no mutation. The only safe next action is to request the later
A0-Real/transport gate with an explicit Human decision contract. Do not use
A0-Lite to bypass that gate.

## Functional walkthrough boundary

After this documentation is accepted, a separate Human Decision Contract must
bind one adopter project/root/revision plus retention and cleanup. The adopter
should be able to find this workflow, complete one supported fresh or existing
single-machine onboarding, read fresh authority/status, perform one approved
local action, see a hold and recovery explanation, and recognize that
A0-Lite is experimental while real second-device work is unavailable.

Functional evidence may establish that the front door is discoverable and
truthful: it can validate **discoverability**, **authority clarity**, **recovery clarity**, and **boundary honesty** as functional questions. It must not
manufacture numeric usability, performance, latency, scale or
real-adopter-friction scores from a synthetic walkthrough; those stay
`not_collected` and await later real usage feedback. This walkthrough does not
authorize an A0-Lite operation, adapter publication, main merge, or release.
