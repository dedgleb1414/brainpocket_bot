"""
core/router.py — разбирает Update и вызывает нужный обработчик.
"""

from core.bot import answer_callback
from core.handlers import (
    handle_start, handle_menu, handle_next_task,
    handle_answer, handle_hint, handle_favorite,
    handle_progress, handle_daily_mode, handle_option_answer,
)

MENU_LABELS = {
    "🧩 Загадки", "🔍 Логика", "⚡ Мини-квиз", "🧠 IQ-задачи",
    "🎲 Случайное", "📈 Мой прогресс", "❤️ Избранное", "⏱ Режим дня",
}

def route_update(update: dict):
    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            handle_start(user_id)
        elif text in MENU_LABELS:
            handle_menu(user_id, text)
        else:
            handle_answer(user_id, text)

    elif "callback_query" in update:
        cb = update["callback_query"]
        user_id = cb["from"]["id"]
        data = cb.get("data", "")
        answer_callback(cb["id"])

        if data.startswith("next:"):
            handle_next_task(user_id, data.split(":")[1])
        elif data.startswith("hint:"):
            handle_hint(user_id, int(data.split(":")[1]))
        elif data.startswith("fav:"):
            handle_favorite(user_id, int(data.split(":")[1]))
        elif data == "progress":
            handle_progress(user_id)
        elif data.startswith("daily:"):
            handle_daily_mode(user_id, int(data.split(":")[1]))
        elif data.startswith("ans:"):
            # ans:task_id:task_type:chosen_answer
            parts = data.split(":", 3)
            task_id = int(parts[1])
            task_type = parts[2]
            chosen = parts[3]
            handle_option_answer(user_id, task_id, chosen, task_type)
