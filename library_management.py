import sqlite3
from datetime import datetime, timezone
from typing import Optional


class LibraryManagementSystem:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.recent_actions: list[str] = []
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                loaned_at TEXT NOT NULL,
                returned_at TEXT,
                FOREIGN KEY(book_id) REFERENCES books(id),
                FOREIGN KEY(member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                reserved_at TEXT NOT NULL,
                fulfilled INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(book_id) REFERENCES books(id),
                FOREIGN KEY(member_id) REFERENCES members(id)
            );
            """
        )

    def add_book(self, title: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO books(title, available) VALUES (?, 1)", (title,)
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_member(self, name: str) -> int:
        cursor = self.conn.execute("INSERT INTO members(name) VALUES (?)", (name,))
        self.conn.commit()
        return int(cursor.lastrowid)

    def lend_book(self, book_id: int, member_id: int) -> bool:
        book = self.conn.execute("SELECT available FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book or book["available"] == 0:
            return False

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO loans(book_id, member_id, loaned_at) VALUES (?, ?, ?)",
            (book_id, member_id, now),
        )
        self.conn.execute("UPDATE books SET available = 0 WHERE id = ?", (book_id,))
        self.conn.commit()
        self._record_action(f"lend:{book_id}:{member_id}")
        return True

    def reserve_book(self, book_id: int, member_id: int) -> bool:
        existing = self.conn.execute(
            "SELECT id FROM reservations WHERE book_id = ? AND member_id = ? AND fulfilled = 0",
            (book_id, member_id),
        ).fetchone()
        if existing:
            return False

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO reservations(book_id, member_id, reserved_at, fulfilled) VALUES (?, ?, ?, 0)",
            (book_id, member_id, now),
        )
        self.conn.commit()
        self._record_action(f"reserve:{book_id}:{member_id}")
        return True

    def return_book(self, book_id: int, member_id: int) -> Optional[int]:
        loan = self.conn.execute(
            """
            SELECT id FROM loans
            WHERE book_id = ? AND member_id = ? AND returned_at IS NULL
            ORDER BY loaned_at DESC, id DESC
            LIMIT 1
            """,
            (book_id, member_id),
        ).fetchone()
        if not loan:
            return None

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("UPDATE loans SET returned_at = ? WHERE id = ?", (now, loan["id"]))

        next_reservation = self.conn.execute(
            """
            SELECT id, member_id
            FROM reservations
            WHERE book_id = ? AND fulfilled = 0
            ORDER BY reserved_at ASC, id ASC
            LIMIT 1
            """,
            (book_id,),
        ).fetchone()

        if next_reservation:
            self.conn.execute(
                "UPDATE reservations SET fulfilled = 1 WHERE id = ?",
                (next_reservation["id"],),
            )
            self.conn.execute(
                "INSERT INTO loans(book_id, member_id, loaned_at) VALUES (?, ?, ?)",
                (book_id, next_reservation["member_id"], now),
            )
            self.conn.execute("UPDATE books SET available = 0 WHERE id = ?", (book_id,))
            assigned_member_id = int(next_reservation["member_id"])
            self._record_action(f"return_and_assign:{book_id}:{member_id}:{assigned_member_id}")
        else:
            self.conn.execute("UPDATE books SET available = 1 WHERE id = ?", (book_id,))
            assigned_member_id = None
            self._record_action(f"return:{book_id}:{member_id}")

        self.conn.commit()
        return assigned_member_id

    def pop_recent_action(self) -> Optional[str]:
        if not self.recent_actions:
            return None
        return self.recent_actions.pop()

    def _record_action(self, action: str) -> None:
        self.recent_actions.append(action)

    def close(self) -> None:
        self.conn.close()
