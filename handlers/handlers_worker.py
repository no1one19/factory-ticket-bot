import asyncio
import logging

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from config import ticket_viewer_ids
from database.database import DB_NAME
from keyboards.reply import main_menu

router = Router()
logger = logging.getLogger(__name__)


async def notify_ticket_viewers(
    bot: Bot,
    ticket_id: int,
    author_id: int,
) -> None:
    """Notify each eligible ticket viewer once, excluding the author."""
    recipients = ticket_viewer_ids() - {author_id}
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Открыть тикет",
                    callback_data=f"open_ticket:{ticket_id}",
                )
            ]
        ]
    )
    text = (
        "🔔 <b>Новый тикет!</b>\n\n"
        f"Появилась новая заявка №{ticket_id}.\n\n"
        "Нажмите кнопку ниже, чтобы открыть её."
    )

    async def send_notification(recipient_id: int) -> None:
        try:
            await bot.send_message(
                recipient_id,
                text,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception(
                "Не удалось уведомить пользователя %s о заявке %s",
                recipient_id,
                ticket_id,
            )

    await asyncio.gather(*(send_notification(user_id) for user_id in recipients))


class TicketState(StatesGroup):
    waiting_for_machine_number = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_criticality = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я <b>ЗАВОДСКОЙ БОТ-АССИСТЕНТ</b>.\n\n"
        "Выберите нужное действие в меню ниже:",
        reply_markup=main_menu,
    )


@router.message(F.text == "📝 Создать заявку")
async def start_ticket_creation(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, введите <b>номер станка</b>:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(TicketState.waiting_for_machine_number)


@router.message(TicketState.waiting_for_machine_number, F.text)
async def process_machine_number(message: Message, state: FSMContext):
    await state.update_data(machine_number=message.text)
    await message.answer("Опишите проблему:")
    await state.set_state(TicketState.waiting_for_description)


@router.message(TicketState.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Пришлите фотографию поломки:")
    await state.set_state(TicketState.waiting_for_photo)


@router.message(TicketState.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔴 Критично"),
                KeyboardButton(text="🟡 Не срочно"),
            ]
        ],
        resize_keyboard=True,
    )
    await message.answer("Укажите уровень критичности:", reply_markup=keyboard)
    await state.set_state(TicketState.waiting_for_criticality)


@router.message(TicketState.waiting_for_photo, ~F.photo)
async def process_photo_invalid(message: Message):
    await message.answer("Пожалуйста, пришлите именно фотографию (как фото, а не файлом).")


@router.message(
    TicketState.waiting_for_criticality,
    F.text.in_(["🔴 Критично", "🟡 Не срочно"]),
)
async def process_criticality(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    machine_number = data["machine_number"]
    description = data["description"]
    photo_id = data["photo_id"]
    criticality = message.text
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO tickets (user_id, machine_number, description, photo_id, criticality)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, machine_number, description, photo_id, criticality),
        )
        await db.commit()
        ticket_id = cursor.lastrowid

    if ticket_id is not None:
        await notify_ticket_viewers(bot, ticket_id, user_id)

    await state.clear()

    await message.answer(
        "✅ <b>Заявка успешно создана и передана механикам.</b>",
        reply_markup=main_menu,
    )


@router.message(TicketState.waiting_for_criticality)
async def process_criticality_invalid(message: Message):
    await message.answer("Пожалуйста, выберите уровень критичности, используя кнопки ниже.")
