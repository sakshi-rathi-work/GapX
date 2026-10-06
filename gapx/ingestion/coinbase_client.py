import json
import logging
import time
from typing import Dict, List
from gapx.ingestion.base_client import BaseWSClient
from gapx.state_store import StateStore, OrderBookSnapshot

logger = logging.getLogger(__name__)

COINBASE_SYMBOL_MAP: Dict[str, str] = {
    "BTC-USD": "BTC/USDT",
    "BTC-USDT": "BTC/USDT",
    "ETH-USD": "ETH/USDT",
    "ETH-USDT": "ETH/USDT",
    "SOL-USD": "SOL/USDT",
    "SOL-USDT": "SOL/USDT",
}

CANONICAL_TO_COINBASE: Dict[str, str] = {
    "BTC/USDT": "BTC-USD",
    "ETH/USDT": "ETH-USD",
    "SOL/USDT": "SOL-USD",
}

class CoinbaseWSClient(BaseWSClient):
    def __init__(self, symbols: List[str], state_store: StateStore):
        self.canonical_symbols = symbols
        self.product_ids = [CANONICAL_TO_COINBASE[s] for s in symbols if s in CANONICAL_TO_COINBASE]
        
        self._books: Dict[str, Dict[str, Dict[float, float]]] = {
            pid: {"bids": {}, "asks": {}} for pid in self.product_ids
        }
        
        ws_url = "wss://ws-feed.exchange.coinbase.com"
        super().__init__(exchange_name="coinbase", ws_url=ws_url, state_store=state_store)

    def get_subscription_payload(self) -> dict | str | None:
        return {
            "type": "subscribe",
            "product_ids": self.product_ids,
            "channels": ["level2_batch"],
        }

    async def handle_message(self, raw_message: str | bytes) -> None:
        data = json.loads(raw_message)
        msg_type = data.get("type")

        if msg_type == "snapshot":
            product_id = data.get("product_id")
            if not product_id or product_id not in self._books:
                return

            book = self._books[product_id]
            book["bids"].clear()
            book["asks"].clear()

            for p_str, q_str in data.get("bids", []):
                p, q = float(p_str), float(q_str)
                if q > 0:
                    book["bids"][p] = q

            for p_str, q_str in data.get("asks", []):
                p, q = float(p_str), float(q_str)
                if q > 0:
                    book["asks"][p] = q

            await self._publish_snapshot(product_id)

        elif msg_type == "l2update":
            product_id = data.get("product_id")
            if not product_id or product_id not in self._books:
                return

            book = self._books[product_id]
            changes = data.get("changes", [])

            for side, p_str, q_str in changes:
                price, qty = float(p_str), float(q_str)
                target_dict = book["bids"] if side == "buy" else book["asks"]
                if qty == 0:
                    target_dict.pop(price, None)
                else:
                    target_dict[price] = qty

            await self._publish_snapshot(product_id)

    async def _publish_snapshot(self, product_id: str) -> None:
        canonical_symbol = COINBASE_SYMBOL_MAP.get(product_id)
        if not canonical_symbol:
            return

        book = self._books[product_id]
        
        sorted_bids = sorted(book["bids"].items(), key=lambda x: x[0], reverse=True)[:20]
        sorted_asks = sorted(book["asks"].items(), key=lambda x: x[0])[:20]

        snapshot = OrderBookSnapshot(
            exchange="coinbase",
            symbol=canonical_symbol,
            bids=sorted_bids,
            asks=sorted_asks,
            exchange_timestamp_ms=time.time() * 1000,
            received_timestamp_ms=time.time() * 1000,
        )

        await self.state_store.set_order_book(snapshot)
