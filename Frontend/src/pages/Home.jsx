import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useComplaints } from "../context/ComplaintsContext";
import { useBulkPickup } from "../context/BulkPickupContext";
import {
  IconReport,
  IconClipboard,
  IconBroom,
  IconGrid,
  IconArrowRight,
  IconUsers,
  IconTruck,
  IconFeed,
  IconPackage,
  IconCalendar,
  IconPlus,
  IconChartBar,
  IconCheckCircle,
  IconClock,
} from "../components/Icons";

const roleConfig = {
  citizen: {
    heading: "Citizen Portal",
    blurb: "Report civic waste issues, schedule bulk collections, and track cleanup progress in your neighborhood.",
    primaryAction: { to: "/report", label: "File New Report", icon: IconPlus },
    actions: [
      {
        to: "/report",
        label: "File a Report",
        desc: "Report overflowing bins, illegal dumping, or street litter with GPS & photos.",
        icon: IconReport,
        featured: true,
      },
      {
        to: "/my-complaints",
        label: "My Complaints",
        desc: "Track status updates, resolution proofs, and crew progress on your reports.",
        icon: IconClipboard,
      },
      {
        to: "/bulk-pickup",
        label: "Schedule Bulk Pickup",
        desc: "Book doorstep collection for furniture, electronics, and heavy waste.",
        icon: IconPackage,
      },
      {
        to: "/schedule",
        label: "Collection Schedule",
        desc: "View routine waste pickup days and vehicle schedules in your ward.",
        icon: IconCalendar,
      },
      {
        to: "/feed",
        label: "Public Feed",
        desc: "View community cleanup transparency feed and verified issue resolutions.",
        icon: IconFeed,
      },
    ],
  },
  crew: {
    heading: "Cleanup Crew Portal",
    blurb: "View field task assignments, track daily routes, and log resolution proofs directly from the field.",
    primaryAction: { to: "/crew", label: "View Task Queue", icon: IconBroom },
    actions: [
      {
        to: "/crew",
        label: "Assigned Tasks",
        desc: "Review your task queue, update status, and attach cleanup completion photos.",
        icon: IconBroom,
        featured: true,
      },
      {
        to: "/feed",
        label: "Public Feed",
        desc: "Browse public transparency feed and verified community impact logs.",
        icon: IconFeed,
      },
    ],
  },
  admin: {
    heading: "Operations Console",
    blurb: "Real-time supervisory console for complaint resolution, workforce allocation, and fleet operations.",
    primaryAction: { to: "/dashboard", label: "Open Dashboard", icon: IconGrid },
    actions: [
      {
        to: "/dashboard",
        label: "Supervisor Dashboard",
        desc: "Live citywide overview of pending complaints, crew statuses, and SLAs.",
        icon: IconGrid,
        featured: true,
      },
      {
        to: "/reports",
        label: "Reports & Trends",
        desc: "Deep-dive resolution analytics, response times, and hotspot heatmaps.",
        icon: IconChartBar,
      },
      {
        to: "/workforce",
        label: "Workforce & Equipment",
        desc: "Manage sanitation workers, safety equipment stock, and duty shifts.",
        icon: IconUsers,
      },
      {
        to: "/vehicles",
        label: "Fleet Assignment",
        desc: "Dispatch collection vehicles, monitor fleet status, and route coverage.",
        icon: IconTruck,
      },
      {
        to: "/bulk-pickup-manage",
        label: "Bulk Management",
        desc: "Audit bulk waste requests, assign heavy vehicles, and schedule crews.",
        icon: IconPackage,
      },
      {
        to: "/feed",
        label: "Public Feed Audit",
        desc: "Moderate citizen community feed, ratings, and resolution transparency.",
        icon: IconFeed,
      },
    ],
  },
};

const roleBadgeNames = {
  citizen: "Citizen",
  crew: "Crew Field",
  admin: "Administrator",
};

export default function Home() {
  const { user } = useAuth();
  const { complaints } = useComplaints();
  const { pickups } = useBulkPickup();
  const navigate = useNavigate();

  if (!user) return null;

  const config = roleConfig[user.role] || roleConfig.citizen;

  // Compute live metrics based on user role
  let metrics = [];

  if (user.role === "citizen") {
    const myComplaints = complaints.filter(
      (c) => c.reportedBy === user.name || !c.reportedBy
    );
    const pendingCount = myComplaints.filter(
      (c) => c.status === "Pending" || c.status === "In Progress"
    ).length;
    const resolvedCount = myComplaints.filter(
      (c) => c.status === "Resolved"
    ).length;
    const scheduledPickups = (pickups || []).filter(
      (p) => p.status === "Requested" || p.status === "Scheduled"
    ).length;

    metrics = [
      { label: "Active Issues", value: pendingCount, icon: IconClock, color: "pending" },
      { label: "Resolved Issues", value: resolvedCount, icon: IconCheckCircle, color: "resolved" },
      { label: "Scheduled Pickups", value: scheduledPickups, icon: IconPackage, color: "progress" },
    ];
  } else if (user.role === "crew") {
    const pendingTasks = complaints.filter(
      (c) => c.status === "Pending" || c.status === "In Progress"
    ).length;
    const resolvedToday = complaints.filter(
      (c) => c.status === "Resolved"
    ).length;
    const activePickups = (pickups || []).filter(
      (p) => p.status === "Scheduled" || p.status === "In Progress"
    ).length;

    metrics = [
      { label: "Open Tasks", value: pendingTasks, icon: IconClock, color: "pending" },
      { label: "Completed", value: resolvedToday, icon: IconCheckCircle, color: "resolved" },
      { label: "Bulk Dispatches", value: activePickups, icon: IconPackage, color: "progress" },
    ];
  } else if (user.role === "admin") {
    const totalComplaints = complaints.length;
    const pendingComplaints = complaints.filter(
      (c) => c.status === "Pending"
    ).length;
    const inProgress = complaints.filter(
      (c) => c.status === "In Progress"
    ).length;

    metrics = [
      { label: "Total Complaints", value: totalComplaints, icon: IconClipboard, color: "progress" },
      { label: "Pending Triage", value: pendingComplaints, icon: IconClock, color: "pending" },
      { label: "In Progress", value: inProgress, icon: IconBroom, color: "resolved" },
    ];
  }

  return (
    <div className="home-dashboard">
      {/* Hero Welcome Banner */}
      <header className="home-hero">
        <div className="home-hero-text">
          <div className="home-eyebrow">
            <span className="live-dot" />
            <span>{roleBadgeNames[user.role] || user.role}</span>
            <span className="eyebrow-sep">&bull;</span>
            <span>Welcome, {user.name}</span>
          </div>
          <h1 className="home-title">{config.heading}</h1>
          <p className="home-subtitle">{config.blurb}</p>
        </div>

        {config.primaryAction && (
          <div className="home-hero-actions">
            <button
              className="home-primary-btn"
              onClick={() => navigate(config.primaryAction.to)}
            >
              <config.primaryAction.icon />
              <span>{config.primaryAction.label}</span>
            </button>
          </div>
        )}
      </header>

      {/* Overview Metric Highlights */}
      {metrics.length > 0 && (
        <div className="home-metrics-grid">
          {metrics.map((m, idx) => (
            <div key={idx} className={`home-metric-card metric-${m.color}`}>
              <div className="home-metric-icon">
                <m.icon />
              </div>
              <div className="home-metric-info">
                <span className="home-metric-value">{m.value}</span>
                <span className="home-metric-label">{m.label}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Action Cards Grid */}
      <section className="home-section">
        <div className="home-section-header">
          <h2>Quick Actions & Services</h2>
          <span className="home-section-hint">Select a card to navigate</span>
        </div>

        <div className="home-actions-grid">
          {config.actions.map((a) => (
            <div
              key={a.to}
              className={`home-action-card ${a.featured ? "featured" : ""}`}
              onClick={() => navigate(a.to)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(a.to);
                }
              }}
            >
              <div className="action-card-top">
                <div className="action-card-icon">
                  <a.icon />
                </div>
                <span className="action-card-arrow">
                  <IconArrowRight />
                </span>
              </div>
              <div className="action-card-body">
                <h3 className="action-card-title">{a.label}</h3>
                <p className="action-card-desc">{a.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

