"""
core/db.py — работа с PostgreSQL через psycopg3 (psycopg[binary]).
Совместимо с Python 3.12+.
"""

import os
import psycopg
from psycopg.rows import dict_row
from datetime import date, timedelta

DATABASE_URL = os.environ["DATABASE_URL"]


def _conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    BIGINT PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id         SERIAL PRIMARY KEY,
    type       TEXT NOT NULL,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    hint       TEXT,
    difficulty INTEGER DEFAULT 1,
    tags       TEXT[],
    wrong_options TEXT[]
);

CREATE TABLE IF NOT EXISTS user_history (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    task_id    INTEGER REFERENCES tasks(id),
    solved     BOOLEAN DEFAULT FALSE,
    favorited  BOOLEAN DEFAULT FALSE,
    shown_at   TIMESTAMP DEFAULT NOW(),
    solved_at  TIMESTAMP,
    UNIQUE (user_id, task_id)
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    user_id           BIGINT PRIMARY KEY,
    task_ids          INTEGER[] NOT NULL,
    current_idx       INTEGER DEFAULT 0,
    question_shown_at TIMESTAMPTZ DEFAULT NOW(),
    failed            BOOLEAN DEFAULT FALSE,
    completed         BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_history_user ON user_history(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_type   ON tasks(type);
"""


def migrate():
    with _conn() as conn:
        conn.execute(SCHEMA)
        conn.commit()
    print("✅ Миграция выполнена")


def upsert_user(user_id: int, username: str | None, first_name: str | None):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, first_seen, last_seen)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_seen = NOW()
        """, (user_id, username, first_name))
        conn.commit()


def mark_shown(user_id: int, task_id: int):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO user_history (user_id, task_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, task_id) DO NOTHING
        """, (user_id, task_id))
        conn.commit()


def mark_solved(user_id: int, task_id: int):
    with _conn() as conn:
        conn.execute("""
            UPDATE user_history
            SET solved = TRUE, solved_at = NOW()
            WHERE user_id = %s AND task_id = %s
        """, (user_id, task_id))
        conn.commit()


def get_last_shown_task(user_id: int) -> int | None:
    with _conn() as conn:
        row = conn.execute("""
            SELECT task_id FROM user_history
            WHERE user_id = %s
            ORDER BY shown_at DESC LIMIT 1
        """, (user_id,)).fetchone()
    return row["task_id"] if row else None


def reset_history(user_id: int, task_type: str | None):
    with _conn() as conn:
        if task_type:
            conn.execute("""
                DELETE FROM user_history
                WHERE user_id = %s AND task_id IN (
                    SELECT id FROM tasks WHERE type = %s
                ) AND solved = FALSE
            """, (user_id, task_type))
        else:
            conn.execute("""
                DELETE FROM user_history WHERE user_id = %s AND solved = FALSE
            """, (user_id,))
        conn.commit()


def add_favorite(user_id: int, task_id: int):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO user_history (user_id, task_id, favorited)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (user_id, task_id)
            DO UPDATE SET favorited = TRUE
        """, (user_id, task_id))
        conn.commit()


def get_favorites(user_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT t.id, t.question, t.type
            FROM user_history uh
            JOIN tasks t ON t.id = uh.task_id
            WHERE uh.user_id = %s AND uh.favorited = TRUE
            ORDER BY uh.shown_at DESC
        """, (user_id,)).fetchall()
    return rows


def get_task_counts() -> dict:
    with _conn() as conn:
        rows = conn.execute("SELECT type, COUNT(*) AS cnt FROM tasks GROUP BY type").fetchall()
    return {r["type"]: r["cnt"] for r in rows}


def get_user_progress(user_id: int) -> dict:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT t.type, COUNT(*) AS cnt
            FROM user_history uh
            JOIN tasks t ON t.id = uh.task_id
            WHERE uh.user_id = %s AND uh.solved = TRUE
            GROUP BY t.type
        """, (user_id,)).fetchall()
    return {r["type"]: r["cnt"] for r in rows}


def get_streak(user_id: int) -> int:
    with _conn() as conn:
        days = [r["day"] for r in conn.execute("""
            SELECT DISTINCT DATE(shown_at) AS day
            FROM user_history
            WHERE user_id = %s
            ORDER BY day DESC
        """, (user_id,)).fetchall()]

    if not days:
        return 0

    streak = 0
    check = date.today()
    for d in days:
        if d == check or d == check - timedelta(days=1):
            streak += 1
            check = d
        else:
            break
    return streak


def get_wrong_options_from_db(exclude_id: int, task_type: str, count: int = 3) -> list[str]:
    """Случайные ответы других задач того же типа."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT answer FROM tasks
            WHERE type = %s AND id != %s
            ORDER BY RANDOM()
            LIMIT %s
        """, (task_type, exclude_id, count)).fetchall()
    return [r["answer"] for r in rows]


# ── Мини-квиз ────────────────────────────────────────────────────────────────

def get_quiz_tasks(user_id: int, count: int = 3) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE type = 'quiz'
            AND id NOT IN (
                SELECT task_id FROM user_history WHERE user_id = %s
            )
            ORDER BY RANDOM()
            LIMIT %s
        """, (user_id, count)).fetchall()
    return [dict(r) for r in rows]


def create_quiz_session(user_id: int, task_ids: list):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO quiz_sessions
                (user_id, task_ids, current_idx, question_shown_at, failed, completed)
            VALUES (%s, %s, 0, NOW(), FALSE, FALSE)
            ON CONFLICT (user_id) DO UPDATE
            SET task_ids          = EXCLUDED.task_ids,
                current_idx       = 0,
                question_shown_at = NOW(),
                failed            = FALSE,
                completed         = FALSE
        """, (user_id, task_ids))
        conn.commit()


def get_quiz_session(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM quiz_sessions WHERE user_id = %s", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def advance_quiz_session(user_id: int):
    with _conn() as conn:
        conn.execute("""
            UPDATE quiz_sessions
            SET current_idx = current_idx + 1, question_shown_at = NOW()
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()


def fail_quiz_session(user_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE quiz_sessions SET failed = TRUE WHERE user_id = %s", (user_id,)
        )
        conn.commit()


def complete_quiz_session(user_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE quiz_sessions SET completed = TRUE WHERE user_id = %s", (user_id,)
        )
        conn.commit()
