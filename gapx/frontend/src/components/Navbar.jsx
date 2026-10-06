import React from 'react';
import { Activity, Wifi, Zap, Database } from 'lucide-react';

export default function Navbar({ isWsConnected, selectedSymbol, setSelectedSymbol }) {
  const symbols = ['ALL', 'BTC/USDT', 'ETH/USDT', 'SOL/USDT'];

  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <Zap className="w-6 h-6 text-blue-400 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-white flex items-center gap-2">
              GAPX <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-mono border border-blue-500/30">v2.0</span>
            </h1>
            <p className="text-xs text-gray-400">Cross-Exchange Real-Time Crypto Arbitrage Engine</p>
          </div>
        </div>

        {/* Symbol Tabs */}
        <div className="flex items-center bg-gray-900/80 p-1 rounded-xl border border-gray-800">
          {symbols.map((sym) => (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedSymbol === sym
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
            >
              {sym}
            </button>
          ))}
        </div>

        {/* Live System Status Badges */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800">
            <span className="text-gray-400">Engine WS:</span>
            <span className={`flex items-center space-x-1.5 font-medium ${isWsConnected ? 'text-emerald-400' : 'text-red-400'}`}>
              <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-emerald-500 pulse-green' : 'bg-red-500'}`}></span>
              <span>{isWsConnected ? 'ONLINE' : 'DISCONNECTED'}</span>
            </span>
          </div>

          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-gray-300 font-mono">
            <span className="text-emerald-400">BINANCE</span> • <span className="text-blue-400">COINBASE</span> • <span className="text-purple-400">KRAKEN</span>
          </div>
        </div>
      </div>
    </header>
  );
}
