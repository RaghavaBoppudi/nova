import sqlite3
from contextlib import contextmanager

DB_PATH = "nova_memory.db"


@contextmanager
def get_connection():
    """Context manager for SQLite connections — ensures proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create sessions and messages tables if they don't exist."""
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')


def create_session() -> int:
    """Create a new conversation session and return its ID."""
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO sessions DEFAULT VALUES")
        return cursor.lastrowid


def save_message(session_id: int, role: str, content: str):
    """Save a single message to the database."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )


def get_session_messages(session_id: int) -> list:
    """Return all messages for a session in chronological order."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


def get_recent_messages(limit: int = 20) -> list:
    """Return the most recent messages across all sessions."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT role, content FROM messages ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [{"role": row[0], "content": row[1]} for row in reversed(cursor.fetchall())]