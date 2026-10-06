import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function SpreadChart({ historyData, symbol }) {
  const labels = historyData.map((d) => new Date(d.detected_at).toLocaleTimeString());
  const netSpreadValues = historyData.map((d) => d.liquidity_adjusted_net_spread_pct);

  const data = {
    labels,
    datasets: [
      {
        label: `${symbol} Liquidity Net Spread %`,
        data: netSpreadValues,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: '#9ca3af', font: { family: 'monospace', size: 12 } },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#6b7280', font: { family: 'monospace', size: 10 } },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#6b7280', font: { family: 'monospace', size: 10 } },
      },
    },
  };

  return (
    <div className="glass-card p-5 mb-6">
      <h3 className="text-lg font-bold text-white mb-4 tracking-wide">
        Spread History Chart ({symbol})
      </h3>
      <div className="h-64">
        {historyData.length > 0 ? (
          <Line data={data} options={options} />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 font-mono text-sm">
            Accumulating spread history data...
          </div>
        )}
      </div>
    </div>
  );
}
