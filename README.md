# 🎟 TicketTgBot

Telegram-бот для онлайн-продажу, бронювання та перевірки електронних квитків.

## Технології

| Компонент | Технологія |
|-----------|-----------|
| Бот | Python 3.12 + aiogram 3.x |
| Backend API | FastAPI + uvicorn |
| База даних | MySQL + SQLAlchemy 2.0 (async) |
| Frontend | Telegram Mini App (HTML/CSS/JS) |
| QR-коди | segno |

## Категорії

- 🎬 **Кіно** — продаж квитків на кіносеанси з вибором місця у залі
- 🚌 **Автобуси** — продаж квитків на рейси з вибором місця у салоні

## Ролі

- **Клієнт** — перегляд подій, купівля квитків, отримання QR-квитка
- **Партнер** — створення подій, редагування схем, перегляд статистики, перевірка квитків
- **Адміністратор** — керування користувачами, зміна ролей

## Встановлення

### З Nix

```bash
nix-shell
```

### Без Nix

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Налаштування

```bash
cp .env.example .env
# Відредагуйте .env: BOT_TOKEN, DATABASE_URL, SECRET_KEY
```

### Запуск

```bash
# FastAPI сервер (з webhook)
uvicorn main:app --reload --port 8000

# Або напряму
python main.py
```

## Структура проєкту

```
TicketTgBot/
├── api/              # FastAPI роутери
├── bot/
│   ├── categories/   # Модулі cinema та bus
│   ├── common/       # /start, /help, мої квитки
│   ├── partner/      # Панель партнера
│   ├── admin/        # Адмін-панель
│   └── middlewares/  # Role middleware
├── core/             # Config, security, utils
├── database/         # Models + repositories
├── services/         # Ticket, QR, payment, verification
├── templates/        # Jinja2 HTML для Mini App
├── static/           # CSS та JS для Mini App
├── main.py           # Точка входу
└── shell.nix         # Nix dev environment
```

## Безпека

- QR-токени зберігаються як SHA-256 хеш у БД
- Двоетапна верифікація: контролер сканує QR → власник підтверджує у боті
- Тимчасове блокування місць під час оформлення покупки
- Рольова модель: клієнт / партнер / адмін
