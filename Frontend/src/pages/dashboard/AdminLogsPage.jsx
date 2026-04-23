import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ScrollText, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight,
  ShieldAlert, 
  Filter,
  Terminal,
  Clock,
  Globe,
  Database,
  Search,
  Download
} from "lucide-react";
import { getAdminLogs } from "../../api/adminApi";
import { toast } from "react-hot-toast";
import { format } from "date-fns";

const ACTION_MAP = {
  admin_login:      { color: "cyan",    label: "ACCESS_GRANTED" },
  update_user:      { color: "amber",   label: "ENTITY_MODIFIED" },
  delete_user:      { color: "rose",    label: "ENTITY_PURGED" },
  delete_prediction:{ color: "orange",  label: "PACKET_DROPPED" },
  export_csv:       { color: "indigo",  label: "DATA_EXPORT" },
  retrain_model:    { color: "emerald", label: "NEURAL_SYNTHESIS" },
  update_threshold: { color: "sky",     label: "THRESHOLD_SYNC" },
};

export const AdminLogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState(null);

  const PAGE_SIZE = 15;

  const fetchLogs = async (p = page, act = action) => {
    setLoading(true);
    try {
      const data = await getAdminLogs(p, PAGE_SIZE, act);
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error("Audit trail retrieval failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(page, action); }, [page, action]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-7xl mx-auto space-y-12 pb-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase text-indigo-400">
            <ScrollText size={14} /> Audit Sequence
          </div>
          <h1 className="text-5xl font-black text-slate-900 tracking-tighter">
            System <span className="text-blue-600 font-semibold">Chronicle</span>
          </h1>
          <p className="text-slate-500 max-w-xl font-medium">
            Immutable ledger of administrative interactions and neural system modifications.
          </p>
        </div>

        <div className="flex gap-3 items-center">
          <button 
            onClick={() => {
              if (!logs.length) return toast.error("No logs to export");
              const header = ["Timestamp", "Action", "Admin Email", "Detail", "IP"];
              const lines = [header.join(",")];
              logs.forEach(log => {
                lines.push([
                  log.timestamp,
                  log.action,
                  log.admin_email,
                  `"${(log.detail || "").replace(/"/g, '""')}"`,
                  log.ip_address || "LOCAL"
                ].join(","));
              });
              const blob = new Blob([lines.join("\n")], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `audit_logs_${Date.now()}.csv`;
              a.click();
              toast.success("Audit logs exported.");
            }}
            className="btn-primary flex items-center gap-2 px-6 h-12"
          >
            <Download size={18} />
            <span className="text-xs font-black tracking-widest uppercase">Export CSV</span>
          </button>
          <button 
            onClick={() => fetchLogs()}
            className=" p-3 rounded-xl border-slate-200 text-slate-500 hover:text-slate-900 transition-all"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Terminal Container */}
      <div className=" rounded-3xl border border-slate-200 shadow-sm overflow-hidden bg-white">
        <div className="flex items-center justify-between px-8 py-4 bg-slate-50 border-b border-slate-100">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">
              <Terminal size={12} /> nexus_audit_log_v2.bin
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest animate-pulse">● System Uplink Active</span>
          </div>
        </div>

        <div className="min-h-[600px] font-mono p-4 space-y-1">
          <AnimatePresence mode="wait">
            {loading ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              </div>
            ) : (
              <div className="space-y-1">
                {logs.map((log, i) => {
                  const actionCfg = ACTION_MAP[log.action] || { color: "slate", label: log.action };
                  return (
                    <motion.div 
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      key={log.id}
                      className="grid grid-cols-12 gap-4 px-4 py-2 hover:bg-slate-50 rounded-lg transition-colors group text-[11px]"
                    >
                      <div className="col-span-2 text-slate-600">
                        [{format(new Date(log.timestamp), "HH:mm:ss.SS")}]
                      </div>
                      <div className="col-span-2">
                        <span className={`text-${actionCfg.color}-600 font-black`}>
                          {actionCfg.label}
                        </span>
                      </div>
                      <div className="col-span-3 text-slate-500 truncate">
                        <span className="text-slate-600">USR:</span> {log.admin_email}
                      </div>
                      <div className="col-span-4 text-slate-500 italic truncate">
                        {log.detail || "No additional payload"}
                      </div>
                      <div className="col-span-1 text-right text-slate-600">
                        {log.ip_address || "LOCAL"}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Controls */}
        <div className="px-8 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center font-mono">
          <div className="flex gap-4">
            <span className="text-[10px] text-slate-600 uppercase tracking-widest">Page {page}/{totalPages}</span>
            <span className="text-[10px] text-slate-600 uppercase tracking-widest">Entries: {total}</span>
          </div>
          <div className="flex gap-4">
            <button 
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="text-slate-500 hover:text-slate-900 transition-colors disabled:opacity-30"
            >
              PREV_CHUNK
            </button>
            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="text-slate-500 hover:text-slate-900 transition-colors disabled:opacity-30"
            >
              NEXT_CHUNK
            </button>
          </div>
        </div>
      </div>

      {/* Action Index */}
      <div className="flex flex-wrap gap-4 opacity-50 hover:opacity-100 transition-opacity">
        {Object.entries(ACTION_MAP).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest">
            <div className={`w-2 h-2 rounded-full bg-${cfg.color}-500`} />
            <span className="text-slate-500">{cfg.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
