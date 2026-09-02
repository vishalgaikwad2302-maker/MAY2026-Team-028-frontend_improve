import { useState } from "react";
import { useOperational } from "../context/OperationalContext";
import { useToast } from "../context/ToastContext";
import { IconUsers, IconWrench, IconSearch, IconPlus, IconCheckCircle, IconAlertTriangle, IconX } from "../components/Icons";

export default function WorkforceEquipment() {
  const {
    workforce,
    equipment,
    updateWorkerStatus,
    addWorker,
    updateEquipmentStatus,
    addEquipment,
  } = useOperational();
  const { notify } = useToast();

  const [activeTab, setActiveTab] = useState("workforce"); // 'workforce' | 'equipment'
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  // Modal States
  const [showAddWorkerModal, setShowAddWorkerModal] = useState(false);
  const [showAddEqModal, setShowAddEqModal] = useState(false);

  // New Worker Form State
  const [newWorker, setNewWorker] = useState({
    name: "",
    email: "",
    password: "crew123",
    role: "Sanitation Specialist",
    shift: "Morning (06:00 - 14:00)",
    ward: "Indiranagar (Ward 12)",
    phone: "",
  });

  // New Equipment Form State
  const [newEq, setNewEq] = useState({
    name: "",
    category: "Sanitation Tools",
    location: "Central Depot",
    stockTotal: 5,
  });

  // Worker edit modal
  const [editingWorker, setEditingWorker] = useState(null);
  // Equipment edit modal
  const [editingEq, setEditingEq] = useState(null);

  // Stats calculation
  const totalOnDuty = workforce.filter((w) => w.status === "On Duty").length;
  const totalAvailableWorkers = workforce.filter((w) => w.status === "Available").length;
  const totalInUseEq = equipment.filter((e) => e.status === "In Use").length;
  const totalMaintEq = equipment.filter((e) => e.status === "Maintenance").length;

  // Filtered Workforce
  const filteredWorkforce = workforce.filter((w) => {
    const q = search.trim().toLowerCase();
    const matchesSearch =
      !q ||
      w.name.toLowerCase().includes(q) ||
      w.role.toLowerCase().includes(q) ||
      w.ward.toLowerCase().includes(q);
    const matchesStatus = statusFilter === "All" || w.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Filtered Equipment
  const filteredEquipment = equipment.filter((e) => {
    const q = search.trim().toLowerCase();
    const matchesSearch =
      !q ||
      e.name.toLowerCase().includes(q) ||
      e.category.toLowerCase().includes(q) ||
      e.location.toLowerCase().includes(q);
    const matchesStatus = statusFilter === "All" || e.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCreateWorker = async (e) => {
    e.preventDefault();
    if (!newWorker.name || !newWorker.phone || !newWorker.email) {
      notify("Please fill in crew member name, login email, and phone number.", "error");
      return;
    }
    const res = await addWorker(newWorker);
    if (res?.error) {
      notify(res.error, "error");
      return;
    }
    notify(`Successfully onboarded ${newWorker.name} with crew portal access!`, "success");
    setNewWorker({
      name: "",
      email: "",
      password: "crew123",
      role: "Sanitation Specialist",
      shift: "Morning (06:00 - 14:00)",
      ward: "Indiranagar (Ward 12)",
      phone: "",
    });
    setShowAddWorkerModal(false);
  };

  const handleCreateEquipment = (e) => {
    e.preventDefault();
    if (!newEq.name) {
      notify("Please enter equipment name.", "error");
      return;
    }
    addEquipment(newEq);
    notify(`Added ${newEq.name} to equipment inventory!`, "success");
    setNewEq({
      name: "",
      category: "Sanitation Tools",
      location: "Central Depot",
      stockTotal: 5,
    });
    setShowAddEqModal(false);
  };

  const handleUpdateWorkerState = (e) => {
    e.preventDefault();
    if (!editingWorker) return;
    updateWorkerStatus(editingWorker.id, editingWorker.status, editingWorker.assignedTask);
    notify(`Updated status for ${editingWorker.name}`, "info");
    setEditingWorker(null);
  };

  const handleUpdateEqState = (e) => {
    e.preventDefault();
    if (!editingEq) return;
    updateEquipmentStatus(editingEq.id, editingEq.status, editingEq.assignedTo);
    notify(`Updated equipment allocation for ${editingEq.name}`, "info");
    setEditingEq(null);
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Municipal Operations</span>
          <h1>Workforce & Equipment Allocation</h1>
          <p className="page-lead">
            Manage sanitation personnel shifts, duty rosters, and allocate machinery & gear across municipal wards.
          </p>
        </div>
        <div className="page-actions">
          {activeTab === "workforce" ? (
            <button className="primary-btn" onClick={() => setShowAddWorkerModal(true)}>
              <IconPlus /> Onboard Crew Member
            </button>
          ) : (
            <button className="primary-btn" onClick={() => setShowAddEqModal(true)}>
              <IconPlus /> Add Equipment
            </button>
          )}
        </div>
      </div>

      {/* KPI Overview Banner */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon accent"><IconUsers /></div>
          <div>
            <span className="kpi-value">{totalOnDuty} / {workforce.length}</span>
            <span className="kpi-label">On-Duty Workforce</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon green"><IconCheckCircle /></div>
          <div>
            <span className="kpi-value">{totalAvailableWorkers}</span>
            <span className="kpi-label">Available Staff</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconWrench /></div>
          <div>
            <span className="kpi-value">{totalInUseEq}</span>
            <span className="kpi-label">Equipment In Use</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon amber"><IconAlertTriangle /></div>
          <div>
            <span className="kpi-value">{totalMaintEq}</span>
            <span className="kpi-label">Under Maintenance</span>
          </div>
        </div>
      </div>

      {/* Sub-tab Navigation */}
      <div className="op-tab-bar">
        <button
          className={`op-tab ${activeTab === "workforce" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("workforce");
            setStatusFilter("All");
          }}
        >
          <IconUsers /> Personnel & Roster ({workforce.length})
        </button>
        <button
          className={`op-tab ${activeTab === "equipment" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("equipment");
            setStatusFilter("All");
          }}
        >
          <IconWrench /> Equipment Inventory ({equipment.length})
        </button>
      </div>

      {/* Search and Filters Bar */}
      <div className="dashboard-toolbar">
        <div className="search-wrap">
          <IconSearch />
          <input
            type="text"
            className="search-input"
            placeholder={
              activeTab === "workforce"
                ? "Search worker name, role, ward..."
                : "Search equipment name, category, depot..."
            }
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
          {(activeTab === "workforce"
            ? ["All", "On Duty", "Available", "Off Duty"]
            : ["All", "Available", "In Use", "Maintenance"]
          ).map((st) => (
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

      {/* TAB 1: WORKFORCE CONTENT */}
      {activeTab === "workforce" && (
        <div className="card-grid">
          {filteredWorkforce.length === 0 ? (
            <div className="empty-state">No workforce personnel match your filter.</div>
          ) : (
            filteredWorkforce.map((w) => (
              <div key={w.id} className="op-card">
                <div className="op-card-header">
                  <div>
                    <span className="op-id">{w.id}</span>
                    <h3 className="op-title">{w.name}</h3>
                    <span className="op-subtitle">{w.role}</span>
                  </div>
                  <span className={`op-status-badge status-${w.status.toLowerCase().replace(" ", "-")}`}>
                    {w.status}
                  </span>
                </div>
                <div className="op-card-body">
                  <div className="op-detail-row">
                    <span className="label">Shift:</span>
                    <span className="value">{w.shift}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Assigned Ward:</span>
                    <span className="value">{w.ward}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Current Task:</span>
                    <span className="value tag">{w.assignedTask}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Contact:</span>
                    <span className="value">{w.phone}</span>
                  </div>
                </div>
                <div className="op-card-footer">
                  <button
                    className="secondary-btn btn-sm"
                    onClick={() => setEditingWorker({ ...w })}
                  >
                    Manage Allocation
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB 2: EQUIPMENT CONTENT */}
      {activeTab === "equipment" && (
        <div className="card-grid">
          {filteredEquipment.length === 0 ? (
            <div className="empty-state">No equipment items match your filter.</div>
          ) : (
            filteredEquipment.map((e) => (
              <div key={e.id} className="op-card">
                <div className="op-card-header">
                  <div>
                    <span className="op-id">{e.id}</span>
                    <h3 className="op-title">{e.name}</h3>
                    <span className="op-subtitle">{e.category}</span>
                  </div>
                  <span className={`op-status-badge status-${e.status.toLowerCase().replace(" ", "-")}`}>
                    {e.status}
                  </span>
                </div>
                <div className="op-card-body">
                  <div className="op-detail-row">
                    <span className="label">Location:</span>
                    <span className="value">{e.location}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Condition:</span>
                    <span className="value badge-neutral">{e.condition}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Allocated To:</span>
                    <span className="value tag">{e.assignedTo}</span>
                  </div>
                  <div className="op-detail-row">
                    <span className="label">Stock Available:</span>
                    <span className="value font-bold">
                      {e.stockAvailable} / {e.stockTotal} Units
                    </span>
                  </div>
                </div>
                <div className="op-card-footer">
                  <button
                    className="secondary-btn btn-sm"
                    onClick={() => setEditingEq({ ...e })}
                  >
                    Reallocate & Status
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* MODAL: Onboard Crew Member */}
      {showAddWorkerModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Onboard Crew Personnel</h2>
              <button className="icon-btn" onClick={() => setShowAddWorkerModal(false)}><IconX /></button>
            </div>
            <form onSubmit={handleCreateWorker} className="complaint-form">
              <label>
                Worker Full Name
                <input
                  type="text"
                  required
                  placeholder="e.g. Rajesh Kumar"
                  value={newWorker.name}
                  onChange={(e) => setNewWorker({ ...newWorker, name: e.target.value })}
                />
              </label>

              <label>
                Portal Login Email
                <input
                  type="email"
                  required
                  placeholder="e.g. rajesh.crew@smartsweep.gov"
                  value={newWorker.email}
                  onChange={(e) => setNewWorker({ ...newWorker, email: e.target.value })}
                />
              </label>

              <label>
                Initial Login Password
                <input
                  type="text"
                  required
                  placeholder="Default: crew123"
                  value={newWorker.password}
                  onChange={(e) => setNewWorker({ ...newWorker, password: e.target.value })}
                />
              </label>

              <label>
                Role & Designation
                <select
                  value={newWorker.role}
                  onChange={(e) => setNewWorker({ ...newWorker, role: e.target.value })}
                >
                  <option value="Sanitation Specialist">Sanitation Specialist</option>
                  <option value="Crew Lead & Heavy Sweeper">Crew Lead & Heavy Sweeper</option>
                  <option value="Compactor Operator">Compactor Operator</option>
                  <option value="Safety & Biohazard Inspector">Safety & Biohazard Inspector</option>
                  <option value="Rapid Response Crew">Rapid Response Crew</option>
                </select>
              </label>

              <label>
                Shift Roster
                <select
                  value={newWorker.shift}
                  onChange={(e) => setNewWorker({ ...newWorker, shift: e.target.value })}
                >
                  <option value="Morning (06:00 - 14:00)">Morning (06:00 - 14:00)</option>
                  <option value="Evening (14:00 - 22:00)">Evening (14:00 - 22:00)</option>
                  <option value="Night (22:00 - 06:00)">Night (22:00 - 06:00)</option>
                </select>
              </label>

              <label>
                Assigned Ward / Zone
                <input
                  type="text"
                  required
                  placeholder="e.g. Indiranagar (Ward 12)"
                  value={newWorker.ward}
                  onChange={(e) => setNewWorker({ ...newWorker, ward: e.target.value })}
                />
              </label>

              <label>
                Contact Phone
                <input
                  type="text"
                  required
                  placeholder="+91 98765 00000"
                  value={newWorker.phone}
                  onChange={(e) => setNewWorker({ ...newWorker, phone: e.target.value })}
                />
              </label>

              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setShowAddWorkerModal(false)}>Cancel</button>
                <button type="submit" className="primary-btn">Onboard & Provision Access</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Add Equipment */}
      {showAddEqModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Add New Equipment</h2>
              <button className="icon-btn" onClick={() => setShowAddEqModal(false)}><IconX /></button>
            </div>
            <form onSubmit={handleCreateEquipment} className="complaint-form">
              <label>
                Equipment / Tool Name
                <input
                  type="text"
                  required
                  placeholder="e.g. Hydraulic Washer Unit"
                  value={newEq.name}
                  onChange={(e) => setNewEq({ ...newEq, name: e.target.value })}
                />
              </label>
              <label>
                Category
                <select
                  value={newEq.category}
                  onChange={(e) => setNewEq({ ...newEq, category: e.target.value })}
                >
                  <option value="Sanitation Tools">Sanitation Tools</option>
                  <option value="Heavy Machinery">Heavy Machinery</option>
                  <option value="Vehicular Equipment">Vehicular Equipment</option>
                  <option value="Safety Gear">Safety Gear</option>
                  <option value="Waste Processing">Waste Processing</option>
                </select>
              </label>
              <label>
                Location / Depot
                <input
                  type="text"
                  required
                  placeholder="e.g. Central Depot"
                  value={newEq.location}
                  onChange={(e) => setNewEq({ ...newEq, location: e.target.value })}
                />
              </label>
              <label>
                Total Units Quantity
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={newEq.stockTotal}
                  onChange={(e) => setNewEq({ ...newEq, stockTotal: e.target.value })}
                />
              </label>
              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setShowAddEqModal(false)}>Cancel</button>
                <button type="submit" className="primary-btn">Add to Inventory</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Edit Worker Allocation */}
      {editingWorker && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Update Personnel Duty: {editingWorker.name}</h2>
              <button className="icon-btn" onClick={() => setEditingWorker(null)}><IconX /></button>
            </div>
            <form onSubmit={handleUpdateWorkerState} className="complaint-form">
              <label>
                Duty Status
                <select
                  value={editingWorker.status}
                  onChange={(e) => setEditingWorker({ ...editingWorker, status: e.target.value })}
                >
                  <option value="On Duty">On Duty</option>
                  <option value="Available">Available</option>
                  <option value="Off Duty">Off Duty</option>
                </select>
              </label>
              <label>
                Assigned Task / Location
                <input
                  type="text"
                  value={editingWorker.assignedTask}
                  onChange={(e) => setEditingWorker({ ...editingWorker, assignedTask: e.target.value })}
                />
              </label>
              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setEditingWorker(null)}>Cancel</button>
                <button type="submit" className="primary-btn">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Edit Equipment Allocation */}
      {editingEq && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Reallocate Equipment: {editingEq.name}</h2>
              <button className="icon-btn" onClick={() => setEditingEq(null)}><IconX /></button>
            </div>
            <form onSubmit={handleUpdateEqState} className="complaint-form">
              <label>
                Status
                <select
                  value={editingEq.status}
                  onChange={(e) => setEditingEq({ ...editingEq, status: e.target.value })}
                >
                  <option value="Available">Available</option>
                  <option value="In Use">In Use</option>
                  <option value="Maintenance">Maintenance</option>
                </select>
              </label>
              <label>
                Assigned Staff / Crew
                <input
                  type="text"
                  value={editingEq.assignedTo}
                  onChange={(e) => setEditingEq({ ...editingEq, assignedTo: e.target.value })}
                />
              </label>
              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setEditingEq(null)}>Cancel</button>
                <button type="submit" className="primary-btn">Update Equipment</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
