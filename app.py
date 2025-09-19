import os
import logging
import asyncio
import aiohttp
import random
import json
import re

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

# ===== Глобальна змінна для програми =====
PTB_APP = None

# ===== Завантаження задач =====
async def load_puzzles() -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PUZZLES_URL) as resp:
                resp.raise_for_status()
                text = await resp.text()
                data = json.loads(text)
                if isinstance(data, list):
                    logger.info(f"Завантажено {len(data)} задач")
                    return data
                else:
                    logger.error("JSON має неправильну структуру.")
                    return []
    except Exception as e:
        logger.error(f"Помилка при завантаженні puzzles.json: {e}")
        return []

# ===== Функція для екранування MarkdownV2 =====
def escape_markdown_v2(text: str) -> str:
    """Екранує спеціальні символи для Telegram MarkdownV2."""
    escape_chars = r"[_*\[\]()~`>#\+\-=|{}.!]"
    return re.sub(f'({escape_chars})', r'\\\1', text)

# ===== Клавіатура =====
def get_keyboard(state: str = "start", puzzle_index: int = None):
    if state == "puzzle_sent":
        keyboard = [
            [InlineKeyboardButton("💡 Показати розв'язок", callback_data=f"sol_{puzzle_index}")],
            [InlineKeyboardButton("♟️ Нова задача", callback_data="new_puzzle")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("♟️ Отримати задачу", callback_data="new_puzzle")]
        ]
    return InlineKeyboardMarkup(keyboard)

# ===== Команди бота =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        escape_markdown_v2("Привіт! Я шаховий бот 🤖♟\nНатисни кнопку, щоб отримати свою першу задачу:"),
        reply_markup=get_keyboard(state="start"),
        parse_mode='MarkdownV2'
    )

# ===== Обробка кнопок =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    puzzles_list = context.bot_data.get('puzzles', [])

    if action == "new_puzzle":
        if not puzzles_list:
            await query.edit_message_text(
                text=escape_markdown_v2("⚠️ Не вдалося завантажити задачі. Спробуйте пізніше."),
                reply_markup=get_keyboard(state="start"),
                parse_mode='MarkdownV2'
            )
            return
        
        puzzle_index, puzzle = random.choice(list(enumerate(puzzles_list)))
        
        title = escape_markdown_v2(puzzle.get('title', 'Задача'))
        url = escape_markdown_v2(puzzle.get('url', ''))
        msg = f"♟️ *{title}*\n{url}"
        
        await query.edit_message_text(
            text=msg, 
            reply_markup=get_keyboard(state="puzzle_sent", puzzle_index=puzzle_index), 
            parse_mode='MarkdownV2'
        )

    elif action.startswith("sol_"):
        try:
            puzzle_index = int(action.split("_")[1])
            puzzle = puzzles_list[puzzle_index]
            
            title = escape_markdown_v2(puzzle.get('title', 'Задача'))
            url = escape_markdown_v2(puzzle.get('url', ''))
            solution = escape_markdown_v2(puzzle.get('solution', 'Розв\'язок не знайдено.'))
            msg = f"♟️ *{title}*\n{url}\n\n💡 *Розв'язок:* {solution}"
            await query.edit_message_text(
                text=msg, 
                reply_markup=get_keyboard(state="start"), 
                parse_mode='MarkdownV2'
            )
        except (IndexError, ValueError):
            await query.edit_message_text(
                text=escape_markdown_v2("⚠️ Помилка: не вдалося знайти цю задачу. Будь ласка, отримайте нову."),
                reply_markup=get_keyboard(state="start"),
                parse_mode='MarkdownV2'
            )

# =======================
# Webhook
# =======================
@app.route("/webhook", methods=["POST"])
async def webhook():
    if PTB_APP:
        try:
            update_data = request.get_json()
            update = Update.de_json(update_data, PTB_APP.bot)
            await PTB_APP.process_update(update)
            return '', 200
        except Exception as e:
            logger.error(f"Помилка при обробці оновлення: {e}")
            return 'Error processing update', 500
    return 'Bot not initialized', 500

@app.route("/", methods=["GET"])
def index():
    return "Шаховий бот працює через Webhook!", 200

# =======================
# Основна функція для налаштування
# =======================
async def setup_bot():
    global PTB_APP
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не знайдений!")
        return

    PTB_APP = Application.builder().token(BOT_TOKEN).build()
    
    puzzles_data = await load_puzzles()
    PTB_APP.bot_data['puzzles'] = puzzles_data
    
    await PTB_APP.initialize()
    
    PTB_APP.add_handler(CommandHandler("start", start_command))
    PTB_APP.add_handler(CallbackQueryHandler(button_handler))

    # ВИПРАВЛЕНО: Використовуємо нову змінну PUBLIC_URL в першу чергу
    webhook_url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RAILWAY_STATIC_URL")
    
    if webhook_url:
        full_webhook_url = f"{webhook_url}/webhook"
        logger.info(f"Встановлюю вебхук на: {full_webhook_url}")
        try:
            await PTB_APP.bot.set_webhook(full_webhook_url, drop_pending_updates=True)
            logger.info(f"Вебхук успішно встановлено на {full_webhook_url}")
        except Exception as e:
            logger.error(f"НЕ вдалося встановити вебхук: {e}")
    else:
        logger.warning("URL для вебхука не знайдений.")

# =======================
# ЗАПУСК
# =======================
if __name__ == "__main__":
    asyncio.run(setup_bot())
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
else:
    asyncio.run(setup_bot())

