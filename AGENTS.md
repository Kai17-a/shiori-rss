# Repository Instructions

This repository uses the following reading order for agentic work:

1. `README.md`
1. `specs/llm-reading-guide.md`
1. If the task touches `frontend/`, read `frontend/README.md` before changing code or tests there
1. If the task touches `api/` or `batch/`, use the `.agents/skills/learning/` skill first and read the relevant learning notes there
1. If the task touches `browser_extension/`, read `browser_extension/README.md` and `specs/components/browser-extension/README.md`
1. Official LLM reference sources for Nuxt, Nuxt UI, and Vue:
   - https://nuxt.com/modules/llms
   - https://nuxt.com/llms-full.txt
   - https://ui.nuxt.com/llms.txt
   - https://ui.nuxt.com/llms-full.txt
   - https://vuejs.org/llms-full.txt

Follow those sources before making changes to Nuxt, Python, Nuxt UI, or TypeScript code in this repository.

If you work in `frontend/`, read `frontend/README.md` and follow the Nuxt, Nuxt UI, and Vue LLM references before changing code or tests there.

If you work in `api/`, read the `learning` skill notes relevant to SQLModel and dbmate before changing code or migrations, and run `ruff`, `pyright`, and the API test suite before finishing.

If you work in `batch/`, read the `learning` skill note for `rusqlite` before changing Rust SQLite access.

If you work in `browser_extension/`, read `browser_extension/README.md` and keep the Chrome extension specs in sync with behavior changes.

For changelog work, keep feature and fix commits aligned with Conventional Commits, prefer feature-sized commits and squash merges, and keep internal-only commits out of `git-cliff` changelog output.

If you change Python code, run `ruff` and `pyright` for the affected package or project before finishing.

If you change Rust code, run the following commands before finishing:

- `cargo check`
- `cargo fmt`
- `cargo test`

If you add shared frontend API plumbing such as a common fetcher or request base layer, add the corresponding unit test or e2e test in the same change set.

When adding or changing DB columns, follow this process:

1. Create a SQL migration file in `db/migrations` named `{yyyymmddhhMMdd}.sql` for the DB operation.
2. Write the SQL into the created file.
3. From the repository root, run `mise x -- dbmate -u "sqlite:data/data.db" up` to apply the DB migrations.
4. If the DB needs to be rolled back, run `mise x -- dbmate -u "sqlite:data/data.db" down`.

If you change code, tests, or repository behavior, finish the task by creating the corresponding commit unless the user explicitly says not to.

If you change any API route, request/response shape, or backend behavior that `browser_extension/entrypoints/popup/App.vue` depends on, run `scripts/check-browser-extension-popup-api-contract.sh` before finishing.
