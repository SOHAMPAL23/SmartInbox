import { axiosClient } from "./axiosClient";

// Matches backend: /admin/retrain
export const retrainModel = async (formData: FormData) => {
  const { data } = await axiosClient.post("/admin/retrain", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

// Matches backend: /admin/update-threshold
export const updateThreshold = async (threshold: number) => {
  const { data } = await axiosClient.post("/admin/update-threshold", { threshold, reason: "Admin Dashboard Tuning" });
  return data;
};

// Matches backend: /admin/model-info
export const getModelInfo = async () => {
  const { data } = await axiosClient.get("/admin/model-info");
  return data;
};

// Matches backend: /admin/metrics
export const getAdminMetrics = async () => {
  const { data } = await axiosClient.get("/admin/metrics");
  return data;
};

export const getFeatureImportance = async (topN: number = 20) => {
  const { data } = await axiosClient.get(`/admin/model-info/feature-importance?top_n=${topN}`);
  return data;
};
