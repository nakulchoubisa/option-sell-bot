# app/brokers/zerodha.py
from typing import Optional, Dict, Any
from .base import Broker

class ZerodhaBroker(Broker):
    def __init__(self, api_key: str, api_secret: str, access_token: str):
        try:
            from kiteconnect import KiteConnect  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "kiteconnect not installed. Add 'kiteconnect' to requirements.txt and rebuild."
            ) from e

        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        # NOTE: You need to generate and supply a valid ACCESS_TOKEN separately.

    def ltp(self, symbol: str) -> float:
        """
        symbol example for NSE options: 'NFO:NIFTY24AUG25000CE'
        for equities: 'NSE:INFY'
        """
        data = self.kite.ltp([symbol])
        last_price = list(data.values())[0]["last_price"]
        return float(last_price)

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        product: str = "MIS",
        variety: str = "regular",
    ) -> Dict[str, Any]:
        transaction_type = "BUY" if side.upper() == "BUY" else "SELL"
        exchange, tradingsymbol = symbol.split(":", 1) if ":" in symbol else ("NFO", symbol)

        order_args = dict(
            variety=variety,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=qty,
            product=product,
            order_type=order_type.upper(),
        )
        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("LIMIT order requires price")
            order_args["price"] = price

        resp = self.kite.place_order(**order_args)  # returns dict with order_id
        return {"order_id": resp["order_id"], "status": "PLACED", **order_args}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        self.kite.cancel_order(variety="regular", order_id=order_id)
        return {"ok": True, "order_id": order_id, "status": "CANCELED"}
