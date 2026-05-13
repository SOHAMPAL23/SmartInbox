import React, { memo } from "react";
import {
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Zap,
  Activity,
  ChevronRight,
  Brain,
  ArrowUpRight,
  Fingerprint,
  Layers,
  ShieldAlert,
  Shield,
  Search,
  Upload,
  BarChart3,
  History
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { useStore } from "../../store/useStore";
import { useNavigate } from "react-router-dom";
import { getUserStats, getSpamTrends, getThreatReport } from "../../api/spamApi";
import { DashboardSkeleton } from "../../components/ui/SkeletonLoaders";
import { motion, AnimatePresence } from "framer-motion";

const containerVariants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05
    }
  }
};

const itemVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-zinc-200 p-3 rounded-xl shadow-2xl">
        <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">{label}</p>
        <div className="flex items-center gap-2">
          <span className="text-sm font-black text-zinc-900">{payload[0].value.toLocaleString()}</span>
          <span className="text-[10px] font-medium text-zinc-400 uppercase">scans</span>
        </div>
      </div>
    );
  }
  return null;
};

const CompactStat = memo(({ label, value, trend, icon: Icon, color }) => (
  <motion.div 
    variants={itemVariants}
    whileHover={{ y: -4 }}
    className="flex items-center gap-4 p-6 bg-white border border-zinc-200 rounded-3xl hover:shadow-2xl hover:shadow-indigo-100/50 transition-all group relative overflow-hidden"
  >
    <div className="absolute top-0 right-0 p-6 opacity-[0.03] group-hover:scale-125 transition-transform duration-500 pointer-events-none">
      <Icon size={64} />
    </div>
    <div className={`p-3 rounded-2xl bg-slate-50 text-slate-600 border border-slate-100 group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-500 transition-all duration-300`}>
      <Icon size={20} />
    </div>
    <div>
      <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-black text-zinc-900 tracking-tight">{value}</span>
        {trend && (
          <span className="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
            {trend}
          </span>
        )}
      </div>
    </div>
  </motion.div>
));

const ThreatBadge = ({ level }) => {
  const cfg = {
    critical: "bg-rose-50 text-rose-600 border-rose-100",
    high: "bg-amber-50 text-amber-600 border-amber-100",
    medium: "bg-indigo-50 text-indigo-600 border-indigo-100",
    low: "bg-emerald-50 text-emerald-600 border-emerald-100",
  };
  const style = cfg[level?.toLowerCase()] || cfg.low;
  return (
    <span className={`px-2.5 py-1 border rounded-lg text-[9px] font-bold uppercase tracking-wider ${style}`}>
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
    date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    total: p.total
  }));

  if (statsLoading || trendsLoading || threatLoading) return <DashboardSkeleton />;
  if (!stats) return null;

  return (
    <motion.div 
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className="max-w-6xl mx-auto space-y-10 pb-16"
    >
      {/* Dynamic Header */}
      <motion.div 
        variants={itemVariants}
        className="relative overflow-hidden bg-white p-10 rounded-[3rem] border border-zinc-200 shadow-sm"
      >
        <div className="absolute top-0 right-0 p-12 opacity-[0.03] pointer-events-none">
          <Zap size={240} className="text-zinc-900" />
        </div>
        
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-indigo-100">
              <Shield size={12} /> Matrix Protocol Active
            </div>
            <h1 className="text-4xl font-black text-zinc-900 tracking-tighter">
              Welcome back, <span className="text-indigo-600">{user?.username || "Agent"}</span>
            </h1>
            <p className="text-sm text-zinc-500 font-medium max-w-xl leading-relaxed">
              Your neural interceptors are currently monitoring all incoming SMS traffic. No breaches detected in the last 24 hours. Systems are operating at <span className="text-zinc-900 font-bold">99.9% integrity</span>.
            </p>
          </div>

          <div className="flex gap-3">
             <motion.button
               whileHover={{ scale: 1.05 }}
               whileTap={{ scale: 0.95 }}
               onClick={() => navigate("/scan")}
               className="bg-zinc-900 text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600 transition-all shadow-xl shadow-indigo-100"
             >
               Initialize Scan
             </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Quick Actions Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {[
          { label: "New Analysis", icon: Search, path: "/scan", color: "text-indigo-600 bg-indigo-50" },
          { label: "Batch Upload", icon: Upload, path: "/batch", color: "text-emerald-600 bg-emerald-50" },
          { label: "Intelligence", icon: BarChart3, path: "/analytics", color: "text-amber-600 bg-amber-50" },
          { label: "Archive", icon: History, path: "/history", color: "text-rose-600 bg-rose-50" }
        ].map((action, i) => (
          <motion.button
            key={i}
            variants={itemVariants}
            whileHover={{ y: -5, backgroundColor: "#f8fafc" }}
            onClick={() => navigate(action.path)}
            className="flex flex-col items-center justify-center p-8 bg-white border border-zinc-200 rounded-[2.5rem] transition-all group"
          >
            <div className={`p-4 rounded-2xl mb-4 ${action.color} group-hover:scale-110 transition-transform duration-300`}>
              <action.icon size={24} />
            </div>
            <span className="text-[10px] font-black text-zinc-900 uppercase tracking-widest">{action.label}</span>
          </motion.button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <motion.div 
          variants={itemVariants}
          className="lg:col-span-2 space-y-8"
        >
          {/* Main Chart */}
          <div className="bg-white border border-zinc-200 p-10 rounded-[3rem] space-y-8 shadow-sm">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-black text-zinc-900 uppercase tracking-[0.2em] flex items-center gap-2">
                <Activity size={18} className="text-indigo-600" /> Neural Intercept Stream
              </h3>
              <div className="px-4 py-1.5 bg-slate-50 border border-slate-100 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                Real-time Telemetry
              </div>
            </div>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends}>
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }} dy={15} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }} />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6366f1', strokeWidth: 2, strokeDasharray: '5 5' }} />
                  <Area type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={4} fillOpacity={1} fill="url(#colorTotal)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <CompactStat label="Total Intercepts" value={stats.total_scanned.toLocaleString()} icon={Fingerprint} />
            <CompactStat label="Secure Traffic" value={(stats.ham_verified || 0).toLocaleString()} icon={Layers} />
            <CompactStat label="Threat Level" value={stats.threat_level} icon={AlertTriangle} />
          </div>
        </motion.div>

        <div className="space-y-8">
          {/* Health Card */}
          <motion.div 
            variants={itemVariants}
            className="bg-zinc-900 rounded-[3rem] p-10 text-white flex flex-col justify-between space-y-12 relative overflow-hidden group shadow-2xl shadow-zinc-200"
          >
            <div className="absolute top-0 right-0 p-12 opacity-[0.05] group-hover:rotate-12 transition-transform duration-700 pointer-events-none">
              <ShieldCheck size={200} />
            </div>
            
            <div className="space-y-8">
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em]">System Integrity</p>
              <div className="flex items-center gap-6">
                <div className="w-16 h-16 rounded-[1.5rem] bg-indigo-500/20 flex items-center justify-center border border-white/10 backdrop-blur-xl group-hover:scale-110 transition-transform duration-500">
                  <ShieldCheck size={32} className="text-emerald-400" />
                </div>
                <div>
                  <h4 className="text-2xl font-black tracking-tight leading-tight">Secure</h4>
                  <p className="text-[10px] text-zinc-500 font-black uppercase tracking-[0.2em] mt-1">Neural Bridge: Active</p>
                </div>
              </div>
            </div>

            <div className="space-y-8">
              <div className="space-y-3">
                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                  <span className="text-zinc-500">Matrix Sync</span>
                  <span className="text-emerald-400">99.9%</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden border border-white/5 p-0.5">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "99.9%" }}
                    transition={{ duration: 2, delay: 0.5 }}
                    className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 rounded-full" 
                  />
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                  <span className="text-zinc-500">Processing Speed</span>
                  <span className="text-indigo-400">Ultra</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden border border-white/5 p-0.5">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 2, delay: 0.8 }}
                    className="h-full bg-gradient-to-r from-emerald-400 via-indigo-500 to-indigo-500 rounded-full" 
                  />
                </div>
              </div>
            </div>

            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate("/history")}
              className="w-full py-5 bg-white text-zinc-900 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.3em] hover:bg-slate-50 transition-all flex items-center justify-center gap-3 shadow-xl"
            >
              Access Logs <ArrowUpRight size={16} />
            </motion.button>
          </motion.div>

          {/* Mini Feed */}
          <motion.div 
            variants={itemVariants}
            className="bg-white border border-zinc-200 rounded-[3rem] p-10 shadow-sm space-y-8"
          >
            <h3 className="text-[10px] font-black text-zinc-900 uppercase tracking-[0.2em] flex items-center gap-2">
              <Zap size={14} className="text-amber-500" /> Neural Feed
            </h3>
            <div className="space-y-6">
              {[
                { time: "Just now", event: "Intercept sequence complete", status: "secure" },
                { time: "2m ago", event: "AI threshold updated to 0.98", status: "system" },
                { time: "15m ago", event: "Bulk batch analysis success", status: "secure" }
              ].map((item, i) => (
                <div key={i} className="flex gap-4">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${item.status === 'secure' ? 'bg-emerald-500' : 'bg-indigo-500'}`} />
                  <div>
                    <p className="text-[11px] font-black text-zinc-900 leading-tight">{item.event}</p>
                    <p className="text-[9px] text-zinc-400 font-bold uppercase tracking-widest mt-1">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Table Section */}
      <motion.div 
        variants={itemVariants}
        className="bg-white border border-zinc-200 rounded-[3.5rem] overflow-hidden shadow-sm hover:shadow-2xl hover:shadow-zinc-100 transition-all duration-700"
      >
        <div className="px-10 py-8 border-b border-zinc-100 bg-zinc-50/50 flex justify-between items-center">
          <div className="space-y-1">
            <h3 className="text-sm font-black text-zinc-900 uppercase tracking-[0.2em] flex items-center gap-2">
              <ShieldAlert size={18} className="text-rose-500" /> Recent Intercepts
            </h3>
            <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Neural classification results</p>
          </div>
          <motion.button 
            whileHover={{ x: 3 }}
            onClick={() => navigate("/history")} 
            className="text-[10px] font-black text-indigo-600 uppercase tracking-widest flex items-center gap-2 hover:underline"
          >
            View Archive <ChevronRight size={14} />
          </motion.button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-100 bg-slate-50/30">
                <th className="px-10 py-5 text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em]">Intercept Content</th>
                <th className="px-10 py-5 text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em]">Neural Status</th>
                <th className="px-10 py-5 text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em] text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-50">
              <AnimatePresence>
                {(threatReport?.recent_threats || []).slice(0, 5).map((t, i) => (
                  <motion.tr 
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="hover:bg-slate-50/80 transition-all group cursor-pointer"
                    onClick={() => navigate("/results", { state: { result: t } })}
                  >
                    <td className="px-10 py-6">
                      <div className="flex items-center gap-4">
                         <div className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${t.is_spam ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'} border border-zinc-100`}>
                            {t.is_spam ? <ShieldAlert size={18} /> : <ShieldCheck size={18} />}
                         </div>
                         <div>
                            <p className="text-xs font-black text-zinc-900 truncate max-w-[400px] mb-1">{t.text}</p>
                            <p className="text-[9px] text-zinc-400 font-black uppercase tracking-widest">{new Date(t.predicted_at).toLocaleString()}</p>
                         </div>
                      </div>
                    </td>
                    <td className="px-10 py-6">
                      <ThreatBadge level={t.threat_level} />
                    </td>
                    <td className="px-10 py-6 text-right">
                      <div className="flex justify-end">
                        <div className="w-10 h-10 rounded-2xl bg-zinc-50 flex items-center justify-center text-zinc-400 group-hover:bg-zinc-900 group-hover:text-white group-hover:rotate-45 transition-all duration-300">
                          <ArrowUpRight size={16} />
                        </div>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default UserDashboard;

