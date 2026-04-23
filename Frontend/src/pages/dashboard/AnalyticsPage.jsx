import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell
} from "recharts";
import { 
  Activity, 
  TrendingUp, 
  ShieldAlert, 
  Zap, 
  RefreshCw,
  Sparkles
} from "lucide-react";
import { getSpamTrends, getUserStats } from "../../api/spamApi";
import { toast } from "react-hot-toast";

export const AnalyticsPage = () => {
  const [trends, setTrends] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lookback, setLookback] = useState(7);

  useEffect(() => {
    fetchAnalytics();
  }, [lookback]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [trendData, statData] = await Promise.all([
        getSpamTrends(lookback),
        getUserStats()
      ]);
      setTrends(trendData.points || []);
      setStats(statData);
    } catch (err) {
      toast.error("Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } }
  };

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="max-w-7xl mx-auto space-y-8"
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-2">
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-100 px-2.5 py-1 rounded-md text-[10px] font-semibold tracking-wider uppercase text-blue-700"
          >
            <Activity size={12} /> Intelligence
          </motion.div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            Threat Analytics
          </h1>
          <p className="text-slate-500 text-sm">
            Real-time telemetry and pattern recognition analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-white rounded-lg p-1 border border-slate-200 shadow-sm">
            {[
              { l: "7D", v: 7 },
              { l: "14D", v: 14 },
              { l: "30D", v: 30 },
              { l: "1Y", v: 365 }
            ].map(opt => (
              <button
                key={opt.v}
                onClick={() => setLookback(opt.v)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${lookback === opt.v ? "bg-slate-900 text-white shadow-sm" : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"}`}
              >
                {opt.l}
              </button>
            ))}
          </div>
          <button 
            onClick={fetchAnalytics}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-800 transition-all shadow-sm"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Detection Velocity */}
        <motion.div variants={cardVariants} className="lg:col-span-2 minimal-card p-6">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <TrendingUp className="text-slate-400 w-5 h-5" />
                Detection Velocity
              </h2>
              <p className="text-xs text-slate-500 mt-1">Signal ingestion over time</p>
            </div>
            <Sparkles className="text-blue-500 w-4 h-4" />
          </div>
          
          <div className="h-[300px] w-full">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-800 rounded-full animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ left: -20 }}>
                  <defs>
                    <linearGradient id="colorSpam" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorHam" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#64748b" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false}
                    tickMargin={10}
                    tickFormatter={(str) => {
                      const d = new Date(str);
                      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                    }}
                  />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} tickMargin={10} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", fontSize: "12px", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                    itemStyle={{ color: "#0f172a", fontWeight: 500 }}
                  />
                  <Area type="monotone" dataKey="spam_count" name="Spam" stroke="#f43f5e" strokeWidth={2} fillOpacity={1} fill="url(#colorSpam)" />
                  <Area type="monotone" dataKey="ham_count" name="Clean" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorHam)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>

        {/* Threat Distribution */}
        <motion.div variants={cardVariants} className="minimal-card p-6 flex flex-col">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="text-slate-400 w-5 h-5" />
              Threat Matrix
            </h2>
            <p className="text-xs text-slate-500 mt-1">Composition Analysis</p>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center">
            {loading ? (
               <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-800 rounded-full animate-spin" />
            ) : stats ? (
              <>
                <div className="h-[200px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <defs>
                        <linearGradient id="pieSpam" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={1}/>
                          <stop offset="95%" stopColor="#be123c" stopOpacity={1}/>
                        </linearGradient>
                        <linearGradient id="pieHam" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={1}/>
                          <stop offset="95%" stopColor="#1d4ed8" stopOpacity={1}/>
                        </linearGradient>
                      </defs>
                      <Pie
                        data={[
                          { name: "Spam", value: stats.spam_blocked },
                          { name: "Clean", value: stats.total_scanned - stats.spam_blocked }
                        ]}
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                        dataKey="value"
                        stroke="none"
                        cornerRadius={6}
                      >
                        <Cell fill="url(#pieSpam)" />
                        <Cell fill="url(#pieHam)" />
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#ffffff", border: "none", borderRadius: "12px", fontSize: "12px", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)" }}
                        itemStyle={{ color: "#0f172a", fontWeight: 600 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-4 w-full mt-6">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-center">
                    <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1">Spam Ratio</p>
                    <p className="text-xl font-bold text-slate-900">
                      {stats.total_scanned > 0 ? ((stats.spam_blocked / stats.total_scanned) * 100).toFixed(1) : 0}%
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-center">
                    <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1">Status</p>
                    <p className={`text-xl font-bold ${stats.threat_level === "High" ? "text-rose-600" : stats.threat_level === "Medium" ? "text-amber-600" : "text-emerald-600"}`}>
                      {stats.threat_level}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500 italic">No telemetry data</p>
            )}
          </div>
        </motion.div>

        {/* Intelligence Insights */}
        <motion.div variants={cardVariants} className="lg:col-span-3 minimal-card p-6">
           <div className="flex items-center gap-3 mb-6">
             <div className="p-2 bg-blue-50 rounded-lg border border-blue-100">
               <Zap className="text-blue-600 w-5 h-5" />
             </div>
             <div>
               <h2 className="text-base font-semibold text-slate-900">Neural Insights</h2>
               <p className="text-xs text-slate-500">Model Performance Telemetry</p>
             </div>
           </div>

           <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-600">Inference Latency</span>
                  <span className="text-slate-900">24ms avg</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: "85%" }} className="h-full bg-blue-500 rounded-full" />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-600">Model Confidence</span>
                  <span className="text-slate-900">98.2%</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: "98%" }} className="h-full bg-purple-500 rounded-full" />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-600">Resource Utilization</span>
                  <span className="text-slate-900">Optimal</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: "45%" }} className="h-full bg-emerald-500 rounded-full" />
                </div>
              </div>
           </div>
        </motion.div>

      </div>
    </motion.div>
  );
};
