import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

// ── Public client (no auth interceptor — for admin panel) ─────────────────────
export const publicClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});
