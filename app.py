from flask import Flask
import requests
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
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        fen = data['puzzle']['fen']
        solution = ' -> '.join(data['puzzle']['solution'])
        puzzle_url = f"https://lichess.org/training/{data['puzzle']['id']}"
        return f"♟️ Щоденна шахова задача\n\nFEN: {fen}\nХіди розв’язку: {solution}\nПосилання: {puzzle_url}"
    else:
        return "Помилка отримання задачі."

# ====== Ендпоінт для розсилки ======
@app.route("/send-puzzle")
def send_puzzle():
    message = get_puzzle()
    bot.send_message(chat_id=CHAT_ID, text=message)
    return "Задача відправлена ✅"

# ====== Запуск веб-сервісу ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))