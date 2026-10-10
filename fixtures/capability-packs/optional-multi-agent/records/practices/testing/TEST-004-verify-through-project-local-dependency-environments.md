---
id: TEST-004
title: Verify through project-local dependency environments
domain: testing
type: checklist
status: active
version: 2
created: 2026-06-12
updated: 2026-06-17
tags: [testing, dependencies, verification, environments, lockfiles, reproducibility]
aliases:
  - TEST-004
  - use project-local dependencies for verification
  - do not rely on global project libraries
  - verification dependency setup is state
related: [RUNTIME-002, RUNTIME-003, TEST-002, IMPL-002]
applies_when:
  - running tests, linters, builds, or type checks in a repository after checkout, pull, or handoff
  - a machine has global Python, Node, or other language packages installed
  - a verification command needs dependencies that may not already be installed
  - a package manager may create lockfiles, virtual environments, or local dependency folders
review_required: false
provenance: "Harvested from tiny-ipa verification on 2026-06-12, where system Python lacked pytest and a uv-based project-local test run created backend/.venv plus an untracked uv.lock while dependency downloads were blocked by slow network. Revised on 2026-06-17 after pnpm/uv adoption showed package-manager commands must be run from the correct lockfile/workspace root."
---

## Principle

Run verification through the repository's project-local dependency environment when one is available. Install global runner and toolchain utilities, but do not rely on global Python or Node project libraries as the basis for declaring a repository verified.

## Rationale

Global project libraries make verification ambiguous. A global `pytest`, `ruff`, `typescript`, `eslint`, `fastapi`, or `vite` may be the wrong version for the repository, may mask missing project metadata, and may produce results that another agent, CI runner, or clean machine cannot reproduce.

Project-local environments duplicate some dependencies across repositories, but that duplication buys isolation and reproducibility:

- each repository can resolve the versions its metadata declares;
- one project can upgrade a dependency without changing another project's verification behavior;
- agents working in parallel on different repositories do not compete over one mutable global library set;
- lockfiles and local environments make failed dependency resolution visible as setup state instead of hidden machine state.

The priority order is correctness and reproducibility first, isolation second, and disk or first-install cost third. Modern package managers mitigate the cost with global caches, but the active environment used for verification should still be project-local.

## Guidance

Before running verification in an unfamiliar or freshly synchronized repository:

1. Inspect the repository's declared commands and environment markers: README, `pyproject.toml`, `package.json`, lockfiles, `.venv`, `uv.lock`, `requirements.txt`, `pnpm-lock.yaml`, `package-lock.json`, `Makefile`, or CI config.
2. Prefer the repository's local runner path:
   - Python: `.venv`, `uv run`, `python -m venv` plus editable install, Poetry, Hatch, or the repo's documented equivalent.
   - Node: `npm ci`, `npm install`, `pnpm install`, `yarn install`, then project scripts such as `npm run build`.
3. Use global installs for runner and toolchain utilities, not for project libraries. Good global candidates include `uv`, `node`, `npm`, `git`, `gh`, `rg`, `jq`, `sqlite`, and `yq`.
4. Treat generated dependency artifacts as verification state. If a command creates `.venv`, `node_modules`, lockfiles, caches, or package-manager metadata, report them explicitly.
5. If dependency resolution is blocked by network, authentication, or package availability, report verification as blocked by dependency setup. Do not describe it as a test failure.
6. Do not silently delete, commit, or ignore generated dependency artifacts. Decide from repository policy whether a new lockfile should be kept, removed, or added to a PR.

Before running an install or CI-style dependency command, confirm the command's package-manager scope:

- current working directory;
- nearest lockfile and package/project manifest;
- workspace root, if the package manager supports workspaces;
- dependency directory or virtual environment the command may create, remove, or rebuild;
- whether the command is meant for the current language layer.

For mixed repositories, do not assume every subdirectory accepts every package manager. A Python backend that uses `uv` and a frontend that uses `pnpm` should make those command boundaries explicit. If a command reports it will remove or rewrite dependency state outside the expected project layer, stop and inspect rather than continuing from muscle memory.

## Use This When

- A test command fails because a global interpreter cannot import the project's test runner.
- An agent is tempted to run `pip install pytest` or `npm install -g typescript` to make a repo pass locally.
- A package manager creates a new lockfile during a verification attempt.
- A slow or unreliable network prevents dependency installation before tests can start.
- Multiple repositories or agent threads share the same developer machine.

## Watch Out For

Do not over-correct by banning useful global tools. The boundary is not "nothing global"; it is "global tools may launch verification, but project libraries should come from the project environment."

Do not treat a globally installed CLI as equivalent to repository verification. A global `ruff` or `tsc` can be useful for quick diagnostics, but final verification evidence should name the project-local command or explain why it could not be run.

Do not hide package-manager side effects. An untracked lockfile, local virtual environment, or partially installed dependency tree is part of the final state the next agent or human needs to understand.

Do not run Node install commands from a backend subdirectory, or Python environment commands from a frontend subdirectory, merely because the tool is globally available. Global runner availability does not prove the current directory is the correct project scope.

## Example

In tiny-ipa, a focused backend test run first failed because `python` was not installed and system `python3` did not have `pytest`. Running `uv run --project backend --extra dev pytest ...` correctly moved verification into the project environment, but dependency downloads were slow and the command created `backend/.venv` plus an untracked `backend/uv.lock` before tests could run.

The correct final report was not "tests failed." It was: dependency setup blocked verification, the attempted project-local runner was `uv`, and the verification attempt left specific local artifacts that need a repository-policy decision.

## Activation

- Tier: task_router
- Phases: setup, verification, final_report, handoff
- Signals: missing test runner, global package fallback, package manager install, newly created lockfile, `.venv`, `node_modules`, dependency download, clean-machine verification
- Evidence: final report names the project-local verification command, whether dependency resolution completed, and any generated dependency artifacts left in the worktree

## Related Practices

- [[RUNTIME-002]]
- [[RUNTIME-003]]
- [[TEST-002]]
- [[IMPL-002]]
