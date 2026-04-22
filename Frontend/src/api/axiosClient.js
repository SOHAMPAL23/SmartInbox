import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

/** Extract access token from localStorage — used by REST client and WebSocket. */
export const getAccessToken = () => {
  try {
    const raw = localStorage.getItem("authTokens");
    return raw ? (JSON.parse(raw)?.access_token ?? null) : null;
  } catch {
    return null;
  }
};

// ── Authenticated axios client ────────────────────────────────────────────────
export const axiosClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000, // 15 s — fast-fail on stalled requests
});

// Auto-inject JWT
axiosClient.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) config.headers["Authorization"] = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle common HTTP errors
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401 && !window.location.pathname.includes("/login")) {
      localStorage.removeItem("authTokens");
      window.location.href = "/login?expired=true";
    }
    if (status === 429) {
      error._isRateLimit = true;
      error.message = "Too many requests. Please wait a moment and try again.";
    }
    if (status === 503) {
      error.message = "The ML model is currently loading. Please try again shortly.";
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
