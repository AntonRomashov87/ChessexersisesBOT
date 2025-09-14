from flask import Flask
import requests
import asyncio
from telegram import Bot
import os

app = Flask(__name__)

# ====== Налаштування ======
TOKEN = "8092371216:AAF7bfwunLqI2ZrGBpE2goMaxXnol07vG0g"
CHAT_ID = "598331739"
bot = Bot(token=TOKEN)

# ====== Функція отримання шахової задачі ======
def get_puzzle():
    url = 'https://lichess.org/api/puzzle/daily'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            puzzle = data.get('puzzle')
            if puzzle and 'fen' in puzzle and 'solution' in puzzle and 'id' in puzzle:
                fen = puzzle['fen']
                solution = ' -> '.join(puzzle['solution'])
                puzzle_url = f"https://lichess.org/training/{puzzle['id']}"
                return f"♟️ Щоденна шахова задача\n\nFEN: {fen}\nХіди розв’язку: {solution}\nПосилання: {puzzle_url}"
            else:
                return "На жаль, сьогодні немає доступної шахової задачі."
        else:
            return f"Помилка отримання задачі: {response.status_code}"
    except Exception as e:
        return f"Помилка при зверненні до Lichess API: {e}"

# ====== Асинхронна функція відправки в Telegram ======
async def send_message_async(message):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"❌ Помилка при відправці в Telegram: {e}")

# ====== Головна сторінка ======
@app.route("/")
def home():
    return "Бот працює! Використовуйте /send-puzzle для отримання шахової задачі."

# ====== Ендпоінт для розсилки ======
@app.route("/send-puzzle")
def send_puzzle():
    message = get_puzzle()
    asyncio.run(send_message_async(message))
    return "Задача відправлена ✅ або повідомлення про помилку буде в логах."

# ====== Запуск веб-сервісу ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
