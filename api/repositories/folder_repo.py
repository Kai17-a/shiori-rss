import sqlite3


class FolderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, name: str, description: str | None = None) -> dict:
        cursor = self.conn.execute(
            "INSERT INTO folders (name, description) VALUES (?, ?)",
            (name, description),
        )
        row = self.conn.execute(
            "SELECT * FROM folders WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def find_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM folders ORDER BY name ASC, id ASC").fetchall()
        return [dict(row) for row in rows]

    def find_by_name(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM folders WHERE name = ?",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def find_by_id(self, folder_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        return dict(row) if row else None

    def update(
        self, folder_id: int, name: str, description: str | None = None
    ) -> dict | None:
        cursor = self.conn.execute(
            "UPDATE folders SET name = ?, description = ? WHERE id = ?",
            (name, description, folder_id),
        )
        if cursor.rowcount == 0:
            return None
        row = self.conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete(self, folder_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        return cursor.rowcount > 0
