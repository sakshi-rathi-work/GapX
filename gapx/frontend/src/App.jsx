import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import AnalyticsSummary from './components/AnalyticsSummary';
import PriceTickerGrid from './components/PriceTickerGrid';
import OpportunityFeed from './components/OpportunityFeed';
import SpreadChart from './components/SpreadChart';
import OrderBookModal from './components/OrderBookModal';

export default function App() {
  const [selectedSymbol, setSelectedSymbol] = useState('ALL');
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [livePrices, setLivePrices] = useState({});
  const [opportunities, setOpportunities] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [spreadHistory, setSpreadHistory] = useState([]);
  const [inspectSymbol, setInspectSymbol] = useState(null);

  // 1. Initial REST data fetch
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const pricesRes = await fetch('http://localhost:8000/prices/live');
        if (pricesRes.ok) {
          const pData = await pricesRes.json();
          setLivePrices(pData);
        }

        const oppsRes = await fetch('http://localhost:8000/opportunities?limit=50');
        if (oppsRes.ok) {
          const oData = await oppsRes.json();
          setOpportunities(oData);
        }

        const analyticsRes = await fetch('http://localhost:8000/analytics/summary?range=24h');
        if (analyticsRes.ok) {
          const aData = await analyticsRes.json();
          setAnalytics(aData);
        }
      } catch (err) {
        console.error('Error fetching initial REST data:', err);
      }
    };

    fetchInitialData();
    const interval = setInterval(fetchInitialData, 5000);
    return () => clearInterval(interval);
  }, []);

  // 2. Fetch spread history for chart
  useEffect(() => {
    const fetchHistory = async () => {
      const activeSym = selectedSymbol === 'ALL' ? 'BTC/USDT' : selectedSymbol;
      try {
        const res = await fetch(`http://localhost:8000/analytics/spread-history?symbol=${encodeURIComponent(activeSym)}&range=24h`);
        if (res.ok) {
          const data = await res.json();
          setSpreadHistory(data);
        }
      } catch (err) {
        console.error('Error fetching spread history:', err);
      }
    };

    fetchHistory();
  }, [selectedSymbol]);

  // 3. Real-time WebSocket connection to Backend
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connectWs = () => {
      ws = new WebSocket('ws://localhost:8000/ws/live');

      ws.onopen = () => {
        setIsWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'ticker') {
            setLivePrices((prev) => ({ ...prev, ...msg.data }));
          } else if (msg.type === 'opportunity') {
            setOpportunities((prev) => [msg.data, ...prev.slice(0, 99)]);
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        setIsWsConnected(false);
        reconnectTimer = setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        setIsWsConnected(false);
        ws.close();
      };
    };

    connectWs();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  const activeChartSymbol = selectedSymbol === 'ALL' ? 'BTC/USDT' : selectedSymbol;

  return (
    <div className="min-h-screen bg-[#080c14] text-gray-100 flex flex-col font-sans">
      <Navbar
        isWsConnected={isWsConnected}
        selectedSymbol={selectedSymbol}
        setSelectedSymbol={setSelectedSymbol}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        <AnalyticsSummary analytics={analytics} />

        <PriceTickerGrid
          livePrices={livePrices}
          onSelectDepth={(sym) => setInspectSymbol(sym)}
          selectedSymbol={selectedSymbol}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <OpportunityFeed
              opportunities={opportunities}
              selectedSymbol={selectedSymbol}
            />
          </div>
          <div className="lg:col-span-1">
            <SpreadChart
              historyData={spreadHistory}
              symbol={activeChartSymbol}
            />
          </div>
        </div>
      </main>

      {inspectSymbol && (
        <OrderBookModal
          symbol={inspectSymbol}
          onClose={() => setInspectSymbol(null)}
        />
      )}
    </div>
  );
}
