# Factory Ticket Bot

Telegram-бот для регистрации и обработки заявок на ремонт оборудования.

## Запуск

1. Установите Python 3.11+ и зависимости: `pip install -r requirements.txt`.
2. Скопируйте `.env.example` в `.env`.
3. Задайте `BOT_TOKEN`, `ADMIN_IDS` и `MECHANIC_IDS`.
4. Создайте локальный ключ шифрования: `python scripts/generate_encryption_key.py`.
5. Запустите `python main.py`.

`ADMIN_IDS` и `MECHANIC_IDS` — списки Telegram user ID через запятую. Администраторы
могут скачивать отчёт и также выполнять действия механика. Просматривать и брать
тикеты могут только механики; завершать тикет может только назначенный механик.

Данные заявок в SQLite шифруются ключом `DATA_ENCRYPTION_KEY` из `.env`. Сохраните
резервную копию этого ключа в безопасном месте: при его потере расшифровать базу
будет невозможно. Сам ключ и файл `.env` нельзя добавлять в Git.

## Проверки

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest -q
```
