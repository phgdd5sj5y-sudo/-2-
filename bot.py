from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import date, timedelta
import asyncio

from config import BOT_TOKEN
from db import engine, users, deals
from sqlalchemy import insert, select, func

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====== ВСПОМОГАТЕЛЬНО ======

def has_access(sub_until):
    return sub_until and sub_until >= date.today()

# ====== START ======

@dp.message(Command("start"))
async def start(msg: types.Message):
    with engine.connect() as conn:
        user = conn.execute(
            select(users).where(users.c.tg_id == msg.from_user.id)
        ).fetchone()

        if not user:
            conn.execute(
                insert(users).values(
                    tg_id=msg.from_user.id,
                    sub_until=date.today()
                )
            )

    await msg.answer(
        "🤖 P2P Бот\n\n"
        "Команды:\n"
        "/add — добавить сделку\n"
        "/stats — статистика\n"
        "/day — прибыль за день\n\n"
        "🔒 Для работы нужна подписка"
    )

# ====== ДОБАВЛЕНИЕ СДЕЛКИ ======

@dp.message(Command("add"))
async def add_deal(msg: types.Message):
    await msg.answer(
        "Введите данные через пробел:\n\n"
        "Биржа ЦенаПокупки ЦенаПродажи Начало₽ Расходы₽\n\n"
        "Пример:\n"
        "Binance 98.5 100.2 100000 500"
    )

@dp.message()
async def save_deal(msg: types.Message):
    parts = msg.text.split()
    if len(parts) != 5:
        return

    exchange, buy, sell, start_rub, expenses = parts

    buy = float(buy)
    sell = float(sell)
    start_rub = float(start_rub)
    expenses = float(expenses)

    spread = (sell - buy) / buy
    profit = start_rub * spread - expenses

    with engine.connect() as conn:
        conn.execute(
            insert(deals).values(
                tg_id=msg.from_user.id,
                date=date.today(),
                exchange=exchange,
                buy_price=buy,
                sell_price=sell,
                start_rub=start_rub,
                expenses=expenses,
                spread=spread,
                profit=profit
            )
        )

    await msg.answer(
        f"✅ Сделка сохранена\n\n"
        f"📈 Спред: {spread*100:.2f}%\n"
        f"💰 Прибыль: {profit:.2f} ₽"
    )

# ====== СТАТИСТИКА ======

@dp.message(Command("stats"))
async def stats(msg: types.Message):
    with engine.connect() as conn:
        total_profit = conn.execute(
            select(func.sum(deals.c.profit))
            .where(deals.c.tg_id == msg.from_user.id)
        ).scalar() or 0

        avg_spread = conn.execute(
            select(func.avg(deals.c.spread))
            .where(deals.c.tg_id == msg.from_user.id)
        ).scalar() or 0

        count = conn.execute(
            select(func.count())
            .where(deals.c.tg_id == msg.from_user.id)
        ).scalar()

        loss = conn.execute(
            select(func.count())
            .where(deals.c.tg_id == msg.from_user.id, deals.c.profit < 0)
        ).scalar()

    await msg.answer(
        f"📊 Статистика\n\n"
        f"💰 Общая прибыль: {total_profit:.2f} ₽\n"
        f"📈 Средний спред: {avg_spread*100:.2f}%\n"
        f"🔁 Сделок: {count}\n"
        f"❌ Убыточных: {loss}"
    )

# ====== ПРИБЫЛЬ ЗА ДЕНЬ ======

@dp.message(Command("day"))
async def day_profit(msg: types.Message):
    today = date.today()

    with engine.connect() as conn:
        profit = conn.execute(
            select(func.sum(deals.c.profit))
            .where(deals.c.tg_id == msg.from_user.id, deals.c.date == today)
        ).scalar() or 0

    await msg.answer(
        f"📅 Сегодня ({today})\n"
        f"💰 Прибыль: {profit:.2f} ₽"
    )

# ====== ЗАПУСК ======

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
