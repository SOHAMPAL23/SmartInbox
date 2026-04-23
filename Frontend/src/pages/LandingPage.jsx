import React, { useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { 
  ShieldCheck, 
  ArrowRight, 
  Activity, 
  Clock, 
  Zap, 
  Lock, 
  Cpu, 
  ChevronRight 
} from "lucide-react";
import { toast } from "react-hot-toast";
import { Hero3D } from "../components/3d/Hero3D";

export const LandingPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");

  const handleInactiveLink = (e) => {
    e.preventDefault();
    toast("Coming soon in v2.0!", { icon: "🚀" });
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.3,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } },
  };

  return (
    <div className="min-h-screen relative bg-[#020617] text-slate-900 selection:bg-cyan-500/30 overflow-hidden">
      {/* 3D Background */}
      <Hero3D />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
          <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg shadow-lg ">
            <Zap className="w-6 h-6 text-slate-900" />
          </div>
          <span className="font-bold text-2xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
            SmartInbox
          </span>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-6"
        >
          <div className="hidden md:flex gap-8 text-sm font-bold uppercase tracking-widest text-slate-500">
            <a href="#" onClick={handleInactiveLink} className="hover:text-slate-900 transition-colors hover:">Platform</a>
            <a href="#" onClick={handleInactiveLink} className="hover:text-slate-900 transition-colors hover:">Docs</a>
          </div>
          <motion.button 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/login")}
            className="btn-primary flex items-center gap-2"
          >
            Get Started <ChevronRight size={18} />
          </motion.button>
        </motion.div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-8 pt-32 pb-48 flex flex-col items-center text-center">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-8 max-w-4xl"
        >
          <motion.div 
            variants={itemVariants}
            className="inline-flex items-center gap-2 bg-slate-50 border border-slate-200 px-4 py-2 rounded-full text-[10px] font-bold tracking-[0.2em] uppercase text-cyan-400 backdrop-blur-md"
          >
            <Cpu size={14} className="animate-pulse" /> Next-Gen SMS Intelligence
          </motion.div>

          <motion.h1 
            variants={itemVariants}
            className="text-7xl md:text-8xl font-black tracking-tighter leading-[0.9]"
          >
            Secure Your <br />
            <span className="text-blue-600 font-semibold">Communications</span>
          </motion.h1>

          <motion.p 
            variants={itemVariants}
            className="text-slate-500 text-xl max-w-2xl mx-auto font-medium leading-relaxed"
          >
            Enterprise-grade neural networks that detect and neutralize SMS spam with 99.9% precision. Powered by advanced TF-IDF + Character-level deep learning.
          </motion.p>

          <motion.div 
            variants={itemVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
          >
            <div className="flex bg-slate-50 border border-slate-200 rounded-2xl p-1  w-full sm:w-auto">
              <input 
                type="email" 
                placeholder="Enter work email"
                className="bg-transparent border-none focus:ring-0 px-6 py-3 text-slate-900 placeholder:text-slate-600 w-full sm:w-64"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate("/login", { state: { email } })}
                className="btn-primary whitespace-nowrap"
              >
                Join Private Beta
              </motion.button>
            </div>
          </motion.div>

          {/* Stats Bar */}
          <motion.div 
            variants={itemVariants}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 pt-20"
          >
            {[
              { label: "Accuracy", value: "99.9%", icon: ShieldCheck, color: "cyan" },
              { label: "Latency", value: "12ms", icon: Clock, color: "blue" },
              { label: "Live Scans", value: "4.2M+", icon: Activity, color: "purple" },
              { label: "SSL Secure", value: "AES-256", icon: Lock, color: "pink" }
            ].map((stat, i) => (
              <div key={i} className="flex flex-col items-center group">
                <div className={`p-3 rounded-2xl bg-${stat.color}-500/10 border border-${stat.color}-500/20 group-hover:scale-110 transition-transform duration-500`}>
                  <stat.icon className={`w-5 h-5 text-${stat.color}-400`} />
                </div>
                <span className="text-2xl font-black mt-4 tracking-tight">{stat.value}</span>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">{stat.label}</span>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </main>

      {/* Floating Action Button / Notification */}
      <motion.div 
        initial={{ opacity: 0, y: 100 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.5 }}
        className="fixed bottom-8 right-8 z-50"
      >
        <div className=" px-6 py-4 rounded-2xl flex items-center gap-4 border border-slate-200 shadow-md">
          <div className="relative">
            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-ping absolute" />
            <div className="w-3 h-3 bg-emerald-500 rounded-full relative" />
          </div>
          <span className="text-xs font-bold text-slate-600 uppercase tracking-widest">
            Nodes Online: 1,284
          </span>
        </div>
      </motion.div>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-100 py-12 bg-black/20 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-8 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-500" />
            <span className="text-slate-500 font-bold text-sm tracking-widest uppercase">© 2026 SmartInbox AI</span>
          </div>
          <div className="flex gap-12 text-[10px] font-bold uppercase tracking-widest text-slate-600">
            <a href="#" onClick={handleInactiveLink} className="hover:text-slate-900 transition-colors">Privacy Policy</a>
            <a href="#" onClick={handleInactiveLink} className="hover:text-slate-900 transition-colors">Terms of Service</a>
            <a href="#" onClick={handleInactiveLink} className="hover:text-slate-900 transition-colors">Security Audit</a>
          </div>
        </div>
      </footer>
    </div>
  );
};
