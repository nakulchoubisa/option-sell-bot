from __future__ import annotations
from datetime import datetime
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, Body, Path
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import SessionLocal, init_db
from app.model import Position
from app.order_model import Order
from app.config import BROKER, KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN
from app.brokers.mock import MockBroker
from app.brokers.paper import PaperBroker
from app.brokers.zerodha_data import ZerodhaData
from app.pnl import compute_today_pnl
from app.brokers.zerodha_data import ZerodhaData
from fastapi.responses import RedirectResponse
try:
    from kiteconnect import KiteConnect
except Exception:
    KiteConnect = None

# ---------- FastAPI ----------
app = FastAPI(title="Option Selling Bot API")

# ---------- API Key ----------
API_KEY = "supersecret123"
def require_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ---------- DB ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Broker ----------
broker = None
@app.on_event("startup")
async def on_startup():
    global broker
    init_db()
    price_source = os.getenv("PRICE_SOURCE", "mock").lower()

    if BROKER == "paper":
        pricer = ZerodhaData(api_key=KITE_API_KEY, access_token=KITE_ACCESS_TOKEN) if price_source == "zerodha" else None
        broker = PaperBroker(SessionLocal, pricer=pricer)
    elif BROKER == "zerodha":
        from app.brokers.zerodha import ZerodhaBroker
        broker = ZerodhaBroker(api_key=KITE_API_KEY, api_secret=KITE_API_SECRET, access_token=KITE_ACCESS_TOKEN)
    else:
        broker = MockBroker()

    print(f"DB initialized, broker={BROKER}, price_source={price_source}")

# ---------- Health ----------
# ---------- Health / Root ----------
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui")

# ---------- Broker Endpoints ----------
@app.get("/broker/mode")
def broker_mode(ok: bool = Depends(require_key)):
    return {"broker": BROKER}

@app.get("/broker/ltp")
def broker_ltp(symbol: str = Query(...), ok: bool = Depends(require_key)):
    try:
        return {"symbol": symbol, "ltp": broker.ltp(symbol)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LTP error: {e}")

class OrderIn(BaseModel):
    symbol: str
    side: str
    qty: int
    order_type: str = "MARKET"
    price: Optional[float] = None
    product: str = "MIS"
    variety: str = "regular"
    position_id: Optional[int] = None

@app.post("/broker/order")
def broker_place_order(payload: OrderIn, ok: bool = Depends(require_key), db: Session = Depends(get_db)):
    # Step 1: Place through broker
    resp = broker.place_order(
        symbol=payload.symbol,
        side=payload.side,
        qty=payload.qty,
        order_type=payload.order_type,
        price=payload.price,
        product=payload.product,
        variety=payload.variety,
    )

    # Step 2: Handle DB position
    pos = (
        db.query(Position)
        .filter(Position.symbol == payload.symbol, Position.status == "OPEN")
        .first()
    )

    if pos is None:
        pos = Position(
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            avg_price=payload.price or 0.0,
            status="OPEN",
            opened_at=datetime.utcnow(),
        )
        db.add(pos)
        db.commit()
        db.refresh(pos)
    else:
        total_qty = pos.qty + payload.qty
        if total_qty > 0:
            pos.avg_price = ((pos.avg_price * pos.qty) + (payload.price or 0.0) * payload.qty) / total_qty
        pos.qty = total_qty
        db.commit()
        db.refresh(pos)

    # Step 3: Record order
    order = Order(
        position_id=pos.id,
        symbol=payload.symbol,
        side=payload.side,
        qty=payload.qty,
        price=payload.price or 0.0,
        status="FILLED",
        created_at=datetime.utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {"broker_response": resp, "position": pos.id, "order": order.id}

@app.post("/broker/positions/{pos_id}/close")
def close_position(pos_id: int, ok: bool = Depends(require_key), db: Session = Depends(get_db)):
    pos = db.get(Position, pos_id)
    if not pos or pos.status == "CLOSED":
        raise HTTPException(status_code=404, detail="Position not found or already closed")

    try:
        ltp = broker.ltp(pos.symbol)
    except Exception:
        ltp = pos.avg_price  # fallback

    # Reverse side (BUY->SELL, SELL->BUY)
    reverse_side = "SELL" if pos.side == "BUY" else "BUY"

    # Create exit order
    exit_order = Order(
        position_id=pos.id,
        symbol=pos.symbol,
        side=reverse_side,
        qty=pos.qty,
        price=ltp,
        status="FILLED",
        created_at=datetime.utcnow(),
    )
    db.add(exit_order)

    # Mark position closed
    pos.status = "CLOSED"
    pos.close_price = ltp
    pos.closed_at = datetime.utcnow()

    # Save realised P&L at close
    if pos.side == "BUY":
        realised = (ltp - pos.avg_price) * pos.qty
    else:
        realised = (pos.avg_price - ltp) * pos.qty
    pos.realised = realised

    db.commit()
    db.refresh(pos)

    return {
        "id": pos.id,
        "symbol": pos.symbol,
        "side": pos.side,
        "qty": pos.qty,
        "avg_price": pos.avg_price,
        "close_price": pos.close_price,
        "realised": pos.realised,
        "status": pos.status,
        "closed_at": pos.closed_at.isoformat(),
        "exit_order_id": exit_order.id,
    }

@app.get("/broker/positions")
def broker_positions(ok: bool = Depends(require_key)):
    with SessionLocal() as db:
        return [p.__dict__ for p in db.query(Position).all()]

@app.get("/broker/orders")
def broker_orders(ok: bool = Depends(require_key)):
    with SessionLocal() as db:
        return [o.__dict__ for o in db.query(Order).all()]

@app.get("/broker/pnl")
def broker_pnl(ok: bool = Depends(require_key)):
    def ltp_fn(sym: str) -> float:
        return broker.ltp(sym)
    with SessionLocal() as db:
        return compute_today_pnl(db, ltp_fn)

@app.post("/broker/pricer")
def set_pricer(source: str = Body(embed=True), ok: bool = Depends(require_key)):
    global broker
    s = source.strip().lower()
    if s == "zerodha":
        broker.pricer = ZerodhaData(api_key=KITE_API_KEY, access_token=KITE_ACCESS_TOKEN)
    elif s == "mock":
        broker.pricer = MockBroker()
    else:
        raise HTTPException(status_code=400, detail="source must be 'zerodha' or 'mock'")
    return {"ok": True, "source": s}

# ---------- Kite Auth ----------
@app.get("/kite/login", response_class=HTMLResponse)
def kite_login():
    api_key = os.getenv("KITE_API_KEY", "")
    if not api_key:
        return HTMLResponse("<h3>Set KITE_API_KEY in env first.</h3>", status_code=500)
    url = f"https://kite.trade/connect/login?v=3&api_key={api_key}"
    return HTMLResponse(f"<a href='{url}' target='_blank'>Login</a>")

@app.get("/kite/callback")
def kite_callback(request: Request):
    if KiteConnect is None:
        return JSONResponse({"error": "kiteconnect not installed"}, status_code=500)

    api_key = os.getenv("KITE_API_KEY", "")
    api_secret = os.getenv("KITE_API_SECRET", "")
    rt = request.query_params.get("request_token")
    if not (api_key and api_secret and rt):
        return {"error": "Missing params"}

    kite = KiteConnect(api_key=api_key)
    try:
        data = kite.generate_session(rt, api_secret=api_secret)
        access_token = data["access_token"]

        env_path = os.path.join(os.getcwd(), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("KITE_ACCESS_TOKEN="):
                        lines.append(f"KITE_ACCESS_TOKEN={access_token}\n")
                    else:
                        lines.append(line)
        else:
            lines.append(f"KITE_ACCESS_TOKEN={access_token}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)

        return {"message": "Access token saved to .env. Restart docker to apply.", "access_token": access_token}
    except Exception as e:
        return {"error": str(e)}
# ---------- Instruments Sync ----------
@app.post("/broker/instruments/sync")
def sync_instruments(ok: bool = Depends(require_key)):
    pricer = getattr(broker, "pricer", None)
    if not isinstance(pricer, ZerodhaData):
        raise HTTPException(status_code=400, detail="Zerodha pricer not configured. Switch pricer to 'zerodha' first.")
    try:
        count = pricer.sync_instruments()
        return {"message": f"Synced {count} instruments"}
    except Exception as e:
        import traceback
        print("Error in sync_instruments:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")



@app.get("/broker/instruments")
def get_instruments(ok: bool = Depends(require_key)):
    if not hasattr(broker, "pricer") or not broker.pricer:
        raise HTTPException(status_code=400, detail="No pricer available")
    try:
        instruments = broker.pricer.get_instruments()
        return instruments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching instruments: {e}")


@app.get("/broker/options/{underlying}")
def get_options(underlying: str, ok: bool = Depends(require_key)):
    if not isinstance(broker.pricer, ZerodhaData):
        raise HTTPException(400, "Pricer is not ZerodhaData")
    return broker.pricer.option_chain(underlying)

@app.get("/broker/options/{symbol}")
def get_options(symbol: str, ok: bool = Depends(require_key)):
    pricer = getattr(broker, "pricer", None)
    if not isinstance(pricer, ZerodhaData):
        raise HTTPException(status_code=400, detail="Zerodha pricer not configured. Switch pricer to 'zerodha' first.")

    try:
        df = pricer.load_instruments()
        df = df[df["name"] == symbol.upper()]  # Filter only symbol contracts (e.g., NIFTY)
        options = df.to_dict(orient="records")
        return {"count": len(options), "options": options}
    except Exception as e:
        import traceback
        print("Error in /broker/options:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Options fetch failed: {str(e)}")


# ---------- UI ----------
@app.get("/ui", response_class=HTMLResponse, tags=["ui"])
def ui_home():
    return FileResponse("app/templates/ui_index.html")
