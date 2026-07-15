import aiosqlite

DB_NAME = "factory_bot.db"


async def init_db() -> None:
    """Create the ticket table when it does not exist."""
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


async def claim_ticket(ticket_id: int, mechanic_id: int) -> int | None:
    """Atomically claim an open ticket and return its owner's Telegram ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            UPDATE tickets
            SET status = 'in_progress', mechanic_id = ?
            WHERE id = ? AND status = 'open'
            """,
            (mechanic_id, ticket_id),
        )
        await db.commit()
        if cursor.rowcount != 1:
            return None

        async with db.execute(
            "SELECT user_id FROM tickets WHERE id = ?", (ticket_id,)
        ) as result:
            row = await result.fetchone()
            return row[0] if row else None


async def finish_ticket(ticket_id: int, mechanic_id: int) -> int | None:
    """Close a ticket only when it belongs to the requesting mechanic."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            UPDATE tickets
            SET status = 'closed'
            WHERE id = ? AND status = 'in_progress' AND mechanic_id = ?
            """,
            (ticket_id, mechanic_id),
        )
        await db.commit()
        if cursor.rowcount != 1:
            return None

        async with db.execute(
            "SELECT user_id FROM tickets WHERE id = ?", (ticket_id,)
        ) as result:
            row = await result.fetchone()
            return row[0] if row else None
