import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database.database import DB_NAME

router = Router()

@router.message(Command("tickets"))
@router.message(F.text == "🛠 Открытые тикеты")
async def cmd_tickets(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем все открытые заявки
        async with db.execute(
            "SELECT id, machine_number, description, photo_id, criticality FROM tickets WHERE status = 'open'"
        ) as cursor:
            tickets = await cursor.fetchall()
            
    if not tickets:
        await message.answer("Все станки работают, заявок нет.")
        return

    for ticket in tickets:
        ticket_id, machine_number, description, photo_id, criticality = ticket
        
        text = (
            f"🎫 <b>Заявка #{ticket_id}</b>\n"
            f"🏭 <b>Станок:</b> <code>{machine_number}</code>\n"
            f"⚠️ <b>Проблема:</b> {description}\n"
            f"🚨 <b>Приоритет:</b> {criticality}"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👨‍🔧 Взять в работу", callback_data=f"take_{ticket_id}")]
            ]
        )
        
        if photo_id:
            await message.answer_photo(photo=photo_id, caption=text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("take_"))
async def callback_take_ticket(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[1])
    mechanic_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, status FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
            
        user_id, status = row
        
        if status != 'open':
            await callback.answer("Эта заявка уже в работе или закрыта.", show_alert=True)
            return

        await db.execute(
            "UPDATE tickets SET status = 'in_progress', mechanic_id = ? WHERE id = ?",
            (mechanic_id, ticket_id)
        )
        await db.commit()
        
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершить ремонт", callback_data=f"finish_{ticket_id}")]
        ]
    )
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=callback.message.caption, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text=callback.message.text, reply_markup=keyboard)
        
    await callback.answer("Вы взяли заявку в работу!")
    
    try:
        await bot.send_message(user_id, f"👨‍🔧 Ваша заявка #{ticket_id} по станку взята в работу!")
    except Exception:
        pass


@router.callback_query(F.data.startswith("finish_"))
async def callback_finish_ticket(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[1])
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, status FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
            
        user_id, status = row
        
        if status != 'in_progress':
            await callback.answer("Эту заявку нельзя завершить.", show_alert=True)
            return

        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()
        
    if callback.message.photo:
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>Ремонт завершен</b>", reply_markup=None)
    else:
        await callback.message.edit_text(text=callback.message.text + "\n\n✅ <b>Ремонт завершен</b>", reply_markup=None)
        
    await callback.answer("Ремонт завершен!")
    
    try:
        await bot.send_message(user_id, f"✅ Ремонт по заявке #{ticket_id} завершен!")
    except Exception:
        pass
