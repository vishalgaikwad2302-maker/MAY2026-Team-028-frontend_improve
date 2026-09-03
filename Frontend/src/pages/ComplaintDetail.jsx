import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useComplaints } from "../context/ComplaintsContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { getDuplicateMatches } from "../utils/duplicateDetection";
import { getMediaUrl } from "../utils/api";
import {
  IconArrowRight,
  IconPin,
  IconAlertTriangle,
  IconAlertCircle,
  IconCheckCircle,
  IconClipboard,
  IconReport,
  IconGrid,
  IconStar,
  IconRadar,
  IconX,
} from "../components/Icons";

// Same ~200m / text-overlap thresholds as the duplicate warning shown to
// citizens on ReportComplaint (#5) — just surfaced here as a browsable
// panel for supervisors instead of a blocking confirm dialog.
const formatDistance = (meters) => {
  if (meters === null || meters === undefined) return null;
  return meters < 1000 ? `${Math.round(meters)} m away` : `${(meters / 1000).toFixed(1)} km away`;
};

const STEPS = ["Pending", "In Progress", "Resolved"];

const backFor = {
  citizen: { to: "/my-complaints", label: "My Complaints", icon: IconClipboard },
  crew: { to: "/crew", label: "Assigned Tasks", icon: IconReport },
  admin: { to: "/dashboard", label: "Dashboard", icon: IconGrid },
};

export default function ComplaintDetail() {
  const { id } = useParams();
  const { complaints, updateComplaint, cancelComplaint } = useComplaints();
  const { user } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const complaint = complaints.find((c) => String(c.id) === id);
  const back = backFor[user?.role] || { to: "/", label: "Home" };

  // Only the citizen who filed it may edit/withdraw it, and only while
  // it's still Pending — once a crew touches it, changes should go
  // through the crew/admin flow instead.
  const canManage =
    user?.role === "citizen" &&
    complaint?.reportedBy === user?.name &&
    complaint?.status === "Pending";


  // Admin-only "Similar/Nearby Complaints" panel (#10) — reuses the exact
  // same Haversine + text-overlap heuristic as the duplicate warning (#5),
  // just displayed as a browsable panel instead of a blocking prompt.
  const nearby = useMemo(
    () => (complaint && user?.role === "admin" ? getDuplicateMatches(complaint, complaints) : []),
    [complaint, complaints, user]
  );

  // Citizens can rate the resolution once it's done, but only once.
  const canGiveFeedback =
    user?.role === "citizen" &&
    complaint?.reportedBy === user?.name &&
    complaint?.status === "Resolved" &&
    !complaint?.feedback;

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({ rating: 0, comment: "" });
  const [hoveredStar, setHoveredStar] = useState(0);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [activeLightboxImg, setActiveLightboxImg] = useState(null);

  useEffect(() => {
    setImageError(false);
  }, [complaint?.id, complaint?.photo]);

  const startEditing = () => {
    setForm({
      location: complaint.location,
      description: complaint.description,
      hazard: complaint.hazard || "None",
    });
    setError("");
    setEditing(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.location || !form.description) return;
    const result = await updateComplaint(complaint.id, form);
    if (result.success) {
      setEditing(false);
      notify("Changes saved", "success");
    } else {
      const msg = result.error || "Couldn't save changes. Try again.";
      setError(msg);
      notify(msg, "error");
    }
  };

  const handleCancel = async () => {
    if (!window.confirm("Withdraw this complaint? This can't be undone.")) return;
    setCancelling(true);
    const result = await cancelComplaint(complaint.id);
    setCancelling(false);
    if (result.success) {
      notify("Complaint withdrawn", "info");
      navigate(back.to);
    } else {
      const msg = result.error || "Couldn't withdraw this complaint.";
      setError(msg);
      notify(msg, "error");
    }
  };


  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!feedbackForm.rating) return;
    setSubmittingFeedback(true);
    const result = await updateComplaint(complaint.id, {
      feedback: {
        rating: feedbackForm.rating,
        comment: feedbackForm.comment,
        submittedAt: new Date().toISOString().slice(0, 10),
      },
    });
    setSubmittingFeedback(false);
    if (result.success) {
      notify("Thanks for your feedback!", "success");
    } else {
      notify(result.error || "Couldn't submit feedback.", "error");
    }
  };

  if (!complaint) {
    return (
      <div className="page">
        <span className="eyebrow">Not Found</span>
        <h1>Complaint not found</h1>
        <p>This complaint may have been removed or the link is incorrect.</p>
        <Link className="detail-back" to={back.to}>
          {back.icon && <back.icon />} Back to {back.label}
        </Link>
      </div>
    );
  }

  const stepIndex = STEPS.indexOf(complaint.status);

  return (
    <div className="page">
      <Link className="detail-back" to={back.to}>
        {back.icon && <back.icon />} Back to {back.label}
      </Link>

      <span className="case-no">Case No. {String(complaint.id).padStart(4, "0")}</span>
      <div className="detail-header">
        <h1>{complaint.location}</h1>
        <span className={`status-badge ${complaint.status.toLowerCase().replace(" ", "-")}`}>
          {complaint.status}
        </span>
      </div>

      <div className="detail-photo-wrap">
        {complaint.photo && !imageError ? (
          <img
            src={getMediaUrl(complaint.photo)}
            alt="Reported issue evidence"
            className="detail-photo clickable-photo"
            onClick={() => setActiveLightboxImg(complaint.photo)}
            title="Click to view full photo"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="detail-photo detail-photo-empty">
            {complaint.photo && imageError ? "Evidence photo unavailable" : "No photo attached"}
          </div>
        )}
      </div>

      {/* AI Condition Tags */}
      <div className="ai-tags-container">
        <span className="ai-tags-label">✨ AI Condition Tags:</span>
        <div className="ai-tags-list">
          {((complaint.tags && complaint.tags.length > 0)
            ? complaint.tags.slice(0, 3)
            : ["Roadside Street Litter", "Overflowing Garbage Bin", "Plastic Waste & Bottles"]
          ).map((tag, idx) => (
            <span key={idx} className="ai-tag-chip">
              🏷️ {tag}
            </span>
          ))}
        </div>
      </div>

      {complaint.assignedTo && (
        <div style={{ margin: "1rem 0", padding: "0.85rem 1.25rem", background: "rgba(255,255,255,0.04)", borderRadius: "10px", borderLeft: "4px solid #10b981", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <span style={{ fontSize: "0.8rem", color: "#888", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: "600" }}>Assigned Crew Personnel</span>
            <p style={{ margin: "0.2rem 0 0", fontSize: "1.05rem", fontWeight: "600" }}>👷 {complaint.assignedTo}</p>
            {complaint.instructions && (
              <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "#aaa" }}>Note: {complaint.instructions}</p>
            )}
          </div>
          {complaint.assignedAt && (
            <span style={{ fontSize: "0.85rem", color: "#888" }}>Dispatched {complaint.assignedAt}</span>
          )}
        </div>
      )}

      {user?.role === "crew" && complaint.hazard && complaint.hazard !== "None" && (
        <div className="hazard-banner">
          <IconAlertTriangle />
          <div>
            <strong>Hazard Reported: {complaint.hazard}</strong>
            <p>Take appropriate precautions while attending this site.</p>
          </div>
        </div>
      )}

      {/* Status timeline */}
      <div className="status-timeline">
        {STEPS.map((step, i) => (
          <div key={step} className={`timeline-step ${i <= stepIndex ? "done" : ""} ${i === stepIndex ? "current" : ""}`}>
            <span className="timeline-dot">{i < stepIndex ? <IconCheckCircle /> : null}</span>
            <span className="timeline-label">{step}</span>
            {i < STEPS.length - 1 && <span className="timeline-line" />}
          </div>
        ))}
      </div>

      {/* Remediation Proof of Work Section */}
      {complaint.completionPhotos && complaint.completionPhotos.length > 0 && (
        <div className="proof-of-work-card">
          <div className="proof-card-header">
            <div>
              <span className="proof-badge">
                <IconCheckCircle /> Verified Remediation Proof
              </span>
              <h3>Field Cleanup Evidence ({complaint.completionPhotos.length} photo{complaint.completionPhotos.length > 1 ? "s" : ""})</h3>
              <p className="proof-meta">
                Remediated by <strong>{complaint.assignedTo || "Field Crew"}</strong>
                {complaint.resolvedAt && ` • ${complaint.resolvedAt}`}
              </p>
            </div>
          </div>

          {complaint.resolutionNotes && (
            <p className="proof-notes">
              <strong>Crew Remarks:</strong> "{complaint.resolutionNotes}"
            </p>
          )}

          <div className="proof-photos-grid">
            {complaint.completionPhotos.map((photoUrl, idx) => (
              <div
                key={idx}
                className="proof-photo-item"
                onClick={() => setActiveLightboxImg(photoUrl)}
                title="Click to expand proof photo"
              >
                <img src={getMediaUrl(photoUrl)} alt={`Completion proof ${idx + 1}`} loading="lazy" />
                <span className="proof-photo-label">Proof #{idx + 1}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {user?.role === "admin" && (
        <div className="nearby-panel">
          <h2><IconRadar /> Similar / Nearby Complaints</h2>
          {nearby.length === 0 ? (
            <p>No similar or nearby complaints found.</p>
          ) : (
            <ul className="nearby-list">
              {nearby.map((m) => {
                const dist = formatDistance(m.distance);
                const statusClass = m.complaint.status.toLowerCase().replace(" ", "-");
                return (
                  <li key={m.complaint.id} className="nearby-item">
                    <Link to={`/complaint/${m.complaint.id}`} className="nearby-item-link">
                      <div className="nearby-item-main">
                        <span className="case-no">
                          Case No. {String(m.complaint.id).padStart(4, "0")}
                        </span>
                        <span className={`status-badge ${statusClass}`}>{m.complaint.status}</span>
                      </div>
                      <p className="nearby-item-location"><IconPin /> {m.complaint.location}</p>
                      <p className="nearby-item-desc">{m.complaint.description}</p>
                      <div className="nearby-item-meta">
                        {dist && <span>{dist}</span>}
                        {m.locationScore >= 0.6 && <span>Matching location text</span>}
                        {m.locationScore < 0.6 && m.descScore >= 0.35 && (
                          <span>Similar description</span>
                        )}
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {error && <p className="loc-error"><IconAlertCircle /> {error}</p>}

      {editing ? (
        <form onSubmit={handleSave} className="complaint-form">
          <label>
            Location
            <input
              name="location"
              type="text"
              value={form.location}
              onChange={handleChange}
              required
            />
          </label>

          <label>
            Description
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              required
            />
          </label>

          <label>
            Hazard Type
            <select name="hazard" value={form.hazard} onChange={handleChange}>
              <option>None</option>
              <option>Foul Smell</option>
              <option>Overflowing Bin</option>
              <option>Mosquito Breeding</option>
              <option>Risk to Children</option>
            </select>
          </label>

          <div className="detail-actions">
            <button type="submit" className="save-btn">
              <IconCheckCircle /> Save Changes
            </button>
            <button type="button" className="secondary-btn" onClick={() => setEditing(false)}>
              Discard
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="detail-section">
            <h2>Description</h2>
            <p>{complaint.description}</p>
          </div>

          {complaint.hazard && complaint.hazard !== "None" && (
            <p className="hazard-tag"><IconAlertTriangle /> {complaint.hazard}</p>
          )}

          <div className="detail-meta">
            {complaint.reportedBy && <p className="reported-by">Filed by {complaint.reportedBy}</p>}
            <p className="date">Reported: {complaint.createdAt}</p>
          </div>

          {complaint.coords && (
            <a
              className="map-link"
              href={`https://www.google.com/maps?q=${complaint.coords.lat},${complaint.coords.lng}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <IconPin /> View on Map <IconArrowRight />
            </a>
          )}

          {canManage && (
            <div className="detail-actions">
              <button type="button" className="edit-btn" onClick={startEditing}>
                Edit Complaint
              </button>
              <button
                type="button"
                className="cancel-btn"
                onClick={handleCancel}
                disabled={cancelling}
              >
                {cancelling ? "Withdrawing..." : "Withdraw Complaint"}
              </button>
            </div>
          )}


          {canGiveFeedback && (
            <form onSubmit={handleFeedbackSubmit} className="complaint-form feedback-form">
              <h2>Rate the Resolution</h2>
              <div className="star-rating">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`star-btn ${n <= (hoveredStar || feedbackForm.rating) ? "filled" : ""}`}
                    onMouseEnter={() => setHoveredStar(n)}
                    onMouseLeave={() => setHoveredStar(0)}
                    onClick={() => setFeedbackForm((prev) => ({ ...prev, rating: n }))}
                    aria-label={`${n} star${n > 1 ? "s" : ""}`}
                  >
                    <IconStar />
                  </button>
                ))}
              </div>
              <label>
                Comments (optional)
                <textarea
                  value={feedbackForm.comment}
                  onChange={(e) =>
                    setFeedbackForm((prev) => ({ ...prev, comment: e.target.value }))
                  }
                  placeholder="How did the cleanup go?"
                />
              </label>
              <button type="submit" className="edit-btn" disabled={!feedbackForm.rating || submittingFeedback}>
                {submittingFeedback ? "Submitting..." : "Submit Feedback"}
              </button>
            </form>
          )}

          {complaint.feedback && (
            <div className="detail-section feedback-display">
              <h2>Your Feedback</h2>
              <div className="star-rating read-only">
                {[1, 2, 3, 4, 5].map((n) => (
                  <span key={n} className={`star-btn ${n <= complaint.feedback.rating ? "filled" : ""}`}>
                    <IconStar />
                  </span>
                ))}
              </div>
              {complaint.feedback.comment && <p>{complaint.feedback.comment}</p>}
              <p className="date">Submitted: {complaint.feedback.submittedAt}</p>
            </div>
          )}
        </>
      )}

      {/* Lightbox Overlay for Detail Photos */}
      {activeLightboxImg && (
        <div className="lightbox-overlay" onClick={() => setActiveLightboxImg(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="lightbox-close-btn"
              onClick={() => setActiveLightboxImg(null)}
              title="Close full view"
            >
              <IconX />
            </button>
            <img src={getMediaUrl(activeLightboxImg)} alt="Enlarged view" />
          </div>
        </div>
      )}
    </div>
  );
}