import { useState } from "react";
import { useComplaints } from "../context/ComplaintsContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ComplaintCard from "../components/ComplaintCard";
import { IconCheckCircle, IconUsers } from "../components/Icons";

export default function CrewTasks() {
  const { complaints, updateStatus } = useComplaints();
  const { user } = useAuth();
  const { notify } = useToast();
  const [activeTab, setActiveTab] = useState("my"); // 'my' | 'all'

  // Normalize user name for comparison
  const userName = (user?.name || user?.email || "").toLowerCase();
  const isGenericCrew =
    userName === "crew" ||
    userName === "crew demo" ||
    userName === "crew member" ||
    userName.includes("demo") ||
    userName.includes("suresh") ||
    userName.includes("patil");

  const allInProgress = complaints.filter((c) => c.status === "In Progress");
  const allResolved = complaints.filter(
    (c) => c.status === "Resolved" || c.status === "Verified" || c.status === "Closed"
  );

  const myTasks = allInProgress.filter((c) => {
    if (!c.assignedTo) return true; // Unassigned in-progress jobs visible to all crew
    const assignee = c.assignedTo.toLowerCase();
    if (isGenericCrew) return true; // Demo account can see all tasks
    return assignee.includes(userName) || userName.includes(assignee);
  });

  const myCompletedTasks = allResolved.filter((c) => {
    if (isGenericCrew) return true;
    if (!c.assignedTo) return true;
    const assignee = c.assignedTo.toLowerCase();
    return assignee.includes(userName) || userName.includes(assignee);
  });

  const displayedTasks =
    activeTab === "my"
      ? myTasks
      : activeTab === "completed"
      ? myCompletedTasks
      : allInProgress;

  const handleComplete = async (id) => {
    const result = await updateStatus(id, "Resolved", {
      assignedTo: user?.name || "Suresh Patil",
    });
    if (result.success) {
      notify(`Case #${String(id).padStart(4, "0")} marked as resolved`, "success");
    } else {
      notify(result.error || "Couldn't mark case resolved.", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Cleanup Crew Operations</span>
          <h1>Field Task Queue</h1>
          <p className="page-lead">
            Welcome, <strong>{user?.name || "Crew Specialist"}</strong>. Review, complete, and track your assigned remediation tasks.
          </p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="filters" style={{ marginBottom: "1.5rem" }}>
        <button
          type="button"
          className={activeTab === "my" ? "active" : ""}
          onClick={() => setActiveTab("my")}
        >
          <IconCheckCircle /> Active Tasks ({myTasks.length})
        </button>
        <button
          type="button"
          className={activeTab === "completed" ? "active" : ""}
          onClick={() => setActiveTab("completed")}
        >
          <IconCheckCircle /> Completed Tasks ({myCompletedTasks.length})
        </button>
        <button
          type="button"
          className={activeTab === "all" ? "active" : ""}
          onClick={() => setActiveTab("all")}
        >
          <IconUsers /> All Ward Jobs ({allInProgress.length})
        </button>
      </div>

      {displayedTasks.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "3rem 1rem", background: "var(--card-bg, rgba(255,255,255,0.03))", borderRadius: "12px" }}>
          <p style={{ fontSize: "1.1rem", fontWeight: "600" }}>
            {activeTab === "my"
              ? "No active tasks assigned to you right now."
              : activeTab === "completed"
              ? "No completed tasks yet."
              : "No in-progress tasks across the ward."}
          </p>
          <p style={{ color: "var(--text-muted, #888)", fontSize: "0.9rem" }}>
            {activeTab === "my"
              ? "Switch to 'All Ward Jobs' to browse active cases or wait for the supervisor to dispatch a task."
              : activeTab === "completed"
              ? "Tasks marked as resolved or closed will appear here as your completed work record."
              : "All reported complaints are either pending assignment or already resolved."}
          </p>
        </div>
      ) : (
        <div className="complaint-list grid-desktop">
          {displayedTasks.map((c) => (
            <ComplaintCard key={c.id} complaint={c} onComplete={handleComplete} />
          ))}
        </div>
      )}
    </div>
  );
}