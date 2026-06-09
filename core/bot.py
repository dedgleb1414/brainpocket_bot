"""
core/bot.py — обёртка над Telegram Bot API.
"""

import os
import requests

TOKEN = os.environ["BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API}/sendMessage", json=payload, timeout=10)


def answer_callback(callback_query_id, text=""):
    requests.post(f"{API}/answerCallbackQuery",
                  json={"callback_query_id": callback_query_id, "text": text}, timeout=5)


def main_menu_keyboard():
    return {
        "keyboard": [
            ["🧩 Загадки", "🔍 Логика"],
            ["⚡ Мини-квиз", "🧠 IQ-задачи"],
            ["🎲 Случайное", "⏱ Режим дня"],
            ["📈 Мой прогресс", "❤️ Избранное"],
        ],
        "resize_keyboard": True,
    }


def task_inline_keyboard(task_id, task_type):
    """Кнопки для однословных задач."""
    return {
        "inline_keyboard": [
            [
                {"text": "💡 Подсказка",   "callback_data": f"hint:{task_id}"},
                {"text": "❤️ Избранное",   "callback_data": f"fav:{task_id}"},
            ],
            [
                {"text": "➡️ Следующая", "callback_data": f"next:{task_type}"},
            ],
        ]
    }


def options_inline_keyboard(task_id, task_type, options, correct_answer):
    """Кнопки с вариантами ответов для многословных задач."""
    rows = []
    for opt in options:
        # Обрезаем до 30 символов чтобы влезло в кнопку
        label = opt[:60] if len(opt) <= 60 else opt[:57] + "…"
        rows.append([{"text": label, "callback_data": f"ans:{task_id}:{task_type}:{opt[:50]}"}])
    rows.append([
        {"text": "💡 Подсказка", "callback_data": f"hint:{task_id}"},
        {"text": "❤️ Избранное", "callback_data": f"fav:{task_id}"},
    ])
    rows.append([{"text": "➡️ Пропустить", "callback_data": f"next:{task_type}"}])
    return {"inline_keyboard": rows}


def daily_mode_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "⚡ 5 минут",  "callback_data": "daily:5"},
            {"text": "🕐 10 минут", "callback_data": "daily:10"},
            {"text": "🕒 15 минут", "callback_data": "daily:15"},
        ]]
    }
