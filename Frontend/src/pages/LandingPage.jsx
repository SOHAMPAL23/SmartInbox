import React, { useState, useEffect } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Shield, Activity, Cpu, Layers, Lock, BarChart3, 
  ArrowRight, Zap, ChevronRight, CheckCircle2,
  Globe, Sparkles, TrendingUp
} from "lucide-react";

const FloatingShape = ({ color, top, left, delay, size, duration = 8, rotate = 0 }) => (
  <motion.div
    animate={{
      y: [0, -30, 0],
      rotate: [rotate, rotate + 10, rotate],
      scale: [1, 1.05, 1],
    }}
    transition={{ duration, repeat: Infinity, delay, ease: "easeInOut" }}
    className={`absolute rounded-3xl blur-[80px] pointer-events-none opacity-40 ${color} ${size}`}
    style={{ top, left }}
  />
);

const FeatureCard = ({ icon: Icon, title, description, delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-50px" }}
    transition={{ delay, duration: 0.6, ease: "easeOut" }}
    whileHover={{ y: -5 }}
    className="group bg-white rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-xl hover:border-indigo-200 transition-all duration-300 relative overflow-hidden"
  >
    <div className="relative z-10">
      <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-6 group-hover:bg-indigo-600 group-hover:text-white group-hover:scale-110 transition-all duration-300 shadow-sm">
        <Icon size={26} />
      </div>
      <h3 className="text-xl font-black text-slate-900 mb-3 tracking-tight group-hover:text-indigo-600 transition-colors">{title}</h3>
      <p className="text-sm text-slate-500 leading-relaxed font-medium">{description}</p>
    </div>
  </motion.div>
);

export const LandingPage = () => {
  const navigate = useNavigate();
  const { scrollYProgress } = useScroll();
  const opacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans overflow-x-hidden selection:bg-indigo-100 selection:text-indigo-900">
      {/* Dynamic Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+CjxyZWN0IHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgZmlsbD0ibm9uZSIvPgo8Y2lyY2xlIGN4PSIyMCIgY3k9IjIwIiByPSIxIiBmaWxsPSJyZ2JhKDcxLDg1LDEwNSwwLjA1KSIvPgo8L3N2Zz4=')] opacity-60 mask-image:linear-gradient(to_bottom,white,transparent)" />
        <FloatingShape color="bg-indigo-300" top="-10%" left="10%" delay={0} size="w-[500px] h-[500px]" rotate={45} />
        <FloatingShape color="bg-purple-300" top="30%" left="70%" delay={2} size="w-[600px] h-[600px]" duration={10} rotate={-20} />
        <FloatingShape color="bg-blue-300" top="60%" left="-10%" delay={4} size="w-[400px] h-[400px]" duration={12} rotate={15} />
      </div>

      {/* Nav */}
      <nav className="fixed w-full z-50 top-0 transition-all duration-300 bg-white/70 backdrop-blur-xl border-b border-slate-200/50">
        <div className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-900 rounded-xl shadow-lg shadow-slate-900/20 group-hover:rotate-12 transition-transform">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-black text-2xl tracking-tighter text-slate-900">
              Smart<span className="text-indigo-600">Inbox</span>
            </span>
          </div>

          <div className="flex items-center gap-6">
            <button
              onClick={() => navigate("/login")}
              className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500 hover:text-slate-900 transition-colors"
            >
              Agent Login
            </button>
            <button
              onClick={() => navigate("/register")}
              className="group flex items-center gap-2 bg-slate-900 px-6 py-2.5 rounded-xl transition-all hover:bg-indigo-600 hover:shadow-lg hover:shadow-indigo-600/20 active:scale-95"
            >
              <span className="text-xs font-bold uppercase tracking-widest text-white">Initialize</span>
              <ArrowRight size={14} className="text-white group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen pt-32 pb-20 px-6 flex flex-col items-center justify-center z-10 overflow-hidden text-center">
        <div className="max-w-4xl mx-auto w-full">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="space-y-10 relative z-20 flex flex-col items-center"
          >
            <div className="inline-flex items-center gap-3 bg-white/80 backdrop-blur-md border border-indigo-100 px-5 py-2.5 rounded-full text-xs font-bold tracking-widest uppercase text-indigo-600 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </span>
              Neural Core Online
            </div>

            <div className="space-y-6">
              <h1 className="text-6xl sm:text-7xl lg:text-8xl font-black tracking-tighter leading-[1.05] text-slate-900">
                Neutralize <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 animate-gradient-x pb-2">
                  Threats.
                </span>
              </h1>
              <p className="text-slate-500 text-lg sm:text-xl font-medium leading-relaxed max-w-2xl mx-auto">
                Deploy advanced neural interceptors designed to identify, isolate, and eliminate malicious SMS traffic before it breaches your perimeter.
              </p>
            </div>

            <div className="flex flex-wrap justify-center items-center gap-4 pt-6">
              <button
                onClick={() => navigate("/register")}
                className="group relative flex items-center gap-3 bg-slate-900 text-white px-8 py-4 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-indigo-600 transition-all hover:scale-105 active:scale-95 shadow-xl shadow-slate-900/20"
              >
                Secure Access
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
              
              <button className="group flex items-center gap-3 bg-white px-8 py-4 rounded-2xl text-sm font-bold tracking-widest text-slate-700 border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all active:scale-95">
                <Sparkles size={18} className="text-indigo-500 group-hover:rotate-12 transition-transform" />
                View Demo
              </button>
            </div>

            <div className="flex items-center gap-6 pt-12">
              <div className="flex -space-x-3">
                {[
                  "https://i.pravatar.cc/100?img=33",
                  "https://i.pravatar.cc/100?img=47",
                  "https://i.pravatar.cc/100?img=12",
                  "https://i.pravatar.cc/100?img=5"
                ].map((src, i) => (
                  <img key={i} src={src} alt="User" className="w-10 h-10 rounded-full border-2 border-white shadow-sm object-cover" />
                ))}
              </div>
              <p className="text-xs font-bold text-slate-500 tracking-wide">
                Trusted by <span className="text-slate-900">12,000+</span> Security Analysts
              </p>
            </div>
          </motion.div>
        </div>
        
        {/* Scroll Indicator */}
        <motion.div 
          style={{ opacity }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-400">Scroll</span>
          <motion.div 
            animate={{ y: [0, 10, 0] }} 
            transition={{ repeat: Infinity, duration: 2 }}
            className="w-[1px] h-12 bg-gradient-to-b from-indigo-300 to-transparent"
          />
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="relative z-20 py-10 border-y border-slate-200/50 bg-white/50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 divide-x divide-slate-200/50">
          {[
            { label: "Threats Blocked", value: "2.4B+" },
            { label: "Active Nodes", value: "15,000+" },
            { label: "Avg. Latency", value: "12ms" },
            { label: "Uptime", value: "99.99%" }
          ].map((stat, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center px-4"
            >
              <h4 className="text-3xl md:text-4xl font-black text-slate-900 mb-2">{stat.value}</h4>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative py-32 px-6 z-10">
        <div className="max-w-7xl mx-auto space-y-24">
          <div className="text-center space-y-6 max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-600 text-xs font-bold uppercase tracking-widest shadow-sm"
            >
              <Globe size={14} /> Global Defense Grid
            </motion.div>
            <h2 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tighter">
              Unmatched <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">Precision.</span>
            </h2>
            <p className="text-slate-500 text-lg font-medium">
              Our architecture leverages state-of-the-art transformer models to dissect and neutralize threats with mathematical certainty.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={Shield}
              title="Neural Intercept"
              description="Real-time message filtering using transformer models trained on billions of threat vectors with 99.9% accuracy."
              delay={0.1}
            />
            <FeatureCard
              icon={BarChart3}
              title="Threat Analytics"
              description="Visualize spam trends and attack patterns through our high-performance interactive dashboard."
              delay={0.2}
            />
            <FeatureCard
              icon={Cpu}
              title="Sub-15ms Latency"
              description="Heavily optimized ONNX inference pipeline ensures your protection operates faster than human perception."
              delay={0.3}
            />
            <FeatureCard
              icon={Layers}
              title="Batch Telemetry"
              description="Process massive historical datasets simultaneously for deep retrospective pattern recognition."
              delay={0.4}
            />
            <FeatureCard
              icon={Lock}
              title="Zero-Knowledge Base"
              description="End-to-end encrypted architecture. Our models mathematically analyze patterns, never personal identities."
              delay={0.5}
            />
            <FeatureCard
              icon={Activity}
              title="Real-time Alerts"
              description="Instant programmatic notifications via WebHooks when anomalous activity spikes are detected."
              delay={0.6}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-6 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-5xl mx-auto bg-slate-900 rounded-[40px] p-12 md:p-20 text-center relative overflow-hidden shadow-2xl shadow-slate-900/20"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.2),transparent)]" />
          <div className="absolute top-0 right-0 p-10 opacity-10 pointer-events-none">
            <TrendingUp size={200} className="text-indigo-400 rotate-12" />
          </div>
          
          <div className="relative z-10 space-y-8 max-w-2xl mx-auto">
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tighter leading-tight">
              Secure your communication matrix today.
            </h2>
            <p className="text-slate-300 text-lg md:text-xl font-medium">
              Join elite security analysts and everyday power users protecting their mobile identity with the world's most advanced neural filter.
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center items-center gap-6 pt-8">
              <button
                onClick={() => navigate("/register")}
                className="w-full sm:w-auto bg-indigo-600 text-white px-10 py-4 rounded-xl text-sm font-black uppercase tracking-widest hover:bg-indigo-500 hover:scale-105 active:scale-95 transition-all shadow-lg shadow-indigo-600/30"
              >
                Initialize Access
              </button>
              <div className="flex items-center gap-2 text-slate-300 text-sm font-bold">
                <CheckCircle2 size={18} className="text-indigo-400" />
                <span>No credit card required</span>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-12 px-6 border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-slate-100 rounded-lg">
              <Zap className="w-4 h-4 text-slate-900" />
            </div>
            <span className="font-black text-xl tracking-tighter text-slate-900">
              Smart<span className="text-indigo-600">Inbox</span>
            </span>
          </div>

          <div className="flex gap-8 text-xs font-bold uppercase tracking-widest text-slate-500">
            <a href="#" className="hover:text-slate-900 transition-colors">Documentation</a>
            <a href="#" className="hover:text-slate-900 transition-colors">API</a>
            <a href="#" className="hover:text-slate-900 transition-colors">Status</a>
          </div>

          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
            © 2026 Neural Core • All Signals Encrypted
          </p>
        </div>
      </footer>
    </div>
  );
};


