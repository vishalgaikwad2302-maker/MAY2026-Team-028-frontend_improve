import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useComplaints } from "../context/ComplaintsContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { findPossibleDuplicates } from "../utils/duplicateDetection";
import { IconPin, IconAlertCircle, IconAlertTriangle, IconCamera, IconUpload, IconReport, IconArrowRight, IconX, IconCheckCircle } from "../components/Icons";

export default function ReportComplaint() {
  const { complaints, addComplaint } = useComplaints();
  const { user } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    location: "",
    description: "",
    hazard: "None",
    complaintType: "",
    photo: null,
    coords: null,
  });

  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState("");
  const [duplicates, setDuplicates] = useState([]);

  // Live in-browser camera capture (works on desktop webcams as well as
  // mobile device cameras, unlike the `capture` attribute which desktop
  // browsers ignore).
  const [cameraOpen, setCameraOpen] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fallbackFileInputRef = useRef(null);

  const stopCameraStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  useEffect(() => stopCameraStream, []);

  const handleOpenCamera = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      // No camera API in this browser (e.g. an insecure/non-HTTPS context) —
      // fall back to the OS file/camera picker instead of a dead end.
      notify("Live camera isn't available here — opening file picker instead.", "info");
      fallbackFileInputRef.current?.click();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOpen(true);
      // Wait for the modal's <video> element to mount before attaching.
      requestAnimationFrame(() => {
        if (videoRef.current) videoRef.current.srcObject = stream;
      });
    } catch {
      // Permission denied, no camera present, or already in use elsewhere —
      // fall back to the OS picker so the user isn't stuck.
      notify("Couldn't access the camera — opening file picker instead.", "info");
      fallbackFileInputRef.current?.click();
    }
  };

  const handleCloseCamera = () => {
    stopCameraStream();
    setCameraOpen(false);
  };

  const handleCapturePhoto = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    setForm((prev) => ({ ...prev, photo: dataUrl }));
    handleCloseCamera();
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (duplicates.length) setDuplicates([]);
  };

  const handlePhoto = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (uploadEvent) => {
        setForm((prev) => ({ ...prev, photo: uploadEvent.target?.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemovePhoto = () => {
    setForm((prev) => ({ ...prev, photo: null }));
  };

  const handleUseLocation = () => {
    if (!navigator.geolocation) {
      setLocError("Geolocation is not supported by this browser.");
      return;
    }
    setLocating(true);
    setLocError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setForm((prev) => ({
          ...prev,
          coords: { lat: latitude, lng: longitude },
          location:
            prev.location || `Lat ${latitude.toFixed(5)}, Lng ${longitude.toFixed(5)}`,
        }));
        setLocating(false);
      },
      (error) => {
        setLocError(
          error.code === error.PERMISSION_DENIED
            ? "Location permission denied. Enter the location manually."
            : "Couldn't fetch your location. Enter it manually."
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const submitComplaint = async () => {
    const res = await addComplaint({ ...form, reportedBy: user?.name });
    if (res && res.success === false) {
      notify(res.error || "Failed to submit complaint. Please check your inputs.", "error");
      return;
    }
    notify("Complaint submitted successfully", "success");
    navigate("/my-complaints");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.location || !form.description) return;

    const matches = findPossibleDuplicates(form, complaints);
    if (matches.length) {
      setDuplicates(matches);
      return;
    }
    await submitComplaint();
  };

  const handleSubmitAnyway = async () => {
    setDuplicates([]);
    await submitComplaint();
  };

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">New Incident Report</span>
          <h1>Report a Garbage Issue</h1>
          <p className="page-lead">
            Provide location details and photos to dispatch municipal crews quickly.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="complaint-form">
        <div className="location-row">
          <div className="field-group">
            <label htmlFor="location">Location / Landmark *</label>
            <input
              id="location"
              name="location"
              type="text"
              value={form.location}
              onChange={handleChange}
              placeholder="e.g. MG Road, Near Bus Stop"
              required
            />
          </div>
          <button
            type="button"
            className="gps-btn"
            onClick={handleUseLocation}
            disabled={locating}
            title="Auto-detect current GPS coordinates"
          >
            <IconPin /> <span>{locating ? "Locating..." : "Use My Location"}</span>
          </button>
        </div>

        {form.coords && (
          <p className="coords-preview">
            <IconCheckCircle /> GPS Captured: {form.coords.lat.toFixed(5)}, {form.coords.lng.toFixed(5)}
          </p>
        )}
        {locError && (
          <p className="loc-error">
            <IconAlertCircle /> {locError}
          </p>
        )}

        <div className="field-group">
          <label htmlFor="description">Issue Description *</label>
          <textarea
            id="description"
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Describe the waste buildup, obstruction, or foul smell..."
            required
          />
        </div>

        <div className="field-group">
          <label htmlFor="hazard">Hazard Classification</label>
          <select id="hazard" name="hazard" value={form.hazard} onChange={handleChange}>
            <option value="None">None (General Litter / Dump)</option>
            <option value="Foul Smell">Foul Smell & Air Quality Concern</option>
            <option value="Overflowing Bin">Overflowing Garbage Bin / Container</option>
            <option value="Mosquito Breeding">Mosquito / Pest Breeding Hazard</option>
            <option value="Risk to Children">Biohazard / Risk to Children</option>
          </select>
        </div>

        <div className="field-group">
          <label htmlFor="complaintType">Complaint Type (Optional)</label>
          <select
            id="complaintType"
            name="complaintType"
            value={form.complaintType}
            onChange={handleChange}
          >
            <option value="">General / Other</option>
            <option value="overflow">Overflowing Bin / Missed Overflow</option>
            <option value="delay">Delayed or Missed Pickup</option>
            <option value="extra_collection">Request Extra Collection</option>
          </select>
        </div>

        <div className="field-group">
          <label>Photo Evidence (Optional)</label>
          {form.photo ? (
            <div className="photo-preview-box">
              <img src={form.photo} alt="Photo preview" className="photo-preview-img" />
              <button
                type="button"
                className="remove-photo-btn"
                onClick={handleRemovePhoto}
                title="Remove photo"
              >
                <IconX /> Remove Photo
              </button>
            </div>
          ) : (
            <div className="photo-source-row">
              <button type="button" className="photo-drop-zone" onClick={handleOpenCamera}>
                <IconCamera className="upload-icon" />
                <div className="upload-text">
                  <strong>Take a photo</strong>
                  <small>Use your device camera</small>
                </div>
              </button>
              {/* Hidden fallback: used only if getUserMedia is unavailable or denied. */}
              <input
                ref={fallbackFileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handlePhoto}
                className="hidden-file-input"
              />
              <label className="photo-drop-zone">
                <IconUpload className="upload-icon" />
                <div className="upload-text">
                  <strong>Upload from device</strong>
                  <small>PNG, JPG, or WEBP up to 10MB</small>
                </div>
                <input type="file" accept="image/*" onChange={handlePhoto} className="hidden-file-input" />
              </label>
            </div>
          )}
        </div>

        {duplicates.length > 0 && (
          <div className="duplicate-warning">
            <p className="duplicate-warning-title">
              <IconAlertTriangle /> {duplicates.length === 1 ? "A similar report exists nearby" : "Similar reports exist nearby"}
            </p>
            <ul className="duplicate-list">
              {duplicates.slice(0, 3).map(({ complaint }) => (
                <li key={complaint.id}>
                  <Link to={`/complaint/${complaint.id}`} target="_blank" rel="noopener noreferrer">
                    Case #{String(complaint.id).padStart(4, "0")} — {complaint.location}
                    <IconArrowRight />
                  </Link>
                  <span className={`status-badge ${complaint.status.toLowerCase().replace(" ", "-")}`}>
                    {complaint.status}
                  </span>
                </li>
              ))}
            </ul>
            <div className="duplicate-actions">
              <button type="button" className="secondary-btn" onClick={() => setDuplicates([])}>
                Edit Details
              </button>
              <button type="button" className="primary-btn" onClick={handleSubmitAnyway}>
                Submit Anyway
              </button>
            </div>
          </div>
        )}

        <button type="submit" className="submit-complaint-btn">
          <IconReport /> <span>Submit Incident Report</span>
        </button>
      </form>

      {cameraOpen && (
        <div className="modal-overlay">
          <div className="modal-content camera-modal-content">
            <div className="modal-header">
              <h2>Take a Photo</h2>
              <button className="icon-btn" onClick={handleCloseCamera} title="Cancel">
                <IconX />
              </button>
            </div>
            <video ref={videoRef} autoPlay playsInline muted className="camera-preview" />
            <div className="modal-actions">
              <button type="button" className="secondary-btn" onClick={handleCloseCamera}>
                Cancel
              </button>
              <button type="button" className="primary-btn" onClick={handleCapturePhoto}>
                <IconCamera /> Capture
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}