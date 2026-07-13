import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from database.database import init_db

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def on_startup():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных успешно инициализирована.")

async def main():
    if not TOKEN:
        logger.error("Токен бота не найден. Убедитесь, что BOT_TOKEN задан в .env")
        return

    # Включаем ParseMode.HTML по умолчанию для всех сообщений
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.startup.register(on_startup)

    from handlers.handlers_worker import router as worker_router
    from handlers.handlers_mechanic import router as mechanic_router
    from handlers.handlers_admin import router as admin_router
    dp.include_router(worker_router)
    dp.include_router(mechanic_router)
    dp.include_router(admin_router)

    logger.info("Запуск Telegram-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
