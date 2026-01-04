import json
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

FILE = "trades.json"

# ----------------------------
# FSM для пошагового ввода сделки
# ----------------------------
class TradeForm(StatesGroup):
    exchange = State()
    buy_rate = State()
    sell_rate = State()
    expenses = State()
    start_rub = State()

# ----------------------------
# Работа с памятью
# ----------------------------
def load_data() -> dict:
    if not os.path.exists(FILE):
        return {}
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data: dict):
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка при сохранении:", e)

def add_trade(user_id: str, exchange: str, buy_rate: float, sell_rate: float,
              expenses: float, start_rub: float):
    data = load_data()
    if user_id not in data:
        data[user_id] = []

    profit = (sell_rate - buy_rate) * start_rub / buy_rate - expenses
    spread = ((sell_rate - buy_rate) / buy_rate) * 100
    trade = {
        "Биржа": exchange,
        "Покупка": buy_rate,
        "Продажа": sell_rate,
        "Расходы": expenses,
        "Сумма ₽": start_rub,
        "Спред %": round(spread, 2),
        "Прибыль ₽": round(profit, 2)
    }
    data[user_id].append(trade)
    save_data(data)
    return trade

def get_user_summary(user_id: str):
    data = load_data()
    trades = data.get(user_id, [])
    total_profit = sum(t["Прибыль ₽"] for t in trades)
    total_loss = sum(-t["Прибыль ₽"] for t in trades if t["Прибыль ₽"] < 0)
    return total_profit, total_loss, trades

# ----------------------------
# Настройка бота
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не установлена!")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ----------------------------
# Команды
# ----------------------------
@dp.message(Command(commands=["start"]))
async def start(message: Message):
    user_id = str(message.from_user.id)
    total_profit, total_loss, _ = get_user_summary(user_id)
    await message.reply(
        f"Привет! 👋\n"
        f"Ваша текущая прибыль: {round(total_profit,2)} ₽\n"
        f"Ваши убытки: {round(total_loss,2)} ₽\n\n"
        "Чтобы добавить новую сделку, напишите /newtrade\n"
        "Посмотреть все сделки: /summary"
    )

# ----------------------------
# Пошаговый ввод сделки
# ----------------------------
@dp.message(Command(commands=["newtrade"]))
async def new_trade(message: Message, state: FSMContext):
    await message.reply("Введите биржу:")
    await state.set_state(TradeForm.exchange)

@dp.message(TradeForm.exchange)
async def trade_exchange(message: Message, state: FSMContext):
    await state.update_data(exchange=message.text)
    await message.reply("Введите курс покупки:")
    await state.set_state(TradeForm.buy_rate)

@dp.message(TradeForm.buy_rate)
async def trade_buy_rate(message: Message, state: FSMContext):
    try:
        buy_rate = float(message.text)
        await state.update_data(buy_rate=buy_rate)
        await message.reply("Введите курс продажи:")
        await state.set_state(TradeForm.sell_rate)
    except:
        await message.reply("Ошибка! Введите число для курса покупки.")

@dp.message(TradeForm.sell_rate)
async def trade_sell_rate(message: Message, state: FSMContext):
    try:
        sell_rate = float(message.text)
        await state.update_data(sell_rate=sell_rate)
        await message.reply("Введите расходы:")
        await state.set_state(TradeForm.expenses)
    except:
        await message.reply("Ошибка! Введите число для курса продажи.")

@dp.message(TradeForm.expenses)
async def trade_expenses(message: Message, state: FSMContext):
    try:
        expenses = float(message.text)
        await state.update_data(expenses=expenses)
        await message.reply("Введите начальную сумму в рублях:")
        await state.set_state(TradeForm.start_rub)
    except:
        await message.reply("Ошибка! Введите число для расходов.")

@dp.message(TradeForm.start_rub)
async def trade_start_rub(message: Message, state: FSMContext):
    try:
        start_rub = float(message.text)
        data = await state.get_data()
        trade = add_trade(
            user_id=str(message.from_user.id),
            exchange=data['exchange'],
            buy_rate=data['buy_rate'],
            sell_rate=data['sell_rate'],
            expenses=data['expenses'],
            start_rub=start_rub
        )
        await message.reply(
            f"Сделка добавлена ✅\n"
            f"Биржа: {trade['Биржа']}\n"
            f"Спред: {trade['Спред %']} %\n"
            f"Прибыль: {trade['Прибыль ₽']} ₽"
        )
        await state.clear()
    except:
        await message.reply("Ошибка! Введите число для начальной суммы.")

# ----------------------------
# Общая таблица пользователя
# ----------------------------
@dp.message(Command(commands=["summary"]))
async def summary(message: Message):
    user_id = str(message.from_user.id)
    total_profit, total_loss, trades = get_user_summary(user_id)
    if not trades:
        await message.reply("❌ Сделок пока нет.")
        return

    # Формируем таблицу
    header = f"{'№':<3}| {'Биржа':<10}| {'Покупка':<8}| {'Продажа':<8}| {'Расходы':<7}| {'Сумма ₽':<8}| {'Спред %':<8}| {'Прибыль ₽':<9}\n"
    separator = "-" * 80 + "\n"
    table = header + separator
    for i, t in enumerate(trades, 1):
        table += f"{i:<3}| {t['Биржа']:<10}| {t['Покупка']:<8}| {t['Продажа']:<8}| {t['Расходы']:<7}| {t['Сумма ₽']:<8}| {t['Спред %']:<8}| {t['Прибыль ₽']:<9}\n"

    table += f"\nИтоговая прибыль: {round(total_profit,2)} ₽\nИтоговые убытки: {round(total_loss,2)} ₽"
    await message.reply(f"<pre>{table}</pre>", parse_mode="HTML")

# ----------------------------
# Запуск бота
# ----------------------------
async def main():
    print("Бот запущен...")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
