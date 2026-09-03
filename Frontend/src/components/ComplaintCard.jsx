import { Link } from "react-router-dom";
import { IconAlertTriangle, IconAlertCircle, IconPin, IconUserPlus, IconCheckCircle, IconArrowRight } from "./Icons";

export default function ComplaintCard({ complaint, onAssign, onComplete, duplicatesOf }) {
  const statusClass = complaint.status.toLowerCase().replace(" ", "-");

  return (
    <div className="complaint-card">
      <span className="case-no">Case No. {String(complaint.id).padStart(4, "0")}</span>
      <div className="complaint-header">
        <h3><Link to={`/complaint/${complaint.id}`} className="card-title-link">{complaint.location}</Link></h3>
        <span className={`status-badge ${statusClass}`}>{complaint.status}</span>
      </div>
      <p>{complaint.description}</p>
      {duplicatesOf?.length > 0 && (
        <p className="duplicate-tag">
          <IconAlertTriangle /> Possible Duplicate of Case #{String(duplicatesOf[0].complaint.id).padStart(4, "0")}
          {duplicatesOf.length > 1 && ` (+${duplicatesOf.length - 1} more)`}
        </p>
      )}
      {complaint.needsHelp && (
        <p className="support-tag"><IconAlertCircle /> Support Requested</p>
      )}
      {complaint.hazard && complaint.hazard !== "None" && (
        <p className="hazard-tag"><IconAlertTriangle /> {complaint.hazard}</p>
      )}
      {complaint.reportedBy && <p className="reported-by">Filed by {complaint.reportedBy}</p>}
      {complaint.assignedTo && (
        <p className="assigned-to-tag" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem", color: "var(--accent-color, #10b981)", fontWeight: "600", marginTop: "0.25rem" }}>
          <IconUserPlus /> Assigned to: {complaint.assignedTo}
        </p>
      )}
      {complaint.completionPhotos && complaint.completionPhotos.length > 0 && (
        <p className="proof-tag" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem", color: "var(--accent, #10b981)", fontWeight: "600", marginTop: "0.25rem" }}>
          <IconCheckCircle /> Proof of Work ({complaint.completionPhotos.length} photo{complaint.completionPhotos.length > 1 ? "s" : ""})
        </p>
      )}
      <p className="date">Reported: {complaint.createdAt}</p>
      <div className="card-actions">
        {complaint.coords && (
          <a className="map-link" href={`https://www.google.com/maps?q=${complaint.coords.lat},${complaint.coords.lng}`} target="_blank" rel="noopener noreferrer">
            <IconPin /> View on Map
          </a>
        )}
        {onAssign && complaint.status === "Pending" && (
          <button className="assign-btn" onClick={() => onAssign(complaint.id)}><IconUserPlus /> Assign Crew</button>
        )}
        {onComplete && complaint.status === "In Progress" && (
          <button className="complete-btn" onClick={() => onComplete(complaint.id)}><IconCheckCircle /> Mark Completed</button>
        )}
        <Link to={`/complaint/${complaint.id}`} className="card-details-link">
          View Details <IconArrowRight />
        </Link>
      </div>
    </div>
  );
}