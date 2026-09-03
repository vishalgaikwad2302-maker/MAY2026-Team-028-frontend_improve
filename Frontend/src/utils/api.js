/**
 * API Client helper module for communicating with the SmartSweep FastAPI backend.
 * Handles JWT authentication headers, token storage, auto-refresh, and error envelopes.
 */

let envApiUrl = (import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
if (envApiUrl && !envApiUrl.endsWith("/api/v1")) {
  envApiUrl = `${envApiUrl}/api/v1`;
}

const BASE_CANDIDATES = [
  envApiUrl,
  "/api/v1",
  "http://localhost:8000/api/v1",
  "http://127.0.0.1:8000/api/v1",
].filter(Boolean);

export const getStoredTokenPair = () => {
  try {
    const access = localStorage.getItem("smartsweep-access-token");
    const refresh = localStorage.getItem("smartsweep-refresh-token");
    return { access, refresh };
  } catch {
    return { access: null, refresh: null };
  }
};

export const setStoredTokenPair = (accessToken, refreshToken) => {
  if (accessToken) localStorage.setItem("smartsweep-access-token", accessToken);
  else localStorage.removeItem("smartsweep-access-token");

  if (refreshToken) localStorage.setItem("smartsweep-refresh-token", refreshToken);
  else localStorage.removeItem("smartsweep-refresh-token");
};

export const clearStoredTokenPair = () => {
  localStorage.removeItem("smartsweep-access-token");
  localStorage.removeItem("smartsweep-refresh-token");
};

async function rawFetch(endpoint, config) {
  let lastError = null;
  for (const base of BASE_CANDIDATES) {
    try {
      const url = `${base}${endpoint}`;
      const response = await fetch(url, config);
      // If we get a 404 HTML response from Vite dev server for relative route, try next candidate
      const contentType = response.headers.get("content-type") || "";
      if (response.status === 404 && contentType.includes("text/html") && base === "/api/v1") {
        continue;
      }
      return response;
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error("Failed to connect to backend server. Make sure backend is running on port 8000.");
}

let onUnauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  onUnauthorizedHandler = handler;
};

export async function apiFetch(endpoint, options = {}) {
  const { access } = getStoredTokenPair();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (access) {
    headers["Authorization"] = `Bearer ${access}`;
  }

  const config = {
    ...options,
    headers,
  };

  let response;
  try {
    response = await rawFetch(endpoint, config);
  } catch (err) {
    return {
      success: false,
      status: 0,
      error: err.message || "Failed to connect to server.",
      code: "NETWORK_ERROR",
    };
  }

  // Auto-refresh token on 401 UNAUTHENTICATED
  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const { refresh } = getStoredTokenPair();
    if (refresh) {
      const refreshed = await refreshTokenApi(refresh);
      if (refreshed.success) {
        headers["Authorization"] = `Bearer ${refreshed.access_token}`;
        try {
          response = await rawFetch(endpoint, { ...config, headers });
          if (response.status === 401) {
            // Second failure on retry -> clear tokens and trigger logout
            clearStoredTokenPair();
            if (onUnauthorizedHandler) onUnauthorizedHandler();
          }
        } catch {
          clearStoredTokenPair();
          if (onUnauthorizedHandler) onUnauthorizedHandler();
        }
      } else {
        clearStoredTokenPair();
        if (onUnauthorizedHandler) onUnauthorizedHandler();
      }
    } else {
      clearStoredTokenPair();
      if (onUnauthorizedHandler) onUnauthorizedHandler();
    }
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    let errorMsg = data?.error?.message || data?.message;
    let details = data?.error?.details;

    // Handle FastAPI Pydantic validation errors (422)
    if (!errorMsg && Array.isArray(data?.detail)) {
      errorMsg = "Validation failed: " + data.detail.map((e) => e.msg).join(", ");
      details = data.detail;
    } else if (!errorMsg && typeof data?.detail === "string") {
      errorMsg = data.detail;
    }

    if (!errorMsg) errorMsg = "An unexpected error occurred.";

    const errorCode = data?.error?.code || "API_ERROR";
    return { success: false, status: response.status, error: errorMsg, code: errorCode, details };
  }

  return { success: true, data };
}

// Authentication API calls
export async function loginApi(email, password) {
  const result = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  if (result.success) {
    setStoredTokenPair(result.data.access_token, result.data.refresh_token);
  }

  return result;
}

export async function registerApi(userData) {
  const result = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(userData),
  });

  return result;
}

export async function getMeApi() {
  return await apiFetch("/auth/me", {
    headers: {
      "Cache-Control": "no-cache",
      "Pragma": "no-cache"
    }
  });
}

export async function createComplaintApi(payload) {
  return await apiFetch("/complaints", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadPhotoApi(fileOrBlob) {
  const formData = new FormData();
  formData.append("photo", fileOrBlob, "evidence.jpg");

  const { access } = getStoredTokenPair();
  const headers = {};
  if (access) {
    headers["Authorization"] = `Bearer ${access}`;
  }

  for (const base of BASE_CANDIDATES) {
    try {
      const response = await fetch(`${base}/complaints/upload-photo`, {
        method: "POST",
        headers,
        body: formData,
      });
      if (response.ok) {
        const data = await response.json();
        return { success: true, url: data.url };
      }
    } catch {
      // try next candidate
    }
  }
  return { success: false, error: "Failed to upload photo to server." };
}

export function getMediaUrl(path) {
  if (!path || typeof path !== "string" || !path.trim() || path === "null" || path === "undefined") {
    return null;
  }
  if (
    path.startsWith("http://") ||
    path.startsWith("https://") ||
    path.startsWith("data:") ||
    path.startsWith("blob:")
  ) {
    return path;
  }

  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  if (import.meta.env.VITE_API_URL) {
    const backendBase = import.meta.env.VITE_API_URL.trim()
      .replace(/\/api\/v1\/?$/, "")
      .replace(/\/$/, "");
    return `${backendBase}${cleanPath}`;
  }

  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ) {
    return `http://${window.location.hostname}:8000${cleanPath}`;
  }

  return cleanPath;
}

export async function refreshTokenApi(refreshToken) {
  let response;
  try {
    response = await rawFetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return { success: false };
  }

  const data = await response.json().catch(() => ({}));
  if (response.ok && data.access_token) {
    setStoredTokenPair(data.access_token, data.refresh_token);
    return { success: true, access_token: data.access_token, refresh_token: data.refresh_token };
  }

  return { success: false };
}

// Transparency / Public Feed API calls
export async function getFeedPostsApi(page = 1, pageSize = 30) {
  return await apiFetch(`/transparency?page=${page}&page_size=${pageSize}`);
}

export async function createTransparencyPostApi(postData) {
  return await apiFetch("/transparency", {
    method: "POST",
    body: JSON.stringify(postData),
  });
}

export async function applaudTransparencyPostApi(postId) {
  return await apiFetch(`/transparency/${postId}/applaud`, {
    method: "POST",
  });
}

export async function addTransparencyCommentApi(postId, commentText) {
  return await apiFetch(`/transparency/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ comment: commentText }),
  });
}

export async function getTransparencyCommentsApi(postId) {
  return await apiFetch(`/transparency/${postId}/comments`);
}

// Complaint Resolution with Completion Proof Photos
export async function resolveComplaintApi(complaintId, { completion_photos, resolution_notes }) {
  return await apiFetch(`/complaints/${complaintId}/resolve`, {
    method: "POST",
    body: JSON.stringify({
      completion_photos,
      resolution_notes: resolution_notes || null,
    }),
  });
}
