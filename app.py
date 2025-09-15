import os
import logging
import asyncio
import aiohttp
import random
import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request

# ===== Логування =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== Налаштування Flask =====
app = Flask(__name__)

# ===== Токен і Chat ID =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ===== URL JSON з задачами (ВИПРАВЛЕНО) =====
PUZZLES_URL = "https://raw.githubusercontent.com/AntonRomashov87/Chess_puzzles/main/puzzles.json"

# ===== Глобальні змінні =====
PUZZLES = []
PTB_APP = None

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
        return "⚠️ Задачі ще не завантажені або сталася помилка."
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
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я шаховий бот 🤖♟\n"
        "Натискай кнопки нижче:",
        reply_markup=get_keyboard()
    )

# ===== Обробка кнопок =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "puzzle":
        msg = get_random_puzzle()
        await query.edit_message_text(text=msg, reply_markup=get_keyboard())
    elif query.data == "start":
        await query.edit_message_text(
            text="Привіт! Я готовий дати тобі задачу ♟️",
            reply_markup=get_keyboard()
        )

# =======================
# Webhook
# =======================
@app.route("/webhook", methods=["POST"])
async def webhook():
    if PTB_APP:
        update_data = request.get_json()
        update = Update.de_json(update_data, PTB_APP.bot)
        await PTB_APP.process_update(update)
        return '', 200
    return 'Bot not initialized', 500

@app.route("/", methods=["GET"])
def index():
    return "Шаховий бот працює через Webhook!", 200

# =======================
# Основна функція для запуску
# =======================
async def setup_bot():
    global PTB_APP
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не знайдений!")
        return

    await load_puzzles()
    
    PTB_APP = Application.builder().token(BOT_TOKEN).build()
    
    PTB_APP.add_handler(CommandHandler("start", start_command))
    PTB_APP.add_handler(CallbackQueryHandler(button_handler))

    webhook_url = os.getenv("RAILWAY_STATIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        full_webhook_url = f"https://{webhook_url}/webhook"
        await PTB_APP.bot.set_webhook(full_webhook_url)
        logger.info(f"Вебхук встановлено на {full_webhook_url}")
    else:
        logger.warning("URL для вебхука не знайдений. Пропускаємо встановлення.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(setup_bot())
    else:
        loop.run_until_complete(setup_bot())

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

