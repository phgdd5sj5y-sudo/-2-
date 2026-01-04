import os, json, asyncio, requests
from datetime import date
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "trades.json"

# ===== BYBIT RATE =====
def get_usdt_rub():
    try:
        r = requests.post(
            "https://api2.bybit.com/fiat/otc/item/online",
            json={"tokenId":"USDT","currencyId":"RUB","side":"SELL","size":"5","page":"1"},
            timeout=5
        )
        prices = [float(i["price"]) for i in r.json()["result"]["items"]]
        return sum(prices) / len(prices)
    except:
        return 80

# ===== STORAGE =====
def load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ===== FSM =====
class TradeFSM(StatesGroup):
    exchange = State()
    buy = State()
    sell = State()
    volume = State()
    capital = State()

# ===== BOT =====
bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== KEYBOARDS =====
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить сделку", callback_data="add")],
        [InlineKeyboardButton(text="📜 История", callback_data="history")],
        [InlineKeyboardButton(text="💰 Прибыль", callback_data="profit")]
    ])

def period_kb(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data=f"{prefix}_today")],
        [InlineKeyboardButton(text="📆 За всё время", callback_data=f"{prefix}_all")]
    ])

# ===== START =====
@dp.message(Command("start"))
async def start(msg: Message):
    data = load().get(str(msg.from_user.id), [])
    total = sum(t["profit_usd"] for t in data)
    rate = get_usdt_rub()

    await msg.reply(
        f"Привет, поработаем сегодня?\n\n"
        f"Твоя прибыль за всё время:\n"
        f"{round(total,2)} $ ({round(total*rate,2)} ₽)\n\n"
        f"👇 Выбери действие",
        reply_markup=main_kb()
    )

# ===== ADD TRADE (BUTTON) =====
@dp.callback_query(F.data == "add")
async def add_trade(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Биржа?")
    await state.set_state(TradeFSM.exchange)
    await cb.answer()

@dp.message(TradeFSM.exchange)
async def exchange(msg: Message, state: FSMContext):
    await state.update_data(exchange=msg.text)
    await msg.answer("Курс покупки?")
    await state.set_state(TradeFSM.buy)

@dp.message(TradeFSM.buy)
async def buy(msg: Message, state: FSMContext):
    await state.update_data(buy=float(msg.text))
    await msg.answer("Курс продажи?")
    await state.set_state(TradeFSM.sell)

@dp.message(TradeFSM.sell)
async def sell(msg: Message, state: FSMContext):
    await state.update_data(sell=float(msg.text))
    await msg.answer("Оборот в USDT?")
    await state.set_state(TradeFSM.volume)

@dp.message(TradeFSM.volume)
async def volume(msg: Message, state: FSMContext):
    await state.update_data(volume=float(msg.text))
    await msg.answer("Начальная сумма? (пример: 1000 USD или 80000 RUB)")
    await state.set_state(TradeFSM.capital)

@dp.message(TradeFSM.capital)
async def finish(msg: Message, state: FSMContext):
    data = await state.get_data()
    value, currency = msg.text.split()
    value = float(value)
    currency = currency.upper()

    spread = (data["sell"] - data["buy"]) / data["buy"] * 100
    profit_usd = (data["sell"] - data["buy"]) * data["volume"]
    rate = get_usdt_rub()
    profit = profit_usd if currency == "USD" else profit_usd * rate

    trade = {
        "date": date.today().isoformat(),
        "exchange": data["exchange"],
        "profit_usd": profit_usd
    }

    db = load()
    db.setdefault(str(msg.from_user.id), []).append(trade)
    save(db)

    await state.clear()
    await msg.answer(
        f"✅ Сделка сохранена\n\n"
        f"Спред: {round(spread,2)} %\n"
        f"Чистая прибыль: {round(profit,2)} {currency}",
        reply_markup=main_kb()
    )

# ===== HISTORY =====
@dp.callback_query(F.data == "history")
async def history(cb: CallbackQuery):
    await cb.message.answer("История сделок:", reply_markup=period_kb("history"))
    await cb.answer()

@dp.callback_query(F.data.startswith("history_"))
async def history_show(cb: CallbackQuery):
    data = load().get(str(cb.from_user.id), [])
    if not data:
        return await cb.message.answer("Сделок нет")

    today = date.today().isoformat()
    if cb.data.endswith("today"):
        data = [t for t in data if t["date"] == today]

    text = "📜 История:\n\n"
    for t in data:
        text += f"{t['date']} | {round(t['profit_usd'],2)} $\n"

    await cb.message.answer(text, reply_markup=main_kb())
    await cb.answer()

# ===== PROFIT =====
@dp.callback_query(F.data == "profit")
async def profit(cb: CallbackQuery):
    await cb.message.answer("Прибыль:", reply_markup=period_kb("profit"))
    await cb.answer()

@dp.callback_query(F.data.startswith("profit_"))
async def profit_show(cb: CallbackQuery):
    data = load().get(str(cb.from_user.id), [])
    if not data:
        return await cb.message.answer("Сделок нет")

    today = date.today().isoformat()
    rate = get_usdt_rub()

    if cb.data.endswith("today"):
        usd = sum(t["profit_usd"] for t in data if t["date"] == today)
    else:
        usd = sum(t["profit_usd"] for t in data)

    await cb.message.answer(
        f"💰 Прибыль:\n\n"
        f"{round(usd,2)} $ ({round(usd*rate,2)} ₽)",
        reply_markup=main_kb()
    )
    await cb.answer()

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
