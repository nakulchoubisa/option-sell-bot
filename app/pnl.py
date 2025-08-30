from __future__ import annotations

# app/pnl.py
from zoneinfo import ZoneInfo
from datetime import datetime, date
from typing import Callable, Dict, Any, List

from sqlalchemy.orm import Session

from app.model import Position
from app.order_model import Order


IST = ZoneInfo("Asia/Kolkata")


# ---------- helpers ----------
def _avg(amount: float, qty: int) -> float:
    return (amount / qty) if qty else 0.0


def _to_ist(dts: datetime) -> datetime:
    """
    Normalize any datetime (naive or tz-aware) to IST.
    If naive, assume it's in UTC (typical for DB timestamps from server).
    """
    if dts.tzinfo is None:
        # assume UTC if naive
        return dts.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)
    return dts.astimezone(IST)


def _is_same_day_ist(dts: datetime | None, d: date) -> bool:
    if dts is None:
        return False
    return _to_ist(dts).date() == d


# ---------- core P&L ----------
def compute_position_pnl(
    db: Session,
    pos: Position,
    ltp_fn: Callable[[str], float],
) -> Dict[str, Any]:
    """
    Computes P&L snapshot for a single position using a simple average-price model.
    Convention:
      - net_qty = sells - buys  (positive => net short, negative => net long)
      - realized = matched_qty * (avg_sell - avg_buy)
      - MTM:
          if net short (net_qty > 0):  (avg_sell - LTP) * net_qty
          if net long  (net_qty < 0):  (LTP - avg_buy) * abs(net_qty)
    """
    orders: List[Order] = (
        db.query(Order)
        .filter(Order.position_id == pos.id)
        .all()
    )

    # Aggregate buys / sells (ignore cancelled/rejected)
    buy_qty = 0
    buy_amt = 0.0
    sell_qty = 0
    sell_amt = 0.0

    for o in orders:
        status = (o.status or "").upper()
        if status in {"CANCELLED", "REJECTED"}:
            continue
        if (o.side or "").upper() == "BUY":
            buy_qty += int(o.qty or 0)
            buy_amt += float(o.price or 0.0) * int(o.qty or 0)
        elif (o.side or "").upper() == "SELL":
            sell_qty += int(o.qty or 0)
            sell_amt += float(o.price or 0.0) * int(o.qty or 0)

    avg_buy = _avg(buy_amt, buy_qty)
    avg_sell = _avg(sell_amt, sell_qty)

    # Realized on the matched quantity
    matched_qty = min(buy_qty, sell_qty)
    realized = matched_qty * (avg_sell - avg_buy)

    # Net exposure (sells - buys); positive => net short
    net_qty = sell_qty - buy_qty

    # LTP for MTM
    ltp = float(ltp_fn(pos.symbol))

    if net_qty > 0:
        mtm = (avg_sell - ltp) * net_qty  # short
    elif net_qty < 0:
        mtm = (ltp - avg_buy) * abs(net_qty)  # long
    else:
        mtm = 0.0

    total_pnl = realized + mtm

    return {
        "position_id": pos.id,
        "symbol": pos.symbol,
        "status": pos.status,
        "net_qty": net_qty,
        "avg_buy": round(avg_buy, 4),
        "avg_sell": round(avg_sell, 4),
        "ltp": round(ltp, 4),
        "realized": round(realized, 2),
        "mtm": round(mtm, 2),
        "total_pnl": round(total_pnl, 2),
        "opened_at": pos.opened_at,
        "closed_at": pos.closed_at,
    }


def compute_today_pnl(
    db: Session,
    ltp_fn: Callable[[str], float],
) -> Dict[str, Any]:
    """
    Aggregates P&L for positions opened 'today' by IST calendar day.
    """
    today = datetime.now(IST).date()

    # You can change the inclusion rule if you want:
    # currently: positions with opened_at on today's IST date.
    all_positions: List[Position] = db.query(Position).all()
    todays_positions = [p for p in all_positions if _is_same_day_ist(p.opened_at, today)]

    per_position = [compute_position_pnl(db, p, ltp_fn) for p in todays_positions]

    realized_sum = round(sum(p["realized"] for p in per_position), 2)
    mtm_sum = round(sum(p["mtm"] for p in per_position), 2)
    total_sum = round(realized_sum + mtm_sum, 2)

    return {
        "day": str(today),
        "count_positions": len(per_position),
        "realized": realized_sum,
        "mtm": mtm_sum,
        "total_pnl": total_sum,
        "positions": per_position,
    }
