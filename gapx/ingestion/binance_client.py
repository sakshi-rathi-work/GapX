import json
import logging
import time
from typing import Dict, List
from gapx.ingestion.base_client import BaseWSClient
from gapx.state_store import StateStore, OrderBookSnapshot

logger = logging.getLogger(__name__)

BINANCE_SYMBOL_MAP: Dict[str, str] = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
}

CANONICAL_TO_BINANCE: Dict[str, str] = {v: k.lower() for k, v in BINANCE_SYMBOL_MAP.items()}

class BinanceWSClient(BaseWSClient):
    def __init__(self, symbols: List[str], state_store: StateStore):
        self.canonical_symbols = symbols
        streams = [f"{CANONICAL_TO_BINANCE[s]}@depth20@100ms" for s in symbols if s in CANONICAL_TO_BINANCE]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        super().__init__(exchange_name="binance", ws_url=ws_url, state_store=state_store)

    def get_subscription_payload(self) -> dict | str | None:
        return None

    async def handle_message(self, raw_message: str | bytes) -> None:
        data = json.loads(raw_message)
        if "data" not in data:
            return

        payload = data["data"]
        stream_name = data.get("stream", "")
        binance_symbol = stream_name.split("@")[0].upper()
        canonical_symbol = BINANCE_SYMBOL_MAP.get(binance_symbol)

        if not canonical_symbol:
            return

        bids = [(float(p), float(q)) for p, q in payload.get("bids", [])]
        asks = [(float(p), float(q)) for p, q in payload.get("asks", [])]

        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        snapshot = OrderBookSnapshot(
            exchange="binance",
            symbol=canonical_symbol,
            bids=bids,
            asks=asks,
            exchange_timestamp_ms=payload.get("E") or (time.time() * 1000),
            received_timestamp_ms=time.time() * 1000,
        )

        await self.state_store.set_order_book(snapshot)
