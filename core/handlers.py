"""
core/handlers.py — вся бизнес-логика бота.
"""

import random
from core.bot import (send_message, main_menu_keyboard, cinema_menu_keyboard, task_inline_keyboard,
                      invite_keyboard, options_inline_keyboard, quiz_options_keyboard,
                      next_task_keyboard)
from core.tasks import get_next_task, get_task_by_id, mark_shown, mark_solved, add_favorite
from core.db import (get_user_progress, get_streak, get_favorites, get_wrong_options_from_db,
                     get_task_counts, get_quiz_tasks, create_quiz_session, get_quiz_session,
                     advance_quiz_session, fail_quiz_session, complete_quiz_session,
                     reset_history)


def handle_start(user_id: int):
    text = (
        "👋 Привет! Я <b>BrainPocket</b> — тренажёр для мозга.\n\n"
        "Выбери раздел и начни прокачиваться:\n"
        "🧩 Загадки · 🔍 Логика · ⚡ Квиз · 🧠 IQ · 🎬 Кинематограф\n\n"
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
    "🦸 Marvel":           "marvel",
    "🔬 Теория Большого взрыва": "tbbt",
    "🛸 Гравити Фолз":     "gravityfalls",
    "🚀 Звёздные Войны":   "starwars",
    "🎲 Случайное":        None,
}

TYPE_INFO = {
    "riddle": ("🧩", "Загадки"),
    "logic":  ("🔍", "Логика"),
    "quiz":   ("⚡", "Квиз"),
    "iq":     ("🧠", "IQ"),
    "lotr":   ("💍", "Властелин Колец"),
    "hp":     ("🪄", "Гарри Поттер"),
    "marvel": ("🦸", "Marvel"),
    "tbbt":   ("🔬", "Теория Б. взрыва"),
    "gravityfalls": ("🛸", "Гравити Фолз"),
    "starwars": ("🚀", "Звёздные Войны"),
}

def handle_menu(user_id: int, label: str):
    if label == "📈 Мой прогресс":
        handle_progress(user_id)
        return
    if label == "❤️ Избранное":
        handle_favorites_list(user_id)
        return
    if label == "🤝 Пригласить друга":
        handle_invite_friend(user_id)
        return
    if label == "⚡ Мини-квиз":
        handle_mini_quiz(user_id)
        return
    if label == "🎬 Кинематограф":
        send_message(user_id, "🎬 Выбери вселенную:", reply_markup=cinema_menu_keyboard())
        return
    if label == "⬅️ Назад":
        send_message(user_id, "Главное меню:", reply_markup=main_menu_keyboard())
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

    DIFF_LABEL = {1: "Легко", 2: "Средне", 3: "Сложно", 4: "Эксперт"}
    emoji = TYPE_INFO.get(task["type"], ("🎲", ""))[0]
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
    totals = get_task_counts()
    streak = get_streak(user_id)

    lines = [f"📈 <b>Мой прогресс</b>\n"]
    for task_type, (emoji, name) in TYPE_INFO.items():
        total = totals.get(task_type, 0)
        if total == 0:
            continue
        solved = p.get(task_type, 0)
        lines.append(f"{emoji} {name}: {solved}/{total}")

    lines.append("")
    lines.append(f"Всего решено: <b>{sum(p.values())}</b>")
    lines.append(f"Серия: <b>{streak} дн.</b> 🔥")
    send_message(user_id, "\n".join(lines))


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


def handle_invite_friend(user_id: int):
    send_message(
        user_id,
        "🤝 <b>Пригласи друга в BrainPocket!</b>\n\n"
        "Поделись ботом — тренируйтесь вместе и сравнивайте успехи.",
        reply_markup=invite_keyboard(),
    )
