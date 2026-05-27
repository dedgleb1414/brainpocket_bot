"""
core/router.py — разбирает Update и вызывает нужный обработчик.
"""

from core.bot import send_message, answer_callback
from core.handlers import (
    handle_start,
    handle_menu,
    handle_next_task,
    handle_answer,
    handle_hint,
    handle_favorite,
    handle_progress,
    handle_daily_mode,
)


def route_update(update: dict):
    # ── Обычное сообщение ──────────────────────────────────────────────────
    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            handle_start(user_id)
        elif text in MENU_LABELS:
            handle_menu(user_id, text)
        else:
            # Свободный ввод — пробуем как ответ на задачу
            handle_answer(user_id, text)

    # ── Нажатие inline-кнопки ─────────────────────────────────────────────
    elif "callback_query" in update:
        cb = update["callback_query"]
        user_id = cb["from"]["id"]
        data = cb.get("data", "")
        cb_id = cb["id"]

        answer_callback(cb_id)  # убираем «часики» у кнопки

        if data.startswith("next:"):
            task_type = data.split(":")[1]
            handle_next_task(user_id, task_type)
        elif data.startswith("hint:"):
            task_id = int(data.split(":")[1])
            handle_hint(user_id, task_id)
        elif data.startswith("fav:"):
            task_id = int(data.split(":")[1])
            handle_favorite(user_id, task_id)
        elif data == "progress":
            handle_progress(user_id)
        elif data.startswith("daily:"):
            minutes = int(data.split(":")[1])
            handle_daily_mode(user_id, minutes)


# Метки главного меню (совпадают с кнопками)
MENU_LABELS = {
    "🧩 Загадки",
    "🔍 Логика",
    "⚡ Мини-квиз",
    "🧠 IQ-задачи",
    "🎲 Случайное",
    "📈 Мой прогресс",
    "❤️ Избранное",
    "⏱ Режим дня",
}
