import { useState, useMemo, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu, 
  Activity, 
  Settings,
  TrendingUp, 
  Users,
  ShieldCheck,
  RefreshCw,
  Server,
  Network
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getModelInfo, updateThreshold, getFeatureImportance,
  getAdminAnalytics, getAdminStats, getAdminUsers
} from "../../api/adminApi";
import { useStore } from "../../store/useStore";
import { toast } from "react-hot-toast";
import { D3LineChart, D3BarChart, D3DonutChart } from "../../components/charts/D3Charts";
import { DashboardSkeleton } from "../../components/ui/SkeletonLoaders";

// ── Optimized Sub-components ──────────────────────────────────────────────────

const StatCard = memo(({ label, value, icon: Icon, color }) => (
  <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-2 rounded-xl bg-${color}-50 text-${color}-600`}>
        <Icon size={20} />
      </div>
    </div>
    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{label}</p>
    <h3 className="text-2xl font-black text-slate-900 mt-1">{value}</h3>
  </div>
));

const TabButton = memo(({ active, onClick, icon: Icon, label }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-3 px-6 py-2.5 rounded-xl text-[10px] font-bold tracking-widest uppercase transition-all ${
      active 
        ? "bg-slate-900 text-white shadow-md" 
        : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
    }`}
  >
    <Icon size={14} />
    {label}
  </button>
));

export const AdminDashboard = () => {
  const [tab, setTab] = useState("model");
  const [threshold, setThreshold] = useState(0.5);
  const queryClient = useQueryClient();

  const { data: modelInfo, isLoading: modelLoading } = useQuery({
    queryKey: ["modelInfo"],
    queryFn: async () => {
      const info = await getModelInfo();
      setThreshold(info?.threshold || 0.5);
      return info;
    },
  });

  const { data: importanceData, isLoading: importanceLoading } = useQuery({
    queryKey: ["featureImportance"],
    queryFn: getFeatureImportance,
  });

  const { data: quickStats, isLoading: statsLoading } = useQuery({
    queryKey: ["adminStats"],
    queryFn: getAdminStats,
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["adminAnalytics"],
    queryFn: () => getAdminAnalytics(30),
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: () => getAdminUsers(1, 10),
  });

  const importance = useMemo(() => 
    (importanceData?.features || []).slice(0, 8).map(f => ({
      label: f.feature.replace("feat_", ""),
      value: f.importance
    })), [importanceData]);

  const trafficData = useMemo(() => 
    (analytics?.recent_activity || []).map(p => ({
      label: p.date,
      value: p.total
    })), [analytics]);

  const userDist = useMemo(() => 
    (usersData?.items || []).slice(0, 5).map(u => ({
      label: u.username,
      value: u.prediction_count
    })), [usersData]);

  const mutation = useMutation({
    mutationFn: updateThreshold,
    onSuccess: () => {
      toast.success("Neural boundary synchronized.");
      queryClient.invalidateQueries({ queryKey: ["modelInfo"] });
    },
    onError: () => {
      toast.error("Synchronization failed.");
    }
  });

  if (modelLoading || statsLoading || analyticsLoading) return <DashboardSkeleton />;

  const handleUpdateThreshold = () => {
    mutation.mutate(threshold);
  };

  const isUpdating = mutation.isLoading;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-bold uppercase tracking-widest border border-emerald-100">
            <Server size={12} /> Live smartinbox Online
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Control Center</h1>
          <p className="text-sm text-slate-500 font-medium">Enterprise oversight and neural engine management.</p>
        </div>

        <div className="flex gap-2 p-1.5 bg-white border border-slate-200 rounded-2xl shadow-sm">
          <TabButton active={tab === "model"} onClick={() => setTab("model")} icon={Cpu} label="Engine" />
          <TabButton active={tab === "analytics"} onClick={() => setTab("analytics")} icon={Activity} label="Traffic" />
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard label="Total Nodes" value={quickStats?.total_users || 0} icon={Users} color="indigo" />
        <StatCard label="Inference Volume" value={quickStats?.total_messages || 0} icon={Activity} color="blue" />
        <StatCard label="Threats Neutralized" value={quickStats?.spam_count || 0} icon={ShieldCheck} color="rose" />
        <StatCard label="Neutral Rate" value={`${quickStats?.spam_rate || 0}%`} icon={TrendingUp} color="emerald" />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8"
        >
          {tab === "model" ? (
            <>
              {/* Configuration Panel */}
              <div className="lg:col-span-1 bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-8">
                <div className="space-y-2">
                  <h3 className="text-lg font-bold flex items-center gap-2">
                    <Settings size={18} className="text-indigo-600" />
                    Engine Config
                  </h3>
                  <p className="text-xs text-slate-400 font-medium uppercase tracking-widest">Active Model: {modelInfo?.model_version}</p>
                </div>

                <div className="space-y-6 pt-6 border-t border-slate-100">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Boundary Threshold</span>
                    <span className="text-lg font-black text-indigo-600 font-mono">{threshold.toFixed(3)}</span>
                  </div>
                  <input 
                    type="range" min="0.1" max="0.9" step="0.01" 
                    value={threshold} 
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                  <button 
                    onClick={handleUpdateThreshold}
                    disabled={isUpdating}
                    className="btn-premium w-full flex items-center justify-center gap-3 disabled:opacity-50"
                  >
                    {isUpdating ? <RefreshCw className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
                    Sync Neural State
                  </button>
                </div>
              </div>

              {/* Feature Importance Chart */}
              <div className="lg:col-span-2 bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-6">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <TrendingUp size={18} className="text-indigo-600" />
                  Feature Weightings
                </h3>
                <div className="h-64">
                  <D3BarChart data={importance} width={700} height={250} />
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Traffic Chart */}
              <div className="lg:col-span-2 bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-6">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Network size={18} className="text-indigo-600" />
                  Traffic Throughput
                </h3>
                <div className="h-80">
                  <D3LineChart data={trafficData} width={700} height={300} />
                </div>
              </div>

              {/* Distribution Chart */}
              <div className="lg:col-span-1 bg-white border border-slate-200 p-8 rounded-3xl shadow-sm space-y-6">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Users size={18} className="text-indigo-600" />
                  Node Distribution
                </h3>
                <div className="h-80">
                  <D3DonutChart data={userDist} size={250} />
                </div>
              </div>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

