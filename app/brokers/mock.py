from datetime import datetime

class MockBroker:
    def __init__(self):
        self.orders = []
        self.positions = []

    def ltp(self, symbol: str) -> float:
        # Always return a dummy price
        return 100.0

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

        # Also track as a position
        pos = {
            "id": len(self.positions) + 1,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "avg_price": price or 100.0,
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
