import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import date
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")  # мы добавим позже

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- FSM ----------
class TradeFSM(StatesGroup):
    exchange = State()
    buy = State()
    sell = State()
    volume = State()
    start_sum = State()

# ---------- КНОПКИ ----------
def main_kb():
    kb = [
        [types.InlineKeyboardButton(text="➕ Добавить сделку", callback_data="add")],
        [types.InlineKeyboardButton(text="📜 История", callback_data="history")],
        [types.InlineKeyboardButton(text="💰 Прибыль", callback_data="profit")],
        [types.InlineKeyboardButton(text="🌐 Открыть кабинет", callback_data="web")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

# ---------- START ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    telegram_id = msg.from_user.id
    profit = 0
    try:
        r = requests.get(f"{API_URL}/profit", params={"telegram_id": telegram_id})
        profit = r.json().get("profit_usd", 0)
    except:
        pass

    await msg.answer(
        f"Привет, поработаем сегодня?\n"
        f"Твоя прибыль за всё время: {profit} $\n\n"
        f"Выбери действие:",
        reply_markup=main_kb()
    )

# ---------- ДОБАВИТЬ СДЕЛКУ ----------
@dp.callback_query(lambda c: c.data == "add")
async def add_trade(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите биржу:")
    await state.set_state(TradeFSM.exchange)

@dp.message(TradeFSM.exchange)
async def trade_exchange(msg: types.Message, state: FSMContext):
    await state.update_data(exchange=msg.text)
    await msg.answer("Введите курс покупки:")
    await state.set_state(TradeFSM.buy)

@dp.message(TradeFSM.buy)
async def trade_buy(msg: types.Message, state: FSMContext):
    try:
        buy = float(msg.text.replace(",", "."))
    except:
        await msg.answer("Введите число")
        return
    await state.update_data(buy=buy)
    await msg.answer("Введите курс продажи:")
    await state.set_state(TradeFSM.sell)

@dp.message(TradeFSM.sell)
async def trade_sell(msg: types.Message, state: FSMContext):
    try:
        sell = float(msg.text.replace(",", "."))
    except:
        await msg.answer("Введите число")
        return
    await state.update_data(sell=sell)
    await msg.answer("Введите объём:")
    await state.set_state(TradeFSM.volume)

@dp.message(TradeFSM.volume)
async def trade_volume(msg: types.Message, state: FSMContext):
    try:
        volume = float(msg.text.replace(",", "."))
    except:
        await msg.answer("Введите число")
        return
    await state.update_data(volume=volume)
    await msg.answer("Введите начальную сумму:")
    await state.set_state(TradeFSM.start_sum)

@dp.message(TradeFSM.start_sum)
async def trade_finish(msg: types.Message, state: FSMContext):
    try:
        start_sum = float(msg.text.replace(",", "."))
    except:
        await msg.answer("Введите число")
        return

    data = await state.get_data()
    profit = (data["sell"] - data["buy"]) * data["volume"]

    payload = {
        "date": date.today().isoformat(),
        "exchange": data["exchange"],
        "buy": data["buy"],
        "sell": data["sell"],
        "volume": data["volume"],
        "start_sum": start_sum,
        "profit_usd": profit
    }

    requests.post(
        f"{API_URL}/trade",
        params={"telegram_id": msg.from_user.id},
        json={"trade_data": payload}
    )

    await msg.answer(
        f"Сделка сохранена ✅\n"
        f"Прибыль: {round(profit, 2)} $",
        reply_markup=main_kb()
    )

    await state.clear()

# ---------- ПРИБЫЛЬ ----------
@dp.callback_query(lambda c: c.data == "profit")
async def profit(cb: types.CallbackQuery):
    r = requests.get(f"{API_URL}/profit", params={"telegram_id": cb.from_user.id})
    profit = r.json().get("profit_usd", 0)
    await cb.message.answer(f"Твоя прибыль: {profit} $", reply_markup=main_kb())

# ---------- ИСТОРИЯ ----------
@dp.callback_query(lambda c: c.data == "history")
async def history(cb: types.CallbackQuery):
    r = requests.get(f"{API_URL}/trades", params={"telegram_id": cb.from_user.id})
    trades = r.json().get("trades", [])

    if not trades:
        await cb.message.answer("Сделок нет")
        return

    text = "История сделок:\n"
    for t in trades:
        text += f"{t['date']} | {t['exchange']} | {round(t['profit_usd'],2)} $\n"

    await cb.message.answer(text, reply_markup=main_kb())

# ---------- ВЕБ ----------
@dp.callback_query(lambda c: c.data == "web")
async def web(cb: types.CallbackQuery):
    url = f"{API_URL.replace('/','')}/web?uid={cb.from_user.id}"
    await cb.message.answer(f"Твой кабинет:\n{url}")

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
