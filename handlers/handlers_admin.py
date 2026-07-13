import os
import csv
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

from database.database import DB_NAME

router = Router()

@router.message(Command("report"))
@router.message(F.text == "📊 Скачать отчет")
async def cmd_report(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, user_id, machine_number, description, criticality, status, mechanic_id FROM tickets"
        ) as cursor:
            tickets = await cursor.fetchall()
            
    if not tickets:
        await message.answer("База данных пуста, отчетов пока нет.")
        return

    filename = "factory_report.csv"
    
    with open(filename, mode="w", newline='', encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([
            "ID", "ID Рабочего", "Номер станка", "Описание", 
            "Критичность", "Статус", "ID Механика"
        ])
        for ticket in tickets:
            writer.writerow(ticket)
            
    document = FSInputFile(filename)
    await message.answer_document(
        document=document, 
        caption="📊 <b>Отчет по всем заявкам на оборудование</b>"
    )
    
    try:
        os.remove(filename)
    except OSError:
        pass
