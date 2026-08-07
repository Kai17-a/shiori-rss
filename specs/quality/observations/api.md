# API Test Observations

| Area      | What it covers           | Main checks                                                   |
| --------- | ------------------------ | ------------------------------------------------------------- |
| Health    | Health-related contract  | Checked indirectly by app startup and E2E, not by `api/tests` |
| Bookmarks | Bookmark CRUD            | Create, list, get by id, update, delete                       |
| Bookmarks | Bookmark list            | Shape, ordering, pagination                                   |
| Bookmarks | Bookmark search/filter   | Query by keyword, folder, tag                                 |
| Bookmarks | Bookmark-tag relations   | Add, replace, remove tags                                     |
| Bookmarks | Bookmark-folder relation | Set and clear folder                                          |
| Bookmarks | Validation               | Required fields, invalid URL, duplicate tags                  |
| Bookmarks | Error handling           | Missing resources, bad payloads                               |
| RSS       | RSS feed CRUD            | Create, list, get by id, update, delete                       |
| RSS       | RSS feed validation      | Invalid URL, non-feed URL, duplicate URL                      |
| RSS       | RSS execution            | Execute feed with configured webhook                          |
| Settings  | Webhook settings         | Get, save, ping, invalid Discord URL                          |
| Settings  | Webhook behavior         | Save only after ping succeeds, missing config handling        |
| Folders   | Folder CRUD              | Create, list, update, delete                                  |
| Folders   | Folder limits            | Enforce maximum folder count                                  |
| Folders   | Delete behavior          | Bookmarks fall back to `folder_id = null`                     |
| Tags      | Tag CRUD                 | Create, list, update, delete                                  |
| Tags      | Tag limits               | Enforce maximum tag count                                     |
| Tags      | Uniqueness               | Duplicate tag name rejected                                   |
| Database  | Schema and startup       | Schema creation and idempotency                               |
| Database  | SQLite errors            | Convert SQLite failures into `500` responses                  |
| Common    | Timestamp updates        | `updated_at` changes on mutation                              |
| Common    | Contract stability       | Response shape matches frontend needs                         |

## Test Types

| Type       | Purpose                                   |
| ---------- | ----------------------------------------- |
| Unit       | Service and repository behavior           |
| Endpoint   | Request/response contract and error codes |
| Regression | Edge cases and previously fixed bugs      |
| Boundary   | Limits, duplicates, missing references    |

## Notes

- Use isolated database state per test.
- Verify both happy path and error path behavior.
- Keep payload assertions aligned with frontend expectations.
- Mock external HTTP calls for RSS feed validation and webhook ping/execute paths.
