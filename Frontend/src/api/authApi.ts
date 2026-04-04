import { axiosClient } from "./axiosClient";

export const loginUser = async (credentials: any) => {
  const { data } = await axiosClient.post("/auth/login", credentials);
  return data;
};

export const registerUser = async (userData: any) => {
  const { data } = await axiosClient.post("/auth/register", userData);
  return data;
};

export const getMe = async () => {
  const { data } = await axiosClient.get("/auth/me");
  return data;
};
