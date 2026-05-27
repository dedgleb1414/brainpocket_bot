"""
core/bot.py — тонкая обёртка над Telegram Bot API (чистый requests, без библиотек).
"""

import os
import requests

TOKEN = os.environ["BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"


# ── Отправка сообщения ────────────────────────────────────────────────────────

def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
    parse_mode: str = "HTML",
):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API}/sendMessage", json=payload, timeout=10)


def answer_callback(callback_query_id: str, text: str = ""):
    requests.post(
        f"{API}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id, "text": text},
        timeout=5,
    )


def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API}/editMessageText", json=payload, timeout=10)


# ── Готовые клавиатуры ────────────────────────────────────────────────────────

def main_menu_keyboard() -> dict:
    """Обычная ReplyKeyboard — главное меню бота."""
    return {
        "keyboard": [
            ["🧩 Загадки", "🔍 Логика"],
            ["⚡ Мини-квиз", "🧠 IQ-задачи"],
            ["🎲 Случайное", "⏱ Режим дня"],
            ["📈 Мой прогресс", "❤️ Избранное"],
        ],
        "resize_keyboard": True,
    }


def task_inline_keyboard(task_id: int, task_type: str) -> dict:
    """Кнопки под задачей."""
    return {
        "inline_keyboard": [
            [
                {"text": "💡 Подсказка",   "callback_data": f"hint:{task_id}"},
                {"text": "❤️ В избранное", "callback_data": f"fav:{task_id}"},
            ],
            [
                {"text": "➡️ Следующая", "callback_data": f"next:{task_type}"},
            ],
        ]
    }


def daily_mode_keyboard() -> dict:
    """Выбор времени для Режима дня."""
    return {
        "inline_keyboard": [
            [
                {"text": "⚡ 5 минут",  "callback_data": "daily:5"},
                {"text": "🕐 10 минут", "callback_data": "daily:10"},
                {"text": "🕒 15 минут", "callback_data": "daily:15"},
            ]
        ]
    }
