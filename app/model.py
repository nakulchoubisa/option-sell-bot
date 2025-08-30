# app/model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)                 # "BUY" / "SELL"
    qty = Column(Integer, nullable=False, default=0)
    avg_price = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="OPEN")  # "OPEN" / "CLOSED"
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

