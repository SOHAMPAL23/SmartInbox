import { useState, useEffect, useCallback, memo } from "react";
import { 
  MessageSquare, 
  RefreshCw, 
  Trash2, 
  Download, 
  Search,
  ShieldAlert, 
  ShieldCheck, 
  ChevronLeft, 
  ChevronRight,
  User,
  Clock
} from "lucide-react";
import {
  getAdminMessages, deleteAdminPrediction, exportAdminPredictions
} from "../../api/adminApi";
import { useStore } from "../../store/useStore";
import { toast } from "react-hot-toast";
import { format } from "date-fns";
import { VirtualList } from "../../components/ui/VirtualList";

const MessageItem = memo(({ item, onDelete }) => (
  <div className="grid grid-cols-12 gap-6 px-8 py-4 items-center hover:bg-slate-50 transition-colors group border-b border-slate-100 bg-white">
    <div className="col-span-6 flex gap-4 items-start">
      <div className={`p-2.5 rounded-xl ${item.is_spam ? "bg-rose-50 text-rose-500" : "bg-emerald-50 text-emerald-500"}`}>
        {item.is_spam ? <ShieldAlert size={18} /> : <ShieldCheck size={18} />}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-bold text-slate-800 truncate leading-snug group-hover:text-indigo-600 transition-colors">
          "{item.message_text}"
        </p>
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1.5 flex items-center gap-2">
          <Clock size={10} className="text-indigo-500" />
          {format(new Date(item.predicted_at), "MMM d, HH:mm")}
        </p>
      </div>
    </div>

    <div className="col-span-2 flex flex-col items-center gap-1">
      <div className="flex items-center gap-2">
        <User size={12} className="text-slate-400" />
        <span className="text-xs font-bold text-slate-700">{item.username}</span>
      </div>
    </div>

    <div className="col-span-2 flex flex-col items-center gap-1.5">
      <span className="text-xs font-black text-slate-900">{(item.probability * 100).toFixed(0)}%</span>
      <div className="w-20 h-1 bg-slate-100 rounded-full overflow-hidden">
        <div 
          className={`h-full ${item.is_spam ? "bg-rose-500" : "bg-emerald-500"}`}
          style={{ width: `${item.probability * 100}%` }}
        />
      </div>
    </div>

    <div className="col-span-2 flex justify-end">
      <button 
        onClick={() => onDelete(item.prediction_id)}
        className="p-2 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 transition-all opacity-0 group-hover:opacity-100"
      >
        <Trash2 size={16} />
      </button>
    </div>
  </div>
));

export const AdminMessagesPage = () => {
  const [data, setData] = useState({ items: [], total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);

  const fetchMessages = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAdminMessages({
        page,
        size: 20,
        isSpam: filter,
        q: search || null,
      });
      setData(res);
    } catch {
      toast.error("Telemetry stream retrieval failed.");
    } finally {
      setLoading(false);
    }
  }, [page, filter, search]);

  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  const handleDelete = async (predId) => {
    try {
      await deleteAdminPrediction(predId);
      toast.success("Packet purged.");
      fetchMessages();
    } catch {
      toast.error("Purge failed.");
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportAdminPredictions({ isSpam: filter });
      toast.success("Intelligence report exported.");
    } catch {
      toast.error("Export sequence failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-50 text-rose-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-rose-100">
            <MessageSquare size={12} /> Packet Monitoring
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Global Intercepts</h1>
          <p className="text-sm text-slate-500 font-medium">Real-time classification monitoring across the ecosystem.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleExport}
            disabled={exporting}
            className="btn-premium flex items-center gap-2 h-10 px-5 disabled:opacity-50"
          >
            {exporting ? <RefreshCw className="animate-spin" size={16} /> : <Download size={16} />}
            <span className="text-[10px] font-bold tracking-widest uppercase">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-6 items-center justify-between bg-white p-4 rounded-3xl border border-slate-200 shadow-sm">
        <div className="flex bg-slate-50 rounded-xl p-1 border border-slate-100">
          {[
            { label: "All Logs", val: null },
            { label: "Spam", val: true },
            { label: "Clean", val: false }
          ].map(f => (
            <button
              key={String(f.val)}
              onClick={() => { setFilter(f.val); setPage(1); }}
              className={`px-5 py-1.5 rounded-lg text-[10px] font-bold tracking-widest uppercase transition-all ${
                filter === f.val 
                  ? "bg-slate-900 text-white shadow-sm" 
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input 
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setSearch(searchInput)}
            placeholder="Search content..."
            className="w-full pl-11 pr-4 h-10 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500/50 transition-all"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-12 gap-6 px-8 py-3 bg-slate-50 border-b border-slate-200 text-[9px] font-bold tracking-widest text-slate-400 uppercase">
          <div className="col-span-6">Payload Matrix</div>
          <div className="col-span-2 text-center">Entity</div>
          <div className="col-span-2 text-center">Confidence</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>

        <div className="min-h-[500px] bg-slate-50">
          {loading ? (
            <div className="h-[500px] flex items-center justify-center">
              <RefreshCw className="animate-spin text-indigo-600" size={32} />
            </div>
          ) : data.items.length > 0 ? (
            <VirtualList 
              items={data.items} 
              itemHeight={73} 
              containerHeight={500}
              renderItem={(item) => <MessageItem key={item.prediction_id} item={item} onDelete={handleDelete} />}
            />
          ) : (
            <div className="h-[500px] flex flex-col items-center justify-center text-slate-500 gap-4">
              <MessageSquare size={48} className="opacity-10" />
              <p className="text-[10px] font-bold uppercase tracking-widest opacity-50">No intercepts detected</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        <div className="p-4 bg-white border-t border-slate-200 flex justify-between items-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Page {page} of {data.pages}
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
              disabled={page >= data.pages}
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
