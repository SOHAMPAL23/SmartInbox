import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ShieldCheck, AlertTriangle, Zap, Download,
  ArrowLeft, Cpu, Activity, Info, Eye, CheckCircle, ChevronRight
} from "lucide-react";
import { RadialAnalytics } from "../../components/charts/RadialAnalytics";
import { toast } from "react-hot-toast";

// ── Threat level config ──────────────────────────────────────────────────────
const THREAT_CONFIG = {
  critical: { label: "CRITICAL",  bg: "bg-red-50",    border: "border-red-200",    text: "text-red-600",    ring: "ring-red-500",   dot: "bg-red-500",   pulse: true  },
  high:     { label: "HIGH",      bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-600", ring: "ring-orange-400",dot: "bg-orange-500",pulse: false },
  medium:   { label: "MEDIUM",    bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-600",  ring: "ring-amber-400", dot: "bg-amber-400", pulse: false },
  low:      { label: "LOW",       bg: "bg-emerald-50",border: "border-emerald-200",text: "text-emerald-600",ring: "ring-emerald-400",dot:"bg-emerald-400",pulse: false },
};

// ── Spam type config ─────────────────────────────────────────────────────────
const TYPE_CONFIG = {
  ham:              { label: "LEGITIMATE",         color: "emerald", icon: ShieldCheck,   desc: "Safe communication" },
  traditional_spam: { label: "TRADITIONAL SPAM",   color: "rose",    icon: AlertTriangle, desc: "Classic spam patterns" },
  ai_spam:          { label: "AI-GENERATED SPAM",  color: "violet",  icon: Zap,           desc: "Sophisticated AI-crafted spam" },
  phishing:         { label: "PHISHING ATTACK",    color: "red",     icon: AlertTriangle, desc: "Credential theft attempt" },
  prompt_injection: { label: "PROMPT INJECTION",   color: "fuchsia", icon: AlertTriangle, desc: "AI filter bypass attempt" },
  suspicious:       { label: "SUSPICIOUS",         color: "amber",   icon: AlertTriangle, desc: "Requires manual review" },
};

// ── Score bar component ──────────────────────────────────────────────────────
const ScoreBar = ({ label, value, color, icon: Icon }) => (
  <div className="space-y-1.5">
    <div className="flex justify-between items-center">
      <div className="flex items-center gap-1.5">
        {Icon && <Icon size={11} className={`text-${color}-500`} />}
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
      <span className={`text-xs font-black text-${color}-600`}>{Math.round(value)}%</span>
    </div>
    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(Math.round(value), 100)}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className={`h-full bg-${color}-500 rounded-full`}
      />
    </div>
  </div>
);

// ── Category badge ───────────────────────────────────────────────────────────
const CategoryBadge = ({ cat }) => {
  const colorMap = {
    ai_spam: "violet", traditional_spam: "rose", phishing: "red",
    prompt_injection: "fuchsia", excessive_caps: "amber",
    crypto_scam: "orange", social_engineering: "pink",
  };
  const color = colorMap[cat] || "slate";
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest bg-${color}-50 text-${color}-600 border border-${color}-100`}>
      {cat.replace(/_/g, " ")}
    </span>
  );
};

// ── Layer score mini card ────────────────────────────────────────────────────
const LayerCard = ({ icon: Icon, label, score, color, sublabel }) => (
  <div className={`bg-${color}-50 border border-${color}-100 rounded-2xl p-4 text-center space-y-1`}>
    <div className={`p-2 rounded-xl bg-${color}-100 text-${color}-600 w-fit mx-auto`}>
      <Icon size={14} />
    </div>
    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
    <p className={`text-xl font-black text-${color}-600`}>{Math.round(score)}<span className="text-xs">%</span></p>
    {sublabel && <p className="text-[8px] text-slate-400 font-medium">{sublabel}</p>}
  </div>
);

// ── Feature importance highlighted text ─────────────────────────────────────
const HighlightedText = ({ text, features }) => {
  if (!features || features.length === 0) return <span>{text}</span>;
  const keywords = features.slice(0, 5).map(f => f.feature).filter(f => f.length > 2);
  if (keywords.length === 0) return <span>{text}</span>;

  const pattern = new RegExp(`(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, i) =>
        keywords.some(k => k.toLowerCase() === part.toLowerCase()) ? (
          <mark key={i} className="bg-amber-200 text-amber-900 rounded px-0.5 font-semibold not-italic">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
};

export const ResultsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result   = location.state?.result;

  if (!result) return <Navigate to="/scan" replace />;

  const isSpam       = result.prediction === 1 || result.final_prediction === "spam";
  const spamType     = result.spam_type || (isSpam ? "suspicious" : "ham");
  const typeInfo     = TYPE_CONFIG[spamType] || TYPE_CONFIG.ham;
  const threatLevel  = (result.threat_level || (isSpam ? "high" : "low")).toLowerCase();
  const threatCfg    = THREAT_CONFIG[threatLevel] || THREAT_CONFIG.low;

  const mlScore     = result.ml_model_score     ?? (result.probability * 100);
  const heurScore   = result.heuristic_score    ?? 0;
  const confidence  = result.final_confidence         ?? result.probability * 100;

  const categories  = result.detected_categories || [];
  const features    = result.feature_importance  || [];
  const reasoning   = result.reasoning           || "";
  const action      = result.recommended_action  || (isSpam ? "Do not engage with this message." : "Message appears safe.");

  const handleExport = () => {
    const rows = [
      ["Field", "Value"],
      ["Text",             result.text || ""],
      ["Verdict",          isSpam ? "SPAM" : "CLEAN"],
      ["Threat Level",     threatLevel.toUpperCase()],
      ["ML Score",         `${Math.round(mlScore)}%`],
      ["Heuristic Score",  `${Math.round(heurScore)}%`],
      ["Spam Type",        spamType],
      ["Reasoning",        reasoning],
      ["Recommended Action", action],
    ];
    const csv  = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `smartinbox_report_${Date.now()}.csv`; a.click();
    toast.success("Intelligence report downloaded.");
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in">
      {/* ── Header ── */}
      <div className="space-y-1">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-indigo-100">
          <Zap size={11} /> Sequence Complete
        </div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Intelligence Verdict</h1>
        <p className="text-sm text-slate-500">4-layer hybrid analysis · {result.latency_ms ? `${result.latency_ms}ms` : "complete"}</p>
      </div>

      {/* ── Verdict banner ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-3xl border-2 p-6 ${isSpam ? "border-rose-200 bg-rose-50" : "border-emerald-200 bg-emerald-50"} relative overflow-hidden`}
      >
        <div className={`absolute top-0 left-0 w-full h-1 ${isSpam ? "bg-gradient-to-r from-rose-400 to-red-600" : "bg-gradient-to-r from-emerald-400 to-teal-500"}`} />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-2xl ${isSpam ? "bg-rose-100" : "bg-emerald-100"}`}>
              {isSpam
                ? <AlertTriangle size={28} className="text-rose-600" />
                : <ShieldCheck size={28} className="text-emerald-600" />}
            </div>
            <div>
              <h2 className={`text-3xl font-black tracking-tight ${isSpam ? "text-rose-600" : "text-emerald-600"}`}>
                {isSpam ? "SPAM DETECTED" : "CLEAN"}
              </h2>
              <p className="text-sm font-medium text-slate-600">{typeInfo.desc}</p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${threatCfg.bg} ${threatCfg.border}`}>
              <span className={`inline-flex rounded-full h-2 w-2 ${threatCfg.dot || "bg-slate-400"}`} />
              <span className={`text-[10px] font-black uppercase tracking-widest ${threatCfg.text}`}>
                {threatCfg.label} THREAT
              </span>
            </div>
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border bg-${typeInfo.color}-50 border-${typeInfo.color}-100 text-${typeInfo.color}-600`}>
              <typeInfo.icon size={11} />
              <span className="text-[9px] font-black uppercase tracking-widest">{typeInfo.label}</span>
            </div>
          </div>
        </div>
      </motion.div>
  
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Message Content</p>
            <div className="bg-slate-50 rounded-xl p-4 text-slate-700 font-medium text-sm leading-relaxed border border-slate-100 italic">
              "<HighlightedText text={result.text || ""} features={features} />"
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <Activity size={11} /> Intelligence Layer Scores
            </p>
            <div className="grid grid-cols-2 gap-3">
              <LayerCard icon={Cpu}   label="Statistical Engine" score={mlScore}   color="indigo" sublabel="ML Core Analysis" />
              <LayerCard icon={Eye}   label="Heuristic Matrix"   score={heurScore} color="rose"   sublabel="Pattern Matching" />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Risk Probability Breakdown</p>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Detection Vectors (Risk %)</p>
                  <ScoreBar label="Statistical Engine Analysis" value={mlScore}   color="indigo" icon={Cpu} />
                  <ScoreBar label="Heuristic Pattern Match"   value={heurScore} color="rose"   icon={Activity} />
                </div>
                <div className="space-y-3">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Verdict Confidence</p>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-2">
                    <div className="flex justify-between text-[10px] font-black uppercase tracking-widest mb-1">
                      <span className="text-rose-500">Spam Prob</span>
                      <span className="text-emerald-500">Ham Prob</span>
                    </div>
                    <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
                      <div className="h-full bg-rose-500 transition-all duration-700" style={{ width: `${isSpam ? confidence : (100 - confidence)}%` }} />
                      <div className="h-full bg-emerald-500 transition-all duration-700" style={{ width: `${!isSpam ? confidence : (100 - confidence)}%` }} />
                    </div>
                    <div className="flex justify-between text-[11px] font-black tabular-nums">
                      <span className="text-rose-600">{Math.round(isSpam ? confidence : (100 - confidence))}%</span>
                      <span className="text-emerald-600">{Math.round(!isSpam ? confidence : (100 - confidence))}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className={`rounded-2xl border p-5 flex items-start gap-4 ${isSpam ? "bg-rose-50 border-rose-100" : "bg-emerald-50 border-emerald-100"}`}>
            {isSpam ? <AlertTriangle size={20} className="text-rose-500 shrink-0 mt-0.5" /> : <CheckCircle size={20} className="text-emerald-500 shrink-0 mt-0.5" />}
            <div>
              <p className={`text-xs font-black uppercase tracking-wider mb-1 ${isSpam ? "text-rose-600" : "text-emerald-600"}`}>Recommended Action</p>
              <p className={`text-sm font-semibold ${isSpam ? "text-rose-800" : "text-emerald-800"}`}>{action}</p>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col items-center space-y-4">
            <RadialAnalytics
              percentage={Math.round(confidence)}
              label={isSpam ? "Spam Confidence" : "Safety Confidence"}
              color={isSpam ? "#f43f5e" : "#10b981"}
            />
            <div className={`text-[9px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${threatCfg.bg} ${threatCfg.border} ${threatCfg.text}`}>
              {threatCfg.label} RISK
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3">
             <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Engine Reasoning</p>
             <p className="text-[11px] text-slate-600 leading-relaxed font-medium bg-slate-50 p-3 rounded-xl border border-slate-100">
                {reasoning}
             </p>
             <div className="flex flex-wrap gap-2">
                {categories.map((cat, i) => <CategoryBadge key={i} cat={cat} />)}
             </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-6 border-t border-slate-100">
        <motion.button
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={() => navigate("/scan")}
          className="btn-premium flex items-center gap-3 px-10 h-12 w-full sm:w-auto"
        >
          <span className="text-[10px] font-bold tracking-widest uppercase">New Scan</span>
          <ChevronRight size={16} />
        </motion.button>
        <button onClick={handleExport} className="bg-white border border-slate-200 px-8 h-12 w-full sm:w-auto rounded-xl text-[10px] font-bold tracking-widest uppercase hover:bg-slate-50 transition-all">Export Report</button>
        <button onClick={() => navigate("/dashboard")} className="text-slate-400 hover:text-slate-900 transition-colors flex items-center gap-2 px-6">
          <ArrowLeft size={15} /><span className="text-[10px] font-bold uppercase tracking-widest">Dashboard</span>
        </button>
      </div>
    </div>
  );
};
