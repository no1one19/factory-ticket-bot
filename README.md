# Factory Ticket Bot

Telegram-бот для регистрации и обработки заявок на ремонт оборудования.

## Запуск

1. Установите Python 3.11+ и зависимости: `pip install -r requirements.txt`.
2. Скопируйте `.env.example` в `.env`.
3. Задайте `BOT_TOKEN`, `ADMIN_IDS` и `MECHANIC_IDS`.
4. Запустите `python main.py`.

`ADMIN_IDS` и `MECHANIC_IDS` — списки Telegram user ID через запятую. Администраторы
могут скачивать отчёт и также выполнять действия механика. Просматривать и брать
тикеты могут только механики; завершать тикет может только назначенный механик.

## Проверки

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```
