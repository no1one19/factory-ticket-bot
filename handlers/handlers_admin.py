import csv
import io

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from config import is_admin
from database.database import DB_NAME

router = Router()


@router.message(Command("report"))
@router.message(F.text == "📊 Скачать отчет")
async def cmd_report(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администраторам.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, user_id, machine_number, description, criticality, "
            "status, mechanic_id FROM tickets"
        ) as cursor:
            tickets = await cursor.fetchall()

    if not tickets:
        await message.answer("База данных пуста, отчетов пока нет.")
        return

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "ID",
            "ID Рабочего",
            "Номер станка",
            "Описание",
            "Критичность",
            "Статус",
            "ID Механика",
        ]
    )
    writer.writerows(tickets)

    document = BufferedInputFile(
        output.getvalue().encode("utf-8-sig"), filename="factory_report.csv"
    )
    await message.answer_document(
        document=document,
        caption="📊 <b>Отчет по всем заявкам на оборудование</b>",
    )
