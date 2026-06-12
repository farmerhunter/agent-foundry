# Refresh Workflow

Pull remote updates, conditionally publish adapters, and install to local runtimes.

## Trigger

- `refresh practices and assets`
- `刷新practices和assets`

## Invariant

The user must always know the exact sync state of their machine:
- which commit the repo is on;
- whether local canonical changes are committed;
- whether those commits are pushed;
- which local runtimes were updated.

Never hide ambiguity. If the state cannot be determined, report it and stop.

---

## Step 0: Locate The Repo

If the current working directory is inside the agent-foundry repo, use it. Otherwise default to `~/Coding/agent-foundry` or the path configured in `runtime/local/runtime_manifest.yaml`. If the repo cannot be found, ask the user for the path.

Change into the repo root before proceeding.

Run a read-only operation-context preflight and keep the output in the final report:

```bash
python3 scripts/operation_context.py status
```

If the report cannot identify Core and the selected Vault, stop before pull, publish, or install. If the command is invoked from a product project, the report must show that project as evidence context only; refresh writes must stay within Core machine-local state, generated adapter output, and managed runtime targets.

---

## Step 1: Determine Local State

Run:

```bash
git status --porcelain
```

Classify changes into two categories:

**A. Canonical or adapter changes** — files under `practices/`, `assets/`, `indexes/`, `adapters/`, `workflows/`, `schemas/`, `scripts/`, `usage/`, `docs/` (excluding machine-local deployment docs).

**B. Unrelated changes** — everything else, including `runtime/local/`, personal notes, IDE files, or experimental edits.

### If category A exists (canonical/adapter changes)

These should **not** be stashed. They represent unpublished work that must be committed before pulling.

Report which files changed and ask:

```text
Local canonical/adapter changes detected:
- <file>
- <file>

Choose:
- Commit and push: git add <files>, git commit, ./sync.sh push, then continue refresh.
- Abort: stop. You commit and push manually, then re-run refresh.
```

Do not offer "stash" for category A changes. Stashing unpublished practices or adapters creates invisible state that is easy to forget.

If the user chooses **Commit and push**:
1. Stage the files: `git add -A` (or specific files).
2. Generate a concise commit message describing the changes. If the message is unclear, ask the user to edit it.
3. Commit.
4. Run `./sync.sh push`.
   - If push succeeds: continue to Step 3 (Pull).
   - If push fails: the script reports the failure and next action. Go to Step 8 (Final Report) with state `unpushed commits`.

If the user chooses **Abort**: stop immediately. Do not proceed to pull, publish, or install.

### If only category B exists (unrelated changes)

Offer:

```text
Unrelated local changes detected:
- <file>

Choose:
- Stash: git stash push -m "agent-foundry refresh auto-stash" → pull → stash pop.
- Abort: stop. You resolve the changes, then re-run refresh.
```

If the user picks **Stash** and `git stash pop` later has conflicts:
- Report which files conflicted.
- Report that the stash is preserved (`git stash list` to see it).
- Tell the user: resolve conflicts, then `git stash drop` to remove the stash.
- Stop. Do not continue to publish or install with a conflicted working tree.

### If clean

Proceed to Step 2.

---

## Step 2: Push Unpushed Commits

Run:

```bash
./sync.sh push
```

This handles pre-flight checks (consistency, named branch, remote configured), retries network failures with exponential backoff, and prints a RUNTIME-003 status block.

If push succeeds: continue to Step 3.

If push fails (auth, rejected, network exhausted):
- The script reports the exact failure and next action.
- If the failure is a non-fast-forward rejection because remote has new commits, go to Step 3A (Assisted Divergent Resolution).
- Otherwise go to Step 8 with state `unpushed commits`. Do not pull; pulling with unpushed commits can create divergent history.

If there are no unpushed commits, the script reports "already up to date" and exits cleanly. Continue to Step 3.

---

## Step 3: Pull

Run:

```bash
./sync.sh pull
```

This checks preconditions (no unpushed commits, clean working tree, named branch, upstream tracking), then runs `git pull --ff-only` with network retry, and prints a RUNTIME-003 status block listing what changed.

If pull fails (network error, auth failure, merge conflict, non-fast-forward divergence, etc.):
- The script reports the exact error and next action.
- If the failure is non-fast-forward divergence, go to Step 3A (Assisted Divergent Resolution).
- Otherwise go to Step 8 with state `pull failed`.
- Do not continue to publish or install.

If the repo has no remote configured, the script reports it and exits. Continue to Step 6 (Install only).

---

## Step 3A: Assisted Divergent Resolution

This step is used only when push or pull reports a non-fast-forward/divergent history. The refresh workflow must not auto-merge silently, but the agent should be able to help the user resolve the divergence end-to-end as an explicit synchronization task.

First report the situation and ask whether to proceed:

```text
Divergent history detected. Automatic refresh is paused.

Choose:
- Resolve with agent assistance: inspect both histories, rebase or merge intentionally, run checks, regenerate adapters if needed, push, then resume install.
- Abort: stop. You resolve manually, then re-run refresh.
```

If the user chooses **Resolve with agent assistance**:

1. Fetch and inspect both sides:

```bash
git fetch origin
git status --short --branch
git log --oneline --graph --decorate --left-right HEAD...@{upstream}
git diff --name-only HEAD...@{upstream}
```

2. Classify the divergence:
   - Local-only commits under `practices/`, `assets/`, `indexes/`, `adapters/`, `workflows/`, `schemas/`, `scripts/`, `usage/`, or `docs` are canonical/adapter work and must be preserved unless the user explicitly rejects them.
   - Remote-only commits must be inspected for overlapping canonical IDs, indexes, adapter outputs, workflow changes, or usage aggregate changes.
   - If either side contains destructive or unclear changes, stop and ask for user direction.

3. Prefer rebase for ordinary canonical/adapters divergence:

```bash
git rebase @{upstream}
```

Use merge only when the user explicitly wants a merge commit or when rebase is inappropriate for the current collaboration context.

4. If conflicts occur, resolve intentionally:
   - Practice conflicts: merge semantic guidance, version, `updated`, `related`, and activation metadata deliberately. Do not choose ours/theirs blindly.
   - Index conflicts: preserve all valid entries, unique IDs, correct paths, statuses, aliases, and ordering.
   - Asset conflicts: preserve canonical practice links, published targets, lifecycle state, and version/update metadata.
   - Adapter conflicts: resolve canonical files first, then regenerate adapters instead of hand-merging generated drift.
   - `usage/usage-aggregate.yaml`: preserve aggregate evidence from both sides when possible; do not drop usage rows just to make the conflict disappear.

5. After resolving conflict files:

```bash
git add -A
git rebase --continue
```

If the chosen operation was merge instead of rebase, complete the merge normally after staging resolved files.

6. After rebase or merge completes, run checks:

```bash
python3 scripts/check_consistency.py
python3 scripts/check_adapter_quality.py
python3 scripts/check_activation.py
```

If changed files include `practices/`, `assets/`, `indexes/`, or `workflows/`, regenerate adapters by following Step 5 before installing. Commit any regenerated adapter changes.

7. Push:

```bash
./sync.sh push
```

If rebase rewrote commits that were already pushed, ask the user before using:

```bash
git push --force-with-lease
```

Never use plain `git push --force`.

8. Resume:
   - If push succeeds and checks pass, continue to Step 6 (Install).
   - If push fails or checks fail, go to Step 8 with a report naming the exact failing step, current commit, and unresolved files.

---

## Step 4: Determine What Changed

Use `@{upstream}` comparison when available, with fallbacks:

```bash
# Preferred: diff against the remote tracking branch since last pull
git diff --name-only @{upstream} HEAD

# Fallback: if the local reflog has a previous HEAD entry
git diff --name-only HEAD@{1} HEAD
```

If neither works (e.g., fresh clone, no reflog), assume all active canonical files may need regeneration and proceed to publish.

---

## Step 5: Conditionally Publish Adapters

If any changed files are under `practices/`, `assets/`, `indexes/`, or `workflows/` — or if Step 4 could not determine changes — regenerate adapters by following `workflows/publish-adapters.md` and `workflows/transform-canonical-to-adapters.md`.

Report which canonical files triggered the regeneration.

If nothing under those directories changed, skip publish and report "adapters already current."

After publishing, if new adapter files were written:
1. Run `python3 scripts/check_consistency.py`.
2. If it fails, stop. Do not install inconsistent adapters.
3. If it passes, stage and commit the adapter changes with a message like `refresh: regenerate adapters`.
4. Run `./sync.sh push --skip-check` to push the commit (consistency was already verified in step 1).
   - If push fails: go to Step 8 with state `unpushed adapter commit`.

---

## Step 6: Install

Run:

```bash
python3 scripts/install_foundry.py --apply
```

If install fails, report the error and go to Step 8 with state `install failed`.

---

## Step 7: Verify Runtime Sync

Run:

```bash
python3 scripts/sync_status.py
```

If `sync_status.py` is unavailable, run `python3 scripts/runtime_manifest.py status` as a fallback.

Report:
- Which targets are enabled.
- Whether their installed files match the current adapter outputs.
- Any warnings (e.g., target disabled, ChatGPT requires manual import).

---

## Step 8: Final Report

Summarize unambiguously:

```text
Repo state:
- Commit: <short-hash> (<branch>)
- Remote: <remote-url or "not configured">
- Unpushed commits: <count and list, or "none">
- Local changes: <clean / stashed / dirty-abort>

Pull:
- Pulled: <yes/no> — files: <list or "none">

Publish:
- Regenerated: <yes/no> — adapters: <list or "none">
- Consistency check: <passed/failed>

Install:
- Updated runtimes: <list>
- Warnings: <list or "none">
```

If any step failed, the report must clearly state:
- what succeeded;
- what failed;
- what the user should do next.

---

## Guardrails

- Never stash canonical or adapter changes. Only commit or abort.
- Never pull when unpushed commits exist. Push first, or abort.
- Never install adapters that fail the consistency check.
- If publish fails, stop. Do not install stale adapters.
- If the repo was clean before refresh and something fails mid-way, report the current state clearly so the user knows what happened and what did not.
- Do not invent options. The choices are: commit+push, stash (for unrelated changes only), assisted divergent resolution (only after non-fast-forward/divergence), retry, or abort.
- Do not silently merge canonical/adapters divergence. Assisted divergent resolution is explicit work with user approval, history inspection, semantic conflict handling, checks, publish, and final sync reporting.

---

## About Git Stash

`git stash` temporarily saves changes that are not ready to be committed, so you can switch branches or pull updates without creating a messy commit. It is a convenience tool, not a replacement for commits.

In this workflow, stash is **only** offered for unrelated changes (category B). It must never be used for canonical practices, assets, indexes, or adapters — those represent real work that should be committed and traceable.

If a stash pop creates conflicts, the stash remains in `git stash list` until you explicitly drop it. Do not drop a stash until you have verified the merged result is correct.
