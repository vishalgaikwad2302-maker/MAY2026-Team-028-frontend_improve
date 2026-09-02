import { useState } from "react";
import { useOperational } from "../context/OperationalContext";
import { useComplaints } from "../context/ComplaintsContext";
import { useToast } from "../context/ToastContext";
import {
  IconTruck,
  IconSearch,
  IconPlus,
  IconX,
  IconCheckCircle,
  IconUsers,
  IconWrench,
} from "../components/Icons";

const MUNICIPAL_WARDS = [
  "Indiranagar (Ward 12)",
  "Koramangala (Ward 08)",
  "MG Road (Ward 04)",
  "Whitefield (Ward 15)",
  "Central Depot (All Wards)",
];

const VEHICLE_TYPES = [
  "Mini Tipper",
  "Compactor",
  "Road Sweeper",
  "Inspection Van",
  "Hazmat Van",
];

const PAYLOAD_CAPACITIES = [
  "1.5 Tons",
  "2.5 Tons",
  "3.0 Tons",
  "4.0 Tons",
  "8.5 Tons",
  "5 Passengers",
];

function normalizeStatus(status) {
  if (!status) return "Available";
  const s = status.toLowerCase();
  if (s === "dispatched" || s === "en route" || s === "on site" || s === "in use") {
    return "Dispatched";
  }
  if (s === "maintenance" || s === "repair") {
    return "Maintenance";
  }
  return "Available";
}

export default function VehicleAssignment() {
  const { vehicles = [], updateVehicleStatus, addVehicle, workforce = [] } = useOperational();
  const { complaints = [] } = useComplaints();
  const { notify } = useToast();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  // Modal States
  const [showAddVehicleModal, setShowAddVehicleModal] = useState(false);
  const [assigningVehicle, setAssigningVehicle] = useState(null);

  const [newV, setNewV] = useState({
    plateNo: "",
    model: "Electric Tipper Truck",
    type: "Mini Tipper",
    capacity: "3.0 Tons",
    ward: "Indiranagar (Ward 12)",
    driver: "Unassigned",
  });

  // Calculate Metrics
  const totalFleet = vehicles.length;
  const totalAvailable = vehicles.filter((v) => normalizeStatus(v.status) === "Available").length;
  const totalDispatched = vehicles.filter((v) => normalizeStatus(v.status) === "Dispatched").length;
  const totalMaintenance = vehicles.filter((v) => normalizeStatus(v.status) === "Maintenance").length;

  // Filtered List
  const filteredVehicles = vehicles.filter((v) => {
    const q = search.trim().toLowerCase();
    const currentNormStatus = normalizeStatus(v.status);

    const matchesSearch =
      !q ||
      v.plateNo?.toLowerCase().includes(q) ||
      v.model?.toLowerCase().includes(q) ||
      v.driver?.toLowerCase().includes(q) ||
      v.ward?.toLowerCase().includes(q) ||
      v.type?.toLowerCase().includes(q) ||
      v.assignedTask?.toLowerCase().includes(q);

    const matchesStatus = statusFilter === "All" || currentNormStatus === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCreateVehicle = (e) => {
    e.preventDefault();
    if (!newV.plateNo.trim()) {
      notify("Please provide a valid license plate number.", "error");
      return;
    }
    addVehicle({
      ...newV,
      plateNo: newV.plateNo.trim().toUpperCase(),
      status: "Available",
      assignedTask: "Standby at Central Depot",
    });
    notify(`Vehicle ${newV.plateNo.toUpperCase()} registered in municipal fleet!`, "success");
    setNewV({
      plateNo: "",
      model: "Electric Tipper Truck",
      type: "Mini Tipper",
      capacity: "3.0 Tons",
      ward: "Indiranagar (Ward 12)",
      driver: "Unassigned",
    });
    setShowAddVehicleModal(false);
  };

  const handleReturnToDepot = (v) => {
    updateVehicleStatus(
      v.id,
      "Available",
      "Unassigned",
      "Standby at Central Depot",
      v.ward || "Central Depot (All Wards)"
    );
    notify(`Vehicle ${v.plateNo} returned to depot and marked Available.`, "success");
  };

  const handleOpenDispatch = (v, defaultStatus = null) => {
    const currentNorm = normalizeStatus(v.status);
    setAssigningVehicle({
      ...v,
      status: defaultStatus || (currentNorm === "Available" ? "Dispatched" : currentNorm),
      driver: v.driver && v.driver !== "Unassigned" ? v.driver : (workforce[0]?.name || "Unassigned"),
      ward: v.ward || MUNICIPAL_WARDS[0],
      assignedTask: v.assignedTask && v.assignedTask !== "Standby at Central Depot"
        ? v.assignedTask
        : "Routine Ward Patrol & Inspection",
    });
  };

  const handleSaveAssignment = (e) => {
    e.preventDefault();
    if (!assigningVehicle) return;

    let finalDriver = assigningVehicle.driver;
    let finalTask = assigningVehicle.assignedTask;

    if (assigningVehicle.status === "Available") {
      finalDriver = "Unassigned";
      finalTask = "Standby at Central Depot";
    }

    updateVehicleStatus(
      assigningVehicle.id,
      assigningVehicle.status,
      finalDriver,
      finalTask,
      assigningVehicle.ward
    );

    notify(`Vehicle dispatch updated for ${assigningVehicle.plateNo}`, "success");
    setAssigningVehicle(null);
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Fleet Operations</span>
          <h1>Vehicle & Fleet Assignment</h1>
          <p className="page-lead">
            Manage municipal fleet status, assign dedicated drivers and crews, and dispatch vehicles to active sanitation zones.
          </p>
        </div>
        <div className="page-actions">
          <button className="primary-btn" onClick={() => setShowAddVehicleModal(true)}>
            <IconPlus /> Register Vehicle
          </button>
        </div>
      </div>

      {/* KPI Overview Banner */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon accent"><IconTruck /></div>
          <div>
            <span className="kpi-value">{totalFleet}</span>
            <span className="kpi-label">Total Fleet</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon green"><IconCheckCircle /></div>
          <div>
            <span className="kpi-value">{totalAvailable}</span>
            <span className="kpi-label">Available in Depot</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconUsers /></div>
          <div>
            <span className="kpi-value">{totalDispatched}</span>
            <span className="kpi-label">Active Dispatched</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon amber"><IconWrench /></div>
          <div>
            <span className="kpi-value">{totalMaintenance}</span>
            <span className="kpi-label">In Maintenance</span>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="dashboard-toolbar">
        <div className="search-wrap">
          <IconSearch />
          <input
            type="text"
            className="search-input"
            placeholder="Search by license plate, vehicle model, driver, ward, or task..."
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
          {["All", "Available", "Dispatched", "Maintenance"].map((st) => (
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

      {/* Vehicle Grid */}
      <div className="card-grid">
        {filteredVehicles.length === 0 ? (
          <div className="empty-state">No fleet vehicles match your filter criteria.</div>
        ) : (
          filteredVehicles.map((v) => {
            const normStatus = normalizeStatus(v.status);
            return (
              <div key={v.id} className="op-card fleet-card">
                <div className="op-card-header">
                  <div className="fleet-badge-wrap">
                    <span className="op-id">{v.id}</span>
                    <h3 className="op-title">{v.plateNo}</h3>
                    <span className="op-subtitle">{v.model} • {v.type}</span>
                  </div>
                  <span className={`op-status-badge status-${normStatus.toLowerCase()}`}>
                    {normStatus}
                  </span>
                </div>

                <div className="op-card-body">
                  <div className="op-detail-row">
                    <span className="label">Driver & Crew:</span>
                    <span className="value font-bold">{v.driver || "Unassigned"}</span>
                  </div>

                  <div className="op-detail-row">
                    <span className="label">Operational Ward:</span>
                    <span className="value">{v.ward || "Central Depot"}</span>
                  </div>

                  <div className="op-detail-row">
                    <span className="label">Assigned Mission:</span>
                    <span className="value tag">{v.assignedTask || "Standby at Central Depot"}</span>
                  </div>

                  <div className="op-detail-row">
                    <span className="label">Payload Capacity:</span>
                    <span className="value">{v.capacity}</span>
                  </div>

                  {v.lastMaintenance && (
                    <div className="op-detail-row">
                      <span className="label">Last Service:</span>
                      <span className="value">{v.lastMaintenance}</span>
                    </div>
                  )}
                </div>

                <div className="op-card-footer">
                  {normStatus === "Dispatched" ? (
                    <div className="fleet-actions-wrap">
                      <button
                        className="primary-btn btn-sm"
                        onClick={() => handleOpenDispatch(v)}
                      >
                        Update Dispatch
                      </button>
                      <button
                        className="secondary-btn btn-sm"
                        onClick={() => handleReturnToDepot(v)}
                      >
                        Return to Depot
                      </button>
                    </div>
                  ) : normStatus === "Available" ? (
                    <div className="fleet-actions-wrap">
                      <button
                        className="primary-btn btn-sm"
                        onClick={() => handleOpenDispatch(v, "Dispatched")}
                      >
                        Dispatch Vehicle
                      </button>
                    </div>
                  ) : (
                    <div className="fleet-actions-wrap">
                      <button
                        className="primary-btn btn-sm"
                        onClick={() => handleReturnToDepot(v)}
                      >
                        Mark Available
                      </button>
                      <button
                        className="secondary-btn btn-sm"
                        onClick={() => handleOpenDispatch(v)}
                      >
                        Edit Status
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* MODAL: Register Vehicle */}
      {showAddVehicleModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Register New Fleet Vehicle</h2>
              <button className="icon-btn" onClick={() => setShowAddVehicleModal(false)}><IconX /></button>
            </div>
            <form onSubmit={handleCreateVehicle} className="complaint-form">
              <label>
                License Plate Number
                <input
                  type="text"
                  required
                  placeholder="e.g. KA-01-EV-2026"
                  value={newV.plateNo}
                  onChange={(e) => setNewV({ ...newV, plateNo: e.target.value })}
                />
              </label>

              <label>
                Vehicle Type
                <select
                  value={newV.type}
                  onChange={(e) => setNewV({ ...newV, type: e.target.value })}
                >
                  {VEHICLE_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </label>

              <label>
                Model Name
                <input
                  type="text"
                  required
                  placeholder="e.g. Electric Heavy Duty Sweeper"
                  value={newV.model}
                  onChange={(e) => setNewV({ ...newV, model: e.target.value })}
                />
              </label>

              <label>
                Payload Capacity
                <select
                  value={newV.capacity}
                  onChange={(e) => setNewV({ ...newV, capacity: e.target.value })}
                >
                  {PAYLOAD_CAPACITIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>

              <label>
                Base Operational Ward
                <select
                  value={newV.ward}
                  onChange={(e) => setNewV({ ...newV, ward: e.target.value })}
                >
                  {MUNICIPAL_WARDS.map((w) => (
                    <option key={w} value={w}>{w}</option>
                  ))}
                </select>
              </label>

              <label>
                Initial Driver / Crew Lead
                <select
                  value={newV.driver}
                  onChange={(e) => setNewV({ ...newV, driver: e.target.value })}
                >
                  <option value="Unassigned">Unassigned (Depot Standby)</option>
                  {workforce.map((w) => (
                    <option key={w.id} value={w.name}>
                      {w.name} ({w.role})
                    </option>
                  ))}
                </select>
              </label>

              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setShowAddVehicleModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="primary-btn">
                  Register Vehicle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Dispatch / Reassign Vehicle */}
      {assigningVehicle && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Dispatch Vehicle: {assigningVehicle.plateNo}</h2>
              <button className="icon-btn" onClick={() => setAssigningVehicle(null)}><IconX /></button>
            </div>
            <form onSubmit={handleSaveAssignment} className="complaint-form">
              <label>
                Operating Status
                <select
                  value={assigningVehicle.status}
                  onChange={(e) => {
                    const nextStatus = e.target.value;
                    setAssigningVehicle((prev) => ({
                      ...prev,
                      status: nextStatus,
                      ...(nextStatus === "Available"
                        ? { driver: "Unassigned", assignedTask: "Standby at Central Depot" }
                        : {}),
                    }));
                  }}
                >
                  <option value="Dispatched">Dispatched (In Use)</option>
                  <option value="Available">Available (In Depot)</option>
                  <option value="Maintenance">Maintenance (Under Repair)</option>
                </select>
              </label>

              <label>
                Driver & Crew Lead
                <select
                  value={assigningVehicle.driver}
                  onChange={(e) => setAssigningVehicle({ ...assigningVehicle, driver: e.target.value })}
                  disabled={assigningVehicle.status === "Available"}
                >
                  <option value="Unassigned">Unassigned</option>
                  {workforce.map((w) => (
                    <option key={w.id} value={w.name}>
                      {w.name} — {w.role} [{w.status}]
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Operational Ward
                <select
                  value={assigningVehicle.ward}
                  onChange={(e) => setAssigningVehicle({ ...assigningVehicle, ward: e.target.value })}
                >
                  {MUNICIPAL_WARDS.map((w) => (
                    <option key={w} value={w}>{w}</option>
                  ))}
                </select>
              </label>

              <label>
                Assigned Mission / Case Reference
                <select
                  value={assigningVehicle.assignedTask}
                  onChange={(e) => setAssigningVehicle({ ...assigningVehicle, assignedTask: e.target.value })}
                  disabled={assigningVehicle.status === "Available"}
                >
                  <option value="Standby at Central Depot">Standby at Central Depot</option>
                  <option value="Routine Ward Patrol & Inspection">Routine Ward Patrol & Inspection</option>
                  <option value="Special Sanitation & Waste Drive">Special Sanitation & Waste Drive</option>
                  {complaints.map((c) => (
                    <option key={c.id} value={`Case #${String(c.id).padStart(4, "0")} (${c.location})`}>
                      Case #{String(c.id).padStart(4, "0")} — {c.location} [{c.status}]
                    </option>
                  ))}
                </select>
              </label>

              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setAssigningVehicle(null)}>
                  Cancel
                </button>
                <button type="submit" className="primary-btn">
                  Save & Apply Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
