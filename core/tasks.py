"""
core/tasks.py — выдача задач без повторов.
"""

import os
import random
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]


def _conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_next_task(user_id: int, task_type: str | None) -> dict | None:
    """
    Возвращает случайную задачу, которую пользователь ещё не видел.

    SELECT * FROM tasks
    WHERE (type = %s OR %s IS NULL)
    AND id NOT IN (
        SELECT task_id FROM user_history WHERE user_id = %s
    )
    ORDER BY RANDOM() LIMIT 1
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks
                WHERE (%s IS NULL OR type = %s)
                AND id NOT IN (
                    SELECT task_id FROM user_history
                    WHERE user_id = %s
                )
                ORDER BY RANDOM()
                LIMIT 1
            """, (task_type, task_type, user_id))
            row = cur.fetchone()
    return dict(row) if row else None


def get_task_by_id(task_id: int) -> dict | None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def mark_shown(user_id: int, task_id: int):
    from core.db import mark_shown as _mark
    _mark(user_id, task_id)


def mark_solved(user_id: int, task_id: int):
    from core.db import mark_solved as _mark
    _mark(user_id, task_id)


def add_favorite(user_id: int, task_id: int):
    from core.db import add_favorite as _fav
    _fav(user_id, task_id)
