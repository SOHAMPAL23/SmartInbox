import { axiosClient } from "./axiosClient";

// ── Single prediction (queued job) ────────────────────────────────────────────
export const predictText = async (text) => {
  const { data } = await axiosClient.post("/user/predict", { text });
  return data;
};

// ── Deep hybrid analysis (synchronous, full 4-layer pipeline) ─────────────────
export const analyzeAiSpam = async (text) => {
  const { data } = await axiosClient.post("/user/analyze-ai-spam", { text }, {
    timeout: 30000, // 30s — Groq may take up to 8s
  });
  return data;
};

// ── JSON batch prediction ─────────────────────────────────────────────────────
export const batchPredict = async (texts) => {
  const { data } = await axiosClient.post("/user/batch-predict", { texts });
  return data;
};

// ── CSV file batch upload ─────────────────────────────────────────────────────
export const predictBatchCSV = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await axiosClient.post("/user/predict-batch-csv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
    onUploadProgress,
  });
  return data;
};

// ── Spam trends ───────────────────────────────────────────────────────────────
export const getSpamTrends = async (days = 7) => {
  const { data } = await axiosClient.get(`/user/spam-trends?days=${days}`);
  return data;
};

// ── Job status ────────────────────────────────────────────────────────────────
export const getJobStatus = async (jobId) => {
  const res = await axiosClient.get(`/jobs/${jobId}`);
  return res.data;
};

// ── User stats ────────────────────────────────────────────────────────────────
export const getUserStats = async () => {
  const { data } = await axiosClient.get("/user/stats");
  return data;
};

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory = async (page = 1, size = 20, isSpam = null) => {
  let url = `/user/history?page=${page}&size=${size}`;
  if (isSpam !== null) url += `&is_spam=${isSpam}`;
  const { data } = await axiosClient.get(url);
  return data;
};

// ── Threat report ─────────────────────────────────────────────────────────────
export const getThreatReport = async (days = 30) => {
  const { data } = await axiosClient.get(`/user/threat-report?days=${days}`);
  return data;
};

// ── Export history as CSV ─────────────────────────────────────────────────────
export const exportHistory = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.isSpam !== null && filters.isSpam !== undefined)
    params.append("is_spam", filters.isSpam);
  if (filters.fromDate) params.append("from_date", filters.fromDate);
  if (filters.toDate)   params.append("to_date",   filters.toDate);

  const response = await axiosClient.get(`/user/export?${params.toString()}`, {
    responseType: "blob",
  });

  const url  = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href  = url;
  const contentDisposition = response.headers["content-disposition"] || "";
  const match = contentDisposition.match(/filename="?([^"]+)"?/);
  link.setAttribute("download", match ? match[1] : "smartinbox_export.csv");
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
