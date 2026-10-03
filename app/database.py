import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime
from app import config
from app.config import MAX_SENT_EMAILS, MAX_INBOX_EMAILS

def get_db_connection() -> sqlite3.Connection:
    db_str = str(config.DB_PATH)
    conn = sqlite3.connect(db_str, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Verify schema exists on disk, auto-initializing if tables were cleared or recreated
    has_users = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if not has_users:
        _init_schema(conn)
    return conn

def _init_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            email_address TEXT NOT NULL,
            imap_host TEXT NOT NULL DEFAULT 'imap.gmail.com',
            imap_port INTEGER NOT NULL DEFAULT 993,
            imap_use_ssl INTEGER NOT NULL DEFAULT 1,
            smtp_host TEXT NOT NULL DEFAULT 'smtp.gmail.com',
            smtp_port INTEGER NOT NULL DEFAULT 465,
            smtp_use_ssl INTEGER NOT NULL DEFAULT 1,
            encrypted_password TEXT NOT NULL,
            sender_name TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS received_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender TEXT,
            sender_email TEXT,
            recipient TEXT,
            subject TEXT,
            snippet TEXT,
            body_plain TEXT,
            body_html TEXT,
            received_at TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_received_date ON received_emails(received_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sent_date ON sent_emails(sent_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")

    # Database-level FIFO Trigger: Once more than 50 messages exist in received_emails, evict the oldest
    conn.execute(f"""
        CREATE TRIGGER IF NOT EXISTS trigger_fifo_received_emails
        AFTER INSERT ON received_emails
        BEGIN
            DELETE FROM received_emails
            WHERE id NOT IN (
                SELECT id FROM received_emails
                ORDER BY received_at DESC, id DESC
                LIMIT {MAX_INBOX_EMAILS}
            );
        END;
    """)

    # Database-level FIFO Trigger: Once more than 50 messages exist in sent_emails, evict the oldest
    conn.execute(f"""
        CREATE TRIGGER IF NOT EXISTS trigger_fifo_sent_emails
        AFTER INSERT ON sent_emails
        BEGIN
            DELETE FROM sent_emails
            WHERE id NOT IN (
                SELECT id FROM sent_emails
                ORDER BY sent_at DESC, id DESC
                LIMIT {MAX_SENT_EMAILS}
            );
        END;
    """)
    conn.commit()

def init_db():
    """Create all required tables and indexes."""
    with get_db_connection() as conn:
        _init_schema(conn)

# --- Users & Sessions ---

def get_user_count() -> int:
    with get_db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        return row["count"] if row else 0

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean = username.strip().lower()
    prefix = clean.split("@")[0] if "@" in clean else clean
    full_email = f"{prefix}@gmail.com"
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(username) = ? OR LOWER(username) = ?",
            (clean, prefix, full_email)
        ).fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def create_user(username: str, password_hash: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        return cursor.lastrowid

def update_user_password(user_id: int, password_hash: str):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id)
        )
        conn.commit()

def update_user_last_login(user_id: int):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()

def save_session(token: str, user_id: int, expires_at: datetime):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat())
        )
        conn.commit()

def get_session(token: str) -> Optional[Dict[str, Any]]:
    now_iso = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT s.*, u.username FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ? AND s.expires_at > ?",
            (token, now_iso)
        ).fetchone()
        return dict(row) if row else None

def delete_session(token: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

def cleanup_expired_sessions():
    now_iso = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))
        conn.commit()

# --- Email Configuration ---

def get_email_config() -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM email_config WHERE id = 1").fetchone()
        return dict(row) if row else None

def save_email_config(
    email_address: str,
    encrypted_password: str,
    sender_name: Optional[str] = None,
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_use_ssl: int = 1,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    smtp_use_ssl: int = 1
):
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO email_config (
                id, email_address, encrypted_password, sender_name,
                imap_host, imap_port, imap_use_ssl,
                smtp_host, smtp_port, smtp_use_ssl, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                email_address = excluded.email_address,
                encrypted_password = CASE WHEN excluded.encrypted_password != '' THEN excluded.encrypted_password ELSE email_config.encrypted_password END,
                sender_name = excluded.sender_name,
                imap_host = excluded.imap_host,
                imap_port = excluded.imap_port,
                imap_use_ssl = excluded.imap_use_ssl,
                smtp_host = excluded.smtp_host,
                smtp_port = excluded.smtp_port,
                smtp_use_ssl = excluded.smtp_use_ssl,
                updated_at = CURRENT_TIMESTAMP
        """, (
            email_address, encrypted_password, sender_name,
            imap_host, imap_port, imap_use_ssl,
            smtp_host, smtp_port, smtp_use_ssl
        ))
        conn.commit()

# --- Received Emails ---

def upsert_received_email(email_data: Dict[str, Any]):
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO received_emails (
                message_id, sender, sender_email, recipient, subject,
                snippet, body_plain, body_html, received_at, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(message_id) DO UPDATE SET
                sender = excluded.sender,
                sender_email = excluded.sender_email,
                recipient = excluded.recipient,
                subject = excluded.subject,
                snippet = excluded.snippet,
                body_plain = excluded.body_plain,
                body_html = excluded.body_html,
                received_at = excluded.received_at
        """, (
            email_data.get("message_id"),
            email_data.get("sender"),
            email_data.get("sender_email"),
            email_data.get("recipient"),
            email_data.get("subject"),
            email_data.get("snippet"),
            email_data.get("body_plain"),
            email_data.get("body_html"),
            email_data.get("received_at")
        ))
        # FIFO Pruning: Keep strictly at most MAX_INBOX_EMAILS (50) by pushing the oldest message out
        conn.execute("""
            DELETE FROM received_emails
            WHERE id NOT IN (
                SELECT id FROM received_emails
                ORDER BY received_at DESC, id DESC
                LIMIT ?
            )
        """, (MAX_INBOX_EMAILS,))
        conn.commit()

def prune_received_emails(max_count: int = MAX_INBOX_EMAILS):
    """Enforce max received emails stored in database."""
    with get_db_connection() as conn:
        conn.execute("""
            DELETE FROM received_emails
            WHERE id NOT IN (
                SELECT id FROM received_emails
                ORDER BY received_at DESC, id DESC
                LIMIT ?
            )
        """, (max_count,))
        conn.commit()

def get_received_emails(query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        if query:
            q = f"%{query}%"
            rows = conn.execute("""
                SELECT id, message_id, sender, sender_email, recipient, subject,
                       snippet, received_at, fetched_at, is_read
                FROM received_emails
                WHERE subject LIKE ? OR sender LIKE ? OR sender_email LIKE ? OR snippet LIKE ?
                ORDER BY received_at DESC, id DESC
                LIMIT ?
            """, (q, q, q, q, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, message_id, sender, sender_email, recipient, subject,
                       snippet, received_at, fetched_at, is_read
                FROM received_emails
                ORDER BY received_at DESC, id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_received_email_by_id(email_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM received_emails WHERE id = ?", (email_id,)).fetchone()
        if row:
            conn.execute("UPDATE received_emails SET is_read = 1 WHERE id = ?", (email_id,))
            conn.commit()
            result = dict(row)
            result["is_read"] = 1
            return result
        return None

# --- Sent Emails (Max 50) ---

def save_sent_email(recipient: str, subject: str, body: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sent_emails (recipient, subject, body, sent_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (recipient, subject, body)
        )
        # Cap to MAX_SENT_EMAILS (50) by removing oldest
        conn.execute("""
            DELETE FROM sent_emails
            WHERE id NOT IN (
                SELECT id FROM sent_emails
                ORDER BY sent_at DESC, id DESC
                LIMIT ?
            )
        """, (MAX_SENT_EMAILS,))
        conn.commit()
        return cursor.lastrowid

def get_sent_emails(query: Optional[str] = None, limit: int = MAX_SENT_EMAILS) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        if query:
            q = f"%{query}%"
            rows = conn.execute("""
                SELECT * FROM sent_emails
                WHERE recipient LIKE ? OR subject LIKE ? OR body LIKE ?
                ORDER BY sent_at DESC, id DESC
                LIMIT ?
            """, (q, q, q, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM sent_emails
                ORDER BY sent_at DESC, id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_sent_email_by_id(email_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM sent_emails WHERE id = ?", (email_id,)).fetchone()
        return dict(row) if row else None

# --- Purge Messages Facility ---

def purge_messages(target: str) -> Dict[str, int]:
    """
    Purge messages from SQLite.
    target can be: 'sent', 'received', or 'all'
    """
    purged_sent = 0
    purged_received = 0
    with get_db_connection() as conn:
        if target in ("sent", "all"):
            cur = conn.execute("DELETE FROM sent_emails")
            purged_sent = cur.rowcount
        if target in ("received", "all"):
            cur = conn.execute("DELETE FROM received_emails")
            purged_received = cur.rowcount
        conn.commit()
        conn.execute("VACUUM")
    return {"purged_sent": purged_sent, "purged_received": purged_received}

def get_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        rc = conn.execute("SELECT COUNT(*) as c FROM received_emails").fetchone()["c"]
        sc = conn.execute("SELECT COUNT(*) as c FROM sent_emails").fetchone()["c"]
        last_sync = conn.execute("SELECT MAX(fetched_at) as m FROM received_emails").fetchone()["m"]
        return {
            "received_count": rc,
            "sent_count": sc,
            "last_sync": last_sync,
            "max_sent_limit": MAX_SENT_EMAILS,
            "max_inbox_limit": MAX_INBOX_EMAILS
        }
