from dataclasses import dataclass
from datetime import datetime, timezone
import itertools
import logging
import time
from typing import Dict, List, Tuple

from gapx.state_store import StateStore, OrderBookSnapshot

logger = logging.getLogger(__name__)

# Static exchange taker fee schedule
EXCHANGE_TAKER_FEES: Dict[str, float] = {
    "binance": 0.0010,   # 0.10%
    "coinbase": 0.0060,  # 0.60%
    "kraken": 0.0026,    # 0.26%
}

def get_taker_fee(exchange: str) -> float:
    return EXCHANGE_TAKER_FEES.get(exchange.lower(), 0.0025)


@dataclass
class FillResult:
    avg_price: float
    total_crypto: float
    total_usd: float
    fully_filled: bool


def estimate_buy_fill(asks: List[Tuple[float, float]], target_usd: float) -> FillResult:
    """Walk ask depth (lowest price first) until target USD notional is spent."""
    if not asks or target_usd <= 0:
        return FillResult(0.0, 0.0, 0.0, False)

    remaining_usd = target_usd
    spent_usd = 0.0
    total_crypto = 0.0

    for price, qty in asks:
        if remaining_usd <= 0:
            break
        level_max_usd = price * qty
        fill_usd = min(remaining_usd, level_max_usd)
        fill_crypto = fill_usd / price

        spent_usd += fill_usd
        total_crypto += fill_crypto
        remaining_usd -= fill_usd

    fully_filled = remaining_usd <= 1e-6
    avg_price = spent_usd / total_crypto if total_crypto > 0 else 0.0

    return FillResult(avg_price, total_crypto, spent_usd, fully_filled)


def estimate_sell_fill(bids: List[Tuple[float, float]], target_crypto: float) -> FillResult:
    """Walk bid depth (highest price first) until target crypto amount is sold."""
    if not bids or target_crypto <= 0:
        return FillResult(0.0, 0.0, 0.0, False)

    remaining_crypto = target_crypto
    sold_crypto = 0.0
    received_usd = 0.0

    for price, qty in bids:
        if remaining_crypto <= 0:
            break
        fill_crypto = min(remaining_crypto, qty)
        fill_usd = fill_crypto * price

        sold_crypto += fill_crypto
        received_usd += fill_usd
        remaining_crypto -= fill_crypto

    fully_filled = remaining_crypto <= 1e-6
    avg_price = received_usd / sold_crypto if sold_crypto > 0 else 0.0

    return FillResult(avg_price, sold_crypto, received_usd, fully_filled)


@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    top_of_book_buy_price: float
    top_of_book_sell_price: float
    gross_spread_pct: float
    fee_adjusted_spread_pct: float
    assumed_trade_size_usd: float
    liquidity_adjusted_net_spread_pct: float
    detection_latency_ms: float
    underlying_data_age_ms: float
    is_actionable: bool
    detected_at: str


class ArbitrageEngine:
    """Arbitrage detection engine comparing pairwise exchange order books."""
    def __init__(
        self,
        state_store: StateStore,
        assumed_trade_size_usd: float = 500.0,
        min_net_spread_pct: float = 0.20,
        max_data_age_ms: float = 2000.0,
    ):
        self.state_store = state_store
        self.assumed_trade_size_usd = assumed_trade_size_usd
        self.min_net_spread_pct = min_net_spread_pct
        self.max_data_age_ms = max_data_age_ms

    async def scan_once(self) -> List[ArbitrageOpportunity]:
        start_time = time.time()
        snapshots = await self.state_store.get_all_snapshots()
        symbols = await self.state_store.get_symbols()
        opportunities: List[ArbitrageOpportunity] = []
        now_ms = time.time() * 1000

        for symbol in symbols:
            ex_snaps: Dict[str, OrderBookSnapshot] = {}
            for (ex, sym), snap in snapshots.items():
                if sym == symbol and snap.best_bid is not None and snap.best_ask is not None:
                    ex_snaps[ex] = snap

            exchanges = list(ex_snaps.keys())
            if len(exchanges) < 2:
                continue

            for ex_buy, ex_sell in itertools.permutations(exchanges, 2):
                snap_buy = ex_snaps[ex_buy]
                snap_sell = ex_snaps[ex_sell]

                top_buy_price = snap_buy.best_ask
                top_sell_price = snap_sell.best_bid

                if top_buy_price is None or top_sell_price is None or top_buy_price <= 0:
                    continue

                # 1. Gross Spread %
                gross_spread_pct = ((top_sell_price - top_buy_price) / top_buy_price) * 100.0

                # 2. Fee Adjustment (top-of-book)
                buy_fee = get_taker_fee(ex_buy)
                sell_fee = get_taker_fee(ex_sell)

                effective_top_buy = top_buy_price * (1.0 + buy_fee)
                effective_top_sell = top_sell_price * (1.0 - sell_fee)
                fee_adjusted_spread_pct = ((effective_top_sell - effective_top_buy) / effective_top_buy) * 100.0

                # 3. Slippage & Liquidity Adjustment (depth walk)
                buy_fill = estimate_buy_fill(snap_buy.asks, self.assumed_trade_size_usd)
                sell_fill = estimate_sell_fill(snap_sell.bids, buy_fill.total_crypto)

                if buy_fill.total_crypto <= 0 or sell_fill.total_crypto <= 0:
                    continue

                effective_avg_buy = buy_fill.avg_price * (1.0 + buy_fee)
                effective_avg_sell = sell_fill.avg_price * (1.0 - sell_fee)
                liquidity_adjusted_net_spread_pct = ((effective_avg_sell - effective_avg_buy) / effective_avg_buy) * 100.0

                # 4. Latency & Data Age
                buy_age = now_ms - snap_buy.received_timestamp_ms
                sell_age = now_ms - snap_sell.received_timestamp_ms
                underlying_data_age_ms = max(buy_age, sell_age)
                detection_latency_ms = (time.time() - start_time) * 1000.0

                # 5. Actionability Determination
                is_actionable = (
                    liquidity_adjusted_net_spread_pct >= self.min_net_spread_pct
                    and underlying_data_age_ms <= self.max_data_age_ms
                    and buy_fill.fully_filled
                    and sell_fill.fully_filled
                )

                opportunities.append(
                    ArbitrageOpportunity(
                        symbol=symbol,
                        buy_exchange=ex_buy,
                        sell_exchange=ex_sell,
                        top_of_book_buy_price=top_buy_price,
                        top_of_book_sell_price=top_sell_price,
                        gross_spread_pct=round(gross_spread_pct, 4),
                        fee_adjusted_spread_pct=round(fee_adjusted_spread_pct, 4),
                        assumed_trade_size_usd=self.assumed_trade_size_usd,
                        liquidity_adjusted_net_spread_pct=round(liquidity_adjusted_net_spread_pct, 4),
                        detection_latency_ms=round(detection_latency_ms, 2),
                        underlying_data_age_ms=round(underlying_data_age_ms, 2),
                        is_actionable=is_actionable,
                        detected_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        return opportunities
