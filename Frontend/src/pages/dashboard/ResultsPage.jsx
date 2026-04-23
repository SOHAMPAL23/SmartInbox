import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { 
  ShieldCheck, 
  AlertTriangle, 
  Zap, 
  Link2, 
  ChevronRight,
  ArrowLeft,
  Download
} from "lucide-react";
import { RadialAnalytics } from "../../components/charts/RadialAnalytics";
import { toast } from "react-hot-toast";

export const ResultsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  if (!result) {
    return <Navigate to="/scan" replace />;
  }

  const isSpam = result.prediction === 1;

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-indigo-100">
          <Zap size={12} /> Sequence Complete
        </div>
        <h1 className="text-4xl font-black text-slate-900 tracking-tight">Intelligence Verdict</h1>
        <p className="text-sm text-slate-500 font-medium">Neural analysis breakdown and classification results.</p>
      </div>

      <div className="bg-white p-10 rounded-[40px] border border-slate-200 shadow-sm relative overflow-hidden">
        <div className={`absolute top-0 left-0 w-full h-1 ${isSpam ? "bg-rose-500" : "bg-emerald-500"}`} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Left: Content */}
          <div className="space-y-8">
            <div className="space-y-3">
              <span className="text-[10px] font-black text-slate-400 tracking-widest uppercase">Payload Matrix</span>
              <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100 italic text-slate-600 font-medium text-lg leading-relaxed">
                "{result.text}"
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Zap size={18} className="text-indigo-600" />
                Inference Insights
              </h3>
              <div className="space-y-3">
                {[
                  { 
                    title: isSpam ? "Malicious Intent" : "Benign Pattern",
                    desc: isSpam ? "Markers indicate high social engineering risk." : "Structure adheres to safe communication protocols.",
                    icon: isSpam ? AlertTriangle : ShieldCheck,
                    color: isSpam ? "rose" : "emerald"
                  },
                  {
                    title: "Linguistic Score",
                    desc: "Neural weights assigned based on token distribution.",
                    icon: Link2,
                    color: "indigo"
                  }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <div className={`p-2 rounded-lg bg-${item.color}-100 h-fit text-${item.color}-600`}>
                      <item.icon size={16} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{item.title}</h4>
                      <p className="text-[10px] text-slate-400 mt-1 font-medium">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Visualization */}
          <div className="flex flex-col items-center justify-center space-y-10 bg-slate-50 rounded-[32px] p-8 border border-slate-200">
            <RadialAnalytics 
              percentage={(result.probability * 100).toFixed(0)} 
              label={isSpam ? "Spam Confidence" : "Safety Confidence"} 
              color={isSpam ? "#f43f5e" : "#10b981"} 
            />

            <div className="text-center">
              <h2 className={`text-6xl font-black tracking-tighter mb-2 ${isSpam ? "text-rose-500" : "text-emerald-500"}`}>
                {isSpam ? "SPAM" : "CLEAN"}
              </h2>
              <div className={`inline-flex items-center gap-2 px-4 py-1 rounded-full border ${isSpam ? "bg-rose-50 border-rose-100 text-rose-600" : "bg-emerald-50 border-emerald-100 text-emerald-600"} text-[9px] font-black uppercase tracking-widest`}>
                {isSpam ? "Dangerous" : "Secure"}
              </div>
            </div>

            <div className="w-full grid grid-cols-2 gap-4 pt-4 border-t border-slate-200">
              <div className="text-center">
                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Latency</p>
                <p className="text-lg font-black text-slate-900">14ms</p>
              </div>
              <div className="text-center">
                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Model</p>
                <p className="text-lg font-black text-slate-900">v1.0</p>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row justify-center items-center gap-4 mt-12 pt-8 border-t border-slate-100">
          <button 
            onClick={() => navigate("/scan")}
            className="btn-premium flex items-center gap-3 px-10 h-12 w-full sm:w-auto"
          >
            <span className="text-[10px] font-bold tracking-widest uppercase">New Scan</span>
            <ChevronRight size={16} />
          </button>
          
          <button 
            onClick={() => {
              const header = ["Message", "Verdict", "Probability (%)"];
              const verdictStr = isSpam ? "SPAM" : "CLEAN";
              const lines = [header.join(","), [`"${result.text}"`, verdictStr, (result.probability * 100).toFixed(1)].join(",")];
              const blob = new Blob([lines.join("\n")], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `smartinbox_report_${Date.now()}.csv`;
              a.click();
              toast.success("Report downloaded.");
            }}
            className="bg-white border border-slate-200 px-10 h-12 w-full sm:w-auto flex items-center justify-center gap-2 text-[10px] font-bold tracking-widest uppercase hover:bg-slate-50 transition-all rounded-xl"
          >
            <Download size={16} /> Export
          </button>

          <button 
            onClick={() => navigate("/dashboard")}
            className="text-slate-400 hover:text-slate-900 transition-colors flex items-center gap-2 px-6"
          >
            <ArrowLeft size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Dashboard</span>
          </button>
        </div>
      </div>
    </div>
  );
};

