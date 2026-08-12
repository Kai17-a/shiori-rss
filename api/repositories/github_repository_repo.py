import sqlite3


class GitHubRepositoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def find_all(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM github_repositories ORDER BY owner, repository, id"
        ).fetchall()
        return [dict(row) for row in rows]

    def find_by_id(self, repository_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM github_repositories WHERE id = ?", (repository_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_by_url(self, repository_url: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM github_repositories WHERE repository_url = ?",
            (repository_url,),
        ).fetchone()
        return dict(row) if row else None

    def insert(self, values: dict[str, object]) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO github_repositories (
                owner, repository, repository_url, latest_release_name,
                latest_release_tag, latest_release_url, latest_release_body,
                latest_release_published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(values[key] for key in (
                "owner", "repository", "repository_url", "latest_release_name",
                "latest_release_tag", "latest_release_url", "latest_release_body",
                "latest_release_published_at",
            )),
        )
        assert cursor.lastrowid is not None
        row = self.find_by_id(cursor.lastrowid)
        assert row is not None
        return row

    def update_release(self, repository_id: int, values: dict[str, object]) -> dict:
        self.conn.execute(
            """
            UPDATE github_repositories SET
                latest_release_name = ?, latest_release_tag = ?,
                latest_release_url = ?, latest_release_body = ?,
                latest_release_published_at = ?,
                fetched_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (
                values["latest_release_name"], values["latest_release_tag"],
                values["latest_release_url"], values["latest_release_body"],
                values["latest_release_published_at"], repository_id,
            ),
        )
        row = self.find_by_id(repository_id)
        assert row is not None
        return row

    def delete(self, repository_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM github_repositories WHERE id = ?", (repository_id,)
        )
        return cursor.rowcount > 0
