import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type AnalyticsRow = Record<string, string | number | null>;

type AnalyticsState = {
  categories: AnalyticsRow[];
  boroughs: AnalyticsRow[];
  agencies: AnalyticsRow[];
  topComplaints: AnalyticsRow[];
};

type ChartRow = {
  label: string;
  count: number;
};

const API_BASE_URL = "http://127.0.0.1:8000";

const endpoints = {
  categories: `${API_BASE_URL}/analytics/categories`,
  boroughs: `${API_BASE_URL}/analytics/boroughs`,
  agencies: `${API_BASE_URL}/analytics/agencies`,
  topComplaints: `${API_BASE_URL}/analytics/top-complaints`,
};

const initialData: AnalyticsState = {
  categories: [],
  boroughs: [],
  agencies: [],
  topComplaints: [],
};

const chartColors = ["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#4f46e5", "#16a34a"];

function getLabel(row: AnalyticsRow): string {
  const label = row.resolution_category ?? row.borough ?? row.agency ?? row.complaint_type ?? "Unknown";
  return String(label);
}

function getCount(row: AnalyticsRow): number {
  const value = row.count ?? row.complaint_count ?? 0;
  return Number(value);
}

function getChartData(rows: AnalyticsRow[]): ChartRow[] {
  return rows
    .map((row) => ({
      label: getLabel(row),
      count: getCount(row),
    }))
    .sort((first, second) => second.count - first.count)
    .slice(0, 10);
}

function formatAxisLabel(label: string): string {
  return label.length > 22 ? `${label.slice(0, 19)}...` : label;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <section className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function DataPanel({ title, rows }: { title: string; rows: AnalyticsRow[] }) {
  const chartData = getChartData(rows);

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>{title}</h2>
        <span>{rows.length} rows</span>
      </header>
      <div className="chart-wrap" aria-label={`${title} bar chart`}>
        {chartData.length === 0 ? (
          <div className="chart-empty">No chart data available</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 6, right: 18, bottom: 6, left: 8 }}>
              <CartesianGrid stroke="#e7edf4" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#657287", fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: "#d9e0e8" }}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={132}
                tick={{ fill: "#334155", fontSize: 12 }}
                tickFormatter={formatAxisLabel}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(37, 99, 235, 0.08)" }}
                formatter={(value) => [Number(value).toLocaleString(), "Count"]}
                labelStyle={{ color: "#101827", fontWeight: 700 }}
                contentStyle={{
                  border: "1px solid #d9e0e8",
                  borderRadius: 6,
                  boxShadow: "0 8px 24px rgba(16, 24, 39, 0.12)",
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18}>
                {chartData.map((entry, index) => (
                  <Cell key={`${entry.label}-${index}`} fill={chartColors[index % chartColors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={2}>No data available</td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={`${getLabel(row)}-${index}`}>
                  <td>{getLabel(row)}</td>
                  <td>{getCount(row).toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function App() {
  const [data, setData] = useState<AnalyticsState>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const responses = await Promise.all(
          Object.values(endpoints).map(async (url) => {
            const response = await fetch(url);
            if (!response.ok) {
              throw new Error(`${url} returned ${response.status}`);
            }
            return response.json() as Promise<AnalyticsRow[]>;
          }),
        );

        setData({
          categories: responses[0],
          boroughs: responses[1],
          agencies: responses[2],
          topComplaints: responses[3],
        });
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load analytics.");
      } finally {
        setLoading(false);
      }
    }

    loadAnalytics();
  }, []);

  const totalComplaints = useMemo(
    () => data.categories.reduce((total, row) => total + getCount(row), 0),
    [data.categories],
  );

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">NYC 311 Analytics</p>
          <h1>Civic Service Request Dashboard</h1>
        </div>
        <span className={loading ? "status loading" : "status"}>{loading ? "Loading" : "Live data"}</span>
      </header>

      {error ? <div className="error-banner">Failed to load analytics: {error}</div> : null}

      <section className="summary-grid">
        <SummaryCard label="Total complaints" value={totalComplaints.toLocaleString()} />
        <SummaryCard label="Resolution categories" value={data.categories.length.toLocaleString()} />
        <SummaryCard label="Boroughs" value={data.boroughs.length.toLocaleString()} />
        <SummaryCard label="Agencies" value={data.agencies.length.toLocaleString()} />
      </section>

      <section className="dashboard-grid">
        <DataPanel title="Resolution category counts" rows={data.categories} />
        <DataPanel title="Borough counts" rows={data.boroughs} />
        <DataPanel title="Agency counts" rows={data.agencies} />
        <DataPanel title="Top complaint types" rows={data.topComplaints} />
      </section>
    </main>
  );
}

export default App;
