import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import aiosqlite

from database import database
from handlers import handlers_worker


class FakeBot:
    def __init__(self, failing_recipient: int | None = None) -> None:
        self.failing_recipient = failing_recipient
        self.attempted: list[int] = []
        self.messages: list[tuple[int, str, object]] = []

    async def send_message(self, chat_id, text, reply_markup=None) -> None:
        self.attempted.append(chat_id)
        if chat_id == self.failing_recipient:
            raise RuntimeError("send failed")
        self.messages.append((chat_id, text, reply_markup))


class FakeState:
    def __init__(self, data) -> None:
        self.data = data
        self.cleared = False

    async def get_data(self):
        return self.data

    async def clear(self) -> None:
        self.cleared = True


class FakeMessage:
    def __init__(self, user_id: int, text: str) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_notifications_exclude_author_and_isolate_send_errors(self):
        bot = FakeBot(failing_recipient=200)

        with patch.object(
            handlers_worker,
            "ticket_viewer_ids",
            return_value=frozenset({100, 200, 300}),
        ):
            await handlers_worker.notify_ticket_viewers(
                bot,
                ticket_id=42,
                author_id=100,
            )

        self.assertEqual(set(bot.attempted), {200, 300})
        self.assertEqual(len(bot.attempted), 2)
        self.assertEqual([message[0] for message in bot.messages], [300])
        self.assertIn("заявка №42", bot.messages[0][1])
        button = bot.messages[0][2].inline_keyboard[0][0]
        self.assertEqual(button.callback_data, "open_ticket:42")

    async def test_ticket_is_committed_before_notifications(self):
        db_path = self.enterContext(tempfile.TemporaryDirectory())
        db_path = f"{db_path}/tickets.db"
        with patch.object(database, "DB_NAME", db_path):
            await database.init_db()

        state = FakeState(
            {
                "machine_number": "M-1",
                "description": "broken",
                "photo_id": "photo",
            }
        )
        message = FakeMessage(user_id=100, text="🔴 Критично")
        bot = FakeBot()
        observed_ticket_ids: list[int] = []

        async def verify_committed(_bot, ticket_id, author_id):
            self.assertEqual(author_id, 100)
            async with aiosqlite.connect(db_path) as db:
                async with db.execute(
                    "SELECT id FROM tickets WHERE id = ?",
                    (ticket_id,),
                ) as cursor:
                    self.assertIsNotNone(await cursor.fetchone())
            observed_ticket_ids.append(ticket_id)

        with (
            patch.object(database, "DB_NAME", db_path),
            patch.object(
                handlers_worker,
                "notify_ticket_viewers",
                verify_committed,
            ),
        ):
            await handlers_worker.process_criticality(message, state, bot)

        self.assertEqual(observed_ticket_ids, [1])
        self.assertTrue(state.cleared)
