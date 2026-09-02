import { useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  Legend,
  LineChart,
  Line,
} from "recharts";
import { useComplaints } from "../context/ComplaintsContext";
import { IconChartBar, IconClipboard, IconCheckCircle, IconClock, IconAlertTriangle } from "../components/Icons";

const STATUS_COLORS = {
  Pending: "var(--pending)",
  "In Progress": "var(--progress)",
  Resolved: "var(--resolved)",
  Cancelled: "var(--text-dim)",
};

const HAZARD_COLORS = [
  "var(--hazard)",
  "var(--pending)",
  "var(--progress)",
  "var(--accent)",
  "var(--text-dim)",
];

// Small custom tooltip so charts pick up the app's dark/light theme
// instead of recharts' default white box.
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label && <div className="tooltip-label">{label}</div>}
      {payload.map((p) => (
        <div key={p.dataKey || p.name}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function ReportsTrends() {
  const { complaints } = useComplaints();

  const statusData = useMemo(() => {
    const counts = {};
    for (const c of complaints) counts[c.status] = (counts[c.status] || 0) + 1;
    return Object.entries(counts).map(([status, count]) => ({ status, count }));
  }, [complaints]);

  const hazardData = useMemo(() => {
    const counts = {};
    for (const c of complaints) {
      const key = c.hazard && c.hazard !== "None" ? c.hazard : "No Hazard Flagged";
      counts[key] = (counts[key] || 0) + 1;
    }
    return Object.entries(counts).map(([hazard, count]) => ({ hazard, count }));
  }, [complaints]);

  const trendData = useMemo(() => {
    const counts = {};
    for (const c of complaints) counts[c.createdAt] = (counts[c.createdAt] || 0) + 1;
    return Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, count]) => ({
        date: new Date(date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
        count,
      }));
  }, [complaints]);

  const resolutionData = useMemo(() => {
    return complaints
      .filter((c) => c.status === "Resolved" && c.resolvedAt)
      .map((c) => {
        const days = Math.max(
          0,
          Math.round((new Date(c.resolvedAt) - new Date(c.createdAt)) / (1000 * 60 * 60 * 24))
        );
        return { case: `#${String(c.id).padStart(4, "0")}`, days };
      });
  }, [complaints]);

  const avgResolutionDays = useMemo(() => {
    if (!resolutionData.length) return null;
    const total = resolutionData.reduce((sum, r) => sum + r.days, 0);
    return (total / resolutionData.length).toFixed(1);
  }, [resolutionData]);

  const totals = useMemo(
    () => ({
      total: complaints.length,
      pending: complaints.filter((c) => c.status === "Pending").length,
      inProgress: complaints.filter((c) => c.status === "In Progress").length,
      resolved: complaints.filter((c) => c.status === "Resolved").length,
    }),
    [complaints]
  );

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Supervisor Insights</span>
          <h1>Reports & Trends</h1>
          <p className="page-lead">
            A live rollup of every complaint on record — status mix, hazard breakdown, filing
            trend, and how long resolved cases actually took.
          </p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon accent"><IconClipboard /></div>
          <div>
            <span className="kpi-value">{totals.total}</span>
            <span className="kpi-label">Total Complaints</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon amber"><IconAlertTriangle /></div>
          <div>
            <span className="kpi-value">{totals.pending}</span>
            <span className="kpi-label">Pending</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconChartBar /></div>
          <div>
            <span className="kpi-value">{totals.inProgress}</span>
            <span className="kpi-label">In Progress</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon green"><IconCheckCircle /></div>
          <div>
            <span className="kpi-value">{totals.resolved}</span>
            <span className="kpi-label">Resolved</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconClock /></div>
          <div>
            <span className="kpi-value">{avgResolutionDays ? `${avgResolutionDays}d` : "—"}</span>
            <span className="kpi-label">Avg. Resolution Time</span>
          </div>
        </div>
      </div>

      <div className="chart-grid">
        <div className="chart-card">
          <h3>Complaints by Status</h3>
          <p className="chart-subtitle">How the current caseload is distributed right now.</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis dataKey="status" tickLine={false} axisLine={{ stroke: "var(--line)" }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
              <Bar dataKey="count" name="Complaints" radius={[6, 6, 0, 0]}>
                {statusData.map((entry) => (
                  <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || "var(--accent)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Complaints by Hazard Type</h3>
          <p className="chart-subtitle">Which hazard classifications show up most often.</p>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={hazardData}
                dataKey="count"
                nameKey="hazard"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {hazardData.map((entry, i) => (
                  <Cell key={entry.hazard} fill={HAZARD_COLORS[i % HAZARD_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: "0.78rem" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Filing Trend</h3>
          <p className="chart-subtitle">Complaints reported per day.</p>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={{ stroke: "var(--line)" }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey="count"
                name="Filed"
                stroke="var(--accent)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "var(--accent)" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Resolution Time by Case</h3>
          <p className="chart-subtitle">
            Days from filing to resolution, resolved cases only
            {resolutionData.length ? ` (avg. ${avgResolutionDays}d)` : ""}.
          </p>
          {resolutionData.length === 0 ? (
            <p className="empty-state">No resolved cases with a resolution date yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={resolutionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                <XAxis dataKey="case" tickLine={false} axisLine={{ stroke: "var(--line)" }} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
                <Bar dataKey="days" name="Days to resolve" fill="var(--resolved)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
