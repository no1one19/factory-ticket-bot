from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import is_mechanic
from database.database import (
    TicketCard,
    claim_ticket,
    finish_ticket,
    get_open_ticket,
    list_open_tickets,
)

router = Router()


def _callback_ticket_id(data: str | None, prefix: str) -> int | None:
    if not data or not data.startswith(prefix):
        return None

    try:
        return int(data.removeprefix(prefix))
    except ValueError:
        return None


async def send_ticket_card(message: Message, ticket: TicketCard) -> None:
    """Send the shared open-ticket card used by lists and notifications."""
    text = (
        f"🎫 <b>Заявка #{ticket.id}</b>\n"
        f"🏭 <b>Станок:</b> <code>{escape(ticket.machine_number)}</code>\n"
        f"⚠️ <b>Проблема:</b> {escape(ticket.description)}\n"
        f"🚨 <b>Приоритет:</b> {escape(ticket.criticality)}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍🔧 Взять в работу",
                    callback_data=f"take_{ticket.id}",
                )
            ]
        ]
    )
    if ticket.photo_id:
        await message.answer_photo(
            photo=ticket.photo_id,
            caption=text,
            reply_markup=keyboard,
        )
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("tickets"))
@router.message(F.text == "🛠 Открытые тикеты")
async def cmd_tickets(message: Message) -> None:
    if not is_mechanic(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только механикам.")
        return

    tickets = await list_open_tickets()

    if not tickets:
        await message.answer("Все станки работают, заявок нет.")
        return

    for ticket in tickets:
        await send_ticket_card(message, ticket)


@router.callback_query(F.data.startswith("open_ticket:"))
async def callback_open_ticket(callback: CallbackQuery) -> None:
    if not is_mechanic(callback.from_user.id):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    ticket_id = _callback_ticket_id(callback.data, "open_ticket:")
    if ticket_id is None:
        await callback.answer("Этот тикет уже недоступен", show_alert=True)
        return

    ticket = await get_open_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Этот тикет уже недоступен", show_alert=True)
        return

    await send_ticket_card(callback.message, ticket)
    await callback.answer()


@router.callback_query(F.data.startswith("take_"))
async def callback_take_ticket(callback: CallbackQuery, bot: Bot) -> None:
    if not is_mechanic(callback.from_user.id):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    ticket_id = _callback_ticket_id(callback.data, "take_")
    if ticket_id is None:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    user_id = await claim_ticket(ticket_id, callback.from_user.id)
    if user_id is None:
        await callback.answer(
            "Заявка не найдена или уже взята в работу.", show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершить ремонт", callback_data=f"finish_{ticket_id}"
                )
            ]
        ]
    )
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=callback.message.caption, reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            text=callback.message.text, reply_markup=keyboard
        )

    await callback.answer("Вы взяли заявку в работу!")
    try:
        await bot.send_message(
            user_id, f"👨‍🔧 Ваша заявка #{ticket_id} по станку взята в работу!"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("finish_"))
async def callback_finish_ticket(callback: CallbackQuery, bot: Bot) -> None:
    if not is_mechanic(callback.from_user.id):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    ticket_id = _callback_ticket_id(callback.data, "finish_")
    if ticket_id is None:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    user_id = await finish_ticket(ticket_id, callback.from_user.id)
    if user_id is None:
        await callback.answer(
            "Заявку может завершить только назначенный механик.", show_alert=True
        )
        return

    suffix = "\n\n✅ <b>Ремонт завершен</b>"
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + suffix, reply_markup=None
        )
    else:
        await callback.message.edit_text(
            text=(callback.message.text or "") + suffix, reply_markup=None
        )

    await callback.answer("Ремонт завершен!")
    try:
        await bot.send_message(user_id, f"✅ Ремонт по заявке #{ticket_id} завершен!")
    except Exception:
        pass
