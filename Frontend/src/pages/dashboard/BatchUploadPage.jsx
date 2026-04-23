import { useState, useCallback, useRef, memo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, 
  FileText, 
  CheckCircle, 
  XCircle, 
  Download, 
  RefreshCw, 
  ShieldAlert, 
  ShieldCheck, 
  HelpCircle,
  ChevronRight,
  Database,
  Layers,
  History
} from "lucide-react";
import { predictBatchCSV, getJobStatus } from "../../api/spamApi";
import { toast } from "react-hot-toast";

const MAX_FILE_SIZE_MB = 5;
const MAX_FILE_SIZE    = MAX_FILE_SIZE_MB * 1024 * 1024;

const VerdictBadge = memo(({ verdict }) => {
  if (!verdict) return null;
  const cfg = {
    SPAM:      { cls: "bg-rose-50 text-rose-600 border-rose-100",    icon: ShieldAlert,  label: "SPAM"      },
    HAM:       { cls: "bg-emerald-50 text-emerald-600 border-emerald-100", icon: ShieldCheck,  label: "CLEAN"  },
    UNCERTAIN: { cls: "bg-amber-50 text-amber-600 border-amber-100", icon: HelpCircle,   label: "UNCERTAIN" },
  }[verdict] || { cls: "bg-slate-50 text-slate-500 border-slate-100", icon: HelpCircle, label: verdict };

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[9px] font-black tracking-widest border ${cfg.cls} shadow-sm`}>
      <cfg.icon size={10} />
      {cfg.label}
    </span>
  );
});

export const BatchUploadPage = () => {
  const [file,          setFile]          = useState(null);
  const [isDragging,    setIsDragging]    = useState(false);
  const [isProcessing,  setIsProcessing]  = useState(false);
  const [uploadPct,     setUploadPct]     = useState(0);
  const [jobId,         setJobId]         = useState(null);
  const [results,       setResults]       = useState(null);
  const [fileError,     setFileError]     = useState("");
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFileSelect = (f) => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setFileError("Invalid format. CSV required.");
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setFileError(`File too large (Max ${MAX_FILE_SIZE_MB}MB)`);
      return;
    }
    setFileError("");
    setFile(f);
    setResults(null);
  };

  const onDragOver  = useCallback((e) => { e.preventDefault(); setIsDragging(true); }, []);
  const onDragLeave = useCallback(() => setIsDragging(false), []);
  const onDrop      = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileSelect(f);
  }, []);

  const handleProcess = async () => {
    if (!file) return;
    setIsProcessing(true);
    setUploadPct(0);
    try {
      const { job_id } = await predictBatchCSV(file, (evt) => {
        if (evt.total) setUploadPct(Math.round((evt.loaded / evt.total) * 50)); // First 50% is upload
      });
      setJobId(job_id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Processing failed.");
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const job = await getJobStatus(jobId);
        setUploadPct(50 + (job.progress || 0) / 2); // Map job progress to 50-100% range

        if (job.status === "completed") {
          clearInterval(pollInterval);
          setIsProcessing(false);
          setJobId(null);
          toast.success("Intelligence ingestion complete.");
          // For batches, we might want to navigate to history or show a summary
          // Here we'll just show the completion toast and allow user to see history
          setResults({ 
            total_rows: job.result.processed, 
            spam_count: job.result.spam_count, 
            ham_count: job.result.ham_count, 
            uncertain_count: job.result.uncertain_count || 0, 
            results: job.result.items || [] 
          });
        } else if (job.status === "failed") {
          clearInterval(pollInterval);
          setIsProcessing(false);
          setJobId(null);
          toast.error(job.error || "Batch ingestion failed.");
        }
      } catch (err) {
        clearInterval(pollInterval);
        setIsProcessing(false);
      }
    }, 1500);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  const downloadResultsCSV = () => {
    if (!results) return;
    const rows = results.results || [];
    const header = ["Row", "Message", "Verdict", "Probability (%)"];
    const lines  = [header.join(",")];
    rows.forEach((r) => {
      lines.push([r.row, `"${(r.message || "").replace(/"/g, '""')}"`, r.verdict || "", (r.probability * 100).toFixed(1)].join(","));
    });
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `smartinbox_batch_${Date.now()}.csv`;
    a.click();
    toast.success("Intelligence report downloaded.");
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-50 text-amber-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-amber-100">
            <Layers size={12} /> Batch Engine
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Intelligence Ingestion</h1>
          <p className="text-sm text-slate-500 font-medium">Upload datasets for automated neural classification.</p>
        </div>
      </div>

      {!results ? (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          <div
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => !isProcessing && fileInputRef.current?.click()}
            className={`relative flex flex-col items-center justify-center p-20 cursor-pointer transition-all ${isDragging ? "bg-indigo-50" : "hover:bg-slate-50"}`}
          >
            <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])} />
            
            <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-6 transition-all ${file ? "bg-emerald-50 scale-110 shadow-sm" : "bg-slate-100"}`}>
              {file ? <CheckCircle size={32} className="text-emerald-500" /> : <Upload size={32} className="text-slate-400" />}
            </div>

            {file ? (
              <div className="text-center space-y-2">
                <h3 className="text-xl font-bold text-slate-900">{file.name}</h3>
                <p className="text-slate-400 font-bold uppercase tracking-widest text-[9px]">{(file.size / 1024).toFixed(1)} KB • READY</p>
                <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="text-rose-500 hover:text-rose-600 transition-colors text-[10px] font-black uppercase tracking-widest pt-4">Remove File</button>
              </div>
            ) : (
              <div className="text-center space-y-3">
                <h3 className="text-xl font-bold text-slate-900">Drop Intelligence Matrix</h3>
                <p className="text-sm text-slate-400 font-medium">CSV payload required for ingestion</p>
                <div className="flex gap-6 justify-center pt-4">
                  <div className="flex items-center gap-2 text-[9px] font-bold text-slate-300 uppercase tracking-widest">
                    <Database size={10} /> CSV
                  </div>
                  <div className="flex items-center gap-2 text-[9px] font-bold text-slate-300 uppercase tracking-widest">
                    <FileText size={10} /> 5MB Max
                  </div>
                </div>
              </div>
            )}

            {fileError && <div className="mt-8 px-4 py-2 bg-rose-50 border border-rose-100 rounded-xl text-rose-600 text-[10px] font-black uppercase tracking-widest flex items-center gap-2"><XCircle size={14} /> {fileError}</div>}
          </div>

          {file && !fileError && (
            <div className="p-6 bg-slate-50 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-6">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center border border-slate-200">
                  <RefreshCw className={`text-indigo-600 ${isProcessing ? "animate-spin" : ""}`} size={18} />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-900">Neural pipeline standby</p>
                  <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Ready to process {file.name}</p>
                </div>
              </div>
              <button 
                onClick={handleProcess} 
                disabled={isProcessing} 
                className="btn-premium flex items-center gap-3 h-12 px-10 w-full sm:w-auto disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span className="text-[10px] font-bold tracking-widest uppercase">{uploadPct}%</span>
                  </>
                ) : (
                  <>
                    <span className="text-[10px] font-bold tracking-widest uppercase">Initialize Ingestion</span>
                    <ChevronRight size={16} />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
            {[
              { label: "Total", value: results.total_rows, color: "indigo" },
              { label: "Spam", value: results.spam_count, color: "rose" },
              { label: "Clean", value: results.ham_count, color: "emerald" },
              { label: "Uncertain", value: results.uncertain_count, color: "amber" },
              { label: "Errors", value: results.errors, color: "slate" }
            ].map((s, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{s.label}</p>
                <p className={`text-2xl font-black text-${s.color}-600 mt-1`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="text-lg font-bold text-slate-900">Ingestion Results</h3>
              <div className="flex gap-2">
                <button 
                  onClick={downloadResultsCSV} 
                  className="bg-white border border-slate-200 h-9 px-4 rounded-xl text-[9px] font-bold uppercase tracking-widest flex items-center gap-2 hover:bg-slate-50 transition-all"
                >
                  <Download size={14} /> Export
                </button>
                <button 
                  onClick={() => setResults(null)} 
                  className="bg-slate-900 text-white h-9 px-4 rounded-xl text-[9px] font-bold uppercase tracking-widest hover:bg-slate-800 transition-all shadow-sm shadow-slate-200"
                >
                  New Batch
                </button>
              </div>
            </div>

            <div className="max-h-[500px] overflow-y-auto divide-y divide-slate-100 no-scrollbar">
              {results.results.map((row) => (
                <div key={row.row} className="grid grid-cols-12 gap-6 px-8 py-5 items-center hover:bg-slate-50 transition-colors group">
                  <div className="col-span-1 text-[9px] font-bold text-slate-300 uppercase">#{row.row}</div>
                  <div className="col-span-8">
                    <p className="text-sm font-bold text-slate-700 truncate group-hover:text-indigo-600 transition-colors">"{row.message}"</p>
                  </div>
                  <div className="col-span-3 flex justify-end">
                    {row.error ? (
                      <span className="text-[9px] font-bold text-rose-600 uppercase tracking-widest bg-rose-50 px-3 py-1 rounded-full border border-rose-100">
                        Error
                      </span>
                    ) : (
                      <VerdictBadge verdict={row.verdict} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

