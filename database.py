"""SQLite persistence layer for reminders and timers."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "lotto8888xbot.db")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                text       TEXT    NOT NULL,
                run_at     TEXT    NOT NULL,
                repeat     TEXT    NOT NULL DEFAULT 'once',
                job_name   TEXT,
                created_at TEXT    NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                label      TEXT    NOT NULL,
                duration_s INTEGER NOT NULL,
                end_at     TEXT    NOT NULL,
                job_name   TEXT,
                created_at TEXT    NOT NULL
            )
        """)


# ------------------ Reminders ------------------
def add_reminder(chat_id, user_id, text, run_at_iso, repeat="once", job_name=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO reminders (chat_id,user_id,text,run_at,repeat,job_name,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (chat_id, user_id, text, run_at_iso, repeat, job_name,
             datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def update_reminder_job(reminder_id, job_name):
    with _conn() as c:
        c.execute("UPDATE reminders SET job_name=? WHERE id=?", (job_name, reminder_id))


def delete_reminder(reminder_id, user_id):
    with _conn() as c:
        cur = c.execute("DELETE FROM reminders WHERE id=? AND user_id=?",
                        (reminder_id, user_id))
        return cur.rowcount


def get_reminder(reminder_id):
    with _conn() as c:
        return c.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone()


def list_reminders(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM reminders WHERE user_id=? ORDER BY run_at ASC", (user_id,)
        ).fetchall()


def all_reminders():
    with _conn() as c:
        return c.execute("SELECT * FROM reminders").fetchall()


# ------------------ Timers ------------------
def add_timer(chat_id, user_id, label, duration_s, end_at_iso, job_name=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO timers (chat_id,user_id,label,duration_s,end_at,job_name,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (chat_id, user_id, label, duration_s, end_at_iso, job_name,
             datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def update_timer_job(timer_id, job_name):
    with _conn() as c:
        c.execute("UPDATE timers SET job_name=? WHERE id=?", (job_name, timer_id))


def delete_timer(timer_id, user_id):
    with _conn() as c:
        cur = c.execute("DELETE FROM timers WHERE id=? AND user_id=?",
                        (timer_id, user_id))
        return cur.rowcount


def get_timer(timer_id):
    with _conn() as c:
        return c.execute("SELECT * FROM timers WHERE id=?", (timer_id,)).fetchone()


def list_timers(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM timers WHERE user_id=? ORDER BY end_at ASC", (user_id,)
        ).fetchall()


def all_timers():
    with _conn() as c:
        return c.execute("SELECT * FROM timers").fetchall()
