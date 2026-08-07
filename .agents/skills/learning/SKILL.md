---
name: learning
description: Repository learning notes for API and batch work. Use when working in `api/`, `batch/`, Python persistence models, SQLite migrations, or Rust SQLite code. This skill points to the bundled SQLModel, dbmate, and rusqlite learning references before implementation.
---

# Learning

Use this skill before changing `api/` or `batch/` code in this repository.

## When To Use

- Python API work in `api/`
- SQLModel model or schema changes
- DB migration work with `dbmate`
- Rust batch work in `batch/`
- SQLite access changes in Python or Rust

## Reading Order

1. `README.md`
2. `AGENTS.md`
3. `specs/llm-reading-guide.md`
4. Then load only the relevant learning note below

## References

- SQLModel and FastAPI model patterns
  - `references/sqlmodel/llm.txt`
  - `references/sqlmodel/00-learning-summary.txt`
  - `references/sqlmodel/01-basics.txt`
  - `references/sqlmodel/02-fastapi-integration.txt`
- DB migrations with dbmate
  - `references/dbmate/llm.txt`
- Rust SQLite access in batch
  - `references/rustqlite/llm.txt`

## Selection Rules

- For `api/` model, schema, repository, or service work:
  - read `references/sqlmodel/llm.txt`
- For DB migration creation, apply, rollback, or schema dump work:
  - read `references/dbmate/llm.txt`
- For `batch/` SQLite query or connection work:
  - read `references/rustqlite/llm.txt`
- If the task spans Python API and migrations:
  - read both `references/sqlmodel/llm.txt` and `references/dbmate/llm.txt`

## Expectations

- Use the learning notes as implementation guidance, not as a substitute for repository code reading.
- Keep the final change aligned with the current repository architecture and specs.
