import os
import logging
import asyncio
import aiohttp
import random
import json
from datetime import datetime

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import nest_asyncio

# ===== Логування =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== Токен і Chat ID =====
BOT_TOKEN = "8092371216:AAF7bfwunLqI2ZrGBpE2goMaxXnol07vG0g"
CHAT_ID = "598331739"

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

# ===== Отримати випадкову задачу =====
def get_random_puzzle():
    if not PUZZLES:
        return "⚠️ Задачі ще не завантажені."
    puzzle = random.choice(PUZZLES)
    return f"♟️ {puzzle.get('title', 'Задача')}:\n{puzzle.get('url', '')}"

# ===== Клавіатура =====
def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("♟️ Puzzle", callback_data="puzzle")],
        [InlineKeyboardButton("ℹ️ Start", callback_data="start")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== Команди бота =====
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я шаховий бот 🤖♟\n"
        "Натискай кнопки нижче:",
        reply_markup=get_keyboard()
    )

# ===== Обробка кнопок =====
async def button_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "puzzle":
        msg = get_random_puzzle()
        await query.edit_message_text(
            text=msg,
            reply_markup=get_keyboard()
        )
    elif query.data == "start":
        await query.edit_message_text(
            text="Привіт! Я готовий дати тобі задачу ♟️",
            reply_markup=get_keyboard()
        )

# ===== Автоматична розсилка =====
async def scheduled_puzzles(bot: Bot):
    while True:
        now = datetime.now()
        if now.hour in [8, 20] and now.minute == 0:
            msg = get_random_puzzle()
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            await asyncio.sleep(61)
        await asyncio.sleep(20)

# ===== Основна функція =====
async def main():
    await load_puzzles()
    app = Application.builder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))

    # Кнопки
    app.add_handler(CallbackQueryHandler(button_handler))

    # Авто-розсилка
    asyncio.create_task(scheduled_puzzles(app.bot))

    logger.info("Бот запущений ✅")
    await app.run_polling()

# ===== Запуск =====
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
