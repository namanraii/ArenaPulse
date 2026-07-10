import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import type { Zone } from '../types';
import { useMemo } from 'react';

interface DashboardChartsProps {
  zones: Zone[];
}

// Mock historical data since websocket only provides current state
const generateHistoricalData = (zones: Zone[]) => {
  const currentAvg = zones.length
    ? zones.reduce((acc, z) => acc + z.density, 0) / zones.length
    : 0.5;
  const data = [];
  const now = new Date();
  for (let i = 30; i >= 0; i -= 5) {
    const time = new Date(now.getTime() - i * 60000);
    // Add some random noise to the historical data, converging to currentAvg
    const noise = (Math.random() - 0.5) * 0.1;
    const value = Math.max(0, Math.min(1, currentAvg + noise * (i / 30)));
    data.push({
      time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      density: Math.round(value * 100),
    });
  }
  return data;
};

const COLORS = ['#3b82f6', '#22c55e', '#eab308', '#ef4444'];

export function DashboardCharts({ zones }: DashboardChartsProps) {
  const historyData = useMemo(() => generateHistoricalData(zones), [zones]);

  // Derive zone status distribution from live data instead of static values
  const zoneStatusData = useMemo(() => {
    if (!zones.length) {
      return [{ name: 'No Data', value: 1 }];
    }
    const critical = zones.filter((z) => z.density >= 0.9).length;
    const congested = zones.filter(
      (z) => z.density >= 0.7 && z.density < 0.9
    ).length;
    const normal = zones.length - critical - congested;
    return [
      { name: 'Normal', value: Math.max(normal, 0) },
      { name: 'Congested', value: congested },
      { name: 'Critical', value: critical },
    ];
  }, [zones]);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1.5rem',
        marginTop: '1.5rem',
      }}
    >
      <section className="panel" aria-labelledby="chart-density-title">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Trends</p>
            <h2 id="chart-density-title">Crowd Density (Last 30m)</h2>
          </div>
        </div>
        <div style={{ width: '100%', height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={historyData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} unit="%" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#f8fafc',
                }}
                itemStyle={{ color: '#38bdf8' }}
              />
              <Line
                type="monotone"
                dataKey="density"
                stroke="#38bdf8"
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel" aria-labelledby="chart-staff-title">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Live Status</p>
            <h2 id="chart-staff-title">Zone Status Distribution</h2>
          </div>
        </div>
        <div style={{ width: '100%', height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={zoneStatusData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {zoneStatusData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#f8fafc',
                }}
                itemStyle={{ color: '#f8fafc' }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
