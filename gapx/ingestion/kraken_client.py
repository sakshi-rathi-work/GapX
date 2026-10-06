import json
import logging
import time
from typing import Dict, List
from gapx.ingestion.base_client import BaseWSClient
from gapx.state_store import StateStore, OrderBookSnapshot

logger = logging.getLogger(__name__)

KRAKEN_SYMBOL_MAP: Dict[str, str] = {
    "XBT/USD": "BTC/USDT",
    "BTC/USD": "BTC/USDT",
    "XBT/USDT": "BTC/USDT",
    "BTC/USDT": "BTC/USDT",
    "ETH/USD": "ETH/USDT",
    "XETH/ZUSD": "ETH/USDT",
    "ETH/USDT": "ETH/USDT",
    "SOL/USD": "SOL/USDT",
    "SOL/USDT": "SOL/USDT",
}

CANONICAL_TO_KRAKEN: Dict[str, str] = {
    "BTC/USDT": "XBT/USD",
    "ETH/USDT": "ETH/USD",
    "SOL/USDT": "SOL/USD",
}

class KrakenWSClient(BaseWSClient):
    def __init__(self, symbols: List[str], state_store: StateStore):
        self.canonical_symbols = symbols
        self.kraken_pairs = [CANONICAL_TO_KRAKEN[s] for s in symbols if s in CANONICAL_TO_KRAKEN]
        
        self._books: Dict[str, Dict[str, Dict[float, float]]] = {
            pair: {"bids": {}, "asks": {}} for pair in self.kraken_pairs
        }

        ws_url = "wss://ws.kraken.com"
        super().__init__(exchange_name="kraken", ws_url=ws_url, state_store=state_store)

    def get_subscription_payload(self) -> dict | str | None:
        return {
            "event": "subscribe",
            "pair": self.kraken_pairs,
            "subscription": {
                "name": "book",
                "depth": 10
            }
        }

    async def handle_message(self, raw_message: str | bytes) -> None:
        data = json.loads(raw_message)

        if isinstance(data, dict):
            return

        if isinstance(data, list) and len(data) >= 4:
            payload_data = data[1]
            pair_name = data[-1]

            canonical_symbol = KRAKEN_SYMBOL_MAP.get(pair_name)
            if not canonical_symbol:
                for k_pair, c_sym in KRAKEN_SYMBOL_MAP.items():
                    if k_pair in pair_name or pair_name in k_pair:
                        canonical_symbol = c_sym
                        break
                if not canonical_symbol:
                    return

            book = self._books.get(pair_name)
            if book is None:
                book = {"bids": {}, "asks": {}}
                self._books[pair_name] = book

            if "bs" in payload_data or "as" in payload_data:
                book["bids"].clear()
                book["asks"].clear()
                for p_str, q_str, *_ in payload_data.get("bs", []):
                    p, q = float(p_str), float(q_str)
                    if q > 0:
                        book["bids"][p] = q
                for p_str, q_str, *_ in payload_data.get("as", []):
                    p, q = float(p_str), float(q_str)
                    if q > 0:
                        book["asks"][p] = q

            if "b" in payload_data:
                for entry in payload_data["b"]:
                    p, q = float(entry[0]), float(entry[1])
                    if q == 0:
                        book["bids"].pop(p, None)
                    else:
                        book["bids"][p] = q

            if "a" in payload_data:
                for entry in payload_data["a"]:
                    p, q = float(entry[0]), float(entry[1])
                    if q == 0:
                        book["asks"].pop(p, None)
                    else:
                        book["asks"][p] = q

            sorted_bids = sorted(book["bids"].items(), key=lambda x: x[0], reverse=True)[:10]
            sorted_asks = sorted(book["asks"].items(), key=lambda x: x[0])[:10]

            snapshot = OrderBookSnapshot(
                exchange="kraken",
                symbol=canonical_symbol,
                bids=sorted_bids,
                asks=sorted_asks,
                exchange_timestamp_ms=time.time() * 1000,
                received_timestamp_ms=time.time() * 1000,
            )

            await self.state_store.set_order_book(snapshot)
