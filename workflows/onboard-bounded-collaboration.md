# Onboard Bounded Collaboration

Use this workflow only after a project explicitly requests native bounded-collaboration onboarding. It initializes two durable roles and assigns no Work. RoleHub is a logical read-only projection, never a native task or readiness prerequisite.

## Inputs

- Saved project identity and repository binding.
- One reuse policy: `fresh_only` or `reuse_allowed`.
- Explicit native-apply authorization.
- Whether the optional peer handshake is requested.
- Public task capabilities exposed by the current runtime.

## Public capability boundary

Codex native onboarding uses `list_projects`, `create_thread`, `read_thread`, `wait_threads`, and `send_message_to_thread`. `reuse_allowed` may additionally use `list_threads`. Do not scan private sessions, databases, transcripts, hidden registries, or filesystem implementation state to recover an identity.

`threadId` is a durable task identity. `clientThreadId` or another pending task ID is only `setup_pending`. If a pending ID cannot be resolved through a public capability, return `thread_id_unresolved` HOLD, retain the accepted creation receipt, and do not call `create_thread` again.

## Procedure

1. Resolve the exact saved project through `list_projects`; verify repository identity and local/worktree policy before creation.
2. Select the policy:
   - `fresh_only`: do not list, read, reuse, rename, archive, or otherwise inspect old tasks. Create exactly one new Coordinator and one new Durable Architect.
   - `reuse_allowed`: inspect public summaries only and reuse a unique matching role; ambiguity holds.
3. Submit compact `RoleSessionInit/v1` initialization to each role. It names the project, role, peer role, one onboarding token, `initialization_only: true`, `work_assigned: false`, and the required public owner readback.
4. Record creation as `accepted`. Do not treat a pending setup handle as initialized. Once a real `threadId` is available, use `read_thread` to verify that exact task reports its owner role, real ID, and initialized state.
5. If a peer handshake was requested, wait until both real IDs have owner readback. One onboarding executor then sends both `PeerHandshake/v1` messages with the same token and an explicit `reply_to_thread_id`. Carry forward the fresh `wait_threads` cursor; an older completed turn cannot satisfy acknowledgement.
6. Emit `NativeOnboardingReceipt/v1` only when both roles are accepted and initialized and, when requested, both acknowledgements are verified. Keep `accepted`, `initialized`, `acknowledged`, and `ready` separate.

## Holds and recovery

- Missing public capability, ambiguous saved project, duplicate reusable roles, invalid owner readback, reused thread identity, forged/stale receipt, or unresolved pending setup is a typed HOLD.
- Never repair a HOLD by private-state scanning, duplicate creation, old-task mutation, deletion, archive, or implicit rollback.
- A partial create may be marked setup-incomplete for follow-up, but automatic cleanup is forbidden.
- Preserve dirty repository state and historical tasks exactly as found.

## Completion boundary

The receipt proves only native role initialization. It does not assign Work or grant scheduler, GitHub, branch, merge, release, cleanup, Vault, adapter-publication, or runtime-install authority. Daily Work still uses its own Execution Contract and owner.
