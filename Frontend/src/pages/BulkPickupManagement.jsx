import { useMemo, useState } from "react";
import { useBulkPickup } from "../context/BulkPickupContext";
import { useOperational } from "../context/OperationalContext";
import { useToast } from "../context/ToastContext";
import {
  IconPackage,
  IconCalendar,
  IconClock,
  IconCheckCircle,
  IconAlertTriangle,
  IconSearch,
  IconX,
} from "../components/Icons";

const STATUS_FILTERS = ["All", "Requested", "Scheduled", "Out for Pickup", "Collected", "Cancelled"];
const ASSIGNABLE_STATUSES = ["Requested", "Scheduled", "Out for Pickup", "Collected", "Cancelled"];

export default function BulkPickupManagement() {
  const { pickups, updatePickup } = useBulkPickup();
  const { workforce, vehicles } = useOperational();
  const { notify } = useToast();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [assigning, setAssigning] = useState(null);

  const metrics = useMemo(() => {
    const count = (s) => pickups.filter((p) => p.status === s).length;
    return {
      total: pickups.length,
      requested: count("Requested"),
      scheduled: count("Scheduled") + count("Out for Pickup"),
      collected: count("Collected"),
    };
  }, [pickups]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return pickups.filter((p) => {
      const matchesSearch =
        !q ||
        p.id.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        p.items.toLowerCase().includes(q) ||
        p.requestedBy.toLowerCase().includes(q) ||
        p.ward.toLowerCase().includes(q) ||
        p.address.toLowerCase().includes(q);
      const matchesStatus = statusFilter === "All" || p.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [pickups, search, statusFilter]);

  const handleSaveAssignment = async (e) => {
    e.preventDefault();
    if (!assigning) return;
    const res = await updatePickup(assigning.id, {
      status: assigning.status,
      scheduledDate: assigning.scheduledDate || null,
      assignedCrew: assigning.assignedCrew,
      assignedVehicle: assigning.assignedVehicle,
    });
    if (res.success) notify(`Pickup ${assigning.id} updated to "${assigning.status}".`, "success");
    else notify(res.error || "Could not update pickup.", "error");
    setAssigning(null);
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Operations</span>
          <h1>Bulk Pickup Management</h1>
          <p className="page-lead">
            Review citizen bulk-waste requests, assign a crew and vehicle, confirm a
            collection date, and track each pickup through to completion.
          </p>
        </div>
      </div>

      {/* KPI Overview */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon accent"><IconPackage /></div>
          <div>
            <span className="kpi-value">{metrics.total}</span>
            <span className="kpi-label">Total Requests</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon amber"><IconAlertTriangle /></div>
          <div>
            <span className="kpi-value">{metrics.requested}</span>
            <span className="kpi-label">Awaiting Scheduling</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconCalendar /></div>
          <div>
            <span className="kpi-value">{metrics.scheduled}</span>
            <span className="kpi-label">Scheduled / En Route</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon green"><IconCheckCircle /></div>
          <div>
            <span className="kpi-value">{metrics.collected}</span>
            <span className="kpi-label">Collected</span>
          </div>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="dashboard-toolbar">
        <div className="search-wrap">
          <IconSearch />
          <input
            type="text"
            className="search-input"
            placeholder="Search by ID, category, item, citizen, ward, or address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="search-clear-btn" onClick={() => setSearch("")}>
              <IconX />
            </button>
          )}
        </div>
        <div className="filters">
          {STATUS_FILTERS.map((st) => (
            <button
              key={st}
              className={statusFilter === st ? "active" : ""}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Pickup Grid */}
      <div className="card-grid">
        {filtered.length === 0 ? (
          <div className="empty-state">No bulk pickup requests match your search.</div>
        ) : (
          filtered.map((p) => (
            <div key={p.id} className="op-card bulk-card">
              <div className="op-card-header">
                <div>
                  <span className="op-id">{p.id}</span>
                  <h3 className="op-title">{p.category}</h3>
                  <span className="op-subtitle">{p.items}</span>
                </div>
                <span className={`op-status-badge status-${p.status.toLowerCase().replace(/ /g, "-")}`}>
                  {p.status}
                </span>
              </div>

              <div className="op-card-body">
                <div className="op-detail-row">
                  <span className="label">Citizen</span>
                  <span className="value font-bold">{p.requestedBy}</span>
                </div>
                <div className="op-detail-row">
                  <span className="label">Ward / Address</span>
                  <span className="value">{p.ward}</span>
                </div>
                <div className="op-detail-row">
                  <span className="label"><IconCalendar /> Preferred</span>
                  <span className="value">{p.preferredDate}</span>
                </div>
                <div className="op-detail-row">
                  <span className="label"><IconClock /> Slot</span>
                  <span className="value">{p.timeSlot}</span>
                </div>
                <div className="op-detail-row">
                  <span className="label">Load</span>
                  <span className="value">{p.loadSize} · {p.quantity} items</span>
                </div>
                <div className="op-detail-row">
                  <span className="label">Assigned Crew</span>
                  <span className="value tag">{p.assignedCrew}</span>
                </div>
                <div className="op-detail-row">
                  <span className="label">Assigned Vehicle</span>
                  <span className="value tag">{p.assignedVehicle}</span>
                </div>
                {p.notes && (
                  <div className="op-detail-row bulk-notes">
                    <span className="label">Notes</span>
                    <span className="value">{p.notes}</span>
                  </div>
                )}
              </div>

              <div className="op-card-footer">
                <button
                  className="primary-btn btn-sm"
                  onClick={() =>
                    setAssigning({
                      id: p.id,
                      status: p.status,
                      scheduledDate: p.scheduledDate || p.preferredDate || "",
                      assignedCrew: p.assignedCrew,
                      assignedVehicle: p.assignedVehicle,
                      label: `${p.id} · ${p.category}`,
                    })
                  }
                >
                  Assign / Update
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Assign / Update Modal */}
      {assigning && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Manage Pickup: {assigning.label}</h2>
              <button className="icon-btn" onClick={() => setAssigning(null)}><IconX /></button>
            </div>
            <form onSubmit={handleSaveAssignment} className="complaint-form">
              <label>
                Status
                <select
                  value={assigning.status}
                  onChange={(e) => setAssigning({ ...assigning, status: e.target.value })}
                >
                  {ASSIGNABLE_STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label>
                Confirmed Collection Date
                <input
                  type="date"
                  value={assigning.scheduledDate}
                  onChange={(e) => setAssigning({ ...assigning, scheduledDate: e.target.value })}
                />
              </label>
              <label>
                Assigned Crew
                <select
                  value={assigning.assignedCrew}
                  onChange={(e) => setAssigning({ ...assigning, assignedCrew: e.target.value })}
                >
                  <option value="Unassigned">Unassigned</option>
                  {workforce.map((w) => (
                    <option key={w.id} value={w.name}>{w.name} — {w.role}</option>
                  ))}
                </select>
              </label>
              <label>
                Assigned Vehicle
                <select
                  value={assigning.assignedVehicle}
                  onChange={(e) => setAssigning({ ...assigning, assignedVehicle: e.target.value })}
                >
                  <option value="Unassigned">Unassigned</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.plateNo}>{v.plateNo} — {v.type}</option>
                  ))}
                </select>
              </label>
              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setAssigning(null)}>Cancel</button>
                <button type="submit" className="primary-btn">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
