import { axiosClient } from "./axiosClient";

export const predictText = async (text: string) => {
  const { data } = await axiosClient.post("/user/predict", { text });
  return data;
};

export const predictCSV = async (formData: FormData) => {
  const { data } = await axiosClient.post("/user/batch-predict", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const getSpamTrends = async (days: number = 7) => {
  const { data } = await axiosClient.get(`/user/spam-trends?days=${days}`);
  return data;
};

export const getHistory = async (page: number = 1, size: number = 20) => {
  const { data } = await axiosClient.get(`/user/history?page=${page}&size=${size}`);
  return data;
};
