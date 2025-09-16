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

# ===== URL JSON з задачами =====
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
    """Повертає словник з даними задачі або None, якщо задач немає."""
    if not PUZZLES:
        return None
    return random.choice(PUZZLES)

# ===== Клавіатура (ОНОВЛЕНО) =====
def get_keyboard(state: str = "start"):
    """Створює динамічну клавіатуру залежно від стану."""
    if state == "puzzle_sent":
        # Кнопки після відправки задачі
        keyboard = [
            [InlineKeyboardButton("💡 Показати розв'язок", callback_data="show_solution")],
            [InlineKeyboardButton("♟️ Нова задача", callback_data="new_puzzle")]
        ]
    else:
        # Початкова клавіатура або після розв'язку
        keyboard = [
            [InlineKeyboardButton("♟️ Отримати задачу", callback_data="new_puzzle")]
        ]
    return InlineKeyboardMarkup(keyboard)

# ===== Команди бота =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я шаховий бот 🤖♟\n"
        "Натисни кнопку, щоб отримати свою першу задачу:",
        reply_markup=get_keyboard(state="start")
    )

# ===== Обробка кнопок (ПОВНІСТЮ ПЕРЕПИСАНО) =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data

    if action == "new_puzzle":
        puzzle = get_random_puzzle()
        if not puzzle:
            await query.edit_message_text(
                text="⚠️ Не вдалося завантажити задачі. Спробуйте пізніше.",
                reply_markup=get_keyboard(state="start")
            )
            return
        
        # Зберігаємо поточну задачу для користувача
        context.user_data['current_puzzle'] = puzzle
        
        msg = f"♟️ **{puzzle.get('title', 'Задача')}**\n{puzzle.get('url', '')}"
        await query.edit_message_text(
            text=msg,
            reply_markup=get_keyboard(state="puzzle_sent"),
            parse_mode='Markdown' # Використовуємо Markdown для жирного шрифту
        )

    elif action == "show_solution":
        puzzle = context.user_data.get('current_puzzle')
        if not puzzle:
            await query.edit_message_text(
                text="Будь ласка, спершу отримайте задачу.",
                reply_markup=get_keyboard(state="start")
            )
            return

        solution = puzzle.get('solution', 'Розв\'язок не знайдено.')
        msg = (
            f"♟️ **{puzzle.get('title', 'Задача')}**\n{puzzle.get('url', '')}\n\n"
            f"💡 **Розв'язок:** {solution}"
        )
        await query.edit_message_text(
            text=msg,
            reply_markup=get_keyboard(state="start"),
            parse_mode='Markdown'
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
    
    # Використовуємо `persistence` для збереження `user_data`
    from telegram.ext import PicklePersistence
    persistence = PicklePersistence(filepath="bot_data")
    
    PTB_APP = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    
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

