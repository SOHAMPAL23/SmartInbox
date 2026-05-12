import React, { memo } from "react";
import {
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Zap,
  Activity,
  Brain,
  Shield,
  Search,
  ChevronRight,
  Sparkles,
  Cpu
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useStore } from "../../store/useStore";
import { useNavigate } from "react-router-dom";
import { getUserStats, getSpamTrends, getThreatReport } from "../../api/spamApi";
import { D3LineChart } from "../../components/charts/D3Charts";
import { DashboardSkeleton } from "../../components/ui/SkeletonLoaders";
import { motion } from "framer-motion";

const StatsCard = memo(({ title, value, icon: Icon, color, trend }) => (
  <motion.div
    whileHover={{ y: -2 }}
    className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm relative overflow-hidden"
  >
    <div className="flex justify-between items-start mb-4 relative z-10">
      <div className={`p-2.5 rounded-xl bg-${color}-50 text-${color}-600 border border-${color}-100`}>
        <Icon size={18} />
      </div>
      {trend && (
        <div className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg border border-emerald-100">
          {trend}
        </div>
      )}
    </div>
    <div className="relative z-10">
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{title}</p>
      <h3 className="text-3xl font-black text-slate-900 mt-1 tracking-tight">{value}</h3>
    </div>
    <div className={`absolute -bottom-4 -right-4 text-${color}-50 opacity-10`}>
      <Icon size={100} />
    </div>
  </motion.div>
));

const ThreatBadge = ({ level }) => {
  const cfg = {
    critical: "bg-red-50 text-red-600 border-red-100",
    high: "bg-orange-50 text-orange-600 border-orange-100",
    medium: "bg-amber-50 text-amber-600 border-amber-100",
    low: "bg-emerald-50 text-emerald-600 border-emerald-100",
  };
  const color = cfg[level?.toLowerCase()] || cfg.low;
  return (
    <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest border ${color}`}>
      {level || "Low"}
    </span>
  );
};

export const UserDashboard = () => {
  const user = useStore((state) => state.user);
  const navigate = useNavigate();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["userStats"],
    queryFn: () => getUserStats(),
    refetchInterval: 30000,
  });

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ["spamTrends"],
    queryFn: () => getSpamTrends(30),
  });

  const { data: threatReport, isLoading: threatLoading } = useQuery({
    queryKey: ["threatReport"],
    queryFn: () => getThreatReport(),
  });

  const trends = (trendsData?.points || []).map(p => ({
    label: p.date,
    value: p.total
  }));

  if (statsLoading || trendsLoading || threatLoading) return <DashboardSkeleton />;
  if (!stats) return null;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in pb-12">
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-[9px] font-black uppercase tracking-widest border border-indigo-100 mb-2">
            <Activity size={10} /> Active Monitoring
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">
            Security Overview
          </h1>
          <p className="text-sm text-slate-500 font-medium">
            Welcome back, <span className="text-indigo-600 font-bold">{user?.username}</span>. System is currently <span className="text-emerald-600 font-bold">Optimal</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/scan")}
            className="btn-premium flex items-center gap-3 h-12 px-8"
          >
            <Zap size={16} />
            <span className="text-[10px] font-bold uppercase tracking-widest">New Analysis</span>
          </button>
        </div>
      </div>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
        <StatsCard
          title="Total Analyzed"
          value={stats.total_scanned.toLocaleString()}
          icon={TrendingUp}
          color="indigo"
          trend={stats.trends.total !== "0" ? stats.trends.total : null}
        />
        <StatsCard
          title="Threats Neutralized"
          value={stats.spam_blocked.toLocaleString()}
          icon={ShieldCheck}
          color="rose"
          trend={stats.trends.spam !== "0" ? stats.trends.spam : null}
        />
        <StatsCard
          title="Global Risk Index"
          value={stats.threat_level}
          icon={AlertTriangle}
          color={stats.threat_level === "High" || stats.threat_level === "Critical" ? "rose" : stats.threat_level === "Medium" ? "amber" : "emerald"}
        />
        <StatsCard
          title="AI Confidence"
          value="99.1%"
          icon={Brain}
          color="violet"
        />
      </div>

      {/* ── Activity Chart ── */}
      <div className="bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-6">
        <div className="flex justify-between items-center">
          <h3 className="text-base font-black text-slate-900 uppercase tracking-tight flex items-center gap-3">
            <Activity size={18} className="text-indigo-600" />
            Traffic Telemetry
          </h3>
          <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-50 px-3 py-1 rounded-full">30-Day Velocity</div>
        </div>
        <div className="h-80 w-full overflow-hidden">
           <D3LineChart data={trends} width={1100} height={300} />
        </div>
      </div>

      {/* ── Recent Threat Intelligence ── */}
      <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
        <div className="p-8 border-b border-slate-100 flex justify-between items-center">
          <h3 className="text-base font-black text-slate-900 uppercase tracking-tight flex items-center gap-3">
            <ShieldCheck size={18} className="text-emerald-600" />
            Advanced Threat Report
          </h3>
          <button
            onClick={() => navigate("/history")}
            className="text-[10px] font-black text-indigo-600 uppercase tracking-widest hover:underline"
          >
            View Full Log
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50">
                <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Analysis Target</th>
                <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Verdict</th>
                <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Threat Level</th>
                <th className="px-8 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">AI Reasoning</th>
                <th className="px-8 py-4 text-right pr-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(threatReport?.recent_threats || []).map((t, i) => (
                <tr key={i} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-8 py-5">
                    <p className="text-sm font-semibold text-slate-700 max-w-xs truncate">{t.text}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{new Date(t.timestamp).toLocaleString()}</p>
                  </td>
                  <td className="px-8 py-5">
                    {t.prediction === "spam" ? (
                      <span className="inline-flex items-center gap-1.5 text-rose-600 font-bold text-xs uppercase tracking-tight">
                        <AlertTriangle size={12} /> Spam
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-emerald-600 font-bold text-xs uppercase tracking-tight">
                        <ShieldCheck size={12} /> Clean
                      </span>
                    )}
                  </td>
                  <td className="px-8 py-5">
                    <ThreatBadge level={t.threat_level} />
                  </td>
                  <td className="px-8 py-5">
                    <p className="text-xs text-slate-500 font-medium max-w-sm italic line-clamp-2">
                      "{t.reasoning || "Analysis complete."}"
                    </p>
                  </td>
                  <td className="px-8 py-5 text-right">
                    <button
                      onClick={() => navigate("/results", { state: { result: t } })}
                      className="p-2 text-slate-300 group-hover:text-indigo-600 transition-colors"
                    >
                      <ChevronRight size={20} />
                    </button>
                  </td>
                </tr>
              ))}
              {(!threatReport?.recent_threats || threatReport.recent_threats.length === 0) && (
                <tr>
                  <td colSpan="5" className="px-8 py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <Search size={32} className="text-slate-200" />
                      <p className="text-sm font-medium text-slate-400 uppercase tracking-widest">No recent threats recorded</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
