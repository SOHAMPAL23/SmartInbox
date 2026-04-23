import React, { memo } from "react";
import { 
  TrendingUp, 
  ShieldCheck, 
  AlertTriangle, 
  Zap, 
  Activity 
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useStore } from "../../store/useStore";
import { useNavigate } from "react-router-dom";
import { getUserStats, getSpamTrends } from "../../api/spamApi";
import { toast } from "react-hot-toast";
import { D3LineChart } from "../../components/charts/D3Charts";
import { DashboardSkeleton } from "../../components/ui/SkeletonLoaders";

const StatsCard = memo(({ title, value, icon: Icon, color, trend }) => (
  <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-2 rounded-xl bg-${color}-50 text-${color}-600`}>
        <Icon size={20} />
      </div>
      {trend && (
        <div className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg">
          {trend}
        </div>
      )}
    </div>
    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{title}</p>
    <h3 className="text-2xl font-black text-slate-900 mt-1">{value}</h3>
  </div>
));

export const UserDashboard = () => {
  const user = useStore((state) => state.user);
  const navigate = useNavigate();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["userStats"],
    queryFn: getUserStats,
  });

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ["spamTrends"],
    queryFn: () => getSpamTrends(30),
  });

  const trends = (trendsData?.points || []).map(p => ({
    label: p.date,
    value: p.total
  }));

  if (statsLoading || trendsLoading) return <DashboardSkeleton />;
  if (!stats) return null;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">
            Hello, {user?.username || "Commander"}
          </h1>
          <p className="text-sm text-slate-500 font-medium">Your personal smartinbox is live and monitoring traffic.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate("/scan")}
            className="btn-premium flex items-center gap-2"
          >
            <Zap size={16} />
            New Scan
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatsCard 
          title="Total Scanned" 
          value={stats.total_scanned.toLocaleString()} 
          icon={TrendingUp} 
          color="indigo" 
          trend={stats.trends.total !== "0" ? stats.trends.total : null} 
        />
        <StatsCard 
          title="Spam Blocked" 
          value={stats.spam_blocked.toLocaleString()} 
          icon={ShieldCheck} 
          color="rose" 
          trend={stats.trends.spam !== "0" ? stats.trends.spam : null} 
        />
        <StatsCard 
          title="Threat Level" 
          value={stats.threat_level} 
          icon={AlertTriangle} 
          color={stats.threat_level === "High" ? "rose" : stats.threat_level === "Medium" ? "amber" : "indigo"} 
        />
        <StatsCard 
          title="System Status" 
          value="Optimal" 
          icon={Activity} 
          color="emerald" 
        />
      </div>

      {/* Traffic Chart */}
      <div className="bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-6">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Activity size={18} className="text-indigo-600" />
            Activity Telemetry
          </h3>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Last 30 Days</div>
        </div>
        <div className="h-80">
          <D3LineChart data={trends} width={1000} height={300} />
        </div>
      </div>
    </div>
  );
};

