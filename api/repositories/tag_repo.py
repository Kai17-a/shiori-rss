import sqlite3


class TagRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, name: str, description: str | None = None) -> dict:
        # Let sqlite3.IntegrityError propagate on duplicate name (UNIQUE constraint)
        cursor = self.conn.execute(
            "INSERT INTO tags (name, description) VALUES (?, ?)",
            (name, description),
        )
        row = self.conn.execute(
            "SELECT * FROM tags WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def find_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM tags ORDER BY name ASC, id ASC").fetchall()
        return [dict(row) for row in rows]

    def find_by_name(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM tags WHERE name = ?",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def find_by_id(self, tag_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()
        return dict(row) if row else None

    def update(
        self, tag_id: int, name: str, description: str | None = None
    ) -> dict | None:
        cursor = self.conn.execute(
            "UPDATE tags SET name = ?, description = ? WHERE id = ?",
            (name, description, tag_id),
        )
        if cursor.rowcount == 0:
            return None
        row = self.conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()
        return dict(row) if row else None

    def delete(self, tag_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        return cursor.rowcount > 0
