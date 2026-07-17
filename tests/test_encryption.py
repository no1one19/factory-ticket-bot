import tempfile
import unittest

import aiosqlite

from database import database
from database.encryption import ENCRYPTED_PREFIX


class TicketEncryptionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.old_db_name = database.DB_NAME
        database.DB_NAME = f"{self.temp_dir.name}/tickets.db"
        self.addCleanup(setattr, database, "DB_NAME", self.old_db_name)
        await database.init_db()

    async def test_new_ticket_is_encrypted_and_can_be_used(self) -> None:
        ticket_id = await database.create_ticket(
            100,
            "M-1",
            "broken motor",
            "photo-id",
            "critical",
        )

        async with aiosqlite.connect(database.DB_NAME) as db:
            async with db.execute(
                "SELECT user_id, machine_number, description, photo_id, "
                "criticality FROM tickets WHERE id = ?",
                (ticket_id,),
            ) as cursor:
                raw_values = await cursor.fetchone()

        self.assertTrue(all(value.startswith(ENCRYPTED_PREFIX) for value in raw_values))
        self.assertNotIn("broken motor", " ".join(raw_values))

        ticket = await database.get_open_ticket(ticket_id)
        self.assertEqual(ticket.machine_number, "M-1")
        self.assertEqual(ticket.description, "broken motor")
        self.assertEqual(await database.claim_ticket(ticket_id, 200), 100)
        self.assertEqual(await database.finish_ticket(ticket_id, 200), 100)

        report = (await database.list_tickets_for_report())[0]
        self.assertEqual(report.user_id, 100)
        self.assertEqual(report.machine_number, "M-1")
        self.assertEqual(report.description, "broken motor")
        self.assertEqual(report.criticality, "critical")
        self.assertEqual(report.status, "closed")
        self.assertEqual(report.mechanic_id, 200)

    async def test_plaintext_legacy_ticket_is_migrated(self) -> None:
        async with aiosqlite.connect(database.DB_NAME) as db:
            cursor = await db.execute(
                """
                INSERT INTO tickets
                    (user_id, machine_number, description, photo_id, criticality)
                VALUES (?, ?, ?, ?, ?)
                """,
                (100, "M-2", "legacy problem", "legacy-photo", "low"),
            )
            await db.commit()
            ticket_id = cursor.lastrowid

        await database.init_db()

        async with aiosqlite.connect(database.DB_NAME) as db:
            async with db.execute(
                "SELECT user_id, machine_number, description, photo_id, "
                "criticality FROM tickets WHERE id = ?",
                (ticket_id,),
            ) as cursor:
                raw_values = await cursor.fetchone()

        self.assertTrue(all(value.startswith(ENCRYPTED_PREFIX) for value in raw_values))
        ticket = await database.get_open_ticket(ticket_id)
        self.assertEqual(ticket.machine_number, "M-2")
        self.assertEqual(ticket.description, "legacy problem")
