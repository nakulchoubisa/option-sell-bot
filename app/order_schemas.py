# app/order_schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class OrderCreate(BaseModel):
    position_id: int
    symbol: str
    side: str = Field(..., examples=["BUY", "SELL"])
    qty: int = Field(..., ge=1)
    price: float = Field(..., ge=0)
    status: str = "FILLED"

class OrderOut(BaseModel):
    id: int
    position_id: int
    symbol: str
    side: str
    qty: int
    price: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
