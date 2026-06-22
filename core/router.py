"""
core/router.py — разбирает Update и вызывает нужный обработчик.
"""

from core.bot import answer_callback
from core.db import upsert_user
from core.handlers import (
    handle_start, handle_menu, handle_next_task,
    handle_answer, handle_hint, handle_favorite,
    handle_progress, handle_option_answer,
    handle_quiz_answer,
)

MENU_LABELS = {
    "🧩 Загадки", "🔍 Логика", "⚡ Мини-квиз", "🧠 IQ-задачи",
    "💍 Властелин Колец", "🪄 Гарри Поттер",
    "🦸 Marvel", "🔬 Теория Большого взрыва",
    "🎲 Случайное", "📈 Мой прогресс", "❤️ Избранное", "🤝 Пригласить друга",
}

def route_update(update: dict):
    if "message" in update:
        msg = update["message"]
        from_user = msg["from"]
        user_id = from_user["id"]
        text = msg.get("text", "")

        upsert_user(user_id, from_user.get("username"), from_user.get("first_name"))

        if text == "/start":
            handle_start(user_id)
        elif text in MENU_LABELS:
            handle_menu(user_id, text)
        else:
            handle_answer(user_id, text)

    elif "callback_query" in update:
        cb = update["callback_query"]
        from_user = cb["from"]
        user_id = from_user["id"]
        data = cb.get("data", "")
        answer_callback(cb["id"])

        upsert_user(user_id, from_user.get("username"), from_user.get("first_name"))

        if data.startswith("next:"):
            handle_next_task(user_id, data.split(":")[1])
        elif data.startswith("hint:"):
            parts = data.split(":")
            task_id = int(parts[1])
            level = int(parts[2]) if len(parts) > 2 else 0
            handle_hint(user_id, task_id, level)
        elif data.startswith("fav:"):
            handle_favorite(user_id, int(data.split(":")[1]))
        elif data == "progress":
            handle_progress(user_id)
        elif data.startswith("ans:"):
            parts = data.split(":")
            task_id = int(parts[1])
            correct_idx = int(parts[2])
            chosen_idx = int(parts[3])
            handle_option_answer(user_id, task_id, correct_idx, chosen_idx)
        elif data.startswith("qans:"):
            parts = data.split(":")
            task_id = int(parts[1])
            correct_idx = int(parts[2])
            chosen_idx = int(parts[3])
            handle_quiz_answer(user_id, task_id, correct_idx, chosen_idx)
