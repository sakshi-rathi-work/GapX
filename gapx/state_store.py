from dataclasses import dataclass, field
import asyncio
import time
from typing import Dict, List, Tuple, Optional

@dataclass
class OrderBookSnapshot:
    exchange: str                  # "binance", "coinbase", "kraken"
    symbol: str                    # Canonical symbol: "BTC/USDT", "ETH/USDT", "SOL/USDT"
    bids: List[Tuple[float, float]]    # [(price, qty), ...] sorted highest price first
    asks: List[Tuple[float, float]]    # [(price, qty), ...] sorted lowest price first
    exchange_timestamp_ms: Optional[float] = None
    received_timestamp_ms: float = field(default_factory=lambda: time.time() * 1000)

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0][0] if self.asks else None

    @property
    def best_bid_qty(self) -> Optional[float]:
        return self.bids[0][1] if self.bids else None

    @property
    def best_ask_qty(self) -> Optional[float]:
        return self.asks[0][1] if self.asks else None


class StateStore:
    """Simple in-memory store for latest order book per (exchange, symbol), guarded by asyncio.Lock."""
    def __init__(self):
        self._store: Dict[Tuple[str, str], OrderBookSnapshot] = {}
        self._lock = asyncio.Lock()

    async def set_order_book(self, snapshot: OrderBookSnapshot) -> None:
        async with self._lock:
            key = (snapshot.exchange.lower(), snapshot.symbol.upper())
            self._store[key] = snapshot

    async def get_order_book(self, exchange: str, symbol: str) -> Optional[OrderBookSnapshot]:
        async with self._lock:
            return self._store.get((exchange.lower(), symbol.upper()))

    async def get_all_snapshots(self) -> Dict[Tuple[str, str], OrderBookSnapshot]:
        async with self._lock:
            return dict(self._store)

    async def get_symbols(self) -> set[str]:
        async with self._lock:
            return {symbol for _, symbol in self._store.keys()}
