# app/brokers/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class Broker(ABC):
    @abstractmethod
    def ltp(self, symbol: str) -> float:
        """Return last traded price for a symbol."""
        raise NotImplementedError

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,          # "BUY" or "SELL"
        qty: int,
        order_type: str = "MARKET",  # "MARKET" or "LIMIT"
        price: Optional[float] = None,
        product: str = "MIS",
        variety: str = "regular",
    ) -> Dict[str, Any]:
        """Place an order; return broker order id/details."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        raise NotImplementedError
