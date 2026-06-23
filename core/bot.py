"""
core/bot.py — обёртка над Telegram Bot API.
"""

import os
import urllib.parse
import requests

TOKEN = os.environ["BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
BOT_USERNAME = "brainpocket_bot"


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
            ["🎬 Кинематограф", "🎲 Случайное"],
            ["📈 Мой прогресс", "❤️ Избранное"],
            ["🤝 Пригласить друга"],
        ],
        "resize_keyboard": True,
    }


def cinema_menu_keyboard():
    return {
        "keyboard": [
            ["💍 Властелин Колец", "🪄 Гарри Поттер"],
            ["🦸 Marvel", "🔬 Теория Большого взрыва"],
            ["⬅️ Назад"],
        ],
        "resize_keyboard": True,
    }


def task_inline_keyboard(task_id, task_type):
    return {
        "inline_keyboard": [
            [
                {"text": "💡 Подсказка", "callback_data": f"hint:{task_id}"},
                {"text": "❤️ Избранное", "callback_data": f"fav:{task_id}"},
            ],
            [{"text": "➡️ Следующая", "callback_data": f"next:{task_type}"}],
        ]
    }


def options_inline_keyboard(task_id, task_type, options, correct_answer):
    """
    Варианты ответов. callback_data = ans:task_id:index
    где index — позиция правильного ответа в списке options.
    Сам текст вариантов хранится только в кнопке, не в callback_data.
    """
    correct_idx = options.index(correct_answer)
    rows = []
    for i, opt in enumerate(options):
        label = opt if len(opt) <= 60 else opt[:57] + "…"
        rows.append([{"text": label, "callback_data": f"ans:{task_id}:{correct_idx}:{i}"}])
    rows.append([
        {"text": "💡 Подсказка", "callback_data": f"hint:{task_id}"},
        {"text": "❤️ Избранное", "callback_data": f"fav:{task_id}"},
    ])
    rows.append([{"text": "➡️ Пропустить", "callback_data": f"next:{task_type}"}])
    return {"inline_keyboard": rows}


def quiz_options_keyboard(task_id, options, correct_answer):
    """Варианты ответов для мини-квиза (qans: вместо ans:)."""
    correct_idx = options.index(correct_answer)
    rows = []
    for i, opt in enumerate(options):
        label = opt if len(opt) <= 60 else opt[:57] + "…"
        rows.append([{"text": label, "callback_data": f"qans:{task_id}:{correct_idx}:{i}"}])
    return {"inline_keyboard": rows}


def next_task_keyboard(task_type):
    return {
        "inline_keyboard": [[
            {"text": "➡️ Ещё задачу", "callback_data": f"next:{task_type}"}
        ]]
    }


def invite_keyboard():
    share_text = "Зацени BrainPocket — бот с загадками, квизами и IQ-задачками! 🧠"
    bot_link = f"https://t.me/{BOT_USERNAME}"
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(bot_link)}&text={urllib.parse.quote(share_text)}"
    return {
        "inline_keyboard": [[
            {"text": "📤 Поделиться с другом", "url": share_url}
        ]]
    }
