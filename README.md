# Telegram Chess Puzzle Bot (Lichess) для Render.com

Цей бот надсилає щоденні шахові задачі з Lichess у Telegram.

## Як запустити на Render.com

1. Клонувати репозиторій.
2. Створити **Web Service** на Render з Python 3.11.
3. Встановити `requirements.txt`.
4. Порт виставляється автоматично через Render (`PORT`).
5. Деплой.

## Розсилка двічі на день

На Render створюємо два **Scheduled Jobs**:
- GET `https://your-app.onrender.com/send-puzzle` о 08:00
- GET `https://your-app.onrender.com/send-puzzle` о 20:00

Готово! Бот автоматично надсилає задачі.