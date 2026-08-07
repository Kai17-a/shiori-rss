import sqlite3


class BookmarkRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(
        self,
        url: str,
        title: str,
        description: str | None,
        folder_id: int | None,
        is_favorite: bool,
    ) -> dict:
        cursor = self.conn.execute(
            "INSERT INTO bookmarks (url, title, description, folder_id, is_favorite) VALUES (?, ?, ?, ?, ?)",
            (url, title, description, folder_id, int(is_favorite)),
        )
        row = self.conn.execute(
            "SELECT * FROM bookmarks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def count_all(
        self,
        folder_id: int | None,
        tag_id: int | None,
        q: str | None,
        is_favorite: bool | None,
    ) -> int:
        query = "SELECT COUNT(*) AS total FROM bookmarks b"
        params: list = []

        conditions: list[str] = []
        if folder_id is not None:
            conditions.append("b.folder_id = ?")
            params.append(folder_id)
        if tag_id is not None:
            conditions.append(
                "EXISTS ("
                "SELECT 1 FROM bookmark_tags bt "
                "WHERE bt.bookmark_id = b.id AND bt.tag_id = ?"
                ")"
            )
            params.append(tag_id)
        if is_favorite is not None:
            conditions.append("b.is_favorite = ?")
            params.append(int(is_favorite))
        if q is not None:
            conditions.append("(b.title LIKE ? OR b.url LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        row = self.conn.execute(query, params).fetchone()
        return int(row["total"]) if row else 0

    def find_all(
        self,
        folder_id: int | None,
        tag_id: int | None,
        q: str | None,
        is_favorite: bool | None,
        order_by: str,
        limit: int,
        offset: int,
    ) -> list[dict]:
        query = "SELECT b.* FROM bookmarks b"
        params: list = []

        conditions: list[str] = []
        if folder_id is not None:
            conditions.append("b.folder_id = ?")
            params.append(folder_id)
        if tag_id is not None:
            conditions.append(
                "EXISTS ("
                "SELECT 1 FROM bookmark_tags bt "
                "WHERE bt.bookmark_id = b.id AND bt.tag_id = ?"
                ")"
            )
            params.append(tag_id)
        if is_favorite is not None:
            conditions.append("b.is_favorite = ?")
            params.append(int(is_favorite))
        if q is not None:
            conditions.append("(b.title LIKE ? OR b.url LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def find_by_id(self, bookmark_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_by_url(self, url: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM bookmarks WHERE url = ?", (url,)
        ).fetchone()
        return dict(row) if row else None

    def update(self, bookmark_id: int, fields: dict) -> dict | None:
        if not fields:
            return self.find_by_id(bookmark_id)

        if "is_favorite" in fields:
            fields = {**fields, "is_favorite": int(bool(fields["is_favorite"]))}

        set_clauses = ", ".join(f"{key} = ?" for key in fields)
        set_clauses += ", updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')"
        params = list(fields.values()) + [bookmark_id]

        cursor = self.conn.execute(
            f"UPDATE bookmarks SET {set_clauses} WHERE id = ?", params
        )
        if cursor.rowcount == 0:
            return None
        return self.find_by_id(bookmark_id)

    def delete(self, bookmark_id: int) -> bool:
        # bookmark_tags rows are removed automatically via ON DELETE CASCADE
        cursor = self.conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        return cursor.rowcount > 0

    def delete_by_criteria(
        self,
        bookmark_id: int | None = None,
        url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        folder_id: int | None = None,
        is_favorite: bool | None = None,
    ) -> bool:
        conditions: list[str] = []
        params: list[object] = []
        if bookmark_id is not None:
            conditions.append("id = ?")
            params.append(bookmark_id)
        if url is not None:
            conditions.append("url = ?")
            params.append(url)
        if title is not None:
            conditions.append("title = ?")
            params.append(title)
        if description is not None:
            conditions.append("description = ?")
            params.append(description)
        if folder_id is not None:
            conditions.append("folder_id = ?")
            params.append(folder_id)
        if is_favorite is not None:
            conditions.append("is_favorite = ?")
            params.append(int(is_favorite))

        if not conditions:
            return False

        cursor = self.conn.execute(
            f"DELETE FROM bookmarks WHERE {' AND '.join(conditions)}", params
        )
        return cursor.rowcount > 0

    def add_tag(self, bookmark_id: int, tag_id: int) -> None:
        # Let sqlite3.IntegrityError propagate on duplicate (PRIMARY KEY violation)
        self.conn.execute(
            "INSERT INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)",
            (bookmark_id, tag_id),
        )

    def remove_tag(self, bookmark_id: int, tag_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM bookmark_tags WHERE bookmark_id = ? AND tag_id = ?",
            (bookmark_id, tag_id),
        )
        return cursor.rowcount > 0

    def get_tags(self, bookmark_id: int) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT t.id, t.name
            FROM tags t
            INNER JOIN bookmark_tags bt ON t.id = bt.tag_id
            WHERE bt.bookmark_id = ?
            """,
            (bookmark_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_tags_by_bookmark_ids(self, bookmark_ids: list[int]) -> dict[int, list[dict]]:
        if not bookmark_ids:
            return {}

        placeholders = ", ".join("?" for _ in bookmark_ids)
        rows = self.conn.execute(
            f"""
            SELECT bt.bookmark_id, t.id, t.name
            FROM bookmark_tags bt
            INNER JOIN tags t ON t.id = bt.tag_id
            WHERE bt.bookmark_id IN ({placeholders})
            ORDER BY bt.bookmark_id ASC, t.id ASC
            """,
            bookmark_ids,
        ).fetchall()
        tags_by_bookmark_id: dict[int, list[dict]] = {
            bookmark_id: [] for bookmark_id in bookmark_ids
        }
        for row in rows:
            tags_by_bookmark_id[int(row["bookmark_id"])].append(
                {"id": row["id"], "name": row["name"]}
            )
        return tags_by_bookmark_id

    def normalize_row(self, row: dict) -> dict:
        normalized = dict(row)
        normalized["is_favorite"] = bool(normalized["is_favorite"])
        return normalized

    def set_tags(self, bookmark_id: int, tag_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM bookmark_tags WHERE bookmark_id = ?",
            (bookmark_id,),
        )
        for tag_id in tag_ids:
            self.conn.execute(
                "INSERT INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)",
                (bookmark_id, tag_id),
            )
