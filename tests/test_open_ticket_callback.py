import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from database.database import TicketCard
from handlers import handlers_mechanic


class FakeMessage:
    def __init__(self, user_id: int = 200) -> None:
        self.from_user = SimpleNamespace(id=user_id)


class FakeCallback:
    def __init__(self, data: str, user_id: int = 200) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage(user_id)
        self.answers: list[tuple[str | None, bool]] = []

    async def answer(self, text=None, show_alert=False) -> None:
        self.answers.append((text, show_alert))


class OpenTicketCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_callback_loads_exact_ticket_and_uses_shared_card(self):
        ticket = TicketCard(42, "M-1", "broken", "photo", "critical")
        callback = FakeCallback("open_ticket:42")
        load_ticket = AsyncMock(return_value=ticket)
        send_card = AsyncMock()

        with (
            patch.object(handlers_mechanic, "is_mechanic", return_value=True),
            patch.object(handlers_mechanic, "get_open_ticket", load_ticket),
            patch.object(handlers_mechanic, "send_ticket_card", send_card),
        ):
            await handlers_mechanic.callback_open_ticket(callback)

        load_ticket.assert_awaited_once_with(42)
        send_card.assert_awaited_once_with(callback.message, ticket)
        self.assertEqual(callback.answers, [(None, False)])

    async def test_unavailable_ticket_shows_required_message(self):
        callback = FakeCallback("open_ticket:42")

        with (
            patch.object(handlers_mechanic, "is_mechanic", return_value=True),
            patch.object(
                handlers_mechanic,
                "get_open_ticket",
                AsyncMock(return_value=None),
            ),
        ):
            await handlers_mechanic.callback_open_ticket(callback)

        self.assertEqual(callback.answers, [("Этот тикет уже недоступен", True)])

    async def test_existing_open_tickets_button_uses_shared_card(self):
        ticket = TicketCard(42, "M-1", "broken", "photo", "critical")
        message = FakeMessage()
        send_card = AsyncMock()

        with (
            patch.object(handlers_mechanic, "is_mechanic", return_value=True),
            patch.object(
                handlers_mechanic,
                "list_open_tickets",
                AsyncMock(return_value=[ticket]),
            ),
            patch.object(handlers_mechanic, "send_ticket_card", send_card),
        ):
            await handlers_mechanic.cmd_tickets(message)

        send_card.assert_awaited_once_with(message, ticket)
