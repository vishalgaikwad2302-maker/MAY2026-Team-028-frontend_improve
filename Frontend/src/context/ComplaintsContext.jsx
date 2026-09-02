import { createContext, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { apiFetch, createComplaintApi, getMediaUrl, uploadPhotoApi } from "../utils/api";

const ComplaintsContext = createContext(null);

const initialComplaints = [
  {
    id: 1,
    location: "MG Road, Near Bus Stop",
    description: "Garbage overflowing for 3 days, foul smell.",
    hazard: "Foul Smell",
    photo: "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9716, lng: 77.5946 },
    reportedBy: "Anita Rao",
    status: "Pending",
    createdAt: "2026-06-20",
    assignedTo: null,
    assignedWorkerId: null,
  },
  {
    id: 2,
    location: "5th Cross, Indiranagar",
    description: "Illegal dumping near park entrance.",
    hazard: "Mosquito Breeding",
    photo: "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9784, lng: 77.6408 },
    reportedBy: "Mohammed Iqbal",
    status: "In Progress",
    createdAt: "2026-06-18",
    assignedTo: "Ramesh Kumar",
    assignedWorkerId: "W-102",
    assignedAt: "2026-06-18",
  },
  {
    id: 3,
    location: "80 Feet Road, Koramangala",
    description: "Overflowing community bin attracting stray animals.",
    hazard: "Overflowing Bin",
    photo: "https://images.unsplash.com/photo-1503596476-1c12a8ba09a9?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9352, lng: 77.6146 },
    reportedBy: "Sagnik Halder",
    status: "Resolved",
    createdAt: "2026-06-10",
    resolvedAt: "2026-06-13",
    assignedTo: "Ramesh Kumar",
    assignedWorkerId: "W-102",
  },
  {
    id: 4,
    location: "Jayanagar 4th Block Park",
    description: "Leaves and general litter piled near the entrance gate.",
    hazard: "None",
    photo: "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9254, lng: 77.5931 },
    reportedBy: "Anita Rao",
    status: "Resolved",
    createdAt: "2026-06-05",
    resolvedAt: "2026-06-06",
  },
  {
    id: 5,
    location: "MG Road Metro Station Exit",
    description: "Medical waste dumped near the footpath, children play nearby.",
    hazard: "Risk to Children",
    photo: "https://images.unsplash.com/photo-1528323273322-d81458248d40?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9758, lng: 77.6069 },
    reportedBy: "Mohammed Iqbal",
    status: "Resolved",
    createdAt: "2026-06-15",
    resolvedAt: "2026-06-21",
  },
  {
    id: 6,
    location: "12th Main, Indiranagar",
    description: "Reported by mistake, bin was already cleared by the time I checked.",
    hazard: "None",
    photo: null,
    coords: { lat: 12.9719, lng: 77.6412 },
    reportedBy: "Sagnik Halder",
    status: "Cancelled",
    createdAt: "2026-06-22",
  },
  {
    id: 7,
    location: "Sony World Signal, Koramangala",
    description: "Foul smell from an uncollected bin for over a week.",
    hazard: "Foul Smell",
    photo: "https://images.unsplash.com/photo-1605600659908-0ef719419d41?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9343, lng: 77.6224 },
    reportedBy: "Anita Rao",
    status: "Pending",
    createdAt: "2026-07-01",
    assignedTo: null,
    assignedWorkerId: null,
  },
  {
    id: 8,
    location: "Jayanagar 9th Block Market",
    description: "Vegetable market waste overflowing onto the road.",
    hazard: "Overflowing Bin",
    photo: "https://images.unsplash.com/photo-1595278069441-2cf29f8005a4?auto=format&fit=crop&w=800&q=80",
    coords: { lat: 12.9184, lng: 77.5847 },
    reportedBy: "Mohammed Iqbal",
    status: "In Progress",
    createdAt: "2026-06-28",
    assignedTo: "Suresh Patil",
    assignedWorkerId: "W-101",
    assignedAt: "2026-06-28",
  },
];

export function ComplaintsProvider({ children }) {
  const [complaints, setComplaints] = useState(() => {
    const saved = localStorage.getItem("smartsweep-complaints");
    return saved ? JSON.parse(saved) : initialComplaints;
  });
  const { user } = useAuth();

  useEffect(() => {
    localStorage.setItem("smartsweep-complaints", JSON.stringify(complaints));
  }, [complaints]);

  const toLocalComplaint = (apiComplaint, fallbackData = {}) => ({
    id: apiComplaint.id,
    location: apiComplaint.title || apiComplaint.address || fallbackData.location || "Unknown Location",
    description: apiComplaint.description || fallbackData.description || "",
    hazard: apiComplaint.category || fallbackData.hazard || "None",
    photo: getMediaUrl(apiComplaint.photo_url) || getMediaUrl(fallbackData.photo) || null,
    coords:
      apiComplaint.latitude != null && apiComplaint.longitude != null
        ? { lat: apiComplaint.latitude, lng: apiComplaint.longitude }
        : fallbackData.coords || null,
    reportedByUserId: apiComplaint.reported_by_user_id ?? fallbackData.reportedByUserId ?? user?.id,
    reportedBy:
      fallbackData.reportedBy ||
      (apiComplaint.reported_by_user_id === user?.id
        ? user?.name
        : `User #${apiComplaint.reported_by_user_id}`),
    status: apiComplaint.status
      ? apiComplaint.status.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase())
      : fallbackData.status || "Pending",
    assignedTo: fallbackData.assignedTo || apiComplaint.assigned_to || null,
    assignedWorkerId: fallbackData.assignedWorkerId || apiComplaint.assigned_worker_id || null,
    assignedAt: fallbackData.assignedAt || apiComplaint.assigned_at || null,
    instructions: fallbackData.instructions || null,
    createdAt: (apiComplaint.created_at || new Date().toISOString()).slice(0, 10),
    resolvedAt: apiComplaint.resolved_at ? apiComplaint.resolved_at.slice(0, 10) : undefined,
    cancelledAt: apiComplaint.cancelled_at ? apiComplaint.cancelled_at.slice(0, 10) : undefined,
  });

  const refreshComplaints = async () => {
    if (!user) {
      setComplaints(initialComplaints);
      return;
    }
    const res = await apiFetch("/complaints?page=1&page_size=100");
    if (res.success && res.data) {
      const rawList = Array.isArray(res.data) ? res.data : res.data.items || [];
      const formatted = rawList.map((item) => toLocalComplaint(item));
      setComplaints(formatted);
    }
  };

  useEffect(() => {
    refreshComplaints();
  }, [user]);

  const addComplaint = async (data) => {
    let photoUrl = data.photo;
    if (data.photo && data.photo.startsWith("data:")) {
      try {
        const blob = await (await fetch(data.photo)).blob();
        const uploadRes = await uploadPhotoApi(blob);
        if (uploadRes.success && uploadRes.url) {
          photoUrl = uploadRes.url;
        }
      } catch (e) {
        console.warn("Photo upload helper failed, proceeding with direct payload", e);
      }
    }

    const payload = {
      location: data.location,
      description: data.description,
      hazard: data.hazard && data.hazard !== "None" ? data.hazard : "None",
      complaint_type: data.complaintType || null,
      photo: photoUrl,
      coords: data.coords,
      ward_id: user?.ward_id ?? null,
    };

    const result = await createComplaintApi(payload);
    if (!result.success) {
      return { success: false, error: result.error };
    }

    const newComplaint = toLocalComplaint(result.data, {
      ...data,
      photo: photoUrl,
      reportedBy: user?.name || "Citizen",
    });
    setComplaints((prev) => [newComplaint, ...prev.filter((c) => c.id !== newComplaint.id)]);
    return { success: true, complaint: newComplaint };
  };

  const updateComplaint = async (id, updates) => {
    const patchBody = {};
    if (updates.location !== undefined) {
      patchBody.title = updates.location;
      patchBody.address = updates.location;
    }
    if (updates.description !== undefined) patchBody.description = updates.description;
    if (updates.hazard !== undefined) patchBody.category = updates.hazard;
    if (updates.photo !== undefined) patchBody.photo_url = updates.photo;
    if (updates.coords !== undefined) {
      patchBody.latitude = updates.coords?.lat ?? null;
      patchBody.longitude = updates.coords?.lng ?? null;
    }
    if (updates.status !== undefined) {
      patchBody.status = updates.status.toLowerCase().replace(/ /g, "_");
    }

    const result = await apiFetch(`/complaints/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patchBody),
    });

    if (!result.success) {
      return { success: false, error: result.error };
    }

    const updated = toLocalComplaint(result.data, updates);
    setComplaints((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated, ...updates } : c)));
    return { success: true };
  };

  const cancelComplaint = async (id) => {
    const result = await apiFetch(`/complaints/${id}/cancel`, {
      method: "POST",
    });

    if (!result.success) {
      return { success: false, error: result.error };
    }

    const updated = toLocalComplaint(result.data);
    setComplaints((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updated, status: "Cancelled" } : c))
    );
    return { success: true };
  };

  const updateStatus = async (id, status, extraData = {}) => {
    const backendStatus = status.toLowerCase().replace(/ /g, "_");
    const result = await apiFetch(`/complaints/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status_value: backendStatus }),
    });

    if (!result.success) {
      return await updateComplaint(id, {
        status,
        ...extraData,
        ...(status === "Resolved" ? { resolvedAt: new Date().toISOString().slice(0, 10) } : {}),
      });
    }

    const updated = toLocalComplaint(result.data, extraData);
    setComplaints((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated, ...extraData } : c)));
    return { success: true };
  };

  return (
    <ComplaintsContext.Provider
      value={{ complaints, addComplaint, updateStatus, updateComplaint, cancelComplaint, refreshComplaints }}
    >
      {children}
    </ComplaintsContext.Provider>
  );
}

export const useComplaints = () => useContext(ComplaintsContext);
