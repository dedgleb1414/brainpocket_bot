# BrainPocket 🧠

Telegram-бот для тренировки мозга: загадки, логика, квиз, IQ-задачи.

## Стек

```
VS Code → GitHub → Vercel (webhook) → Telegram Bot API
                        ↓
                  PostgreSQL (Supabase / Neon)
```

## Структура проекта

```
brainpocket/
├── api/
│   └── webhook.py       # точка входа Vercel, принимает Update
├── core/
│   ├── router.py        # разбирает Update, вызывает handlers
│   ├── handlers.py      # вся бизнес-логика
│   ├── bot.py           # обёртка над Telegram API
│   ├── db.py            # PostgreSQL: history, progress, favorites
│   └── tasks.py         # выдача задач без повторов
├── data/
│   └── tasks.json       # пример задач (загружается через fix.py)
├── fix.py               # CLI-инструмент для обслуживания
├── vercel.json          # конфиг деплоя
├── requirements.txt
├── .env.example
└── .gitignore
```

## Быстрый старт

### 1. Клонируй и настрой окружение

```bash
git clone https://github.com/тебя/brainpocket
cd brainpocket
cp .env.example .env
# отредактируй .env
pip install -r requirements.txt
```

### 2. Создай бота

Напиши [@BotFather](https://t.me/BotFather) → `/newbot` → получи `BOT_TOKEN`.

### 3. Создай базу данных

Зарегистрируйся на [Supabase](https://supabase.com) или [Neon](https://neon.tech),
создай проект, скопируй `DATABASE_URL` в `.env`.

```bash
python fix.py migrate        # создать таблицы
python fix.py load data/tasks.json  # загрузить тестовые задачи
python fix.py stats          # проверить
```

### 4. Задеплой на Vercel

```bash
npm i -g vercel
vercel login
vercel --prod
```

В настройках проекта на Vercel добавь переменные окружения:
- `BOT_TOKEN`
- `DATABASE_URL`

### 5. Зарегистрируй webhook

```bash
# Добавь в .env: WEBHOOK_URL=https://твой-проект.vercel.app/api/webhook
python fix.py setwebhook
```

Готово — бот работает!

---

## fix.py — команды

| Команда | Что делает |
|---|---|
| `python fix.py migrate` | Создаёт таблицы в БД |
| `python fix.py load data/tasks.json` | Загружает задачи из JSON |
| `python fix.py stats` | Статистика задач по типу/сложности |
| `python fix.py reset 123456` | Сбросить историю пользователя |
| `python fix.py setwebhook` | Зарегистрировать webhook |
| `python fix.py delwebhook` | Удалить webhook |
| `python fix.py task 42` | Просмотр задачи по ID |
| `python fix.py find "три двери"` | Поиск задачи по тексту |

## Формат задачи (JSON)

```json
{
  "id": 145,
  "type": "logic",
  "question": "Три двери...",
  "answer": "Дверь №2, потому что...",
  "hint": "Вероятность меняется при открытии двери",
  "difficulty": 3
}
```

Типы: `riddle` · `logic` · `quiz` · `iq`  
Сложность: `1`=Легко · `2`=Средне · `3`=Сложно · `4`=Эксперт

## Добавление задач

1. Добавь задачи в `data/tasks.json`
2. `python fix.py load data/tasks.json` — загрузит только новые (по `id`)
