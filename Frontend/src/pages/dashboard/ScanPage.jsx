import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FileText, ShieldCheck, Zap, Lock, ChevronRight, Search, Cpu, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { predictText, getJobStatus } from "../../api/spamApi";
import { toast } from "react-hot-toast";

export const ScanPage = () => {
  const [text, setText] = useState("");
  const [isPredicting, setIsPredicting] = useState(false);
  const [jobId, setJobId] = useState(null);
  const navigate = useNavigate();

  const handlePredict = async () => {
    if (!text.trim()) return;
    setIsPredicting(true);
    try {
      const { job_id } = await predictText(text);
      setJobId(job_id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Analysis failed.");
      setIsPredicting(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    let pollInterval = setInterval(async () => {
      try {
        const job = await getJobStatus(jobId);
        if (job.status === "completed") {
          clearInterval(pollInterval);
          navigate("/results", { state: { result: job.result } });
        } else if (job.status === "failed") {
          clearInterval(pollInterval);
          toast.error(job.error || "Neural processing failed.");
          setIsPredicting(false);
          setJobId(null);
        }
      } catch (err) {
        clearInterval(pollInterval);
        setIsPredicting(false);
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [jobId, navigate]);

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-indigo-100">
          <Search size={12} /> Neural Gateway
        </div>
        <h1 className="text-4xl font-black text-slate-900 tracking-tight">Instant Analysis</h1>
        <p className="text-sm text-slate-500 font-medium">Input suspicious content for real-time neural classification.</p>
      </div>

      {/* Input Section */}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            <FileText size={14} /> Payload Stream
          </div>
          <div className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">
            {text.length} / 1000
          </div>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste message content here..."
          maxLength={1000}
          className="w-full h-64 bg-slate-50 border border-slate-200 rounded-2xl p-6 text-lg text-slate-900 placeholder:text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all resize-none font-medium"
        />

        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2 text-slate-400">
            <Lock size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Encrypted</span>
          </div>
          
          <button
            onClick={handlePredict}
            disabled={!text.trim() || isPredicting}
            className="btn-premium flex items-center justify-center gap-3 px-10 h-12 w-full sm:w-auto disabled:opacity-50"
          >
            {isPredicting ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span className="text-[10px] font-bold tracking-widest uppercase">Start Analysis</span>
                <ChevronRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { icon: Cpu, title: "Neural Core", desc: "RandomForest pipeline trained on 2M+ message vectors.", color: "indigo" },
          { icon: ShieldCheck, title: "Precision", desc: "Char-level analysis for defanging phishing hooks.", color: "emerald" },
          { icon: Zap, title: "Latency", desc: "Sub-100ms inference via optimized FastAPI backend.", color: "rose" }
        ].map((feature, i) => (
          <div key={i} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className={`p-2.5 rounded-xl bg-${feature.color}-50 text-${feature.color}-600 border border-${feature.color}-100 w-fit mb-4`}>
              <feature.icon size={16} />
            </div>
            <h4 className="text-sm font-bold text-slate-900 mb-1">{feature.title}</h4>
            <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
              {feature.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
