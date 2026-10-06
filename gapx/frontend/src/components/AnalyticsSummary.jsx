import React from 'react';
import { TrendingUp, Award, Layers, Clock } from 'lucide-react';

export default function AnalyticsSummary({ analytics }) {
  const cards = [
    {
      title: 'Actionable Opps (24h)',
      value: analytics?.actionable_opportunities ?? 0,
      subtext: `Total logged: ${analytics?.total_opportunities ?? 0}`,
      icon: TrendingUp,
      color: 'text-emerald-400',
      border: 'border-emerald-500/20',
      bg: 'bg-emerald-500/10',
    },
    {
      title: 'Avg Liquidity Net Spread',
      value: `${(analytics?.avg_net_spread_pct ?? 0).toFixed(3)}%`,
      subtext: 'Fee + Depth Slippage Adjusted',
      icon: Award,
      color: 'text-blue-400',
      border: 'border-blue-500/20',
      bg: 'bg-blue-500/10',
    },
    {
      title: 'Max Captured Spread',
      value: `${(analytics?.max_net_spread_pct ?? 0).toFixed(3)}%`,
      subtext: 'Highest net yield in 24h',
      icon: Layers,
      color: 'text-purple-400',
      border: 'border-purple-500/20',
      bg: 'bg-purple-500/10',
    },
    {
      title: 'Top Exchange Pair',
      value: analytics?.most_active_exchange_pair ?? 'N/A',
      subtext: 'Most frequent spread route',
      icon: Clock,
      color: 'text-amber-400',
      border: 'border-amber-500/20',
      bg: 'bg-amber-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div key={idx} className={`glass-card p-4 flex items-center justify-between border ${card.border}`}>
            <div>
              <p className="text-xs text-gray-400 font-medium">{card.title}</p>
              <h3 className="text-2xl font-bold text-white mt-1 tracking-tight">{card.value}</h3>
              <p className="text-[11px] text-gray-500 mt-0.5">{card.subtext}</p>
            </div>
            <div className={`p-3 rounded-xl ${card.bg} ${card.color}`}>
              <Icon className="w-6 h-6" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
