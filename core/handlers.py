"""
core/handlers.py — вся бизнес-логика бота.
"""

from core.bot import send_message, main_menu_keyboard, task_inline_keyboard, daily_mode_keyboard
from core.tasks import get_next_task, get_task_by_id, mark_shown, mark_solved, add_favorite
from core.db import get_user_progress, get_streak, get_favorites


# ── /start ────────────────────────────────────────────────────────────────────

def handle_start(user_id: int):
    text = (
        "👋 Привет! Я <b>BrainPocket</b> — тренажёр для мозга.\n\n"
        "Выбери раздел и начни прокачиваться:\n"
        "🧩 Загадки · 🔍 Логика · ⚡ Квиз · 🧠 IQ\n\n"
        "Задачи не повторяются, пока не пройдёшь все 🔥"
    )
    send_message(user_id, text, reply_markup=main_menu_keyboard())


# ── Главное меню ──────────────────────────────────────────────────────────────

MENU_TO_TYPE = {
    "🧩 Загадки":    "riddle",
    "🔍 Логика":     "logic",
    "⚡ Мини-квиз":  "quiz",
    "🧠 IQ-задачи":  "iq",
    "🎲 Случайное":  None,  # случайный тип
}

def handle_menu(user_id: int, label: str):
    if label == "📈 Мой прогресс":
        handle_progress(user_id)
        return
    if label == "❤️ Избранное":
        handle_favorites_list(user_id)
        return
    if label == "⏱ Режим дня":
        send_message(user_id, "Выбери сколько времени у тебя есть:", reply_markup=daily_mode_keyboard())
        return

    task_type = MENU_TO_TYPE.get(label)
    handle_next_task(user_id, task_type)


# ── Выдача задачи ─────────────────────────────────────────────────────────────

def handle_next_task(user_id: int, task_type: str | None):
    task = get_next_task(user_id, task_type)

    if task is None:
        # Все задачи этого типа пройдены — сброс цикла
        from core.db import reset_history
        reset_history(user_id, task_type)
        task = get_next_task(user_id, task_type)
        if task:
            send_message(user_id, "🎉 Ты прошёл все задачи! Начинаем новый круг.")

    if task is None:
        send_message(user_id, "Задачи не найдены. Попробуй другой раздел.")
        return

    mark_shown(user_id, task["id"])

    TYPE_EMOJI = {"riddle": "🧩", "logic": "🔍", "quiz": "⚡", "iq": "🧠"}
    DIFF_LABEL = {1: "Легко", 2: "Средне", 3: "Сложно", 4: "Эксперт"}

    emoji = TYPE_EMOJI.get(task["type"], "🎲")
    diff  = DIFF_LABEL.get(task["difficulty"], "")

    text = (
        f"{emoji} <b>Задача #{task['id']}</b>  <i>{diff}</i>\n\n"
        f"{task['question']}"
    )
    send_message(user_id, text, reply_markup=task_inline_keyboard(task["id"], task["type"]))


# ── Ответ пользователя ────────────────────────────────────────────────────────

def handle_answer(user_id: int, text: str):
    """
    Простая проверка: сохраняем последнюю показанную задачу в user_history
    и сравниваем ответ (нечёткое совпадение).
    """
    from core.db import get_last_shown_task
    task_id = get_last_shown_task(user_id)
    if not task_id:
        return

    task = get_task_by_id(task_id)
    if not task:
        return

    correct = task["answer"].strip().lower()
    given   = text.strip().lower()

    if correct in given or given in correct:
        mark_solved(user_id, task_id)
        send_message(user_id, f"✅ Верно!\n\n<b>Ответ:</b> {task['answer']}")
    else:
        send_message(user_id, f"❌ Не совсем. Попробуй ещё или жми 💡 Подсказку.")


# ── Подсказка ─────────────────────────────────────────────────────────────────

def handle_hint(user_id: int, task_id: int):
    task = get_task_by_id(task_id)
    hint = task.get("hint") if task else None
    if hint:
        send_message(user_id, f"💡 <i>{hint}</i>")
    else:
        send_message(user_id, "💡 Подсказки к этой задаче нет. Думай!")


# ── Избранное ─────────────────────────────────────────────────────────────────

def handle_favorite(user_id: int, task_id: int):
    add_favorite(user_id, task_id)
    send_message(user_id, "❤️ Добавлено в избранное!")


def handle_favorites_list(user_id: int):
    favs = get_favorites(user_id)
    if not favs:
        send_message(user_id, "❤️ Избранное пустое. Сохраняй понравившиеся задачи!")
        return

    lines = [f"❤️ <b>Избранное ({len(favs)} задач)</b>\n"]
    for t in favs[:10]:  # показываем первые 10
        lines.append(f"#{t['id']} — {t['question'][:60]}…")
    send_message(user_id, "\n".join(lines))


# ── Прогресс ──────────────────────────────────────────────────────────────────

def handle_progress(user_id: int):
    p = get_user_progress(user_id)
    streak = get_streak(user_id)

    text = (
        f"📈 <b>Мой прогресс</b>\n\n"
        f"🧩 Загадки:   {p.get('riddle',0)}/1000\n"
        f"🔍 Логика:    {p.get('logic',0)}/500\n"
        f"⚡ Квиз:      {p.get('quiz',0)}/1000\n"
        f"🧠 IQ:        {p.get('iq',0)}/700\n\n"
        f"Всего решено: <b>{sum(p.values())}</b>\n"
        f"Серия: <b>{streak} дн.</b> 🔥"
    )
    send_message(user_id, text)


# ── Режим дня ─────────────────────────────────────────────────────────────────

DAILY_PACKS = {
    5:  [("riddle", 1), ("logic", 1)],
    10: [("riddle", 1), ("logic", 1), ("quiz", 1)],
    15: [("riddle", 1), ("logic", 1), ("quiz", 1), ("iq", 1)],
}

def handle_daily_mode(user_id: int, minutes: int):
    pack = DAILY_PACKS.get(minutes, DAILY_PACKS[10])
    send_message(user_id, f"⏱ Режим дня — <b>{minutes} минут</b>. Поехали!\n")
    for task_type, _ in pack:
        handle_next_task(user_id, task_type)
