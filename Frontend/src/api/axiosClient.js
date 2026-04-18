import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

// ── Authenticated client – always sends JWT ───────────────────────────────────
export const axiosClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Auto-inject JWT from localStorage
axiosClient.interceptors.request.use(
  (config) => {
    try {
      const raw = localStorage.getItem("authTokens");
      if (raw) {
        const tokens = JSON.parse(raw);
        if (tokens?.access_token) {
          config.headers["Authorization"] = `Bearer ${tokens.access_token}`;
        }
      }
    } catch {
      // Malformed storage – ignore
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 / 429 / 503
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
