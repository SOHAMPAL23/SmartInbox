import axios from "axios";

const API_URL = "http://localhost:8000/api/v1";

export const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Response interceptor to catch 401s for login expiry
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            if (!window.location.pathname.includes("/login")) {
                // Auto-logout: Remove tokens and redirect to login
                localStorage.removeItem("authTokens");
                window.location.href = "/login?expired=true";
            }
        }
        return Promise.reject(error);
    }
);
