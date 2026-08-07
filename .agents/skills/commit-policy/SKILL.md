---
name: commit-policy
description: Apply Conventional Commits with repository rules that keep commits reversible, and require tests and specs to be rolled back alongside code when history is rewritten.
---

# Commit Policy

Use this skill when writing commit messages, preparing a revert, or rewriting history.

## Base standard

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Commit types

- `feat`: user-facing feature
- `fix`: bug fix
- `docs`: documentation only
- `test`: tests only
- `refactor`: code refactor without behavior change
- `chore`: maintenance that does not affect product behavior
- `revert`: revert a previous commit

## Revert-safe rules

- A commit should contain one feature-sized change only.
- A feature-sized change is a single user-visible behavior addition, modification, or removal.
- A commit should not mix feature code with unrelated cleanup.
- Code, tests, and specs for one feature should stay in the same commit.
- Each commit should be independently revertible without leaving the repository in an obviously inconsistent state.
- When a behavior change touches code, tests, and specs, keep them aligned in the same change set.

## Revert and rebase rules

- If `revert` is performed, roll back the matching tests and specs too.
- If `rebase` or any history rewrite drops or reorders a behavior change, update the corresponding tests and specs to match the resulting state.
- Do not keep documentation for behavior that no longer exists.
- After a rollback, verify the codebase, tests, and specs describe the same behavior.

## Suggested format

```text
type(scope): short summary

optional body

optional footer
```

## Recommended footers

- `BREAKING CHANGE: ...`
- `Revert: <commit hash>`
