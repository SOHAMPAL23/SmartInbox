import { useState, useEffect, memo } from "react";
import { motion } from "framer-motion";
import {
  ScrollText, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight,
  Terminal,
  Download
} from "lucide-react";
import { getAdminLogs } from "../../api/adminApi";
import { useStore } from "../../store/useStore";
import { toast } from "react-hot-toast";
import { format } from "date-fns";

const ACTION_MAP = {
  admin_login:      { color: "indigo",  label: "AUTH_INIT" },
  update_user:      { color: "amber",   label: "ENTITY_PATCH" },
  delete_user:      { color: "rose",    label: "ENTITY_PURGE" },
  delete_prediction:{ color: "orange",  label: "PACKET_DROP" },
  export_csv:       { color: "blue",    label: "EXFILTRATION" },
  retrain_model:    { color: "emerald", label: "CORE_SYNTH" },
  update_threshold: { color: "sky",     label: "PARAM_SYNC" },
};

const LogEntry = memo(({ log, i }) => {
  const actionCfg = ACTION_MAP[log.action] || { color: "slate", label: log.action };
  return (
    <motion.div 
      initial={{ opacity: 0, x: -5 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.01 }}
      className="grid grid-cols-12 gap-4 px-6 py-2 hover:bg-slate-50 transition-colors group font-mono text-[10px]"
    >
      <div className="col-span-2 text-slate-400">
        [{format(new Date(log.timestamp), "HH:mm:ss.SS")}]
      </div>
      <div className="col-span-2">
        <span className={`text-${actionCfg.color}-600 font-bold`}>
          {actionCfg.label}
        </span>
      </div>
      <div className="col-span-3 text-slate-500 truncate">
        {log.admin_email}
      </div>
      <div className="col-span-4 text-slate-400 truncate italic">
        {log.detail || "No payload"}
      </div>
      <div className="col-span-1 text-right text-slate-300">
        {log.ip_address || "LOCAL"}
      </div>
    </motion.div>
  );
});

export const AdminLogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await getAdminLogs(page, 20, null);
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error("Audit trail retrieval failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, [page]);

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-indigo-100">
            <ScrollText size={12} /> Audit Sequence
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">System Chronicle</h1>
          <p className="text-sm text-slate-500 font-medium">Immutable ledger of administrative interactions.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              const header = ["Timestamp", "Action", "Admin", "Detail", "IP"];
              const lines = [header.join(","), ...logs.map(l => [l.timestamp, l.action, l.admin_email, `"${l.detail}"`, l.ip_address || "LOCAL"].join(","))];
              const blob = new Blob([lines.join("\n")], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `smartinbox_audit_${Date.now()}.csv`;
              a.click();
            }}
            className="btn-premium flex items-center gap-2 h-10 px-5"
          >
            <Download size={16} />
            <span className="text-[10px] font-bold tracking-widest uppercase">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Terminal View */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-6 py-3 bg-slate-50 border-b border-slate-100">
          <div className="flex items-center gap-2 text-[9px] font-black text-slate-400 uppercase tracking-widest">
            <Terminal size={12} /> audit_stream.log
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Live Sync</span>
          </div>
        </div>

        <div className="min-h-[600px] py-4 bg-white">
          {loading ? (
            <div className="h-[500px] flex items-center justify-center">
              <RefreshCw className="animate-spin text-indigo-600" size={32} />
            </div>
          ) : (
            <div className="space-y-0.5">
              {logs.map((log, i) => (
                <LogEntry key={log.id} log={log} i={i} />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center font-mono">
          <div className="text-[9px] text-slate-400 uppercase tracking-widest font-bold">
            CHUNK {page}/{totalPages} — TOTAL {total}
          </div>
          <div className="flex gap-4">
            <button 
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="text-[9px] font-bold text-slate-400 hover:text-indigo-600 transition-colors disabled:opacity-30 uppercase tracking-widest"
            >
              PREV_BKP
            </button>
            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="text-[9px] font-bold text-slate-400 hover:text-indigo-600 transition-colors disabled:opacity-30 uppercase tracking-widest"
            >
              NEXT_BKP
            </button>
          </div>
        </div>
      </div>

      {/* Index */}
      <div className="flex flex-wrap gap-6 px-4">
        {Object.entries(ACTION_MAP).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest">
            <div className={`w-2 h-2 rounded-full bg-${cfg.color}-500 shadow-sm shadow-${cfg.color}-200`} />
            <span className="text-slate-400">{cfg.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

