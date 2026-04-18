import { axiosClient } from "./axiosClient";

export const predictText = async (text: string) => {
  const { data } = await axiosClient.post("/user/predict", { text });
  return data;
};

export const predictCSV = async (formData: FormData) => {
  const { data } = await axiosClient.post("/user/predict-batch-csv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const getSpamTrends = async (days: number = 7) => {
  const { data } = await axiosClient.get(`/user/spam-trends?days=${days}`);
  return data;
};

export const getHistory = async (page: number = 1, size: number = 20, isSpam?: boolean) => {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (isSpam !== undefined && isSpam !== null) {
    params.set("is_spam", String(isSpam));
  }
  const { data } = await axiosClient.get(`/user/history?${params}`);
  return data;
};

export const exportHistory = async (filters?: { isSpam?: boolean; fromDate?: string; toDate?: string }) => {
  const params = new URLSearchParams();
  if (filters?.isSpam !== undefined && filters.isSpam !== null) {
    params.set("is_spam", String(filters.isSpam));
  }
  if (filters?.fromDate) params.set("from_date", filters.fromDate);
  if (filters?.toDate) params.set("to_date", filters.toDate);
  const query = params.toString() ? `?${params.toString()}` : "";
  const { data } = await axiosClient.get(`/user/export${query}`, {
    responseType: "blob",
  });
  return data;
};
