import React, { useEffect, useState } from 'react';
import { X, RefreshCw } from 'lucide-react';

export default function OrderBookModal({ symbol, onClose }) {
  const [selectedExchange, setSelectedExchange] = useState('binance');
  const [orderbook, setOrderbook] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let intervalId;

    const fetchOrderbook = async () => {
      try {
        const res = await fetch(`http://localhost:8000/orderbook/live?exchange=${selectedExchange}&symbol=${encodeURIComponent(symbol)}`);
        if (res.ok) {
          const data = await res.json();
          setOrderbook(data);
        }
      } catch (err) {
        console.error('Error fetching orderbook depth:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchOrderbook();
    intervalId = setInterval(fetchOrderbook, 500);

    return () => clearInterval(intervalId);
  }, [symbol, selectedExchange]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="glass-card max-w-2xl w-full p-6 border border-gray-800 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white p-1 rounded-lg bg-gray-800/50 hover:bg-gray-800"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              {symbol} Order Book Depth
            </h3>
            <p className="text-xs text-gray-400">Live order book depth stream per exchange</p>
          </div>

          <div className="flex items-center space-x-1 bg-gray-900 p-1 rounded-lg border border-gray-800 mr-8">
            {['binance', 'coinbase', 'kraken'].map((ex) => (
              <button
                key={ex}
                onClick={() => setSelectedExchange(ex)}
                className={`px-3 py-1 rounded text-xs font-semibold uppercase ${
                  selectedExchange === ex ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {loading || !orderbook ? (
          <div className="py-12 text-center text-gray-500 font-mono flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Fetching live order book depth...</span>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 font-mono text-xs">
            {/* Bids (Buy Side - Green) */}
            <div>
              <h4 className="text-xs font-sans font-bold text-emerald-400 uppercase tracking-wider mb-2 border-b border-gray-800 pb-1">
                Bids (Buy Orders)
              </h4>
              <div className="space-y-1">
                {orderbook.bids.slice(0, 10).map(([price, qty], i) => (
                  <div key={i} className="flex justify-between p-1.5 rounded bg-emerald-950/20 border border-emerald-900/30">
                    <span className="text-emerald-400 font-semibold">${price.toFixed(2)}</span>
                    <span className="text-gray-300">{qty.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Asks (Sell Side - Red) */}
            <div>
              <h4 className="text-xs font-sans font-bold text-red-400 uppercase tracking-wider mb-2 border-b border-gray-800 pb-1">
                Asks (Sell Orders)
              </h4>
              <div className="space-y-1">
                {orderbook.asks.slice(0, 10).map(([price, qty], i) => (
                  <div key={i} className="flex justify-between p-1.5 rounded bg-red-950/20 border border-red-900/30">
                    <span className="text-red-400 font-semibold">${price.toFixed(2)}</span>
                    <span className="text-gray-300">{qty.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
