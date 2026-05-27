"""
core/db.py — работа с PostgreSQL (Supabase / Neon).
Подключение через DATABASE_URL из переменных окружения Vercel.
"""

import os
import psycopg2
import psycopg2.extras
from datetime import date, timedelta

DATABASE_URL = os.environ["DATABASE_URL"]


def _conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# ── Схема БД (выполни один раз через fix.py migrate) ─────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         SERIAL PRIMARY KEY,
    type       TEXT NOT NULL,          -- riddle | logic | quiz | iq
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    hint       TEXT,
    difficulty INTEGER DEFAULT 1,      -- 1=легко 2=средне 3=сложно 4=эксперт
    tags       TEXT[]
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

CREATE INDEX IF NOT EXISTS idx_history_user ON user_history(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_type   ON tasks(type);
"""


def migrate():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    print("✅ Миграция выполнена")


# ── История / показы ──────────────────────────────────────────────────────────

def mark_shown(user_id: int, task_id: int):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_history (user_id, task_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, task_id) DO NOTHING
            """, (user_id, task_id))
        conn.commit()


def mark_solved(user_id: int, task_id: int):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE user_history
                SET solved = TRUE, solved_at = NOW()
                WHERE user_id = %s AND task_id = %s
            """, (user_id, task_id))
        conn.commit()


def get_last_shown_task(user_id: int) -> int | None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT task_id FROM user_history
                WHERE user_id = %s
                ORDER BY shown_at DESC LIMIT 1
            """, (user_id,))
            row = cur.fetchone()
    return row["task_id"] if row else None


def reset_history(user_id: int, task_type: str | None):
    """Сброс цикла: удаляем историю показов для данного типа (не решённые)."""
    with _conn() as conn:
        with conn.cursor() as cur:
            if task_type:
                cur.execute("""
                    DELETE FROM user_history
                    WHERE user_id = %s AND task_id IN (
                        SELECT id FROM tasks WHERE type = %s
                    ) AND solved = FALSE
                """, (user_id, task_type))
            else:
                cur.execute("""
                    DELETE FROM user_history WHERE user_id = %s AND solved = FALSE
                """, (user_id,))
        conn.commit()


# ── Избранное ─────────────────────────────────────────────────────────────────

def add_favorite(user_id: int, task_id: int):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_history (user_id, task_id, favorited)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (user_id, task_id)
                DO UPDATE SET favorited = TRUE
            """, (user_id, task_id))
        conn.commit()


def get_favorites(user_id: int) -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id, t.question, t.type
                FROM user_history uh
                JOIN tasks t ON t.id = uh.task_id
                WHERE uh.user_id = %s AND uh.favorited = TRUE
                ORDER BY uh.shown_at DESC
            """, (user_id,))
            return cur.fetchall()


# ── Прогресс и серии ──────────────────────────────────────────────────────────

def get_user_progress(user_id: int) -> dict:
    """Возвращает {type: solved_count}."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.type, COUNT(*) AS cnt
                FROM user_history uh
                JOIN tasks t ON t.id = uh.task_id
                WHERE uh.user_id = %s AND uh.solved = TRUE
                GROUP BY t.type
            """, (user_id,))
            rows = cur.fetchall()
    return {r["type"]: r["cnt"] for r in rows}


def get_streak(user_id: int) -> int:
    """Считает серию активных дней подряд."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT DATE(shown_at) AS day
                FROM user_history
                WHERE user_id = %s
                ORDER BY day DESC
            """, (user_id,))
            days = [r["day"] for r in cur.fetchall()]

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
