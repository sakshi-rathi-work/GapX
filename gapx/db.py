import aiosqlite
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any, Dict, List, Optional
from gapx.detection import ArbitrageOpportunity

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gapx.db"))

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    sell_exchange TEXT NOT NULL,
    top_of_book_buy_price REAL NOT NULL,
    top_of_book_sell_price REAL NOT NULL,
    gross_spread_pct REAL NOT NULL,
    fee_adjusted_spread_pct REAL NOT NULL,
    assumed_trade_size_usd REAL NOT NULL,
    liquidity_adjusted_net_spread_pct REAL NOT NULL,
    detection_latency_ms INTEGER NOT NULL,
    underlying_data_age_ms INTEGER NOT NULL,
    is_actionable INTEGER NOT NULL,
    detected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_opp_symbol_detected ON opportunities(symbol, detected_at);
CREATE INDEX IF NOT EXISTS idx_opp_actionable ON opportunities(is_actionable);
"""

async def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create SQLite database and opportunities table if they don't exist."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
    logger.info(f"Database initialized at {db_path}")

async def save_opportunity(opp: ArbitrageOpportunity, db_path: str = DEFAULT_DB_PATH) -> int:
    """Insert a single detected opportunity into SQLite."""
    sql = """
    INSERT INTO opportunities (
        symbol, buy_exchange, sell_exchange,
        top_of_book_buy_price, top_of_book_sell_price,
        gross_spread_pct, fee_adjusted_spread_pct,
        assumed_trade_size_usd, liquidity_adjusted_net_spread_pct,
        detection_latency_ms, underlying_data_age_ms,
        is_actionable, detected_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        opp.symbol, opp.buy_exchange, opp.sell_exchange,
        opp.top_of_book_buy_price, opp.top_of_book_sell_price,
        opp.gross_spread_pct, opp.fee_adjusted_spread_pct,
        opp.assumed_trade_size_usd, opp.liquidity_adjusted_net_spread_pct,
        int(opp.detection_latency_ms), int(opp.underlying_data_age_ms),
        1 if opp.is_actionable else 0, opp.detected_at,
    )

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(sql, params)
        await db.commit()
        return cursor.lastrowid or 0

async def save_opportunities_batch(opps: List[ArbitrageOpportunity], db_path: str = DEFAULT_DB_PATH) -> int:
    """Bulk insert list of detected opportunities into SQLite."""
    if not opps:
        return 0

    sql = """
    INSERT INTO opportunities (
        symbol, buy_exchange, sell_exchange,
        top_of_book_buy_price, top_of_book_sell_price,
        gross_spread_pct, fee_adjusted_spread_pct,
        assumed_trade_size_usd, liquidity_adjusted_net_spread_pct,
        detection_latency_ms, underlying_data_age_ms,
        is_actionable, detected_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params_list = [
        (
            opp.symbol, opp.buy_exchange, opp.sell_exchange,
            opp.top_of_book_buy_price, opp.top_of_book_sell_price,
            opp.gross_spread_pct, opp.fee_adjusted_spread_pct,
            opp.assumed_trade_size_usd, opp.liquidity_adjusted_net_spread_pct,
            int(opp.detection_latency_ms), int(opp.underlying_data_age_ms),
            1 if opp.is_actionable else 0, opp.detected_at,
        )
        for opp in opps
    ]

    async with aiosqlite.connect(db_path) as db:
        await db.executemany(sql, params_list)
        await db.commit()
        return len(opps)

async def query_opportunities(
    symbol: Optional[str] = None,
    actionable_only: bool = False,
    min_spread: Optional[float] = None,
    since: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Query historical opportunities from SQLite."""
    conditions = []
    params = []

    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol.upper())

    if actionable_only:
        conditions.append("is_actionable = 1")

    if min_spread is not None:
        conditions.append("liquidity_adjusted_net_spread_pct >= ?")
        params.append(min_spread)

    if since:
        conditions.append("detected_at >= ?")
        params.append(since)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
    SELECT id, symbol, buy_exchange, sell_exchange,
           top_of_book_buy_price, top_of_book_sell_price,
           gross_spread_pct, fee_adjusted_spread_pct,
           assumed_trade_size_usd, liquidity_adjusted_net_spread_pct,
           detection_latency_ms, underlying_data_age_ms,
           is_actionable, detected_at
    FROM opportunities
    {where_clause}
    ORDER BY detected_at DESC
    LIMIT ?
    """
    params.append(limit)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def query_analytics_summary(
    time_range_hours: float = 24.0,
    db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Compute aggregate analytics stats over given time range."""
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
    cutoff_iso = cutoff_dt.isoformat()

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        count_sql = """
        SELECT COUNT(*) as total_count,
               SUM(CASE WHEN is_actionable = 1 THEN 1 ELSE 0 END) as actionable_count,
               AVG(liquidity_adjusted_net_spread_pct) as avg_net_spread,
               MAX(liquidity_adjusted_net_spread_pct) as max_net_spread
        FROM opportunities
        WHERE detected_at >= ?
        """
        async with db.execute(count_sql, (cutoff_iso,)) as cursor:
            summary_row = await cursor.fetchone()

        pair_sql = """
        SELECT buy_exchange || ' -> ' || sell_exchange as pair,
               COUNT(*) as count
        FROM opportunities
        WHERE detected_at >= ? AND is_actionable = 1
        GROUP BY pair
        ORDER BY count DESC
        LIMIT 1
        """
        async with db.execute(pair_sql, (cutoff_iso,)) as cursor:
            pair_row = await cursor.fetchone()

        most_active_pair = pair_row["pair"] if pair_row else "N/A"

        return {
            "total_opportunities": summary_row["total_count"] if summary_row else 0,
            "actionable_opportunities": summary_row["actionable_count"] if summary_row and summary_row["actionable_count"] else 0,
            "avg_net_spread_pct": round(summary_row["avg_net_spread"] or 0.0, 4),
            "max_net_spread_pct": round(summary_row["max_net_spread"] or 0.0, 4),
            "most_active_exchange_pair": most_active_pair,
            "time_range_hours": time_range_hours
        }

async def query_spread_history(
    symbol: str,
    time_range_hours: float = 24.0,
    limit: int = 500,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Query time series of spread % for charting."""
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
    cutoff_iso = cutoff_dt.isoformat()

    sql = """
    SELECT detected_at, buy_exchange, sell_exchange,
           gross_spread_pct, fee_adjusted_spread_pct, liquidity_adjusted_net_spread_pct, is_actionable
    FROM opportunities
    WHERE symbol = ? AND detected_at >= ?
    ORDER BY detected_at ASC
    LIMIT ?
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, (symbol.upper(), cutoff_iso, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
