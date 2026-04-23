import { useState, useEffect, memo, useCallback } from "react";
import { motion } from "framer-motion";
import { format } from "date-fns";
import { 
  Download, 
  FileText, 
  RefreshCw, 
  ShieldAlert, 
  ShieldCheck, 
  Zap, 
  ChevronLeft, 
  ChevronRight,
  History
} from "lucide-react";
import { getHistory, exportHistory } from "../../api/spamApi";
import { useStore } from "../../store/useStore";
import { toast } from "react-hot-toast";
import { VirtualList } from "../../components/ui/VirtualList";

const LogItem = memo(({ msg }) => (
  <div className="grid grid-cols-12 gap-6 px-8 py-4 items-center hover:bg-slate-50 transition-colors group border-b border-slate-100 bg-white">
    <div className="col-span-6 flex gap-4 items-start">
      <div className={`p-2.5 rounded-xl ${msg.is_spam ? "bg-rose-50 text-rose-500" : "bg-emerald-50 text-emerald-500"}`}>
        <FileText size={18} />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-bold text-slate-800 truncate leading-snug group-hover:text-indigo-600 transition-colors">
          "{msg.text}"
        </p>
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1.5 flex items-center gap-1.5">
          <Zap size={10} className="text-indigo-500" />
          v{msg.model_version} • {format(new Date(msg.predicted_at), "MMM d, HH:mm")}
        </p>
      </div>
    </div>

    <div className="col-span-3 flex justify-center">
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${msg.is_spam ? "bg-rose-50 border-rose-100 text-rose-600" : "bg-emerald-50 border-emerald-100 text-emerald-600"} text-[9px] font-black tracking-widest uppercase`}>
        {msg.is_spam ? <ShieldAlert size={12} /> : <ShieldCheck size={12} />}
        {msg.is_spam ? "Spam" : "Clean"}
      </div>
    </div>

    <div className="col-span-3 flex flex-col items-end gap-1.5">
      <span className="text-xs font-black text-slate-900">{(msg.probability * 100).toFixed(0)}%</span>
      <div className="w-20 h-1 bg-slate-100 rounded-full overflow-hidden">
        <div 
          className={`h-full ${msg.is_spam ? "bg-rose-500" : "bg-emerald-500"}`}
          style={{ width: `${msg.probability * 100}%` }}
        />
      </div>
    </div>
  </div>
));

export const HistoryPage = () => {
  const storeHistory = useStore((state) => state.history);
  const [history, setHistory] = useState(storeHistory || []);
  const [pagination, setPagination] = useState({ total: 0, page: 1, size: 20, totalPages: 1 });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(storeHistory.length === 0);
  const [isExporting, setIsExporting] = useState(false);
  const [filterSpam, setFilterSpam] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const histData = await getHistory(page, 20, filterSpam);
      setHistory(histData.items || []);
      setPagination({
        total: histData.total || 0,
        page: histData.page || 1,
        size: histData.size || 20,
        totalPages: Math.ceil((histData.total || 0) / (histData.size || 20)),
      });
    } catch (err) {
      toast.error("Failed to load telemetry logs.");
    } finally {
      setLoading(false);
    }
  }, [page, filterSpam]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportHistory({ isSpam: filterSpam });
      toast.success("Telemetry report exported.");
    } catch {
      toast.error("Export sequence failed.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-indigo-100">
            <History size={12} /> Archival smartinbox
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Detection Logs</h1>
          <p className="text-sm text-slate-500 font-medium">Browse and export historical classification telemetry.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleExport}
            disabled={isExporting}
            className="btn-premium flex items-center gap-2 h-10 px-5 disabled:opacity-50"
          >
            {isExporting ? <RefreshCw className="animate-spin" size={16} /> : <Download size={16} />}
            <span className="text-[10px] font-bold tracking-widest uppercase">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Main Logs Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Table Controls */}
        <div className="p-4 border-b border-slate-100 flex flex-wrap gap-4 items-center justify-between bg-slate-50/50">
          <div className="flex bg-white rounded-xl p-1 border border-slate-200">
            {[
              { label: "All Logs", val: null },
              { label: "Spam", val: true },
              { label: "Clean", val: false }
            ].map(f => (
              <button
                key={f.label}
                onClick={() => { setFilterSpam(f.val); setPage(1); }}
                className={`px-4 py-1.5 rounded-lg text-[10px] font-bold tracking-widest uppercase transition-all ${
                  filterSpam === f.val 
                    ? "bg-slate-900 text-white shadow-sm" 
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Total: <span className="text-slate-900">{pagination.total.toLocaleString()}</span>
          </div>
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-12 gap-6 px-8 py-3 bg-slate-50 border-b border-slate-200 text-[9px] font-bold tracking-widest text-slate-400 uppercase">
          <div className="col-span-6">Message Matrix</div>
          <div className="col-span-3 text-center">Verdict</div>
          <div className="col-span-3 text-right">Probability</div>
        </div>

        {/* Table Body with Virtualization */}
        <div className="min-h-[500px] bg-slate-50">
          {loading ? (
            <div className="h-[500px] flex items-center justify-center">
              <RefreshCw className="animate-spin text-indigo-600" size={32} />
            </div>
          ) : history.length > 0 ? (
            <VirtualList 
              items={history} 
              itemHeight={73} 
              containerHeight={500}
              renderItem={(msg) => <LogItem key={msg.id} msg={msg} />}
            />
          ) : (
            <div className="h-[500px] flex flex-col items-center justify-center text-slate-500 gap-4">
              <FileText size={48} className="opacity-10" />
              <p className="text-[10px] font-bold uppercase tracking-widest opacity-50">No logs detected</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        <div className="p-4 bg-white border-t border-slate-200 flex justify-between items-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Page {pagination.page} of {pagination.totalPages}
          </p>
          <div className="flex gap-2">
            <button 
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="p-1.5 bg-white border border-slate-200 rounded-lg disabled:opacity-30 hover:bg-slate-50 transition-all"
            >
              <ChevronLeft size={18} />
            </button>
            <button 
              disabled={page >= pagination.totalPages}
              onClick={() => setPage(page + 1)}
              className="p-1.5 bg-white border border-slate-200 rounded-lg disabled:opacity-30 hover:bg-slate-50 transition-all"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

