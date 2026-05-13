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
  Network,
  Zap,
  Lock,
  ArrowUpRight
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

const containerVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } }
};

const StatCard = memo(({ label, value, icon: Icon, trend }) => (
  <motion.div 
    variants={itemVariants}
    whileHover={{ y: -5 }}
    className="bg-white border border-zinc-200 p-8 rounded-[2.5rem] relative overflow-hidden transition-all shadow-sm hover:shadow-xl hover:shadow-zinc-100"
  >
    <div className="flex justify-between items-start mb-6">
      <div className={`p-4 rounded-2xl bg-zinc-900 text-white shadow-lg shadow-zinc-200`}>
        <Icon size={20} />
      </div>
      {trend && (
        <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full uppercase tracking-widest border border-emerald-100">
          +{trend}%
        </span>
      )}
    </div>
    <p className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em]">{label}</p>
    <h3 className="text-3xl font-black text-zinc-900 mt-2 tracking-tighter">{value}</h3>
  </motion.div>
));

const TabButton = memo(({ active, onClick, icon: Icon, label }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-3 px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all ${
      active 
        ? "bg-zinc-900 text-white shadow-xl shadow-zinc-200" 
        : "text-zinc-400 hover:text-zinc-900 hover:bg-white"
    }`}
  >
    <Icon size={16} />
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
    queryFn: () => getFeatureImportance(20),
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
      toast.success("Matrix Synchronized.");
      queryClient.invalidateQueries({ queryKey: ["modelInfo"] });
    },
    onError: () => {
      toast.error("Handshake failed.");
    }
  });

  if (modelLoading || statsLoading || analyticsLoading) return <DashboardSkeleton />;

  const handleUpdateThreshold = () => {
    mutation.mutate({ threshold });
  };

  const isUpdating = mutation.isLoading;

  return (
    <motion.div 
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className="max-w-6xl mx-auto space-y-10 pb-20"
    >
      {/* Admin Header */}
      <motion.div 
        variants={itemVariants}
        className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white p-10 rounded-[3rem] border border-zinc-200 shadow-sm relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 p-12 opacity-[0.02] pointer-events-none">
          <Settings size={200} className="text-zinc-900" />
        </div>

        <div className="space-y-4 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-50 text-rose-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-rose-100">
            <Lock size={12} /> Root Access Confirmed
          </div>
          <h1 className="text-4xl font-black text-zinc-900 tracking-tighter">Command Center</h1>
          <p className="text-sm text-zinc-400 font-medium max-w-lg leading-relaxed">
            Neural architecture oversight and global node management. 
            System version <span className="text-zinc-900 font-bold">v{modelInfo?.model_version}</span> is currently stable.
          </p>
        </div>

        <div className="flex gap-2 p-1.5 bg-zinc-50 border border-zinc-100 rounded-2xl relative z-10">
          <TabButton active={tab === "model"} onClick={() => setTab("model")} icon={Cpu} label="Engine" />
          <TabButton active={tab === "analytics"} onClick={() => setTab("analytics")} icon={Activity} label="Traffic" />
        </div>
      </motion.div>

      {/* Admin Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard label="Global Nodes" value={quickStats?.total_users || 0} icon={Users} trend="12" />
        <StatCard label="Total Inferences" value={(quickStats?.total_messages || 0).toLocaleString()} icon={Activity} />
        <StatCard label="Spam Intercepts" value={(quickStats?.spam_count || 0).toLocaleString()} icon={ShieldCheck} />
        <StatCard label="Neural Precision" value={`${quickStats?.spam_rate || 0}%`} icon={TrendingUp} />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8"
        >
          {tab === "model" ? (
            <>
              <div className="lg:col-span-1 bg-zinc-900 text-white rounded-[3rem] p-10 space-y-10 shadow-2xl shadow-zinc-200 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-12 opacity-[0.05] group-hover:rotate-12 transition-transform duration-700 pointer-events-none">
                   <Zap size={180} />
                </div>
                
                <div className="space-y-2">
                  <p className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em]">Engine Control</p>
                  <h3 className="text-2xl font-black tracking-tight">Handshake Threshold</h3>
                </div>

                <div className="space-y-10 pt-6">
                  <div className="flex justify-between items-end">
                    <div className="space-y-1">
                       <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Classification Bias</p>
                       <p className="text-sm font-black text-white">Neural Sensitivity</p>
                    </div>
                    <span className="text-5xl font-black text-white tracking-tighter">{threshold.toFixed(2)}</span>
                  </div>
                  
                  <div className="relative h-2 w-full bg-white/5 rounded-full border border-white/5 p-0.5">
                    <input 
                      type="range" min="0.1" max="0.9" step="0.01" 
                      value={threshold} 
                      onChange={(e) => setThreshold(parseFloat(e.target.value))}
                      className="absolute inset-0 w-full opacity-0 cursor-pointer z-10"
                    />
                    <motion.div 
                      className="h-full bg-gradient-to-r from-indigo-500 to-indigo-300 rounded-full"
                      style={{ width: `${(threshold - 0.1) / 0.8 * 100}%` }}
                    />
                  </div>

                  <motion.button 
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleUpdateThreshold}
                    disabled={isUpdating}
                    className="w-full h-16 bg-white text-zinc-900 rounded-2xl text-[10px] font-black uppercase tracking-[0.3em] hover:bg-slate-50 transition-all flex items-center justify-center gap-3 shadow-xl"
                  >
                    {isUpdating ? <RefreshCw className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
                    Apply Threshold
                  </motion.button>
                </div>
              </div>

              <div className="lg:col-span-2 bg-white border border-zinc-200 p-10 rounded-[3rem] space-y-8 shadow-sm">
                <div className="flex justify-between items-center">
                   <h3 className="text-[10px] font-black text-zinc-900 uppercase tracking-[0.2em] flex items-center gap-2">
                     <Network size={16} className="text-indigo-600" /> Neural Feature Weights
                   </h3>
                </div>
                <div className="h-80 w-full overflow-hidden">
                  <D3BarChart data={importance} width={700} height={300} />
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="lg:col-span-2 bg-white border border-zinc-200 p-10 rounded-[3rem] space-y-8 shadow-sm">
                <div className="flex justify-between items-center">
                   <h3 className="text-[10px] font-black text-zinc-900 uppercase tracking-[0.2em] flex items-center gap-2">
                     <TrendingUp size={16} className="text-emerald-600" /> Global Throughput
                   </h3>
                </div>
                <div className="h-96 w-full">
                  <D3LineChart data={trafficData} width={700} height={350} />
                </div>
              </div>

              <div className="lg:col-span-1 bg-white border border-zinc-200 p-10 rounded-[3rem] space-y-8 shadow-sm">
                <h3 className="text-[10px] font-black text-zinc-900 uppercase tracking-[0.2em]">Node Distribution</h3>
                <div className="h-96 flex flex-col items-center justify-center">
                  <D3DonutChart data={userDist} size={280} />
                  <div className="mt-8 grid grid-cols-2 gap-4 w-full">
                     {userDist.slice(0, 4).map((u, i) => (
                       <div key={i} className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${['bg-indigo-500', 'bg-emerald-500', 'bg-amber-500', 'bg-rose-500'][i]}`} />
                          <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest truncate">{u.label}</span>
                       </div>
                     ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  );
};

export default AdminDashboard;

