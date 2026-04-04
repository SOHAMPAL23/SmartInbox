import axios from "axios";

const API_URL = "http://localhost:8000/api/v1";

export const axiosClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes("/login")) {
         localStorage.removeItem("authTokens");
         window.location.href = "/login?expired=true";
    }
    return Promise.reject(error);
  }
);
