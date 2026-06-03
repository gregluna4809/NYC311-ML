import { useEffect, useMemo, useState } from "react";

type AnalyticsRow = Record<string, string | number | null>;

type AnalyticsState = {
  categories: AnalyticsRow[];
  boroughs: AnalyticsRow[];
  agencies: AnalyticsRow[];
  topComplaints: AnalyticsRow[];
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

function getLabel(row: AnalyticsRow): string {
  const label = row.resolution_category ?? row.borough ?? row.agency ?? row.complaint_type ?? "Unknown";
  return String(label);
}

function getCount(row: AnalyticsRow): number {
  const value = row.count ?? row.complaint_count ?? 0;
  return Number(value);
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
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>{title}</h2>
        <span>{rows.length} rows</span>
      </header>
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
