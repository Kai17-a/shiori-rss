---
name: performance-check
description: Investigate performance regressions in this repository by checking recent changes, API/frontend request paths, SQLite migrations, query plans, and missing indexes before proposing fixes. Use when the user asks why the app is slow, whether DB migrations are adequate for performance, or to audit API/list-page latency.
---

# Performance Check

Use this skill to diagnose app performance regressions before changing code.

## Scope

- API list endpoints, especially bookmarks and RSS.
- Frontend pages that repeatedly call API endpoints or fetch all pages client-side.
- SQLite migrations, schema, indexes, and query plans.
- Recent commits that may have changed filtering, sorting, pagination, or response building.

## Required Repository Reading

Follow `AGENTS.md` reading order first:

1. `README.md`
2. `specs/llm-reading-guide.md`
3. If inspecting `api/` or migrations, use the `learning` skill and read its SQLModel/dbmate guidance as applicable.
4. If inspecting `frontend/`, read `frontend/README.md` before changing or recommending frontend code changes.

## Workflow

1. Check worktree and recent changes.
   - `git status --short`
   - `git log --oneline --decorate -n 12`
   - `git show --stat --oneline <suspect-commit>`

2. Identify hot request paths.
   - Search API repositories/services for `ORDER BY`, `WHERE`, `JOIN`, `COUNT`, `LIMIT`, `OFFSET`.
   - Search frontend pages/composables for repeated `/bookmarks`, `/rss-feeds`, pagination loops, and client-side filtering.
   - Pay attention to list pages, dashboard pages, favorites pages, folder/tag detail pages, and RSS article pages.

3. Compare implementation with migrations.
   - Read `db/migrations/*.sql` and `db/schema.sql`.
   - Confirm tables, foreign keys, unique constraints, and indexes support current API filters and sort orders.
   - Compare with `api/model/models.py` if SQLModel table definitions are relevant.

4. Run SQLite query-plan checks against `data/data.db` when present.
   - Use `EXPLAIN QUERY PLAN` for representative list/count queries.
   - Look for:
     - `SCAN <table>` on growing tables.
     - `USE TEMP B-TREE FOR ORDER BY`.
     - joins that use only the wrong side of a composite primary key.
     - filters on unindexed boolean/date/folder/tag columns.

5. Check for N+1 queries.
   - Look for response builders that fetch related rows per item.
   - In this repo, bookmark list responses should be checked for per-bookmark tag lookups.

6. Report findings before editing.
   - Separate confirmed causes from plausible risks.
   - Include file references and query-plan snippets.
   - Prioritize fixes by expected impact.

## Common Checks

Bookmark list default sort:

```bash
sqlite3 data/data.db "EXPLAIN QUERY PLAN SELECT DISTINCT b.* FROM bookmarks b ORDER BY b.created_at DESC, b.id DESC LIMIT 20 OFFSET 0;"
```

Bookmark favorite count:

```bash
sqlite3 data/data.db "EXPLAIN QUERY PLAN SELECT COUNT(*) AS total FROM bookmarks WHERE is_favorite = 1;"
```

Tag-filter bookmark join:

```bash
sqlite3 data/data.db "EXPLAIN QUERY PLAN SELECT DISTINCT b.* FROM bookmarks b INNER JOIN bookmark_tags bt ON b.id = bt.bookmark_id WHERE bt.tag_id = 1 ORDER BY b.created_at DESC, b.id DESC LIMIT 20 OFFSET 0;"
```

RSS feed list sort:

```bash
sqlite3 data/data.db "EXPLAIN QUERY PLAN SELECT * FROM rss_feeds ORDER BY title ASC, id ASC LIMIT 20 OFFSET 0;"
```

RSS article list sort:

```bash
sqlite3 data/data.db "EXPLAIN QUERY PLAN SELECT * FROM rss_feed_articles WHERE feed_id = 1 ORDER BY published IS NULL ASC, published DESC, id DESC LIMIT 20 OFFSET 0;"
```

## Typical Findings In This Repo

- `bookmarks` needs indexes that match list filters and default sort, not only `url` uniqueness.
- `bookmark_tags` primary key `(bookmark_id, tag_id)` supports bookmark-to-tags lookups, but tag-to-bookmarks filtering may need `(tag_id, bookmark_id)`.
- `rss_feeds` list sorting by `title ASC, id ASC` needs a matching index as data grows.
- `rss_feed_articles` ordering by `published IS NULL, published DESC, id DESC` may still use a temp sort unless the query or expression index matches it.
- Frontend pages that fetch all bookmark pages and filter in the browser should usually be moved to server-side filters.

## Output Format

Keep the answer concise and diagnostic:

- `主因`: confirmed bottlenecks with evidence.
- `DB定義`: migration/index gaps and whether they are functional vs performance issues.
- `影響`: which screens or endpoints are affected.
- `次に直すなら`: ordered fix list.

Do not make schema or code changes unless the user asks for fixes after the diagnosis.
