import React, { useState } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Shield, Activity, Cpu, Lock,
  ArrowRight, Zap, ChevronRight, CheckCircle2,
  Globe, Sparkles, TrendingUp, Fingerprint, Layers, User
} from "lucide-react";
import { useStore } from "../store/useStore";
import { toast } from "react-hot-toast";
import Logo from "../components/ui/Logo";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export const LandingPage = () => {
  const navigate = useNavigate();
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const login = useStore((state) => state.login);
  const { scrollY } = useScroll();

  const handleDemoAccess = async () => {
    setIsDemoLoading(true);
    try {
      await login("demo@example.com", "demo1234");
      toast.success("Intelligence access granted. Initializing demo environment.");
      navigate("/dashboard");
    } catch (err) {
      toast.error("Demo authentication failed. Please try manual login.");
    } finally {
      setIsDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-900 overflow-x-hidden">
      {/* Premium Background Decorations */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.4, 0.3]
          }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
          className="absolute top-[-15%] right-[-10%] w-[800px] h-[800px] bg-indigo-200/30 rounded-full blur-[120px]"
        />
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.3, 0.2]
          }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[-15%] left-[-10%] w-[900px] h-[900px] bg-rose-100/20 rounded-full blur-[140px]"
        />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-white/70 backdrop-blur-2xl border-b border-slate-200/50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="cursor-pointer"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <Logo size="md" horizontal />
          </motion.div>

          <div className="flex items-center gap-4 sm:gap-8">
            <div className="hidden md:flex items-center gap-6">
              <button onClick={() => navigate("/login")} className="text-xs font-bold text-slate-400 uppercase tracking-widest hover:text-indigo-600 transition-colors">Access</button>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate("/register")}
              className="bg-slate-900 text-white text-[10px] font-bold uppercase tracking-widest px-6 py-3 rounded-xl hover:bg-indigo-600 hover:shadow-xl hover:shadow-indigo-100 transition-all"
            >
              Initialize
            </motion.button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-48 pb-32 px-6">
        <div className="max-w-5xl mx-auto text-center space-y-12">
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-8"
          >
            <motion.div
              variants={fadeInUp}
              className="inline-flex items-center gap-2 px-4 py-1.5 bg-white border border-slate-200 rounded-full shadow-sm"
            >
              <div className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Network Secure • v2.4.0</span>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="text-6xl sm:text-7xl lg:text-9xl font-black tracking-tighter leading-[0.9] text-slate-900"
            >
              Neutralize<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-rose-500 animate-gradient-x pb-4">
                Threats
              </span>
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              className="max-w-2xl mx-auto text-slate-500 text-lg md:text-xl font-medium leading-relaxed"
            >
              Deploy advanced neural interceptors designed to identify, isolate, and eliminate malicious SMS traffic before it breaches your perimeter.
            </motion.p>

            <motion.div
              variants={fadeInUp}
              className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-4"
            >
              <motion.button
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate("/register")}
                className="group w-full sm:w-auto flex items-center justify-center gap-3 bg-slate-900 text-white px-10 py-5 rounded-2xl text-xs font-bold uppercase tracking-widest hover:bg-indigo-600 hover:shadow-2xl hover:shadow-indigo-200 transition-all duration-300"
              >
                Secure Access
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleDemoAccess}
                disabled={isDemoLoading}
                className="group w-full sm:w-auto flex items-center justify-center gap-3 bg-white px-10 py-5 rounded-2xl text-xs font-bold uppercase tracking-widest text-slate-700 border border-slate-200 hover:border-slate-300 hover:shadow-xl hover:shadow-slate-100 transition-all duration-300 disabled:opacity-50"
              >
                {isDemoLoading ? (
                  <div className="w-4 h-4 border-2 border-indigo-600/30 border-t-indigo-600 rounded-full animate-spin" />
                ) : (
                  <Sparkles size={0} className="text-indigo-500 group-hover:rotate-12 transition-transform" />
                )}
                Quick Demo
              </motion.button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Floating Dashboard Preview */}
      <section className="px-6 pb-32">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-6xl mx-auto rounded-[2.5rem] bg-white border border-slate-200 shadow-2xl overflow-hidden relative group"
        >
          <div className="absolute inset-0 bg-gradient-to-tr from-indigo-50/20 to-transparent pointer-events-none" />
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
            </div>
            <div className="mx-auto bg-white border border-slate-200 rounded-lg px-4 py-1 text-[9px] font-bold text-slate-400 uppercase tracking-widest">
              secure-terminal.smartinbox.ai
            </div>
          </div>
          <div className="aspect-[16/9] md:aspect-[21/9] bg-white p-8 overflow-hidden relative">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-10">
              {[
                { label: "Neural Traffic", value: "84.2k", color: "bg-indigo-500" },
                { label: "Threat Intercepts", value: "1,204", color: "bg-rose-500" },
                { label: "Encryption", value: "256-bit", color: "bg-emerald-500" },
                { label: "Active Nodes", value: "128", color: "bg-amber-500" }
              ].map((stat, i) => (
                <div key={i} className="p-4 rounded-2xl bg-slate-50 border border-slate-100 relative overflow-hidden group">
                  <div className={`absolute top-0 left-0 w-1 h-full ${stat.color} opacity-20`} />
                  <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">{stat.label}</p>
                  <p className="text-xl font-black text-slate-900 tracking-tighter">{stat.value}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2 h-64 rounded-3xl bg-slate-50 border border-slate-100 p-6">
                <div className="flex justify-between items-center mb-6">
                  <div className="h-2 w-24 bg-slate-200 rounded-full" />
                  <div className="h-2 w-12 bg-slate-200 rounded-full" />
                </div>
                <div className="flex items-end gap-2 h-40">
                  {[40, 70, 45, 90, 65, 80, 50, 95, 60, 85, 40, 75].map((h, i) => (
                    <motion.div
                      key={i}
                      initial={{ height: 0 }}
                      animate={{ height: `${h}%` }}
                      transition={{ duration: 1, delay: i * 0.05 }}
                      className="flex-1 bg-indigo-100 rounded-t-md group-hover:bg-indigo-500 transition-colors"
                    />
                  ))}
                </div>
              </div>
              <div className="h-64 rounded-3xl bg-slate-900 p-8 space-y-6 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-6 opacity-10">
                  <Activity size={48} className="text-white" />
                </div>
                <div className="flex justify-between items-center relative z-10">
                  <div className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-[7px] font-black text-indigo-400 uppercase tracking-widest">
                    Live Intercepts
                  </div>
                  <div className="flex gap-1">
                    <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                    <div className="w-1 h-1 rounded-full bg-emerald-500/40" />
                  </div>
                </div>
                
                <div className="space-y-4 relative z-10">
                  {[
                    { text: "Intercepted: AI-Phish-992", status: "Neutralized", color: "text-emerald-400" },
                    { text: "Neural Bridge Sync: OK", status: "Active", color: "text-indigo-400" },
                    { text: "Bulk Scan: 48.2k SMS", status: "Verified", color: "text-amber-400" }
                  ].map((item, i) => (
                    <motion.div 
                      key={i}
                      initial={{ x: -20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: 0.5 + i * 0.2 }}
                      className="flex items-center gap-4 group/item"
                    >
                      <div className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover/item:bg-white/10 transition-colors">
                        <Fingerprint size={16} className="text-indigo-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-bold text-white truncate">{item.text}</p>
                        <p className={`text-[8px] font-black uppercase tracking-widest ${item.color} mt-0.5`}>{item.status}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>

                {/* Animated Scan Line */}
                <motion.div 
                  animate={{ top: ["0%", "100%", "0%"] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent z-20 pointer-events-none"
                />
              </div>
            </div>
          </div>
        </motion.div>
      </section>      {/* Global Intelligence Network - Live Stats */}
      <section className="py-32 bg-slate-50 px-6 overflow-hidden relative">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
          <div className="space-y-10">
            <div className="space-y-4">
              <h2 className="text-xs font-bold text-rose-600 uppercase tracking-[0.3em]">Real-time Network</h2>
              <p className="text-5xl font-black text-slate-900 tracking-tighter leading-none">Global Defense Activity</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
              <div className="space-y-2">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Threats Neutralized</p>
                <motion.p
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  className="text-5xl font-black text-indigo-600 tracking-tighter"
                >
                  12.8M+
                </motion.p>
              </div>
              <div className="space-y-2">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Active Operatives</p>
                <motion.p
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  className="text-5xl font-black text-slate-900 tracking-tighter"
                >
                  48.2k
                </motion.p>
              </div>
            </div>

            <div className="p-8 bg-white rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-100 space-y-6">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <Globe size={14} className="text-indigo-500" /> Active Deployment Map
              </p>
              <div className="h-48 w-full bg-slate-50 rounded-2xl relative overflow-hidden group">
                <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/world-map.png')] bg-center bg-no-repeat bg-contain" />
                {[1, 2, 3, 4, 5].map(i => (
                  <motion.div
                    key={i}
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity, delay: i * 0.4 }}
                    className="absolute w-3 h-3 bg-indigo-500 rounded-full border-2 border-white shadow-lg"
                    style={{
                      top: `${Math.random() * 80 + 10}%`,
                      left: `${Math.random() * 80 + 10}%`
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 rounded-[3rem] p-12 text-white space-y-12 shadow-2xl shadow-zinc-200 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-12 opacity-10 pointer-events-none">
              <Shield size={200} />
            </div>

            <div className="space-y-2">
              <h3 className="text-2xl font-black tracking-tight leading-none">Verified Operatives</h3>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Network Member Testimonials</p>
            </div>

            <div className="space-y-8">
              {[
                { name: "Agent X", role: "Security Lead", text: "The neural bridge latency is practically zero. Best-in-class defense." },
                { name: "Alpha-9", role: "Network Architect", text: "Matrix protocol has successfully neutralized every spear-phishing attempt." }
              ].map((agent, i) => (
                <div key={i} className="flex gap-6 items-start">
                  <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center border border-white/10 shrink-0">
                    <Fingerprint size={24} className="text-indigo-400" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-zinc-300 leading-relaxed italic">"{agent.text}"</p>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] font-black uppercase tracking-widest text-white">{agent.name}</span>
                      <div className="w-1 h-1 rounded-full bg-zinc-600" />
                      <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-500">{agent.role}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-8 border-t border-white/5 flex justify-between items-center">
              <div className="flex -space-x-3">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="w-10 h-10 rounded-full bg-zinc-800 border-2 border-zinc-900 flex items-center justify-center overflow-hidden">
                    <User size={20} className="text-zinc-600" />
                  </div>
                ))}
                <div className="w-10 h-10 rounded-full bg-indigo-600 border-2 border-zinc-900 flex items-center justify-center text-[10px] font-black">
                  +2k
                </div>
              </div>
              <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Trust Index: 99.8%</p>
            </div>
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="py-32 px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="max-w-5xl mx-auto bg-indigo-600 rounded-[3rem] p-12 md:p-24 text-center relative overflow-hidden shadow-2xl shadow-indigo-200"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-white/20 via-transparent to-transparent" />
          <motion.div
            animate={{
              rotate: [0, 360],
            }}
            transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
            className="absolute top-0 right-0 p-10 opacity-5 pointer-events-none"
          >
            <TrendingUp size={400} className="text-white" />
          </motion.div>

          <div className="relative z-10 space-y-10 max-w-2xl mx-auto">
            <h2 className="text-4xl md:text-6xl font-black text-white tracking-tighter leading-[0.95]">
              Secure your communication matrix today.
            </h2>
            <motion.button
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate("/register")}
              className="bg-white text-indigo-600 px-14 py-6 rounded-2xl text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-slate-50 transition-all shadow-xl shadow-black/10"
            >
              Deploy Matrix Now
            </motion.button>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-20 border-t border-slate-100 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-3">
            <Zap size={20} className="text-indigo-600" />
            <span className="text-lg font-black text-slate-900 tracking-tight">SmartInbox</span>
          </div>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.3em]">
            &copy; 2026 SMARTINBOX AI • ALL RIGHTS RESERVED
          </p>
          <div className="flex gap-8">
            <button className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-900 transition-colors">Privacy</button>
            <button className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-900 transition-colors">Terms</button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;

