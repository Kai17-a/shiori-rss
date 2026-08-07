---
name: repo-test-routine
description: Run and verify this repository's test workflow. Use when checking API lint/tests, frontend unit tests, or Playwright E2E after code or behavior changes.
---

# Repo Test Routine

Use this skill when the task is to verify code changes in this repository.

## Workflow

1. Start with `./scripts/run-all-tests.sh` when you need a full pass.
2. Use `./scripts/run-e2e-tests.sh` when the change affects browser behavior, routing, or UI state.
3. If the change is API-only, run the affected API checks:
   - `uv run --directory api ruff check .`
   - `uv run --directory api pytest -q`
   - `uv run --directory api pyright`
4. If the change is frontend-only, run:
   - `bun run test`
   - `./scripts/run-e2e-tests.sh` when the UI flow matters

## Rules

- Keep unrelated worktree changes intact.
- Prefer the repository scripts over ad hoc command lists.
- For E2E, assume both API and frontend must be reachable unless the helper script sets them up.
- If a check fails, fix the underlying issue instead of narrowing the scope unless the user asked for a targeted run.
