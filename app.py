import os
import logging
import asyncio
import aiohttp
import random
import json
from datetime import datetime, time

from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import nest_asyncio

# ===== Логування =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== Токен і Chat ID =====
BOT_TOKEN = "8092371216:AAF7bfwunLqI2ZrGBpE2goMaxXnol07vG0g"
CHAT_ID = "598331739"  # або -1001234567890 для групи

# ===== URL JSON з задачами =====
PUZZLES_URL = "https://raw.githubusercontent.com/AntonRomashov87/Chess_puzzles/main/puzzles.json"

# ===== Глобальний список задач =====
PUZZLES = []

# ===== Завантаження задач =====
async def load_puzzles():
    global PUZZLES
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PUZZLES_URL) as resp:
                resp.raise_for_status()
                text = await resp.text()
                data = json.loads(text)
                if isinstance(data, list):
                    PUZZLES = data
                    logger.info(f"Завантажено {len(PUZZLES)} задач")
                else:
                    logger.error("JSON має неправильну структуру.")
    except Exception as e:
        logger.error(f"Помилка при завантаженні puzzles.json: {e}")
        PUZZLES = []

# ===== Відправка випадкової задачі =====
async def send_random_puzzle(bot: Bot):
    if not PUZZLES:
        logger.warning("Задачі ще не завантажені.")
        return
    puzzle = random.choice(PUZZLES)
    msg = f"♟️ {puzzle.get('title', 'Задача')}:\n{puzzle.get('url', '')}"
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        logger.info("Задача надіслана ✅")
    except Exception as e:
        logger.error(f"Помилка при відправці в Telegram: {e}")

# ===== Команди бота =====
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я шаховий бот 🤖♟\n"
        "Напиши /puzzle, щоб отримати випадкову задачу."
    )

async def puzzle_command(update, context: ContextTypes.DEFAULT_TYPE):
    await send_random_puzzle(context.bot)

# ===== Функція для автоматичної розсилки =====
async def scheduled_puzzles(bot: Bot):
    while True:
        now = datetime.now()
        # Надсилаємо двічі на день: 08:00 і 20:00
        if now.hour in [8, 20] and now.minute == 0:
            await send_random_puzzle(bot)
            await asyncio.sleep(61)  # чекаємо 61 секунду, щоб не надіслати повторно
        await asyncio.sleep(20)

# ===== Основна функція =====
async def main():
    # Завантажуємо задачі
    await load_puzzles()

    # Створюємо Application (асинхронний бот)
    app = Application.builder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("puzzle", puzzle_command))

    # Запускаємо фонове завдання для автоматичної розсилки
    asyncio.create_task(scheduled_puzzles(app.bot))

    logger.info("Бот запущений ✅")
    await app.run_polling()

# ===== Запуск =====
if __name__ == "__main__":
    # Дозволяє використовувати asyncio у Render
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
