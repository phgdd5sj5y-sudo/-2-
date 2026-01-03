from sqlalchemy import *
from datetime import date

engine = create_engine("sqlite:///bot.db")
meta = MetaData()

users = Table(
    "users", meta,
    Column("id", Integer, primary_key=True),
    Column("tg_id", Integer, unique=True),
    Column("sub_until", Date),
)

deals = Table(
    "deals", meta,
    Column("id", Integer, primary_key=True),
    Column("tg_id", Integer),
    Column("date", Date),
    Column("exchange", String),
    Column("buy_price", Float),
    Column("sell_price", Float),
    Column("start_rub", Float),
    Column("expenses", Float),
    Column("spread", Float),
    Column("profit", Float),
)

meta.create_all(engine)
