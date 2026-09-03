import { useState } from "react";
import { useComplaints } from "../context/ComplaintsContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ComplaintCard from "../components/ComplaintCard";
import { IconCheckCircle, IconUsers, IconPlus, IconX } from "../components/Icons";
import { compressImage, formatBytes } from "../utils/imageCompressor";
import { uploadPhotoApi } from "../utils/api";

export default function CrewTasks() {
  const { complaints, resolveComplaint } = useComplaints();
  const { user } = useAuth();
  const { notify } = useToast();
  const [activeTab, setActiveTab] = useState("my"); // 'my' | 'completed' | 'all'

  // Completion Proof Modal States
  const [completingComplaint, setCompletingComplaint] = useState(null);
  const [selectedImages, setSelectedImages] = useState([]); // [{ file, previewUrl, compressedSize, originalSize, name }]
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [isCompressing, setIsCompressing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  // Open the proof modal
  const handleOpenCompleteModal = (id) => {
    const target = complaints.find((c) => c.id === id);
    if (!target) return;
    setCompletingComplaint(target);
    setSelectedImages([]);
    setResolutionNotes("");
  };

  // Close & clean up preview URLs
  const handleCloseModal = () => {
    selectedImages.forEach((img) => {
      if (img.previewUrl) URL.revokeObjectURL(img.previewUrl);
    });
    setSelectedImages([]);
    setResolutionNotes("");
    setCompletingComplaint(null);
    setIsSubmitting(false);
    setIsCompressing(false);
  };

  // Handle client-side image compression (<200 KB)
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (selectedImages.length + files.length > 3) {
      notify("You can upload a maximum of 3 proof photos.", "warning");
      return;
    }

    setIsCompressing(true);
    const newItems = [];

    for (const file of files) {
      if (!file.type.startsWith("image/")) {
        notify(`Skipped "${file.name}": Only image files are allowed.`, "warning");
        continue;
      }

      try {
        const compressed = await compressImage(file, { maxKB: 200, maxDimension: 1600 });
        newItems.push({
          file: compressed.file,
          previewUrl: compressed.previewUrl,
          originalSize: compressed.originalSize,
          compressedSize: compressed.compressedSize,
          name: file.name,
        });
      } catch (err) {
        console.error("Compression error:", err);
        notify(`Could not process "${file.name}".`, "error");
      }
    }

    setSelectedImages((prev) => [...prev, ...newItems].slice(0, 3));
    setIsCompressing(false);
    e.target.value = "";
  };

  const removeImage = (indexToRemove) => {
    setSelectedImages((prev) => {
      const removed = prev[indexToRemove];
      if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl);
      return prev.filter((_, idx) => idx !== indexToRemove);
    });
  };

  // Submit completion proof & mark resolved
  const handleSubmitProof = async (e) => {
    e.preventDefault();
    if (!completingComplaint) return;

    if (selectedImages.length === 0) {
      notify("Please upload at least 1 proof photo of completed work.", "error");
      return;
    }

    setIsSubmitting(true);

    try {
      // 1. Upload compressed proof photos
      const uploadedUrls = [];
      for (const img of selectedImages) {
        const uploadRes = await uploadPhotoApi(img.file);
        if (uploadRes.success && uploadRes.url) {
          uploadedUrls.push(uploadRes.url);
        } else {
          console.warn("Upload failed for photo:", img.name);
        }
      }

      if (uploadedUrls.length === 0) {
        notify("Failed to upload proof photos. Please check your connection.", "error");
        setIsSubmitting(false);
        return;
      }

      // 2. Mark complaint resolved with proof photos
      const result = await resolveComplaint(completingComplaint.id, {
        completionPhotos: uploadedUrls,
        resolutionNotes: resolutionNotes.trim() || undefined,
      });

      if (result.success) {
        notify(
          `Case #${String(completingComplaint.id).padStart(4, "0")} resolved with ${uploadedUrls.length} proof photo(s)! 👏`,
          "success"
        );
        handleCloseModal();
      } else {
        notify(result.error || "Failed to mark case as resolved.", "error");
      }
    } catch (err) {
      console.error("Error submitting completion proof:", err);
      notify("Error submitting completion proof. Try again.", "error");
    } finally {
      setIsSubmitting(false);
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
        <div
          className="empty-state"
          style={{
            textAlign: "center",
            padding: "3rem 1rem",
            background: "var(--card-bg, rgba(255,255,255,0.03))",
            borderRadius: "12px",
          }}
        >
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
              ? "Tasks marked as resolved or closed with photographic proof will appear here."
              : "All reported complaints are either pending assignment or already resolved."}
          </p>
        </div>
      ) : (
        <div className="complaint-list grid-desktop">
          {displayedTasks.map((c) => (
            <ComplaintCard
              key={c.id}
              complaint={c}
              onComplete={activeTab !== "completed" ? handleOpenCompleteModal : undefined}
            />
          ))}
        </div>
      )}

      {/* MINIMAL COMPLETION PROOF MODAL */}
      {completingComplaint && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Complete Task & Submit Proof</h2>
                <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem", color: "var(--text-muted, #888)" }}>
                  Case #{String(completingComplaint.id).padStart(4, "0")} • {completingComplaint.location}
                </p>
              </div>
              <button className="icon-btn" onClick={handleCloseModal} title="Close">
                <IconX />
              </button>
            </div>

            <form onSubmit={handleSubmitProof} className="complaint-form">
              {/* Photo Upload Dropzone (1-3 photos, < 200 KB) */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "0.4rem",
                  }}
                >
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-h)" }}>
                    Proof of Work Photos <span className="required-star">*</span>
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                    {selectedImages.length}/3 photos (min 1 required)
                  </span>
                </div>

                {selectedImages.length < 3 && (
                  <label className="minimal-dropzone">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      onChange={handleFileSelect}
                      disabled={isCompressing || isSubmitting}
                      style={{ display: "none" }}
                    />
                    <IconPlus />
                    <div className="dropzone-text">
                      <strong>Click to upload proof of cleanup</strong>
                      <small>Auto-compressed under 200 KB • Up to 3 photos</small>
                    </div>
                  </label>
                )}

                {isCompressing && (
                  <div className="compressing-indicator">
                    <div className="spinner-small" />
                    <span>Compressing proof photo to &lt;200 KB...</span>
                  </div>
                )}

                {selectedImages.length > 0 && (
                  <div className="compressed-previews-grid">
                    {selectedImages.map((img, idx) => (
                      <div key={idx} className="preview-thumb-card">
                        <img src={img.previewUrl} alt={`Proof ${idx + 1}`} />
                        <div className="preview-thumb-info">
                          <span className="preview-size-badge">
                            ✓ {formatBytes(img.compressedSize)}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="remove-thumb-btn"
                          onClick={() => removeImage(idx)}
                          title="Remove photo"
                        >
                          <IconX />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Optional Field Notes */}
              <label>
                <span>Field Resolution Notes (Optional)</span>
                <textarea
                  rows={3}
                  placeholder="e.g. Cleared 1.2 tons of mixed waste, disinfected pavement."
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  maxLength={1000}
                />
              </label>

              {/* Modal Actions */}
              <div className="modal-actions" style={{ marginTop: "1rem" }}>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={handleCloseModal}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={isSubmitting || isCompressing || selectedImages.length === 0}
                >
                  {isSubmitting ? "Uploading & Resolving..." : "Mark Resolved with Proof"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}