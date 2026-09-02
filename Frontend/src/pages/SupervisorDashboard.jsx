import { useMemo, useState } from "react";
import { useComplaints } from "../context/ComplaintsContext";
import { useOperational } from "../context/OperationalContext";
import { useToast } from "../context/ToastContext";
import { getDuplicateMatches } from "../utils/duplicateDetection";
import ComplaintCard from "../components/ComplaintCard";
import { IconSearch, IconSliders, IconX, IconUserPlus } from "../components/Icons";

// Kept in sync with the hazard options offered on ReportComplaint /
// ComplaintDetail's edit form — "None" is intentionally left out of the
// filter list since filtering for "no hazard" isn't a useful admin query.
const HAZARD_TYPES = [
  "Foul Smell",
  "Overflowing Bin",
  "Mosquito Breeding",
  "Risk to Children",
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
];

const DEFAULT_ADVANCED = {
  hazard: "All",
  needsHelpOnly: false,
  dateFrom: "",
  dateTo: "",
  sortBy: "newest",
};

export default function SupervisorDashboard() {
  const { complaints, updateStatus } = useComplaints();
  const { workforce = [] } = useOperational();
  const { notify } = useToast();
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advanced, setAdvanced] = useState(DEFAULT_ADVANCED);

  // Assignment Modal States
  const [assigningComplaint, setAssigningComplaint] = useState(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState("");
  const [assignmentNotes, setAssignmentNotes] = useState("");

  const advancedActive =
    advanced.hazard !== "All" ||
    advanced.needsHelpOnly ||
    advanced.dateFrom ||
    advanced.dateTo ||
    advanced.sortBy !== "newest";

  const handleAdvancedChange = (field, value) =>
    setAdvanced((prev) => ({ ...prev, [field]: value }));

  const clearFilters = () => {
    setSearch("");
    setAdvanced(DEFAULT_ADVANCED);
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();

    return complaints
      .filter((c) => filter === "All" || c.status === filter)
      .filter((c) => {
        if (!q) return true;
        const caseNo = String(c.id).padStart(4, "0");
        return (
          c.location?.toLowerCase().includes(q) ||
          c.description?.toLowerCase().includes(q) ||
          c.reportedBy?.toLowerCase().includes(q) ||
          caseNo.includes(q) ||
          `#${caseNo}`.includes(q)
        );
      })
      .filter((c) => advanced.hazard === "All" || c.hazard === advanced.hazard)
      .filter((c) => !advanced.needsHelpOnly || c.needsHelp)
      .filter((c) => !advanced.dateFrom || c.createdAt >= advanced.dateFrom)
      .filter((c) => !advanced.dateTo || c.createdAt <= advanced.dateTo)
      .sort((a, b) =>
        advanced.sortBy === "oldest"
          ? a.createdAt.localeCompare(b.createdAt)
          : b.createdAt.localeCompare(a.createdAt)
      );
  }, [complaints, filter, search, advanced]);

  const handleAssign = (id) => {
    const complaint = complaints.find((c) => c.id === id);
    if (!complaint) return;
    const dupes = getDuplicateMatches(complaint, complaints);
    if (dupes.length) {
      const caseList = dupes
        .map((m) => `#${String(m.complaint.id).padStart(4, "0")}`)
        .join(", ");
      const proceed = window.confirm(
        `This looks like a possible duplicate of case ${caseList}. Assign crew anyway?`
      );
      if (!proceed) return;
    }

    setAssigningComplaint(complaint);
    setSelectedWorkerId(workforce[0]?.id || "");
    setAssignmentNotes("");
  };

  const handleConfirmAssignment = async (e) => {
    e.preventDefault();
    if (!assigningComplaint || !selectedWorkerId) return;

    const worker = workforce.find((w) => w.id === selectedWorkerId);
    const workerName = worker ? worker.name : selectedWorkerId;

    const result = await updateStatus(assigningComplaint.id, "In Progress", {
      assignedTo: workerName,
      assignedWorkerId: selectedWorkerId,
      instructions: assignmentNotes.trim() || undefined,
      assignedAt: new Date().toISOString().slice(0, 10),
    });

    if (result.success) {
      notify(`Assigned Case #${String(assigningComplaint.id).padStart(4, "0")} to ${workerName}`, "success");
      setAssigningComplaint(null);
      setSelectedWorkerId("");
      setAssignmentNotes("");
    } else {
      notify(result.error || "Couldn't assign crew.", "error");
    }
  };

  return (
    <div className="page">
      <h1>Supervisor Dashboard</h1>

      <div className="dashboard-toolbar">
        <div className="search-wrap">
          <IconSearch />
          <input
            type="text"
            className="search-input"
            placeholder="Search by location, description, case no. or reporter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              <IconX />
            </button>
          )}
        </div>
        <button
          type="button"
          className={`filter-toggle-btn ${showAdvanced ? "active" : ""} ${advancedActive ? "has-value" : ""}`}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          <IconSliders /> Advanced Filters
        </button>
      </div>

      {showAdvanced && (
        <div className="adv-filters-panel">
          <div className="adv-filters-grid">
            <label>
              Hazard Type
              <select
                value={advanced.hazard}
                onChange={(e) => handleAdvancedChange("hazard", e.target.value)}
              >
                <option value="All">All Hazards</option>
                {HAZARD_TYPES.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Sort By
              <select
                value={advanced.sortBy}
                onChange={(e) => handleAdvancedChange("sortBy", e.target.value)}
              >
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Reported From
              <input
                type="date"
                value={advanced.dateFrom}
                onChange={(e) => handleAdvancedChange("dateFrom", e.target.value)}
              />
            </label>

            <label>
              Reported To
              <input
                type="date"
                value={advanced.dateTo}
                onChange={(e) => handleAdvancedChange("dateTo", e.target.value)}
              />
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={advanced.needsHelpOnly}
                onChange={(e) => handleAdvancedChange("needsHelpOnly", e.target.checked)}
              />
              Support Requested Only
            </label>
          </div>

          {(advancedActive || search) && (
            <button type="button" className="clear-filters-btn" onClick={clearFilters}>
              <IconX /> Clear All Filters
            </button>
          )}
        </div>
      )}

      <div className="filters">
        {["All", "Pending", "In Progress", "Resolved"].map((f) => (
          <button
            key={f}
            className={filter === f ? "active" : ""}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      <p className="results-count">
        {filtered.length} {filtered.length === 1 ? "complaint" : "complaints"} found
      </p>

      {filtered.length === 0 ? (
        <p>No complaints match your search and filters.</p>
      ) : (
        <div className="complaint-list grid-desktop">
          {filtered.map((c) => (
            <ComplaintCard
              key={c.id}
              complaint={c}
              onAssign={handleAssign}
              duplicatesOf={getDuplicateMatches(c, complaints)}
            />
          ))}
        </div>
      )}

      {/* MODAL: Assign Crew Personnel */}
      {assigningComplaint && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Dispatch Crew to Case #{String(assigningComplaint.id).padStart(4, "0")}</h2>
              <button className="icon-btn" onClick={() => setAssigningComplaint(null)}><IconX /></button>
            </div>
            <form onSubmit={handleConfirmAssignment} className="complaint-form">
              <div style={{ padding: "0.85rem", background: "rgba(255,255,255,0.05)", borderRadius: "8px", marginBottom: "1rem" }}>
                <p style={{ margin: 0, fontWeight: "600" }}>📍 {assigningComplaint.location}</p>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "#aaa" }}>{assigningComplaint.description}</p>
                {assigningComplaint.hazard && (
                  <span className="hazard-tag" style={{ display: "inline-block", marginTop: "0.5rem" }}>
                    ⚠️ {assigningComplaint.hazard}
                  </span>
                )}
              </div>

              <label>
                Select Field Personnel / Crew Lead
                <select
                  required
                  value={selectedWorkerId}
                  onChange={(e) => setSelectedWorkerId(e.target.value)}
                >
                  <option value="">-- Choose Field Personnel --</option>
                  {workforce.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.role} - {w.shift})
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Dispatch Instructions / Special Notes (Optional)
                <textarea
                  rows={2}
                  placeholder="e.g. High priority area near school gate. Bring odor neutralizer."
                  value={assignmentNotes}
                  onChange={(e) => setAssignmentNotes(e.target.value)}
                />
              </label>

              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setAssigningComplaint(null)}>Cancel</button>
                <button type="submit" className="primary-btn" disabled={!selectedWorkerId}>
                  <IconUserPlus /> Confirm & Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
