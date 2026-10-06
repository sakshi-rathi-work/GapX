import React from 'react';
import { ArrowRight, CheckCircle2, XCircle, Clock, Zap } from 'lucide-react';

export default function OpportunityFeed({ opportunities, selectedSymbol }) {
  const filtered = selectedSymbol === 'ALL'
    ? opportunities
    : opportunities.filter((o) => o.symbol === selectedSymbol);

  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <Zap className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-white tracking-wide">Live Arbitrage Stream</h2>
          <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full font-mono">
            {filtered.length} detected
          </span>
        </div>
        <span className="text-xs text-gray-500 font-mono">Assumed Trade Size: $500</span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500 font-mono text-sm">
          Scanning order books for cross-exchange spreads...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 font-sans uppercase text-[11px] tracking-wider">
                <th className="pb-3 px-2">Status</th>
                <th className="pb-3 px-2">Symbol</th>
                <th className="pb-3 px-2">Arbitrage Route</th>
                <th className="pb-3 px-2 text-right">Gross Spread</th>
                <th className="pb-3 px-2 text-right">Fee-Adj Spread</th>
                <th className="pb-3 px-2 text-right">Liquidity Net Spread</th>
                <th className="pb-3 px-2 text-right">Data Age</th>
                <th className="pb-3 px-2 text-right">Detected At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filtered.slice(0, 30).map((opp, idx) => {
                const isActionable = opp.is_actionable;
                return (
                  <tr key={idx} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 px-2">
                      {isActionable ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>ACTIONABLE</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-[10px] font-semibold bg-gray-800 text-gray-400 border border-gray-700">
                          <XCircle className="w-3 h-3 text-gray-500" />
                          <span>PASS</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-2 font-bold text-white">{opp.symbol}</td>
                    <td className="py-3 px-2">
                      <div className="flex items-center space-x-1 text-gray-300">
                        <span className="uppercase text-emerald-400 font-semibold">{opp.buy_exchange}</span>
                        <ArrowRight className="w-3 h-3 text-gray-500" />
                        <span className="uppercase text-blue-400 font-semibold">{opp.sell_exchange}</span>
                      </div>
                    </td>
                    <td className="py-3 px-2 text-right text-gray-400">
                      {opp.gross_spread_pct.toFixed(3)}%
                    </td>
                    <td className="py-3 px-2 text-right text-gray-300">
                      {opp.fee_adjusted_spread_pct.toFixed(3)}%
                    </td>
                    <td className={`py-3 px-2 text-right font-bold ${isActionable ? 'text-emerald-400' : 'text-gray-300'}`}>
                      {opp.liquidity_adjusted_net_spread_pct.toFixed(3)}%
                    </td>
                    <td className="py-3 px-2 text-right text-gray-400">
                      {opp.underlying_data_age_ms}ms
                    </td>
                    <td className="py-3 px-2 text-right text-gray-500 text-[11px]">
                      {new Date(opp.detected_at).toLocaleTimeString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
