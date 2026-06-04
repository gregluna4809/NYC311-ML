import { type FormEvent, useEffect, useMemo, useState } from "react";
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

type PredictionFormState = {
  agency: string;
  complaint_type: string;
  borough: string;
  day_of_week: string;
  month: number;
  hour_of_day: number;
  weekend_flag: boolean;
};

type PredictionResponse = {
  predicted_category: string;
  confidence: number;
  model: string;
};

type ComplaintTypeMetadata = {
  complaint_type: string;
  agencies: string[];
};

const API_BASE_URL = "http://127.0.0.1:8000";

const endpoints = {
  categories: `${API_BASE_URL}/analytics/categories`,
  boroughs: `${API_BASE_URL}/analytics/boroughs`,
  agencies: `${API_BASE_URL}/analytics/agencies`,
  topComplaints: `${API_BASE_URL}/analytics/top-complaints`,
};
const complaintTypeMetadataEndpoint = `${API_BASE_URL}/metadata/complaint-types`;

const initialData: AnalyticsState = {
  categories: [],
  boroughs: [],
  agencies: [],
  topComplaints: [],
};

const chartColors = ["#005ea8", "#111111", "#6b7280", "#8ecae6", "#f9a825", "#4b5563", "#0072bc", "#9ca3af"];
const dayOptions = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const modelPerformance = [
  { label: "Majority Class Baseline", value: 44.3 },
  { label: "Logistic Regression", value: 72.1 },
  { label: "XGBoost", value: 72.9 },
  { label: "Enhanced XGBoost", value: 74.4 },
];

const initialPredictionForm: PredictionFormState = {
  agency: "",
  complaint_type: "",
  borough: "BROOKLYN",
  day_of_week: "Saturday",
  month: 6,
  hour_of_day: 14,
  weekend_flag: true,
};

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

function getSelectOptions(rows: AnalyticsRow[], fallbackValue: string): string[] {
  const options = rows.map(getLabel).filter((label) => label !== "Unknown");
  return Array.from(new Set([fallbackValue, ...options])).sort((first, second) => first.localeCompare(second));
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <section className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function ModelPerformancePanel() {
  return (
    <section className="panel model-panel">
      <header className="panel-header">
        <h2>Model Performance</h2>
        <span>Validation accuracy</span>
      </header>
      <div className="model-list">
        {modelPerformance.map((model) => (
          <div className="model-row" key={model.label}>
            <div className="model-row-top">
              <span>{model.label}</span>
              <strong>{model.value.toFixed(1)}%</strong>
            </div>
            <div className="model-track" aria-hidden="true">
              <div className="model-fill" style={{ width: `${model.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PredictionPanel({
  boroughOptions,
  complaintTypeMetadata,
  metadataLoading,
}: {
  boroughOptions: string[];
  complaintTypeMetadata: ComplaintTypeMetadata[];
  metadataLoading: boolean;
}) {
  const [form, setForm] = useState<PredictionFormState>(initialPredictionForm);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const complaintOptions = useMemo(
    () => complaintTypeMetadata.map((metadata) => metadata.complaint_type),
    [complaintTypeMetadata],
  );
  const selectedComplaintMetadata = useMemo(
    () => complaintTypeMetadata.find((metadata) => metadata.complaint_type === form.complaint_type),
    [complaintTypeMetadata, form.complaint_type],
  );
  const agencyOptions = selectedComplaintMetadata?.agencies ?? [];
  const canPredict = Boolean(form.complaint_type && form.agency && form.borough) && !metadataLoading;

  useEffect(() => {
    if (complaintTypeMetadata.length === 0) {
      return;
    }

    setForm((currentForm) => {
      const currentComplaintMetadata = complaintTypeMetadata.find(
        (metadata) => metadata.complaint_type === currentForm.complaint_type,
      );
      const nextComplaintMetadata = currentComplaintMetadata ?? complaintTypeMetadata[0];
      const currentAgencyIsValid = nextComplaintMetadata.agencies.includes(currentForm.agency);

      return {
        ...currentForm,
        complaint_type: nextComplaintMetadata.complaint_type,
        agency: currentAgencyIsValid ? currentForm.agency : nextComplaintMetadata.agencies[0] ?? "",
      };
    });
  }, [complaintTypeMetadata]);

  function updateComplaintType(complaintType: string) {
    const nextComplaintMetadata = complaintTypeMetadata.find((metadata) => metadata.complaint_type === complaintType);
    setForm({
      ...form,
      complaint_type: complaintType,
      agency: nextComplaintMetadata?.agencies[0] ?? "",
    });
    setPrediction(null);
    setPredictionError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canPredict) {
      setPredictionError("Select a valid complaint type and agency before predicting.");
      return;
    }

    setPredicting(true);
    setPrediction(null);
    setPredictionError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail = typeof errorBody?.detail === "string" ? errorBody.detail : `Prediction returned ${response.status}`;
        throw new Error(detail);
      }

      setPrediction((await response.json()) as PredictionResponse);
    } catch (submitError) {
      setPredictionError(submitError instanceof Error ? submitError.message : "Unable to generate prediction.");
    } finally {
      setPredicting(false);
    }
  }

  return (
    <section className="panel prediction-panel">
      <header className="panel-header">
        <h2>Predict Resolution Category</h2>
        <span>Live FastAPI model</span>
      </header>
      <form className="prediction-form" onSubmit={handleSubmit}>
        <label>
          Agency
          <select
            value={form.agency}
            disabled={agencyOptions.length === 0}
            onChange={(event) => setForm({ ...form, agency: event.target.value })}
          >
            {agencyOptions.map((agency) => (
              <option key={agency} value={agency}>
                {agency}
              </option>
            ))}
          </select>
        </label>
        <label>
          Complaint Type
          <select
            value={form.complaint_type}
            disabled={complaintOptions.length === 0}
            onChange={(event) => updateComplaintType(event.target.value)}
          >
            {complaintOptions.map((complaintType) => (
              <option key={complaintType} value={complaintType}>
                {complaintType}
              </option>
            ))}
          </select>
        </label>
        <label>
          Borough
          <select value={form.borough} onChange={(event) => setForm({ ...form, borough: event.target.value })}>
            {boroughOptions.map((borough) => (
              <option key={borough} value={borough}>
                {borough}
              </option>
            ))}
          </select>
        </label>
        <label>
          Day of Week
          <select
            value={form.day_of_week}
            onChange={(event) => setForm({ ...form, day_of_week: event.target.value })}
          >
            {dayOptions.map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
          </select>
        </label>
        <label>
          Month
          <input
            type="number"
            min="1"
            max="12"
            value={form.month}
            onChange={(event) => setForm({ ...form, month: Number(event.target.value) })}
          />
        </label>
        <label>
          Hour of Day
          <input
            type="number"
            min="0"
            max="23"
            value={form.hour_of_day}
            onChange={(event) => setForm({ ...form, hour_of_day: Number(event.target.value) })}
          />
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={form.weekend_flag}
            onChange={(event) => setForm({ ...form, weekend_flag: event.target.checked })}
          />
          Weekend
        </label>
        <div className="prediction-actions">
          <button type="submit" disabled={predicting || !canPredict}>
            {predicting ? "Predicting" : metadataLoading ? "Loading options" : "Predict"}
          </button>
        </div>
      </form>
      {predictionError ? <div className="prediction-error">Prediction failed: {predictionError}</div> : null}
      {prediction ? (
        <div className="prediction-result">
          <span>Predicted Resolution Category</span>
          <strong>{prediction.predicted_category}</strong>
          <div className="confidence-block">
            <div className="confidence-label">
              <span>Confidence</span>
              <strong>{Math.round(prediction.confidence * 100)}%</strong>
            </div>
            <div className="confidence-track" aria-hidden="true">
              <div
                className="confidence-fill"
                style={{ width: `${Math.min(Math.max(prediction.confidence, 0), 1) * 100}%` }}
              />
            </div>
          </div>
        </div>
      ) : null}
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
              <CartesianGrid stroke="#d6e4f0" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#4b5563", fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: "#bfd3e6" }}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={132}
                tick={{ fill: "#111827", fontSize: 12 }}
                tickFormatter={formatAxisLabel}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(0, 94, 168, 0.08)" }}
                formatter={(value) => [Number(value).toLocaleString(), "Count"]}
                labelStyle={{ color: "#111111", fontWeight: 700 }}
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #bfd3e6",
                  borderRadius: 8,
                  boxShadow: "0 12px 28px rgba(17, 24, 39, 0.14)",
                  color: "#374151",
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
  const [complaintTypeMetadata, setComplaintTypeMetadata] = useState<ComplaintTypeMetadata[]>([]);
  const [metadataLoading, setMetadataLoading] = useState(true);
  const [metadataError, setMetadataError] = useState<string | null>(null);
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

  useEffect(() => {
    async function loadComplaintTypeMetadata() {
      try {
        const response = await fetch(complaintTypeMetadataEndpoint);
        if (!response.ok) {
          throw new Error(`${complaintTypeMetadataEndpoint} returned ${response.status}`);
        }
        setComplaintTypeMetadata((await response.json()) as ComplaintTypeMetadata[]);
      } catch (loadError) {
        setMetadataError(loadError instanceof Error ? loadError.message : "Unable to load complaint type metadata.");
      } finally {
        setMetadataLoading(false);
      }
    }

    loadComplaintTypeMetadata();
  }, []);

  const totalComplaints = useMemo(
    () => data.categories.reduce((total, row) => total + getCount(row), 0),
    [data.categories],
  );
  const boroughOptions = useMemo(() => getSelectOptions(data.boroughs, initialPredictionForm.borough), [data.boroughs]);

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">NYC 311 Analytics</p>
          <h1>Civic Service Request Dashboard</h1>
          <p className="dashboard-intro">
            This dashboard analyzes NYC 311 service requests using real NYC Open Data. It shows how complaints are
            distributed across agencies, boroughs, and resolution categories, and uses a trained XGBoost model to predict
            how long a new complaint is likely to take to resolve.
          </p>
          <div className="workflow-row" aria-label="How it works">
            <span>NYC Open Data</span>
            <span>PostgreSQL</span>
            <span>FastAPI</span>
            <span>XGBoost Prediction</span>
          </div>
        </div>
        <span className={loading ? "status loading" : "status"}>{loading ? "Loading" : "Live data"}</span>
      </header>

      {error ? <div className="error-banner">Failed to load analytics: {error}</div> : null}
      {metadataError ? <div className="error-banner">Failed to load prediction options: {metadataError}</div> : null}

      <section className="summary-grid">
        <SummaryCard label="Total complaints" value={totalComplaints.toLocaleString()} />
        <SummaryCard label="Resolution categories" value={data.categories.length.toLocaleString()} />
        <SummaryCard label="Boroughs" value={data.boroughs.length.toLocaleString()} />
        <SummaryCard label="Agencies" value={data.agencies.length.toLocaleString()} />
      </section>

      <PredictionPanel
        boroughOptions={boroughOptions}
        complaintTypeMetadata={complaintTypeMetadata}
        metadataLoading={metadataLoading}
      />

      <ModelPerformancePanel />

      <section className="dashboard-grid">
        <DataPanel title="Resolution category counts" rows={data.categories} />
        <DataPanel title="Borough counts" rows={data.boroughs} />
        <DataPanel title="Agency counts" rows={data.agencies} />
        <DataPanel title="Top complaint types" rows={data.topComplaints} />
      </section>

      <footer className="site-footer">
        NYC311-ML • Portfolio Project • Uses NYC Open Data • Not affiliated with or endorsed by the City of New York
      </footer>
    </main>
  );
}

export default App;
