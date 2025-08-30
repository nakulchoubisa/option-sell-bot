# app/schemas.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class PositionBase(BaseModel):
    symbol: str = Field(..., examples=["NIFTY24AUG25000CE"])
    side: str = Field(..., examples=["BUY", "SELL"])
    qty: int = Field(..., ge=1, examples=[50])
    avg_price: float = Field(0.0, ge=0)

class PositionCreate(PositionBase):
    status: str = "OPEN"

class PositionUpdate(BaseModel):
    qty: Optional[int] = Field(None, ge=1)
    avg_price: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, examples=["OPEN", "CLOSED"])

class PositionOut(PositionBase):
    id: int
    status: str
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy -> Pydantic v2
