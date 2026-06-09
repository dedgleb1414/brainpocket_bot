"""
core/tasks.py — выдача задач без повторов (psycopg3).
"""

import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]


def _conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def get_next_task(user_id, task_type):
    with _conn() as conn:
        if task_type:
            row = conn.execute("""
                SELECT * FROM tasks
                WHERE type = %s
                AND id NOT IN (
                    SELECT task_id FROM user_history WHERE user_id = %s
                )
                ORDER BY RANDOM() LIMIT 1
            """, (task_type, user_id)).fetchone()
        else:
            row = conn.execute("""
                SELECT * FROM tasks
                WHERE id NOT IN (
                    SELECT task_id FROM user_history WHERE user_id = %s
                )
                ORDER BY RANDOM() LIMIT 1
            """, (user_id,)).fetchone()
    return dict(row) if row else None


def get_task_by_id(task_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()
    return dict(row) if row else None


def get_random_answers(exclude_id, task_type, count=3):
    """Возвращает случайные ответы других задач того же типа — для вариантов."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT answer FROM tasks
            WHERE type = %s AND id != %s
            ORDER BY RANDOM()
            LIMIT %s
        """, (task_type, exclude_id, count)).fetchall()
    return [r["answer"] for r in rows]


def mark_shown(user_id, task_id):
    from core.db import mark_shown as _mark
    _mark(user_id, task_id)


def mark_solved(user_id, task_id):
    from core.db import mark_solved as _mark
    _mark(user_id, task_id)


def add_favorite(user_id, task_id):
    from core.db import add_favorite as _fav
    _fav(user_id, task_id)
