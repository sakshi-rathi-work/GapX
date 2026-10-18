# GapX ⚡ Real-Time Crypto Arbitrage Scanner & Analytics

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org/)

**GapX** is a high-performance, real-time cross-exchange cryptocurrency arbitrage detection and market monitoring engine. It maintains concurrent, persistent WebSocket connections to **Binance**, **Coinbase**, and **Kraken**, continuously ingesting Level-2 order book depth for major crypto pairs (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`).

Unlike naive scanners that evaluate top-of-book prices in isolation, GapX applies realistic trading domain logic: it performs **depth-walking order book simulation** for configurable trade sizes (e.g., $500 USD), factors in **exchange taker fees**, checks **underlying data staleness/latency**, and verifies total fillability before flagging an opportunity as genuinely **actionable**.

---

## 📌 Project Overview & Operating Philosophy

### 1. Pre-Funded Balances Model
GapX assumes pre-funded balances already exist across target exchanges. It does **not** model the "buy on Exchange A, initiate an on-chain blockchain transfer, sell on Exchange B" workflow. Because on-chain transfers take minutes (or longer) while cross-exchange price discrepancies typically resolve in seconds or sub-seconds, GapX isolates and solves the time-sensitive component: **instant detection and net spread calculation across pre-allocated exchange capital**.

### 2. Detection & Analytics Only (No Real-Money Orders)
The system strictly detects, logs, streams, and aggregates arbitrage opportunities for research, risk modeling, and latency analysis. It does **not** execute live financial transactions.

### 3. Empirical Production Run Results & Simulated Profit
Over continuous local monitoring spanning October 6–7, 2026 (~28 hours of runtime):
- **1,660,828+** total cross-exchange spreads scanned and evaluated.
- **8,485+** strictly **actionable** opportunities identified (net spread $\ge$ 0.20% after taker fees and order book depth slippage).
- **Average net actionable spread:** `~0.276%` (Peak: `~0.544%`).
- **Primary actionable routes:** `Binance -> Kraken` (4,764) and `Kraken -> Binance` (3,721).
- **Asset breakdown:** `ETH/USDT` (4,927 actionable ticks, avg net spread 0.281%) and `BTC/USDT` (3,558 actionable ticks, avg net spread 0.268%).

#### 💰 Hypothetical Profitability Analysis ($500 Notional Trade Size)
Simulating execution against the recorded order book depth and fee-adjusted spreads:
- **Realistic Discrete-Window Model (1 fill per arbitrage window):**
  - Because price discrepancies typically persist across several 300ms scanner ticks before closing, grouping consecutive ticks into discrete events (>2s cooldown) reveals **3,322 distinct arbitrage windows**.
  - Executing a single $500 trade per window yields **$5,477.38 in simulated net profit** (averaging ~$1.65 net profit per filled trade).
- **Theoretical Full-Fill Model (capturing all actionable scan cycles):**
  - If re-filling liquidity was possible across all 8,485 detected cycles, total cumulative net yield reaches **$11,691.65**.

> *Note: These figures represent an ex-post mathematical replay using real Level-2 depth snapshots minus exchange taker fees and estimated depth slippage; they do not account for external execution race conditions or inventory rebalancing costs.*

---

## 🚀 Key Features

- **Concurrent Multi-Exchange Ingestion (`asyncio`)**:
  - Independent WebSocket clients for Binance (`@depth20@100ms`), Coinbase (`level2_batch`), and Kraken (`book depth 10`).
  - Isolated supervisor tasks ensuring connection issues or disconnects on one exchange never impact others.
  - Per-exchange exponential backoff reconnect logic (1s to 30s) and keepalive ping/pong management.
  - Canonical symbol normalization across exchange-specific naming conventions (`BTC-USD`, `XBT/USD`, `BTCUSDT` $\rightarrow$ `BTC/USDT`).

- **Order Book Depth Ingestion & Slippage Estimation**:
  - Ingests top 10–20 bids and asks to build dynamic order books.
  - Walks the order book ladder (`estimate_buy_fill` & `estimate_sell_fill`) to compute the exact volume-weighted average fill price (VWAP) for a specified notional size ($500 default).

- **Realistic Fee- and Latency-Aware Detection Engine**:
  - **Gross Spread %**: Top-of-book bid/ask percentage difference.
  - **Fee Adjustment**: Deducts published exchange taker fees (Binance: 0.10%, Kraken: 0.26%, Coinbase: 0.60%).
  - **Liquidity-Adjusted Net Spread %**: Calculated from full depth walk execution simulation plus taker fees.
  - **Staleness / Latency Guard**: Opportunities based on order book snapshots older than 2,000ms are excluded from actionability.
  - **Actionability Determination**: Marked `is_actionable = true` only when the net spread exceeds the threshold (e.g., 0.20%), the trade is 100% fillable within available depth, and data is fresh.

- **Asynchronous SQLite Persistence (`aiosqlite`)**:
  - Non-blocking batch inserts of detected opportunities with microsecond timestamps, latency metrics, and spread breakdowns.
  - Indexed queries for rapid historical queries and rolling analytics summaries.

- **FastAPI REST API & WebSocket Gateway**:
  - High-throughput async REST endpoints for live tickers, book depth, historical opportunity queries, and 24h metrics.
  - Real-time WebSocket feed (`/ws/live`) streaming live market tickers and detected arbitrage events directly to the UI.

- **Reactive Glassmorphism Dashboard (React 19 + Tailwind CSS + Chart.js)**:
  - **Live Ticker Grid**: Real-time best bid/ask and top route per asset pair.
  - **Depth Inspector Modal**: Live 10-level bid/ask order book depth viewer.
  - **Live Opportunity Stream**: Color-coded feed distinguishing `ACTIONABLE` vs `PASS` opportunities.
  - **Spread History Chart**: Interactive time-series tracking spread percentages over time.
  - **24-Hour Analytics KPI Cards**: Rolling count of actionable opportunities, average net spread, peak spread, and top route.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph MarketData [Live Exchange WebSocket Feeds]
        B_WS["Binance WS Stream<br/>(@depth20@100ms)"]
        C_WS["Coinbase WS Feed<br/>(level2_batch)"]
        K_WS["Kraken WS Feed<br/>(book depth 10)"]
    end

    subgraph IngestionLayer [Ingestion Layer (asyncio Tasks)]
        B_Client["BinanceWSClient<br/>(Normalized Event Parser)"]
        C_Client["CoinbaseWSClient<br/>(L2 Delta Book Builder)"]
        K_Client["KrakenWSClient<br/>(L2 Snapshot & Delta Sync)"]
        Backoff["Supervision Loop<br/>(Exponential Backoff & Pings)"]
    end

    subgraph MemoryStore [Shared State Layer]
        StateStore["StateStore (In-Memory)<br/>asyncio.Lock guarded<br/>OrderBookSnapshot per Exchange/Symbol"]
    end

    subgraph Detection [Detection Engine (300ms Loop)]
        Pairwise["Pairwise Exchange Permutations<br/>(Binance ⇄ Coinbase ⇄ Kraken)"]
        DepthWalk["Order Book Depth Walk<br/>(Slippage at $500 Notional)"]
        FeeCalc["Taker Fee Adjustment<br/>(0.10% / 0.60% / 0.26%)"]
        LatencyFilter["Data Staleness & Latency Guard<br/>(Age ≤ 2000ms)"]
        ActionableCheck{"Net Spread ≥ 0.20% &<br/>Fully Fillable & Fresh?"}
    end

    subgraph Persistence [Storage Layer]
        SQLite[("gapx.db (SQLite via aiosqlite)<br/>opportunities table with indexes")]
    end

    subgraph APILayer [FastAPI Backend Service (:8000)]
        REST["REST Endpoints<br/>/prices/live, /orderbook/live<br/>/opportunities, /analytics/*"]
        WS_Gateway["WebSocket Gateway<br/>/ws/live (Broadcast Manager)"]
    end

    subgraph FrontendApp [React 19 Dashboard (:5173)]
        TickerUI["PriceTickerGrid<br/>(Live Bids/Asks)"]
        FeedUI["OpportunityFeed<br/>(Actionable vs Pass)"]
        ChartUI["SpreadChart<br/>(Chart.js Time Series)"]
        ModalUI["OrderBookModal<br/>(L2 Depth Inspection)"]
        StatsUI["AnalyticsSummary<br/>(24h KPIs)"]
    end

    %% Connections
    B_WS --> B_Client
    C_WS --> C_Client
    K_WS --> K_Client
    Backoff -.-> B_Client & C_Client & K_Client

    B_Client & C_Client & K_Client -->|OrderBookSnapshot| StateStore

    StateStore -->|Scan latest snapshots| Pairwise
    Pairwise --> DepthWalk
    DepthWalk --> FeeCalc
    FeeCalc --> LatencyFilter
    LatencyFilter --> ActionableCheck

    ActionableCheck -->|ArbitrageOpportunity Event| SQLite
    ActionableCheck -->|Real-time Broadcast| WS_Gateway

    SQLite -->|Historical & Analytics Queries| REST
    StateStore -->|Live Book & Prices| REST

    REST -->|Initial REST Polling| FrontendApp
    WS_Gateway -->|Live WS Ticker & Opps Push| FrontendApp

    FrontendApp --> TickerUI & FeedUI & ChartUI & ModalUI & StatsUI
```

---

## 💻 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language & Concurrency** | Python 3.11+, `asyncio` | High-concurrency event loops, non-blocking ingestion & detection |
| **WebSockets (Backend)** | `websockets` (v12.0+) | Low-latency async WebSocket clients for external exchanges |
| **Backend Framework** | FastAPI (v0.110+), Uvicorn | High-performance ASGI REST and WebSocket server |
| **Database & ORM** | SQLite, `aiosqlite` | Asynchronous local opportunity persistence and analytics queries |
| **Validation & Schema** | Dataclasses, Pydantic | Typed data structures for snapshots and arbitrage opportunities |
| **Frontend Framework** | React 19, Vite (v8.3+) | Modern reactive user interface and rapid hot-module reloading |
| **Styling** | Tailwind CSS (v4), Glassmorphism | Dark-themed, responsive dashboard styling |
| **Charting** | Chart.js, `react-chartjs-2` | Smooth time-series spread visualization |
| **Icons** | Lucide React | Modern UI iconography |

---

## 📊 Current Progress

### Phase 1: Core Pipeline (Completed ✅)
- [x] **Multi-Exchange Ingestion**: Concurrent WebSocket feeds for Binance, Coinbase, and Kraken.
- [x] **Auto-Reconnect with Backoff**: Resilient supervision loops with exponential backoff and custom ping frames.
- [x] **Level-2 Depth Ingestion**: Top 10–20 depth tracking per exchange/pair with canonical normalization.
- [x] **Shared State Layer**: Thread-safe in-memory `StateStore` protected with `asyncio.Lock`.
- [x] **Detection Engine**:
  - [x] Pairwise cross-exchange comparison across tracked symbols (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`).
  - [x] Top-of-book gross spread calculation.
  - [x] Static taker fee schedule deductions.
  - [x] Order book depth-walk for slippage and realistic volume-weighted execution price.
  - [x] Microsecond detection latency and order-book data age tracking.
  - [x] Dynamic `is_actionable` qualification based on net spread, fillability, and freshness.
- [x] **Historical Logging**: Non-blocking SQLite persistence via `aiosqlite` with indexing.
- [x] **FastAPI API & Streaming Gateway**: Full suite of REST endpoints + `/ws/live` push channel.
- [x] **React Dashboard**:
  - [x] Live price ticker grid with spread route highlighting.
  - [x] Interactive Level-2 order book depth inspector modal.
  - [x] Live opportunity stream with real-time badges (`ACTIONABLE` / `PASS`).
  - [x] Chart.js net spread history line chart.
  - [x] 24-hour summary cards with rolling KPIs.
- [x] **Extended Live Run**: Successfully verified with 1.66M+ opportunities recorded in `gapx.db`.

### Phase 2: Stretch Features (Roadmap 🧭)
- [ ] **Execution Simulator**: Replay historical SQLite records with starting capital to simulate cumulative P&L.
- [ ] **Discord / Telegram Webhooks**: Real-time push alerts for high-yield actionable opportunities.
- [ ] **Redis StateStore**: Multi-process shared state backend to decouple ingestion and detection processes.
- [ ] **Containerization & Deployment**: Dockerized backend container for cloud VM + Vercel deployment for React frontend.
- [ ] **Automated Test Suite**: Pytest coverage for detection mathematics, depth walk edge cases, and fee calculations.

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python 3.11+** installed
- **Node.js 18+** & **npm** installed
- Git

### 1. Clone & Set Up the Repository
```bash
git clone https://github.com/your-username/GapX.git
cd GapX
```

### 2. Backend Setup (FastAPI & Ingestion Engine)
Create and activate a virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Start the GapX scanner and API server:
```bash
python -m uvicorn gapx.api:app --reload --port 8000
```
*The backend will automatically initialize `gapx.db` (if not present), establish WebSocket connections to Binance, Coinbase, and Kraken, and start the 300ms scanning loop.*

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live Prices Endpoint**: [http://localhost:8000/prices/live](http://localhost:8000/prices/live)
- **Live WebSocket Feed**: `ws://localhost:8000/ws/live`

### 3. Frontend Setup (React Dashboard)
In a separate terminal, navigate to the frontend directory:
```bash
cd gapx/frontend
npm install
npm run dev
```

Open your browser and navigate to:
```
http://localhost:5173
```

---

## 📁 Project Structure

```
GapX/
├── .gitignore                          # Git ignore rules
├── requirements.txt                    # Python dependencies
├── crypto-arbitrage-scanner-spec.md    # System design & architecture specification
├── gapx.db                             # SQLite database storing historical opportunities
├── gapx/
│   ├── __init__.py
│   ├── api.py                          # FastAPI app (REST endpoints, lifespan, WS gateway)
│   ├── db.py                           # SQLite schema, aiosqlite batch inserts & queries
│   ├── detection.py                    # Arbitrage engine, fee calculation & depth-walk logic
│   ├── state_store.py                  # In-memory thread-safe store for OrderBookSnapshots
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base_client.py              # Base WebSocket client with reconnect & backoff
│   │   ├── binance_client.py           # Binance depth20 stream client & parser
│   │   ├── coinbase_client.py          # Coinbase level2_batch stream client & parser
│   │   └── kraken_client.py            # Kraken book depth 10 stream client & parser
│   └── frontend/
│       ├── index.html                  # HTML entry point
│       ├── package.json                # React dependencies and build scripts
│       ├── vite.config.js              # Vite configuration with Tailwind CSS plugin
│       └── src/
│           ├── main.jsx                # React root mount
│           ├── App.jsx                 # Main application controller (WS + REST orchestration)
│           ├── index.css               # Global styling, custom scrollbars, and animations
│           └── components/
│               ├── Navbar.jsx          # Header with WS connection status and symbol filters
│               ├── AnalyticsSummary.jsx# 24h KPI metrics cards
│               ├── PriceTickerGrid.jsx # Live bid/ask prices and best spread route
│               ├── OpportunityFeed.jsx # Real-time opportunity table with actionable tags
│               ├── SpreadChart.jsx     # Chart.js time-series spread visualization
│               └── OrderBookModal.jsx  # Interactive L2 depth inspector per exchange
```

---

## ⚙️ Configuration Parameters

Key operational thresholds can be configured in `gapx/detection.py` and `gapx/api.py`:

| Parameter | Location | Default Value | Description |
|---|---|---|---|
| `TRACKED_SYMBOLS` | `gapx/api.py` | `["BTC/USDT", "ETH/USDT", "SOL/USDT"]` | Asset pairs ingested and compared |
| `assumed_trade_size_usd` | `gapx/detection.py` | `$500.0` | Notional USD size used for order book depth-walk slippage |
| `min_net_spread_pct` | `gapx/detection.py` | `0.20%` | Minimum net spread after fees & slippage to flag as actionable |
| `max_data_age_ms` | `gapx/detection.py` | `2000.0 ms` | Maximum allowable age of order book data before discarding as stale |
| `EXCHANGE_TAKER_FEES` | `gapx/detection.py` | Binance: `0.10%`, Coinbase: `0.60%`, Kraken: `0.26%` | Static taker fee schedule per exchange |
| `Scanner Loop Interval` | `gapx/api.py` | `300 ms` | Frequency of pairwise state comparisons |

---

## 🛡️ Scope & Boundaries

To maintain a clean and reliable engineering scope, the following boundaries are deliberate:
- **No Real-Money Trading:** System is an observational, quantitative scanner.
- **Pre-Funded Capital Assumption:** No modeling of on-chain deposit/withdrawal wait times.
- **Static Exchange Fee Tiers:** Uses documented standard taker fees rather than private authenticated API fee tiers.
- **Local-First Architecture:** Single-node async Python process and local SQLite database; Redis and Docker are designated Phase 2 stretch enhancements.

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
