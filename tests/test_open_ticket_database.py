import tempfile
import unittest

import aiosqlite

from database import database


class OpenTicketDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.old_db_name = database.DB_NAME
        database.DB_NAME = f"{self.temp_dir.name}/tickets.db"
        self.addCleanup(setattr, database, "DB_NAME", self.old_db_name)
        await database.init_db()

    async def create_ticket(self) -> int:
        async with aiosqlite.connect(database.DB_NAME) as db:
            cursor = await db.execute(
                """
                INSERT INTO tickets
                    (user_id, machine_number, description, photo_id, criticality)
                VALUES (?, ?, ?, ?, ?)
                """,
                (100, "M-1", "broken", "photo", "critical"),
            )
            await db.commit()
            return cursor.lastrowid

    async def test_closed_and_deleted_tickets_are_unavailable(self) -> None:
        closed_ticket_id = await self.create_ticket()
        deleted_ticket_id = await self.create_ticket()

        self.assertIsNotNone(await database.get_open_ticket(closed_ticket_id))
        self.assertIsNotNone(await database.get_open_ticket(deleted_ticket_id))

        async with aiosqlite.connect(database.DB_NAME) as db:
            await db.execute(
                "UPDATE tickets SET status = 'closed' WHERE id = ?",
                (closed_ticket_id,),
            )
            await db.execute(
                "DELETE FROM tickets WHERE id = ?",
                (deleted_ticket_id,),
            )
            await db.commit()

        self.assertIsNone(await database.get_open_ticket(closed_ticket_id))
        self.assertIsNone(await database.get_open_ticket(deleted_ticket_id))
