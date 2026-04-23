import React, { useState, useEffect, useRef, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, ShieldAlert, Info, Check, X } from "lucide-react";
import { axiosClient, getAccessToken } from "../../api/axiosClient";

const POLL_INTERVAL = 15_000; // 15s fallback polling
const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000/api/v1";

export const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const wsRef = useRef(null);
  const pollRef = useRef(null);
  const reconnectRef = useRef(null);

  // ── Fetch via REST (initial + fallback polling) ───────────────────────────
  const fetchNotifs = useCallback(async () => {
    try {
      const { data } = await axiosClient.get("/notifications");
      setNotifications(data.items || []);
    } catch {
      // silent — user may be on a page before login is complete
    }
  }, []);

  // ── WebSocket connection ──────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;

    try {
      const ws = new WebSocket(`${WS_BASE}/ws/notifications?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        // WS is live — clear fallback polling
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const notif = JSON.parse(event.data);
          if (notif.type === "ping") return;
          setNotifications((prev) => [notif, ...prev]);
        } catch { /* ignore malformed */ }
      };

      ws.onclose = () => {
        // Start fallback polling, schedule reconnect with backoff
        if (!pollRef.current) {
          pollRef.current = setInterval(fetchNotifs, POLL_INTERVAL);
        }
        reconnectRef.current = setTimeout(connectWS, 5000);
      };

      ws.onerror = () => ws.close();
    } catch {
      // WS not available — rely on polling only
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchNotifs, POLL_INTERVAL);
      }
    }
  }, [fetchNotifs]);

  useEffect(() => {
    fetchNotifs();
    connectWS();

    // Listen for custom event fired by ScanPage after spam detection
    const onNewNotif = () => fetchNotifs();
    window.addEventListener("notification:new", onNewNotif);

    return () => {
      window.removeEventListener("notification:new", onNewNotif);
      wsRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connectWS, fetchNotifs]);

  const handleRead = useCallback(async (id) => {
    try {
      await axiosClient.patch(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch { /* silent */ }
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="relative">
      <button
        id="notification-bell"
        onClick={() => setIsOpen((o) => !o)}
        className={`relative p-2 rounded-xl border transition-all duration-150
          ${isOpen
            ? "bg-blue-50 border-blue-200 text-blue-600"
            : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-800"
          }`}
      >
        <Bell size={17} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full
                           flex items-center justify-center text-[9px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

              <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="absolute right-0 top-full mt-3 w-[340px] bg-white/95 backdrop-blur-xl border border-slate-200/60
                         rounded-3xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] z-50 overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100/50 bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Bell size={14} className="text-slate-500" />
                  <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest">
                    Notifications
                  </h4>
                  {unreadCount > 0 && (
                    <span className="bg-rose-500 text-white px-2 py-0.5 rounded-full text-[9px] font-bold shadow-sm">{unreadCount} new</span>
                  )}
                </div>
                <button onClick={() => setIsOpen(false)} className="p-1.5 rounded-xl hover:bg-slate-200/50 transition-colors">
                  <X size={14} className="text-slate-400" />
                </button>
              </div>

              {/* List */}
              <div className="max-h-[380px] overflow-y-auto custom-scrollbar divide-y divide-slate-100/50">
                {notifications.length > 0 ? notifications.map((n) => (
                    <div
                    key={n.id}
                    className={`flex gap-4 p-5 group transition-all duration-200
                      ${!n.is_read ? "bg-blue-50/40" : "hover:bg-slate-50/80"}`}
                  >
                    <div className={`flex-shrink-0 p-2 rounded-xl mt-0.5 shadow-sm
                      ${n.type === "security" ? "bg-rose-100 text-rose-500" : "bg-blue-100 text-blue-500"}`}
                    >
                      {n.type === "security" ? <ShieldAlert size={16} /> : <Info size={16} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-bold text-slate-800 truncate">{n.title}</p>
                      <p className="text-[12px] text-slate-500 leading-relaxed mt-1 line-clamp-2">{n.message}</p>
                      <p className="text-[10px] font-medium text-slate-400 mt-2 flex items-center gap-1">
                        {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={() => handleRead(n.id)}
                        title="Mark as read"
                        className="opacity-0 group-hover:opacity-100 flex-shrink-0 p-1 rounded-lg
                                   hover:bg-emerald-50 text-emerald-500 transition-all"
                      >
                        <Check size={13} />
                      </button>
                    )}
                  </div>
                )) : (
                  <div className="py-12 text-center">
                    <Bell size={20} className="text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No notifications yet</p>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
