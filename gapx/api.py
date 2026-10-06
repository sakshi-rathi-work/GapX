import asyncio
from contextlib import asynccontextmanager
import json
import logging
from typing import Dict, Optional, Set
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from gapx.state_store import StateStore, OrderBookSnapshot
from gapx.ingestion.binance_client import BinanceWSClient
from gapx.ingestion.coinbase_client import CoinbaseWSClient
from gapx.ingestion.kraken_client import KrakenWSClient
from gapx.detection import ArbitrageEngine, ArbitrageOpportunity
from gapx.db import (
    init_db,
    save_opportunities_batch,
    query_opportunities,
    query_analytics_summary,
    query_spread_history,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gapx.api")

state_store = StateStore()
TRACKED_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

binance_client = BinanceWSClient(TRACKED_SYMBOLS, state_store)
coinbase_client = CoinbaseWSClient(TRACKED_SYMBOLS, state_store)
kraken_client = KrakenWSClient(TRACKED_SYMBOLS, state_store)

detection_engine = ArbitrageEngine(
    state_store=state_store,
    assumed_trade_size_usd=500.0,
    min_net_spread_pct=0.20,
    max_data_age_ms=2000.0,
)

class ConnectionManager:
    """Manages live WebSocket connections to dashboard UI clients."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        to_remove = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                to_remove.add(connection)
        for dead in to_remove:
            self.active_connections.discard(dead)

ws_manager = ConnectionManager()

async def background_scanner_loop():
    """Background task scanning shared state for arbitrage opportunities every 300ms."""
    logger.info("Starting background arbitrage scanner loop (interval 300ms)...")
    while True:
        try:
            opps = await detection_engine.scan_once()
            if opps:
                await save_opportunities_batch(opps)
                for opp in opps:
                    await ws_manager.broadcast({
                        "type": "opportunity",
                        "data": opp.__dict__
                    })

            snapshots = await state_store.get_all_snapshots()
            live_prices = {}
            for (ex, sym), snap in snapshots.items():
                if sym not in live_prices:
                    live_prices[sym] = {}
                live_prices[sym][ex] = {
                    "best_bid": snap.best_bid,
                    "best_ask": snap.best_ask,
                    "best_bid_qty": snap.best_bid_qty,
                    "best_ask_qty": snap.best_ask_qty,
                    "updated_at_ms": snap.received_timestamp_ms,
                }
            
            if live_prices:
                await ws_manager.broadcast({
                    "type": "ticker",
                    "data": live_prices
                })

        except Exception as e:
            logger.error(f"Error in scanner loop: {e}", exc_info=True)

        await asyncio.sleep(0.3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLite database...")
    await init_db()

    logger.info("Starting exchange WebSocket ingestion clients...")
    await binance_client.start()
    await coinbase_client.start()
    await kraken_client.start()

    scanner_task = asyncio.create_task(background_scanner_loop())

    yield

    logger.info("Shutting down scanner and WebSocket clients...")
    scanner_task.cancel()
    await binance_client.stop()
    await coinbase_client.stop()
    await kraken_client.stop()

app = FastAPI(
    title="GapX API",
    description="GapX - Real-Time Crypto Arbitrage Scanner API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/prices/live")
async def get_live_prices():
    snapshots = await state_store.get_all_snapshots()
    result: Dict[str, Dict[str, dict]] = {}
    for (ex, sym), snap in snapshots.items():
        if sym not in result:
            result[sym] = {}
        result[sym][ex] = {
            "best_bid": snap.best_bid,
            "best_ask": snap.best_ask,
            "best_bid_qty": snap.best_bid_qty,
            "best_ask_qty": snap.best_ask_qty,
            "received_timestamp_ms": snap.received_timestamp_ms,
        }
    return result

@app.get("/orderbook/live")
async def get_live_orderbook(
    exchange: str = Query(..., description="binance, coinbase, or kraken"),
    symbol: str = Query(..., description="e.g. BTC/USDT"),
):
    snap = await state_store.get_order_book(exchange, symbol)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Orderbook not found for {exchange} {symbol}")

    return {
        "exchange": snap.exchange,
        "symbol": snap.symbol,
        "bids": snap.bids[:10],
        "asks": snap.asks[:10],
        "received_timestamp_ms": snap.received_timestamp_ms,
    }

@app.get("/opportunities")
async def get_opportunities_endpoint(
    symbol: Optional[str] = None,
    actionable_only: bool = False,
    min_spread: Optional[float] = None,
    since: Optional[str] = None,
    limit: int = 100,
):
    return await query_opportunities(
        symbol=symbol,
        actionable_only=actionable_only,
        min_spread=min_spread,
        since=since,
        limit=limit,
    )

@app.get("/analytics/summary")
async def get_analytics_summary_endpoint(range: str = Query("24h")):
    try:
        hours = float(range.replace("h", ""))
    except ValueError:
        hours = 24.0

    return await query_analytics_summary(time_range_hours=hours)

@app.get("/analytics/spread-history")
async def get_spread_history_endpoint(
    symbol: str = Query("BTC/USDT"),
    range: str = Query("24h")
):
    try:
        hours = float(range.replace("h", ""))
    except ValueError:
        hours = 24.0

    return await query_spread_history(symbol=symbol, time_range_hours=hours)

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
