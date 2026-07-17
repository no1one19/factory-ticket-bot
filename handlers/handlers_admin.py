import csv
import io

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from config import is_admin
from database.database import list_tickets_for_report

router = Router()


@router.message(Command("report"))
@router.message(F.text == "📊 Скачать отчет")
async def cmd_report(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администраторам.")
        return

    tickets = await list_tickets_for_report()

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
