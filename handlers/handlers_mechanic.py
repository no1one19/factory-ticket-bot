from html import escape

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import is_mechanic
from database.database import DB_NAME, claim_ticket, finish_ticket

router = Router()


def _callback_ticket_id(data: str | None) -> int | None:
    try:
        return int((data or "").split("_", maxsplit=1)[1])
    except (IndexError, ValueError):
        return None


@router.message(Command("tickets"))
@router.message(F.text == "🛠 Открытые тикеты")
async def cmd_tickets(message: Message) -> None:
    if not is_mechanic(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только механикам.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, machine_number, description, photo_id, criticality "
            "FROM tickets WHERE status = 'open'"
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await message.answer("Все станки работают, заявок нет.")
        return

    for ticket_id, machine_number, description, photo_id, criticality in tickets:
        text = (
            f"🎫 <b>Заявка #{ticket_id}</b>\n"
            f"🏭 <b>Станок:</b> <code>{escape(machine_number)}</code>\n"
            f"⚠️ <b>Проблема:</b> {escape(description)}\n"
            f"🚨 <b>Приоритет:</b> {escape(criticality)}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👨‍🔧 Взять в работу", callback_data=f"take_{ticket_id}"
                    )
                ]
            ]
        )
        if photo_id:
            await message.answer_photo(
                photo=photo_id, caption=text, reply_markup=keyboard
            )
        else:
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("take_"))
async def callback_take_ticket(callback: CallbackQuery, bot: Bot) -> None:
    if not is_mechanic(callback.from_user.id):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    ticket_id = _callback_ticket_id(callback.data)
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

    ticket_id = _callback_ticket_id(callback.data)
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
