from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import date

app = FastAPI()

# База данных (SQLite — нормально для старта)
engine = create_engine("sqlite:///database.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------- МОДЕЛИ ----------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)
    date = Column(String)
    exchange = Column(String)
    buy = Column(Float)
    sell = Column(Float)
    volume = Column(Float)
    start_sum = Column(Float)
    profit_usd = Column(Float)

Base.metadata.create_all(engine)

# ---------- ВСПОМОГАТЕЛЬНОЕ ----------

def get_db():
    return SessionLocal()

def get_or_create_user(db, telegram_id: int):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
    return user

# ---------- API ----------

@app.post("/trade")
def add_trade(telegram_id: int, trade_data: dict):
    db = get_db()
    get_or_create_user(db, telegram_id)

    trade = Trade(
        telegram_id=telegram_id,
        date=trade_data["date"],
        exchange=trade_data["exchange"],
        buy=trade_data["buy"],
        sell=trade_data["sell"],
        volume=trade_data["volume"],
        start_sum=trade_data["start_sum"],
        profit_usd=trade_data["profit_usd"]
    )

    db.add(trade)
    db.commit()
    return {"status": "ok"}

@app.get("/trades")
def get_trades(telegram_id: int, period: str = "all"):
    db = get_db()
    query = db.query(Trade).filter(Trade.telegram_id == telegram_id)

    if period == "today":
        today = date.today().isoformat()
        query = query.filter(Trade.date == today)

    trades = query.all()

    return {
        "trades": [
            {
                "date": t.date,
                "exchange": t.exchange,
                "buy": t.buy,
                "sell": t.sell,
                "volume": t.volume,
                "start_sum": t.start_sum,
                "profit_usd": t.profit_usd
            } for t in trades
        ]
    }

@app.get("/profit")
def get_profit(telegram_id: int):
    db = get_db()
    trades = db.query(Trade).filter(Trade.telegram_id == telegram_id).all()
    total = sum(t.profit_usd for t in trades)
    return {"profit_usd": round(total, 2)}
