import aiosqlite

DB_NAME = "factory_bot.db"

async def init_db():
    """
    Асинхронное подключение к SQLite и создание таблицы tickets.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                machine_number TEXT NOT NULL,
                description TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                criticality TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                mechanic_id INTEGER
            )
            """
        )
        await db.commit()
