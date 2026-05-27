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
- Commit and push: git add <files>, git commit, git push, then continue refresh.
- Abort: stop. You commit and push manually, then re-run refresh.
```

Do not offer "stash" for category A changes. Stashing unpublished practices or adapters creates invisible state that is easy to forget.

If the user chooses **Commit and push**:
1. Stage the files: `git add -A` (or specific files).
2. Generate a concise commit message describing the changes. If the message is unclear, ask the user to edit it.
3. Commit.
4. Push.
   - If push succeeds: continue to Step 3 (Pull).
   - If push fails (network, auth): report clearly and go to Step 8 (Final Report) with state `unpushed commits`.

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

## Step 2: Check For Unpushed Commits

Run:

```bash
git log @{upstream}..HEAD --oneline
```

If there are unpushed commits (e.g., from a previous session where push failed):

1. Report the commits.
2. Attempt to push.
3. If push succeeds: continue.
4. If push fails: go to Step 8 with state `unpushed commits`. Do not pull; pulling with unpushed commits can create divergent history.

---

## Step 3: Pull

Run:

```bash
git pull
```

If pull fails (network error, auth failure, merge conflict, etc.):
- Report the exact error.
- Go to Step 8 with state `pull failed`.
- Do not continue to publish or install.

If the repo has no remote configured, report "no remote configured for agent-foundry repo — nothing to pull" and continue to Step 6 (Install only).

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
4. Attempt to push the commit.
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
- Do not invent options. The choices are: commit+push, stash (for unrelated changes only), retry, or abort.

---

## About Git Stash

`git stash` temporarily saves changes that are not ready to be committed, so you can switch branches or pull updates without creating a messy commit. It is a convenience tool, not a replacement for commits.

In this workflow, stash is **only** offered for unrelated changes (category B). It must never be used for canonical practices, assets, indexes, or adapters — those represent real work that should be committed and traceable.

If a stash pop creates conflicts, the stash remains in `git stash list` until you explicitly drop it. Do not drop a stash until you have verified the merged result is correct.
