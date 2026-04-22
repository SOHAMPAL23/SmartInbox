/**
 * adminApi.js
 * -----------
 * All admin API calls. Uses the authenticated axiosClient (JWT injected)
 * so every request is properly authorized.
 *
 * const ADMIN_API = "/api/v1/admin"  (handled by axiosClient baseURL + prefix)
 */
import { axiosClient } from "./axiosClient";

// ── Auth ──────────────────────────────────────────────────────────────────────

/** POST /admin/login – dedicated admin login endpoint */
export const adminLogin = async ({ email, password }) => {
  const { data } = await axiosClient.post("/admin/login", { email, password });
  return data;
};

// ── Model management ──────────────────────────────────────────────────────────

export const retrainModel = async (formData) => {
  const { data } = await axiosClient.post("/admin/retrain", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300_000,
  });
  return data;
};

export const updateThreshold = async (threshold, reason = "Admin Dashboard Tuning") => {
  const { data } = await axiosClient.post("/admin/update-threshold", { threshold, reason });
  return data;
};

export const getModelInfo = async () => {
  const { data } = await axiosClient.get("/admin/model-info");
  return data;
};

export const getAdminMetrics = async () => {
  const { data } = await axiosClient.get("/admin/metrics");
  return data;
};

export const getFeatureImportance = async (topN = 20) => {
  const { data } = await axiosClient.get(`/admin/model-info/feature-importance?top_n=${topN}`);
  return data;
};

export const getModelVersions = async () => {
  const { data } = await axiosClient.get("/admin/model-versions");
  return data;
};

// ── Dashboard & stats ─────────────────────────────────────────────────────────

export const getAdminDashboard = async (days = 30) => {
  const { data } = await axiosClient.get(`/admin/dashboard?days=${days}`);
  return data;
};

export const getAdminStats = async () => {
  const { data } = await axiosClient.get("/admin/stats");
  return data;
};

// ── Global analytics ──────────────────────────────────────────────────────────

export const getAdminAnalytics = async (days = 30) => {
  const { data } = await axiosClient.get(`/admin/analytics?days=${days}`);
  return data;
};

// ── User management ───────────────────────────────────────────────────────────

export const getAdminUsers = async (page = 1, size = 20) => {
  const { data } = await axiosClient.get(`/admin/users?page=${page}&size=${size}`);
  return data;
};

export const toggleUserStatus = async (userId, isActive) => {
  const { data } = await axiosClient.patch(`/admin/users/${userId}`, { is_active: isActive });
  return data;
};

export const updateUserRole = async (userId, role) => {
  const { data } = await axiosClient.patch(`/admin/users/${userId}`, { role });
  return data;
};

/** DELETE /admin/users/{id} – permanently delete user + all their data */
export const deleteUser = async (userId) => {
  const { data } = await axiosClient.delete(`/admin/users/${userId}`);
  return data;
};

export const getUserAnalyticsForAdmin = async (userId, days = 30) => {
  const { data } = await axiosClient.get(`/admin/users/${userId}/analytics?days=${days}`);
  return data;
};

export const sendAdminNotification = async ({ userId, title, message, type }) => {
  const { data } = await axiosClient.post("/admin/notifications", {
    user_id: userId,
    title,
    message,
    type,
  });
  return data;
};

// ── Message / prediction monitoring ──────────────────────────────────────────

/**
 * GET /admin/messages
 * @param {number} page
 * @param {number} size
 * @param {boolean|null} isSpam  - null=all, true=spam, false=ham
 * @param {string|null}  userId
 * @param {string|null}  q       - text search
 */
export const getAdminMessages = async ({ page = 1, size = 20, isSpam = null, userId = null, q = null } = {}) => {
  const params = new URLSearchParams({ page, size });
  if (isSpam !== null) params.append("is_spam", isSpam);
  if (userId)          params.append("user_id", userId);
  if (q)               params.append("q", q);
  const { data } = await axiosClient.get(`/admin/messages?${params}`);
  return data;
};

export const deleteAdminPrediction = async (predictionId) => {
  const { data } = await axiosClient.delete(`/admin/predictions/${predictionId}`);
  return data;
};

// ── Audit logs ────────────────────────────────────────────────────────────────

export const getAdminLogs = async (page = 1, size = 20, action = null) => {
  const params = new URLSearchParams({ page, size });
  if (action) params.append("action", action);
  const { data } = await axiosClient.get(`/admin/logs?${params}`);
  return data;
};

// ── CSV Export ────────────────────────────────────────────────────────────────

export const exportAdminPredictions = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.isSpam !== null && filters.isSpam !== undefined)
    params.append("is_spam", filters.isSpam);
  if (filters.fromDate) params.append("from_date", filters.fromDate);
  if (filters.toDate)   params.append("to_date",   filters.toDate);

  const response = await axiosClient.get(`/admin/export?${params}`, { responseType: "blob" });

  const url  = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href  = url;
  const cd    = response.headers["content-disposition"] || "";
  const match = cd.match(/filename="?([^"]+)"?/);
  link.setAttribute("download", match ? match[1] : "smartinbox_admin_export.csv");
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
