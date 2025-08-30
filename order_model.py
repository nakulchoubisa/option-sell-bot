# app/order_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)         # BUY / SELL
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String, default="FILLED")     # FILLED / CANCELED / REJECTED / PENDING
    created_at = Column(DateTime, default=datetime.utcnow)

# (Optional) backref on Position — add in app/model.py:
# from sqlalchemy.orm import relationship
# orders = relationship("Order", cascade="all, delete-orphan", backref="position")
