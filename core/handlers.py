"""
core/handlers.py — вся бизнес-логика бота.
"""

import random
from core.bot import (send_message, main_menu_keyboard, task_inline_keyboard,
                      daily_mode_keyboard, options_inline_keyboard, quiz_options_keyboard,
                      next_task_keyboard)
from core.tasks import get_next_task, get_task_by_id, mark_shown, mark_solved, add_favorite
from core.db import (get_user_progress, get_streak, get_favorites, get_wrong_options_from_db,
                     get_quiz_tasks, create_quiz_session, get_quiz_session,
                     advance_quiz_session, fail_quiz_session, complete_quiz_session,
                     reset_history)


def handle_start(user_id: int):
    text = (
        "👋 Привет! Я <b>BrainPocket</b> — тренажёр для мозга.\n\n"
        "Выбери раздел и начни прокачиваться:\n"
        "🧩 Загадки · 🔍 Логика · ⚡ Квиз · 🧠 IQ · 💍 ВК · 🪄 Гарри Поттер\n\n"
        "Задачи не повторяются, пока не пройдёшь все 🔥"
    )
    send_message(user_id, text, reply_markup=main_menu_keyboard())


MENU_TO_TYPE = {
    "🧩 Загадки":          "riddle",
    "🔍 Логика":           "logic",
    "⚡ Мини-квиз":        "quiz",
    "🧠 IQ-задачи":        "iq",
    "💍 Властелин Колец":  "lotr",
    "🪄 Гарри Поттер":     "hp",
    "🎲 Случайное":        None,
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
    if label == "⚡ Мини-квиз":
        handle_mini_quiz(user_id)
        return
    task_type = MENU_TO_TYPE.get(label)
    handle_next_task(user_id, task_type)


def is_multiword(answer: str) -> bool:
    return len(answer.strip().split()) >= 2


def build_options(task: dict) -> list[str]:
    """
    Собирает 4 варианта ответа.
    Приоритет: wrong_options из задачи → случайные из БД.
    """
    wrong = task.get("wrong_options") or []

    # Если в задаче не хватает вариантов — добьём из БД
    if len(wrong) < 3:
        extra = get_wrong_options_from_db(task["id"], task["type"], count=3 - len(wrong))
        wrong = wrong + extra

    options = [task["answer"]] + wrong[:3]
    random.shuffle(options)
    return options


def handle_next_task(user_id: int, task_type):
    task = get_next_task(user_id, task_type)

    if task is None:
        reset_history(user_id, task_type)
        task = get_next_task(user_id, task_type)
        if task:
            send_message(user_id, "🎉 Ты прошёл все задачи! Начинаем новый круг.")

    if task is None:
        send_message(user_id, "Задачи не найдены. Попробуй другой раздел.")
        return

    mark_shown(user_id, task["id"])

    TYPE_EMOJI = {"riddle": "🧩", "logic": "🔍", "quiz": "⚡", "iq": "🧠", "lotr": "💍", "hp": "🪄"}
    DIFF_LABEL = {1: "Легко", 2: "Средне", 3: "Сложно", 4: "Эксперт"}
    emoji = TYPE_EMOJI.get(task["type"], "🎲")
    diff  = DIFF_LABEL.get(task["difficulty"], "")

    text = (
        f"{emoji} <b>Задача #{task['id']}</b>  <i>{diff}</i>\n\n"
        f"{task['question']}"
    )

    if is_multiword(task["answer"]):
        options = build_options(task)
        keyboard = options_inline_keyboard(task["id"], task["type"], options, task["answer"])
        send_message(user_id, text, reply_markup=keyboard)
    else:
        send_message(user_id, text + "\n\n✏️ <i>Напиши ответ</i>",
                     reply_markup=task_inline_keyboard(task["id"], task["type"]))


def handle_answer(user_id: int, text: str):
    from core.db import get_last_shown_task
    task_id = get_last_shown_task(user_id)
    if not task_id:
        return

    task = get_task_by_id(task_id)
    if not task:
        return

    if is_multiword(task["answer"]):
        return

    correct = task["answer"].strip().lower()
    given   = text.strip().lower()

    if correct in given or given in correct:
        mark_solved(user_id, task_id)
        send_message(user_id, f"✅ Верно!\n\n<b>Ответ:</b> {task['answer']}",
                     reply_markup=next_task_keyboard(task["type"]))
    else:
        send_message(user_id, f"❌ Не совсем. Попробуй ещё или жми 💡 Подсказку.")


def handle_option_answer(user_id: int, task_id: int, correct_idx: int, chosen_idx: int):
    task = get_task_by_id(task_id)
    if not task:
        return

    if chosen_idx == correct_idx:
        mark_solved(user_id, task_id)
        send_message(user_id, f"✅ Верно!\n\n<b>Ответ:</b> {task['answer']}",
                     reply_markup=next_task_keyboard(task["type"]))
    else:
        send_message(user_id, "❌ Неверно. Попробуй ещё или жми 💡 Подсказку.")


def handle_hint(user_id: int, task_id: int, level: int = 0):
    task = get_task_by_id(task_id)
    if not task:
        return

    if level == 0:
        hint = task.get("hint")
        stronger_btn = {"inline_keyboard": [[
            {"text": "💡 Показать ответ", "callback_data": f"hint:{task_id}:1"}
        ]]}
        if hint:
            send_message(user_id, f"💡 <i>{hint}</i>", reply_markup=stronger_btn)
        else:
            send_message(user_id, "💡 Подсказки нет.", reply_markup=stronger_btn)
    else:
        send_message(user_id, f"💡 <b>Ответ:</b> {task['answer']}")


def handle_favorite(user_id: int, task_id: int):
    add_favorite(user_id, task_id)
    send_message(user_id, "❤️ Добавлено в избранное!")


def handle_favorites_list(user_id: int):
    favs = get_favorites(user_id)
    if not favs:
        send_message(user_id, "❤️ Избранное пустое. Сохраняй понравившиеся задачи!")
        return
    lines = [f"❤️ <b>Избранное ({len(favs)} задач)</b>\n"]
    for t in favs[:10]:
        lines.append(f"#{t['id']} — {t['question'][:60]}…")
    send_message(user_id, "\n".join(lines))


def handle_progress(user_id: int):
    p = get_user_progress(user_id)
    streak = get_streak(user_id)
    text = (
        f"📈 <b>Мой прогресс</b>\n\n"
        f"🧩 Загадки:          {p.get('riddle',0)}/1000\n"
        f"🔍 Логика:           {p.get('logic',0)}/500\n"
        f"⚡ Квиз:             {p.get('quiz',0)}/1000\n"
        f"🧠 IQ:               {p.get('iq',0)}/700\n"
        f"💍 Властелин Колец:  {p.get('lotr',0)}/20\n"
        f"🪄 Гарри Поттер:     {p.get('hp',0)}/20\n\n"
        f"Всего решено: <b>{sum(p.values())}</b>\n"
        f"Серия: <b>{streak} дн.</b> 🔥"
    )
    send_message(user_id, text)


# ── Мини-квиз ────────────────────────────────────────────────────────────────

def handle_mini_quiz(user_id: int):
    tasks = get_quiz_tasks(user_id, 3)
    if len(tasks) < 3:
        reset_history(user_id, "quiz")
        tasks = get_quiz_tasks(user_id, 3)
    if len(tasks) < 3:
        send_message(user_id, "⚡ Недостаточно вопросов для квиза. Попробуй позже.")
        return

    task_ids = [t["id"] for t in tasks]
    create_quiz_session(user_id, task_ids)
    for tid in task_ids:
        mark_shown(user_id, tid)

    send_message(
        user_id,
        "⚡ <b>Мини-квиз!</b>\n\n"
        "3 вопроса подряд, на каждый — 20 секунд.\n"
        "Ошибёшься или не успеешь — квиз завершается. Поехали!"
    )
    _show_quiz_question(user_id, tasks[0], 1)


def _show_quiz_question(user_id: int, task: dict, question_num: int):
    options = build_options(task)
    text = (
        f"⚡ <b>Вопрос {question_num}/3</b>  ⏱ <i>20 секунд</i>\n\n"
        f"{task['question']}"
    )
    send_message(user_id, text, reply_markup=quiz_options_keyboard(task["id"], options, task["answer"]))


def handle_quiz_answer(user_id: int, task_id: int, correct_idx: int, chosen_idx: int):
    from datetime import datetime, timezone

    session = get_quiz_session(user_id)
    if not session or session["failed"] or session["completed"]:
        return

    shown_at = session["question_shown_at"]
    if shown_at.tzinfo is None:
        shown_at = shown_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - shown_at).total_seconds()

    task = get_task_by_id(task_id)
    answer_text = task["answer"] if task else "?"

    if elapsed > 20:
        fail_quiz_session(user_id)
        send_message(user_id,
            f"⏰ Время вышло!\n\n<b>Правильный ответ:</b> {answer_text}\n\nКвиз завершён.")
        return

    if chosen_idx != correct_idx:
        fail_quiz_session(user_id)
        send_message(user_id,
            f"❌ Неверно.\n\n<b>Правильный ответ:</b> {answer_text}\n\nКвиз завершён.")
        return

    mark_solved(user_id, task_id)

    current_idx = session["current_idx"]
    task_ids = session["task_ids"]

    if current_idx >= 2:
        complete_quiz_session(user_id)
        send_message(user_id, "✅ Верно!\n\n🎉 <b>Квиз пройден!</b> Все 3 вопроса отгаданы!")
    else:
        advance_quiz_session(user_id)
        send_message(user_id, "✅ Верно! Следующий вопрос…")
        next_task = get_task_by_id(task_ids[current_idx + 1])
        if next_task:
            _show_quiz_question(user_id, next_task, current_idx + 2)


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
