from datetime import datetime

class PaperBroker:
    def __init__(self, session_factory, pricer=None):
        self.session_factory = session_factory
        self.pricer = pricer
        self.orders = []
        self.positions = []

    def ltp(self, symbol: str) -> float:
        if self.pricer:
            return self.pricer.ltp(symbol)
        return 100.0  # fallback dummy price

    def place_order(self, symbol: str, side: str, qty: int, order_type: str = "MARKET",
                    price: float = None, product: str = "MIS", variety: str = "regular",
                    position_id: int = None):
        order = {
            "id": len(self.orders) + 1,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": order_type,
            "price": price,
            "product": product,
            "variety": variety,
            "position_id": position_id,
            "status": "FILLED",
            "created_at": datetime.utcnow().isoformat()
        }
        self.orders.append(order)

        pos = {
            "id": len(self.positions) + 1,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "avg_price": price or self.ltp(symbol),
            "status": "OPEN",
            "opened_at": datetime.utcnow().isoformat(),
            "close_price": None,
            "ltp": self.ltp(symbol),
            "unrealised": 0.0,
        }
        self.positions.append(pos)
        return order

    def cancel_order(self, order_id: int):
        for o in self.orders:
            if o["id"] == order_id:
                o["status"] = "CANCELLED"
                return o
        return {"error": "Order not found"}
