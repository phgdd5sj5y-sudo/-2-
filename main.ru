import json
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import os

# --- СТАТИСТИКА ---
FILE = "stats.json"

def load_stats():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_stats(data):
    with open(FILE, "w") as f:
        json.dump(data, f)

def add_profit(amount: float):
    today = date.today().isoformat()
    data = load_stats()
    if today not in data:
        data[today] = 0
    data[today] += amount
    save_stats(data)

def get_today_profit():
    today = date.today().isoformat()
    data = load_stats()
    return data.get(today, 0)

# --- БОТ ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    await message.reply("Бот запущен. Прибыль / статистика работает.")

@dp.message(Command("add"))
async def add(message: Message):
    # Пример: /add 100
    try:
        amount = float(message.text.split()[1])
        add_profit(amount)
        await message.reply(f"Добавлено {amount} к прибыли за сегодня.")
    except:
        await message.reply("Использование: /add <сумма>")

@dp.message(Command("profit"))
async def profit(message: Message):
    profit_val = get_today_profit()
    await message.reply(f"Прибыль за сегодня: {profit_val} ₽")

@dp.message(Command("stats"))
async def stats(message: Message):
    data = load_stats()
    text = "Статистика по датам:\n"
    for d, p in data.items():
        text += f"{d}: {p} ₽\n"
    await message.reply(text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
