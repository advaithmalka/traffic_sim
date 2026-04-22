import { useMemo } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import type { TelemetrySnapshot } from '../types';

interface TelemetryChartProps {
  data: TelemetrySnapshot[];
}

/**
 * Real-time telemetry chart showing average speed and flow over time.
 */
export function TelemetryChart({ data }: TelemetryChartProps) {
  // Transform data for display using active simulation time.
  const chartData = useMemo(() => {
    if (data.length === 0) return [];
    return data.map((d) => ({
      time: Math.round(d.elapsedMs / 1000),
      speed: d.avg_speed,
      flow: Math.round(d.flow / 100), // Scale down for dual-axis display
    }));
  }, [data]);

  if (chartData.length < 2) {
    return (
      <div
        style={{
          height: '140px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '12px',
          fontStyle: 'italic',
        }}
      >
        Collecting telemetry data...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '140px' }}>
      <ResponsiveContainer>
        <AreaChart
          data={chartData}
          margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="speedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4f8eff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#4f8eff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="flowGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(100, 120, 180, 0.1)"
          />
          <XAxis
            dataKey="time"
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: 'rgba(100, 120, 180, 0.2)' }}
            tickLine={false}
            label={{
              value: 's',
              position: 'insideBottomRight',
              offset: -5,
              fill: '#64748b',
              fontSize: 10,
            }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: 'rgba(100, 120, 180, 0.2)' }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(15, 20, 35, 0.95)',
              border: '1px solid rgba(100, 120, 180, 0.3)',
              borderRadius: '8px',
              fontSize: '11px',
              color: '#e2e8f0',
              backdropFilter: 'blur(10px)',
            }}
            labelFormatter={(value) => `${value}s`}
            formatter={(value, name) => {
              const numericValue = typeof value === 'number' ? value : Number(value ?? 0);
              const seriesName = String(name ?? '');

              if (seriesName === 'speed') return [`${numericValue} mph`, 'Avg Speed'];
              if (seriesName === 'flow') return [`${numericValue * 100} veh/h`, 'Flow'];
              return [numericValue, seriesName];
            }}
          />
          <Area
            type="monotone"
            dataKey="speed"
            stroke="#4f8eff"
            strokeWidth={2}
            fill="url(#speedGradient)"
            dot={false}
            animationDuration={0}
          />
          <Area
            type="monotone"
            dataKey="flow"
            stroke="#34d399"
            strokeWidth={1.5}
            fill="url(#flowGradient)"
            dot={false}
            animationDuration={0}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
