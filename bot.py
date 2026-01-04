import json
from datetime import date
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# ----------------------------
# Файл для хранения статистики
# ----------------------------
FILE = "stats.json"

# ----------------------------
# Работа со статистикой
# ----------------------------
def load_stats() -> dict:
    """Загрузить статистику из файла"""
    if not os.path.exists(FILE):
        return {}
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}
    except Exception as e:
        print("Ошибка при загрузке stats.json:", e)
        return {}

def save_stats(data: dict):
    """Сохранить статистику в файл"""
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка при сохранении stats.json:", e)

def add_profit(amount: float):
    """Добавить прибыль за сегодня"""
    today = date.today().isoformat()
    data = load_stats()
    if today not in data:
        data[today] = 0.0
    data[today] += amount
    save_stats(data)
    print(f"[DEBUG] Добавлено {amount} ₽. Сегодня всего: {data[today]} ₽")

def get_today_profit() -> float:
    """Получить прибыль за сегодня"""
    today = date.today().isoformat()
    data = load_stats()
    return data.get(today, 0.0)

# ----------------------------
# Настройка бота
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ----------------------------
# Обработчики команд
# ----------------------------
@dp.message(Command(commands=["start"]))
async def start(message: Message):
    await message.reply(
        "Бот запущен!\n"
        "Команды:\n"
        "/add <сумма> — добавить прибыль\n"
        "/profit — показать прибыль за сегодня\n"
        "/stats — показать полную статистику"
    )

@dp.message(Command(commands=["add"]))
async def add(message: Message):
    try:
        amount = float(message.text.split()[1])
        add_profit(amount)
        await message.reply(f"Добавлено {amount} ₽ к прибыли за сегодня.")
    except (IndexError, ValueError):
        await message.reply("Использование: /add <сумма> (например: /add 100)")

@dp.message(Command(commands=["profit"]))
async def profit(message: Message):
    today_profit = get_today_profit()
    if today_profit == 0:
        await message.reply("❌ Нет сделок за сегодня.")
    else:
        await message.reply(f"Прибыль за сегодня: {today_profit} ₽")

@dp.message(Command(commands=["stats"]))
async def stats(message: Message):
    data = load_stats()
    if not data:
        await message.reply("📂 Статистика пустая, сделок нет.")
        return
    text = "📊 Статистика по датам:\n"
    for d, p in sorted(data.items()):
        text += f"{d}: {p} ₽\n"
    await message.reply(text)

# ----------------------------
# Запуск бота
# ----------------------------
async def main():
    print("Бот запущен...")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
