import json
import os
import asyncio
import requests
from datetime import date, datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE = "trades.json"

# ================== BYBIT P2P ==================
def get_usdt_rub_bybit():
    url = "https://api2.bybit.com/fiat/otc/item/online"
    payload = {
        "tokenId": "USDT",
        "currencyId": "RUB",
        "side": "SELL",
        "page": "1",
        "size": "10",
        "payment": []
    }

    try:
        r = requests.post(url, json=payload, timeout=5)
        data = r.json()
        prices = [float(i["price"]) for i in data["result"]["items"][:5]]
        return round(sum(prices) / len(prices), 2)
    except:
        return 0

# ================== ХРАНЕНИЕ ==================
def load_data():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_trade(user_id, trade):
    data = load_data()
    data.setdefault(user_id, []).append(trade)
    save_data(data)

# ================== FSM ==================
class TradeFSM(StatesGroup):
    currency = State()
    trade_date = State()
    trade_type = State()
    exchange = State()
    buy = State()
    sell = State()
    volume = State()
    start_sum = State()

# ================== БОТ ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== START ==================
@dp.message(Command("start"))
async def start(msg: Message):
    data = load_data().get(str(msg.from_user.id), [])
    total_profit = sum(t["profit_usd"] for t in data)
    rate = get_usdt_rub_bybit()

    await msg.reply(
        "👋 P2P Арбитраж Бот\n\n"
        f"Сделок: {len(data)}\n"
        f"Общая прибыль: {round(total_profit,2)} $ ({round(total_profit*rate,2)} ₽)\n\n"
        "Команды:\n"
        "/newtrade — новая сделка\n"
        "/history — история\n"
        "/profit — прибыль"
    )

# ================== NEW TRADE ==================
@dp.message(Command("newtrade"))
async def newtrade(msg: Message, state: FSMContext):
    await msg.reply("Выбери валюту расчёта: USD или RUB")
    await state.set_state(TradeFSM.currency)

@dp.message(TradeFSM.currency)
async def currency(msg: Message, state: FSMContext):
    cur = msg.text.upper()
    if cur not in ("USD", "RUB"):
        return await msg.reply("Напиши USD или RUB")
    await state.update_data(currency=cur)
    await msg.reply("Дата сделки? (сегодня или 01.01.2001)")
    await state.set_state(TradeFSM.trade_date)

@dp.message(TradeFSM.trade_date)
async def trade_date(msg: Message, state: FSMContext):
    if msg.text.lower() == "сегодня":
        d = date.today().isoformat()
    else:
        try:
            d = datetime.strptime(msg.text, "%d.%m.%Y").date().isoformat()
        except:
            return await msg.reply("Формат даты: 01.01.2001")
    await state.update_data(date=d)
    await msg.reply("Тип сделки: Биржа / Межбиржевой")
    await state.set_state(TradeFSM.trade_type)

@dp.message(TradeFSM.trade_type)
async def trade_type(msg: Message, state: FSMContext):
    await state.update_data(type=msg.text)
    await msg.reply("Биржа:")
    await state.set_state(TradeFSM.exchange)

@dp.message(TradeFSM.exchange)
async def exchange(msg: Message, state: FSMContext):
    await state.update_data(exchange=msg.text)
    await msg.reply("Курс покупки:")
    await state.set_state(TradeFSM.buy)

@dp.message(TradeFSM.buy)
async def buy(msg: Message, state: FSMContext):
    await state.update_data(buy=float(msg.text))
    await msg.reply("Курс продажи:")
    await state.set_state(TradeFSM.sell)

@dp.message(TradeFSM.sell)
async def sell(msg: Message, state: FSMContext):
    await state.update_data(sell=float(msg.text))
    await msg.reply("Объём валюты:")
    await state.set_state(TradeFSM.volume)

@dp.message(TradeFSM.volume)
async def volume(msg: Message, state: FSMContext):
    await state.update_data(volume=float(msg.text))
    await msg.reply("Начальная сумма:")
    await state.set_state(TradeFSM.start_sum)

@dp.message(TradeFSM.start_sum)
async def finish(msg: Message, state: FSMContext):
    data = await state.get_data()
    start_sum = float(msg.text)

    spread = (data["sell"] - data["buy"]) / data["buy"] * 100
    profit_usd = (data["sell"] - data["buy"]) * data["volume"]

    rate = get_usdt_rub_bybit()
    profit_rub = profit_usd * rate

    trade = {
        **data,
        "start_sum": start_sum,
        "spread": round(spread, 2),
        "profit_usd": round(profit_usd, 2),
        "profit_rub": round(profit_rub, 2)
    }

    add_trade(str(msg.from_user.id), trade)
    await state.clear()

    await msg.reply(
        "✅ Сделка сохранена\n\n"
        f"Спред: {trade['spread']} %\n"
        f"Прибыль: {trade['profit_usd']} $ ({trade['profit_rub']} ₽)\n"
        f"Курс USDT/RUB (Bybit): {rate}"
    )

# ================== HISTORY ==================
@dp.message(Command("history"))
async def history(msg: Message):
    data = load_data().get(str(msg.from_user.id), [])
    if not data:
        return await msg.reply("❌ Сделок нет")

    text = "📜 История сделок:\n\n"
    for t in data:
        text += (
            f"{t['date']} | {t['exchange']}\n"
            f"Спред: {t['spread']} %\n"
            f"Профит: {t['profit_usd']} $ ({t['profit_rub']} ₽)\n\n"
        )
    await msg.reply(text)

# ================== PROFIT ==================
@dp.message(Command("profit"))
async def profit(msg: Message):
    data = load_data().get(str(msg.from_user.id), [])
    if not data:
        return await msg.reply("❌ Нет сделок")

    today = date.today().isoformat()
    rate = get_usdt_rub_bybit()

    day_profit = sum(t["profit_usd"] for t in data if t["date"] == today)
    total_profit = sum(t["profit_usd"] for t in data)

    await msg.reply(
        "📊 Прибыль\n\n"
        f"За сегодня: {round(day_profit,2)} $ ({round(day_profit*rate,2)} ₽)\n"
        f"За всё время: {round(total_profit,2)} $ ({round(total_profit*rate,2)} ₽)\n\n"
        f"Курс Bybit: {rate}"
    )

# ================== RUN ==================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
