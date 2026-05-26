# Refresh Workflow

Pull remote updates, conditionally regenerate adapters, and install to local runtimes.

## Trigger

- `refresh practices and assets`
- `刷新practices和assets`

## Steps

### 0. Locate the repo

If the current working directory is inside the agent-foundry repo, use it. Otherwise default to `~/Coding/agent-foundry` or the path configured in `runtime/local/runtime_manifest.yaml`. If the repo cannot be found, ask the user for the path.

Change into the repo root before proceeding.

### 1. Verify remote

```bash
git remote -v
```

If no remote is configured, report "no remote configured for agent-foundry repo — nothing to pull" and skip to step 7 (install only).

### 2. Check for local uncommitted changes

```bash
git status --porcelain
```

- If clean: proceed to step 3.
- If dirty:
  - Report which files are changed.
  - Ask the user to choose:
    - **Stash**: `git stash push -m "agent-foundry refresh auto-stash"` → pull → `git stash pop`.
    - **Abort**: stop here. Tell the user to commit or discard changes, then re-run refresh.
  - Do not invent additional options. Do not proceed without a choice.
  - If the user picks Stash and `git stash pop` has conflicts:
    - Report: which files conflicted, that the stash is preserved (`git stash list` to see it).
    - Tell the user: resolve conflicts, then `git stash drop` to remove the stash.
    - Stop — do not continue to publish or install with a conflicted working tree.

### 3. Pull

Run `git pull`.

If pull fails (network error, auth failure, merge conflict, etc.), report the exact error and stop. Do not continue to publish or install.

### 4. Determine what changed

Use `@{upstream}` comparison when available, with fallbacks:

```bash
# Preferred: diff against the remote tracking branch since last pull
git diff --name-only @{upstream} HEAD

# Fallback: if the local reflog has a previous HEAD entry
git diff --name-only HEAD@{1} HEAD
```

If neither works (e.g., fresh clone, no reflog), assume all active canonical files may need regeneration and proceed to publish.

### 5. Conditionally publish adapters

If any changed files are under `practices/`, `assets/`, `indexes/`, or `workflows/` — or if step 4 could not determine changes — regenerate adapters by following `workflows/publish-adapters.md` and `workflows/transform-canonical-to-adapters.md`.

Report which canonical files triggered the regeneration.

If nothing under those directories changed, skip publish and report "adapters already current."

### 6. Install

Run `python3 scripts/install_foundry.py --apply`.

If install fails, report the error and stop.

### 7. Report

Summarize:

- Whether remote changes were pulled (and which files), or skipped (no remote / already up to date).
- Whether publish ran (and which adapters were regenerated), or skipped.
- Which local runtimes were updated.
- Any warnings (e.g., hermes disabled, chatgpt requires manual import).

## Guardrails

- Never discard or overwrite local changes without asking.
- If any step fails after a stash pop conflict, remind the user about `git stash list`.
- Do not skip consistency checks; `install_foundry.py --apply` runs them automatically.
- If publish fails, stop — do not install stale adapters.
- If the repo was clean before refresh and something fails mid-way, report the current state clearly so the user knows what happened and what did not.
