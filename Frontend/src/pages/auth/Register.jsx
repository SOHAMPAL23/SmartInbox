import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Mail, Lock, User, ShieldCheck, Zap, ChevronRight } from "lucide-react";
import { registerUser } from "../../api/authApi";
import { toast } from "react-hot-toast";

export const Register = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ 
    username: "", 
    email: "", 
    password: "" 
  });

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await registerUser(formData);
      toast.success("Identity established.");
      navigate("/login");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail) 
        ? detail.map(d => d.msg).join(", ") 
        : detail || "Registration failed.";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[420px] bg-white p-8 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50"
      >
        {/* Header */}
        <div className="flex flex-col items-center mb-10">
          <div className="p-3 bg-slate-900 rounded-2xl mb-4">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Create Identity</h1>
          <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mt-2">
            Join the SmartInbox Network
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-[10px] font-bold tracking-widest text-slate-500 uppercase ml-1">Username</label>
            <div className="relative group">
              <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
              <input 
                type="text" 
                required 
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full pl-12 pr-4 h-14 rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-indigo-500/50 transition-all"
                placeholder="agent_smartinbox"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-bold tracking-widest text-slate-500 uppercase ml-1">Email</label>
            <div className="relative group">
              <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
              <input 
                type="email" 
                required 
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full pl-12 pr-4 h-14 rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-indigo-500/50 transition-all"
                placeholder="agent@smartinbox.ai"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-bold tracking-widest text-slate-500 uppercase ml-1">Passphrase</label>
            <div className="relative group">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
              <input 
                type="password" 
                required 
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full pl-12 pr-4 h-14 rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-indigo-500/50 transition-all tracking-widest"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full h-14 mt-4 bg-slate-900 text-white rounded-2xl flex items-center justify-center gap-3 text-sm font-bold tracking-widest uppercase hover:bg-slate-800 transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                Initialize
                <ChevronRight size={18} />
              </>
            )}
          </button>
        </form>
        
        <div className="mt-8 text-center">
           <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
             Already authorized? {" "}
             <Link to="/login" className="text-indigo-600 hover:text-indigo-700 transition-colors ml-1">
               Return to Login
             </Link>
           </p>
        </div>

        <div className="mt-8 flex items-center justify-center gap-6 text-[10px] font-bold text-slate-300 uppercase tracking-widest border-t border-slate-100 pt-8">
          <span className="flex items-center gap-2"><Lock size={12} /> TLS 1.3</span>
          <span className="flex items-center gap-2"><ShieldCheck size={12} /> Verified</span>
        </div>
      </motion.div>
    </div>
  );
};

