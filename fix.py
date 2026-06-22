#!/usr/bin/env python3
"""
fix.py — локальный инструмент для обслуживания бота.
Запускать из корня проекта:

  python fix.py migrate          — создать таблицы в БД
  python fix.py load data/tasks.json   — загрузить новые задачи (пропускает дубли)
  python fix.py reload data/tasks.json — обновить существующие задачи (upsert)
  python fix.py stats            — статистика по задачам в БД
  python fix.py users            — статистика по подписчикам бота
  python fix.py reset <user_id>  — сбросить историю пользователя
  python fix.py setwebhook       — зарегистрировать webhook в Telegram
  python fix.py delwebhook       — удалить webhook
  python fix.py task <id>        — просмотр задачи по ID
  python fix.py find <text>      — поиск задач по тексту
  python fix.py generate_options           — сгенерировать варианты ответов для задач без wrong_options
  python fix.py generate_options quiz      — только для определённого типа
  python fix.py generate_options quiz 50   — тип + размер батча (по умолчанию 20)
"""

import sys
import json
import os
import requests
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
BOT_TOKEN    = os.environ["BOT_TOKEN"]
WEBHOOK_URL  = os.environ.get("WEBHOOK_URL", "")


def conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def cmd_migrate():
    from core.db import migrate
    migrate()


def cmd_load(path: str):
    with open(path, encoding="utf-8") as f:
        tasks = json.load(f)

    inserted = skipped = 0
    with conn() as c:
        for t in tasks:
            cur = c.execute("""
                INSERT INTO tasks (id, type, question, answer, hint, difficulty, tags, wrong_options)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                t.get("id"), t["type"], t["question"], t["answer"],
                t.get("hint"), t.get("difficulty", 1), t.get("tags", []),
                t.get("wrong_options", []),
            ))
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        c.commit()

    print(f"✅ Загружено: {inserted}  |  Пропущено (дубли): {skipped}")


def cmd_reload(path: str):
    with open(path, encoding="utf-8") as f:
        tasks = json.load(f)

    inserted = updated = 0
    with conn() as c:
        for t in tasks:
            cur = c.execute("""
                INSERT INTO tasks (id, type, question, answer, hint, difficulty, tags, wrong_options)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET type          = EXCLUDED.type,
                    question      = EXCLUDED.question,
                    answer        = EXCLUDED.answer,
                    hint          = EXCLUDED.hint,
                    difficulty    = EXCLUDED.difficulty,
                    tags          = EXCLUDED.tags,
                    wrong_options = EXCLUDED.wrong_options
            """, (
                t.get("id"), t["type"], t["question"], t["answer"],
                t.get("hint"), t.get("difficulty", 1), t.get("tags", []),
                t.get("wrong_options", []),
            ))
            if cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1
        c.commit()

    print(f"✅ Новых: {inserted}  |  Обновлено: {updated}")


def cmd_stats():
    with conn() as c:
        rows = c.execute("""
            SELECT type, difficulty, COUNT(*) as cnt
            FROM tasks GROUP BY type, difficulty
            ORDER BY type, difficulty
        """).fetchall()

    if not rows:
        print("База задач пуста.")
        return

    cur_type = None
    total = 0
    for r in rows:
        if r["type"] != cur_type:
            cur_type = r["type"]
            print(f"\n{cur_type}:")
        label = {1:"Легко",2:"Средне",3:"Сложно",4:"Эксперт"}.get(r["difficulty"], str(r["difficulty"]))
        print(f"  {label:10} {r['cnt']:>5}")
        total += r["cnt"]
    print(f"\nИтого: {total}")


def cmd_users():
    with conn() as c:
        total = c.execute("SELECT count(*) as cnt FROM users").fetchone()["cnt"]
        if total == 0:
            print("Подписчиков пока нет.")
            return

        new_today = c.execute(
            "SELECT count(*) as cnt FROM users WHERE first_seen >= CURRENT_DATE"
        ).fetchone()["cnt"]
        new_7d = c.execute(
            "SELECT count(*) as cnt FROM users WHERE first_seen >= NOW() - INTERVAL '7 days'"
        ).fetchone()["cnt"]
        active_today = c.execute(
            "SELECT count(*) as cnt FROM users WHERE last_seen >= CURRENT_DATE"
        ).fetchone()["cnt"]
        active_7d = c.execute(
            "SELECT count(*) as cnt FROM users WHERE last_seen >= NOW() - INTERVAL '7 days'"
        ).fetchone()["cnt"]
        last_5 = c.execute(
            "SELECT user_id, username, first_name, first_seen FROM users ORDER BY first_seen DESC LIMIT 5"
        ).fetchall()

    print(f"Всего подписчиков:      {total}")
    print(f"Новых сегодня:           {new_today}")
    print(f"Новых за 7 дней:         {new_7d}")
    print(f"Активных сегодня:        {active_today}")
    print(f"Активных за 7 дней:      {active_7d}")
    print("\nПоследние 5 подписавшихся:")
    for u in last_5:
        name = u["username"] or u["first_name"] or "—"
        print(f"  {u['user_id']:>12}  @{name}  {u['first_seen']}")


def cmd_reset(user_id: int):
    with conn() as c:
        cur = c.execute("DELETE FROM user_history WHERE user_id = %s", (user_id,))
        deleted = cur.rowcount
        c.commit()
    print(f"✅ Удалено {deleted} записей для user_id={user_id}")


def cmd_setwebhook():
    if not WEBHOOK_URL:
        print("❌ Задай WEBHOOK_URL в .env")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": WEBHOOK_URL}
    )
    print(r.json())


def cmd_delwebhook():
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    print(r.json())


def cmd_task(task_id: int):
    with conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row:
        for k, v in row.items():
            print(f"{k:12} {v}")
    else:
        print(f"Задача #{task_id} не найдена")


def cmd_find(text: str):
    with conn() as c:
        rows = c.execute("""
            SELECT id, type, difficulty, LEFT(question, 80) as q
            FROM tasks
            WHERE question ILIKE %s OR answer ILIKE %s
            LIMIT 20
        """, (f"%{text}%", f"%{text}%")).fetchall()
    if not rows:
        print("Ничего не найдено")
    for r in rows:
        diff = {1:"L",2:"M",3:"H",4:"X"}.get(r["difficulty"], "?")
        print(f"#{r['id']:>5} [{r['type']:6}] [{diff}] {r['q']}")


def _call_claude(api_key: str, prompt: str) -> str | None:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    API error {resp.status_code}: {resp.text[:200]}")
        return None
    return resp.json()["content"][0]["text"].strip()


def _generate_wrong_options(api_key: str, task: dict) -> list[str] | None:
    prompt = (
        f"Для задания из игры-тренажёра мозга придумай ровно 3 НЕПРАВИЛЬНЫХ варианта ответа.\n\n"
        f"Вопрос: {task['question']}\n"
        f"Правильный ответ: {task['answer']}\n\n"
        f"Требования:\n"
        f"- Варианты должны быть правдоподобными и похожими по стилю на правильный ответ\n"
        f"- Не должно быть очевидно, что они неправильные\n"
        f"- Каждый вариант — отдельная строка, без нумерации\n"
        f"- Ровно 3 строки, ничего лишнего"
    )
    text = _call_claude(api_key, prompt)
    if not text:
        return None
    options = [line.strip("•–— ").strip() for line in text.splitlines() if line.strip()][:3]
    return options if len(options) == 3 else None


def cmd_generate_options(task_type: str | None = None, batch: int = 20):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Задай ANTHROPIC_API_KEY в .env")
        return

    with conn() as c:
        query = """
            SELECT id, type, question, answer FROM tasks
            WHERE (wrong_options IS NULL OR array_length(wrong_options, 1) IS NULL)
              AND array_length(string_to_array(trim(answer), ' '), 1) >= 2
        """
        params: list = []
        if task_type:
            query += " AND type = %s"
            params.append(task_type)
        query += " ORDER BY id LIMIT %s"
        params.append(batch)
        rows = c.execute(query, params).fetchall()

    if not rows:
        print("✅ Все задачи с многословными ответами уже имеют варианты.")
        return

    print(f"Найдено {len(rows)} задач без вариантов. Генерирую...\n")
    updated = errors = 0

    for task in rows:
        options = _generate_wrong_options(api_key, task)
        if options:
            with conn() as c:
                c.execute(
                    "UPDATE tasks SET wrong_options = %s WHERE id = %s",
                    (options, task["id"])
                )
                c.commit()
            print(f"  #{task['id']:>5} ✓  {options}")
            updated += 1
        else:
            print(f"  #{task['id']:>5} ✗  не удалось сгенерировать")
            errors += 1

    print(f"\nГотово: обновлено {updated}, ошибок {errors}")


COMMANDS = {
    "migrate":    lambda _: cmd_migrate(),
    "load":       lambda args: cmd_load(args[0]) if args else print("Укажи путь к JSON"),
    "reload":     lambda args: cmd_reload(args[0]) if args else print("Укажи путь к JSON"),
    "stats":      lambda _: cmd_stats(),
    "users":      lambda _: cmd_users(),
    "reset":      lambda args: cmd_reset(int(args[0])) if args else print("Укажи user_id"),
    "setwebhook": lambda _: cmd_setwebhook(),
    "delwebhook": lambda _: cmd_delwebhook(),
    "task":       lambda args: cmd_task(int(args[0])) if args else print("Укажи ID"),
    "find":       lambda args: cmd_find(" ".join(args)) if args else print("Укажи текст"),
    "generate_options": lambda args: cmd_generate_options(
        task_type=args[0] if args else None,
        batch=int(args[1]) if len(args) > 1 else 20,
    ),
}

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(0)
    COMMANDS[argv[0]](argv[1:])
