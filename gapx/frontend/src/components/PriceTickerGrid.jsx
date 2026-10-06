import React from 'react';
import { Eye, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function PriceTickerGrid({ livePrices, onSelectDepth, selectedSymbol }) {
  const symbolsToDisplay = selectedSymbol === 'ALL'
    ? ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    : [selectedSymbol];

  const exchanges = ['binance', 'coinbase', 'kraken'];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      {symbolsToDisplay.map((symbol) => {
        const symbolPrices = livePrices[symbol] || {};

        // Find min ask and max bid across exchanges to show best opportunity route
        let bestBuyEx = null;
        let lowestAsk = Infinity;
        let bestSellEx = null;
        let highestBid = -Infinity;

        exchanges.forEach((ex) => {
          const snap = symbolPrices[ex];
          if (snap) {
            if (snap.best_ask && snap.best_ask < lowestAsk) {
              lowestAsk = snap.best_ask;
              bestBuyEx = ex;
            }
            if (snap.best_bid && snap.best_bid > highestBid) {
              highestBid = snap.best_bid;
              bestSellEx = ex;
            }
          }
        });

        const grossSpread = (highestBid > 0 && lowestAsk < Infinity)
          ? (((highestBid - lowestAsk) / lowestAsk) * 100).toFixed(3)
          : null;

        return (
          <div key={symbol} className="glass-card p-5 flex flex-col justify-between glass-card-hover">
            <div>
              <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping"></div>
                  <h3 className="text-lg font-bold text-white tracking-wide">{symbol}</h3>
                </div>
                {grossSpread !== null && (
                  <span className={`text-xs font-mono font-bold px-2 py-1 rounded ${
                    parseFloat(grossSpread) > 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800 text-gray-400'
                  }`}>
                    Spread: {grossSpread}%
                  </span>
                )}
              </div>

              {/* Table of Exchange Prices */}
              <div className="space-y-3 font-mono text-xs">
                {exchanges.map((ex) => {
                  const data = symbolPrices[ex];
                  const isBestBuy = ex === bestBuyEx;
                  const isBestSell = ex === bestSellEx;

                  return (
                    <div key={ex} className="flex items-center justify-between p-2 rounded bg-gray-900/60 border border-gray-800/80">
                      <div className="flex items-center space-x-2">
                        <span className="uppercase text-gray-400 font-sans font-semibold text-[11px] w-16">{ex}</span>
                        {isBestBuy && <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1 rounded">BUY</span>}
                        {isBestSell && <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1 rounded">SELL</span>}
                      </div>

                      {data ? (
                        <div className="flex items-center space-x-4 text-right">
                          <div>
                            <span className="text-gray-500 block text-[9px]">BID</span>
                            <span className="text-emerald-400 font-semibold">{data.best_bid ? `$${data.best_bid.toFixed(2)}` : '—'}</span>
                          </div>
                          <div>
                            <span className="text-gray-500 block text-[9px]">ASK</span>
                            <span className="text-red-400 font-semibold">{data.best_ask ? `$${data.best_ask.toFixed(2)}` : '—'}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-600 text-[11px]">Connecting...</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* View Depth Button */}
            <div className="mt-4 pt-3 border-t border-gray-800 flex justify-end">
              <button
                onClick={() => onSelectDepth(symbol)}
                className="flex items-center space-x-1.5 text-xs text-blue-400 hover:text-blue-300 font-medium bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 px-3 py-1.5 rounded-lg transition"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Inspect Order Book Depth</span>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
