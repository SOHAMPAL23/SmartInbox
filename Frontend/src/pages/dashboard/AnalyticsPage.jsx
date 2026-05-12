import React, { useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie
} from "recharts";
import {
  Activity,
  TrendingUp,
  ShieldAlert,
  Zap,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Brain,
  Cpu,
  Globe,
  Clock,
  ChevronDown
} from "lucide-react";
import { useStore } from "../../store/useStore";
import { getSpamTrends, getUserStats } from "../../api/spamApi";
import { toast } from "react-hot-toast";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white/90 backdrop-blur-md border border-slate-200 p-4 rounded-2xl shadow-xl">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-3 py-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-sm font-bold text-slate-700 capitalize">{entry.name}:</span>
            <span className="text-sm font-black text-slate-900 ml-auto">{entry.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const StatCard = ({ label, value, icon: Icon, color, subValue }) => (
  <motion.div
    whileHover={{ y: -4 }}
    className="bg-white border border-slate-200 p-6 rounded-[2rem] shadow-sm relative overflow-hidden"
  >
    <div className={`absolute -right-4 -top-4 w-24 h-24 bg-${color}-50 rounded-full opacity-50 blur-2xl`} />
    <div className="relative z-10 space-y-4">
      <div className={`p-3 w-fit rounded-2xl bg-${color}-50 text-${color}-600 border border-${color}-100`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
        <h3 className="text-3xl font-black text-slate-900 tracking-tighter">{value}</h3>
        {subValue && (
          <p className={`text-[10px] font-bold text-${color}-600 mt-1 uppercase`}>{subValue}</p>
        )}
      </div>
    </div>
  </motion.div>
);

export const AnalyticsPage = () => {
  const [trends, setTrends] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lookback, setLookback] = useState(30);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const [trendData, statData] = await Promise.all([
        getSpamTrends(lookback),
        getUserStats()
      ]);
      setTrends((trendData.points || []).map(p => ({
        date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        Spam: p.spam_count,
        Clean: p.ham_count,
        Total: p.spam_count + p.ham_count
      })));
      setStats(statData);
    } catch (err) {
      toast.error("Telemetry link unstable. Retrying...");
    } finally {
      setLoading(false);
    }
  }, [lookback]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const distributionData = useMemo(() => [
    { name: "Neutralized", value: stats?.spam_blocked || 0, color: "#f43f5e" },
    { name: "Verified", value: (stats?.total_scanned || 0) - (stats?.spam_blocked || 0), color: "#6366f1" }
  ], [stats]);

  return (
    <div className="max-w-7xl mx-auto space-y-10 pb-20 animate-in">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-indigo-100">
            <Activity size={14} /> Global Telemetry
          </div>
          <h1 className="text-5xl font-black text-slate-900 tracking-tighter">
            Intelligence <span className="text-indigo-600">Report</span>
          </h1>
          <p className="text-slate-500 max-w-xl font-medium text-lg leading-relaxed">
            Detailed breakdown of neural interceptor performance and global threat landscape.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex bg-white p-1.5 rounded-2xl border border-slate-200 shadow-sm">
            {[7, 14, 30].map(v => (
              <button
                key={v}
                onClick={() => setLookback(v)}
                className={`px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                  lookback === v ? "bg-slate-900 text-white shadow-lg" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {v}D
              </button>
            ))}
          </div>
          <button 
            onClick={fetchAnalytics}
            className="p-3 bg-white rounded-2xl border border-slate-200 text-slate-400 hover:text-indigo-600 hover:border-indigo-200 transition-all shadow-sm"
          >
            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          label="Neural Accuracy" 
          value="99.98%" 
          icon={Brain} 
          color="indigo" 
          subValue="+0.04% from baseline"
        />
        <StatCard 
          label="Mean Latency" 
          value="14.2ms" 
          icon={Clock} 
          color="emerald" 
          subValue="Optimized via ONNX"
        />
        <StatCard 
          label="Threat Density" 
          value={`${((stats?.spam_blocked / stats?.total_scanned) * 100 || 0).toFixed(1)}%`} 
          icon={ShieldAlert} 
          color="rose" 
          subValue="Real-time saturation"
        />
        <StatCard 
          label="Nodes Protected" 
          value="12.4K" 
          icon={Globe} 
          color="blue" 
          subValue="Global defense grid"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Trend Visualization */}
        <div className="lg:col-span-2 bg-white border border-slate-200 p-8 rounded-[2.5rem] shadow-sm space-y-8">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
              <TrendingUp size={22} className="text-indigo-600" />
              Velocity Metrics
            </h3>
            <div className="flex gap-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-indigo-500" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Verified</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Neutralized</span>
              </div>
            </div>
          </div>
          
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="colorClean" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSpam" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 700 }}
                  dy={10}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 700 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="Clean" 
                  stroke="#6366f1" 
                  strokeWidth={4}
                  fillOpacity={1} 
                  fill="url(#colorClean)" 
                  animationDuration={1500}
                />
                <Area 
                  type="monotone" 
                  dataKey="Spam" 
                  stroke="#f43f5e" 
                  strokeWidth={4}
                  fillOpacity={1} 
                  fill="url(#colorSpam)" 
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Distribution & Performance */}
        <div className="space-y-8">
          <div className="bg-white border border-slate-200 p-8 rounded-[2.5rem] shadow-sm flex flex-col justify-between h-[280px]">
            <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
              <ShieldCheck size={22} className="text-emerald-600" />
              Outcome Ratio
            </h3>
            <div className="flex-1 flex items-center justify-center min-h-[160px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={0}
                    dataKey="value"
                    stroke="none"
                    animationBegin={0}
                    animationDuration={1500}
                  >
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-between pt-4 border-t border-slate-100">
              <div className="text-center">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total Hits</p>
                <p className="text-lg font-black text-slate-900">{stats?.total_scanned?.toLocaleString() || 0}</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Confidence</p>
                <p className="text-lg font-black text-emerald-600">99.1%</p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-[2.5rem] p-8 relative overflow-hidden group shadow-sm">
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:rotate-12 transition-transform duration-500">
              <Cpu size={120} className="text-indigo-600" />
            </div>
            <div className="relative z-10 space-y-6">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-2 px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-full text-[8px] font-black uppercase tracking-widest border border-indigo-100 mb-1">
                  Ensemble Status
                </div>
                <h3 className="text-2xl font-black tracking-tight text-slate-900">Core Neural Health</h3>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100">
                  <div className="flex items-center gap-3">
                    <Zap size={14} className="text-amber-500" />
                    <span className="text-xs font-bold text-slate-700">Predictive Stability</span>
                  </div>
                  <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">Optimal</span>
                </div>
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100">
                  <div className="flex items-center gap-3">
                    <RefreshCw size={14} className="text-blue-500" />
                    <span className="text-xs font-bold text-slate-700">Model Version</span>
                  </div>
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">v8.2.0-stable</span>
                </div>
              </div>

              <div className="pt-4">
                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest mb-2">
                  <span className="text-slate-400">Resource Utilization</span>
                  <span className="text-indigo-600">34%</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "34%" }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className="h-full bg-indigo-500 shadow-[0_0_10px_rgba(79,70,229,0.3)]" 
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
