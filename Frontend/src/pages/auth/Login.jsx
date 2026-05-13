import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Mail, Lock, ShieldCheck, Zap, Fingerprint, Activity, ChevronRight } from "lucide-react";
import { useStore } from "../../store/useStore";
import { toast } from "react-hot-toast";
import Logo from "../../components/ui/Logo";

const containerVariants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] } }
};

export const Login = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ email: "", password: "" });
  const login = useStore((state) => state.login);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const data = await login(formData.email, formData.password);
      toast.success("Identity verified.");
      const redirectPath = data.role === "admin" ? "/admin" : "/dashboard";
      navigate(redirectPath, { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail) 
        ? detail.map(d => d.msg).join(", ") 
        : detail || "Authentication failed.";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 font-sans relative overflow-hidden">
      {/* Soft Background Decorations */}
      <div className="absolute inset-0 pointer-events-none">
        <motion.div 
          animate={{ 
            opacity: [0.3, 0.5, 0.3],
            scale: [1, 1.2, 1]
          }}
          transition={{ duration: 10, repeat: Infinity }}
          className="absolute top-[-10%] right-[-5%] w-[800px] h-[800px] bg-indigo-100 rounded-full blur-[120px]" 
        />
        <motion.div 
          animate={{ 
            opacity: [0.2, 0.4, 0.2],
            scale: [1, 1.1, 1]
          }}
          transition={{ duration: 7, repeat: Infinity }}
          className="absolute bottom-[-15%] left-[-10%] w-[900px] h-[900px] bg-rose-50 rounded-full blur-[140px]" 
        />
      </div>

      <motion.div 
        variants={containerVariants}
        initial="initial"
        animate="animate"
        className="w-full max-w-[460px] bg-white p-12 rounded-[3.5rem] border border-slate-200 shadow-2xl shadow-indigo-100/50 relative z-10"
      >
        <motion.div variants={itemVariants} className="flex flex-col items-center mb-10">
          <Logo size="lg" />
          <p className="text-[10px] font-black tracking-[0.4em] text-slate-400 uppercase mt-4">
            Secure Authentication
          </p>
        </motion.div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <motion.div variants={itemVariants} className="space-y-3">
            <label className="text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase ml-2">Email Address</label>
            <div className="relative group">
              <Mail size={18} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
              <input 
                type="email" 
                required 
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full pl-14 pr-6 h-14 rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-indigo-600 focus:bg-white transition-all placeholder:text-slate-300"
                placeholder="agent@smartinbox.ai"
              />
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="space-y-3">
            <label className="text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase ml-2">Passphrase</label>
            <div className="relative group">
              <Lock size={18} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
              <input 
                type="password" 
                required 
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full pl-14 pr-6 h-14 rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-indigo-600 focus:bg-white transition-all tracking-widest placeholder:text-slate-300"
                placeholder="••••••••"
              />
            </div>
          </motion.div>

          <motion.button 
            variants={itemVariants}
            type="submit" 
            disabled={isLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full h-16 mt-4 bg-slate-900 text-white rounded-2xl flex items-center justify-center gap-4 text-[11px] font-black tracking-[0.2em] uppercase hover:bg-indigo-600 transition-all duration-300 disabled:opacity-50 shadow-xl shadow-slate-200"
          >
            {isLoading ? (
              <Activity className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Authorize Access
                <ChevronRight size={20} />
              </>
            )}
          </motion.button>
        </form>
        
        <motion.div variants={itemVariants} className="mt-10 space-y-4 text-center">
           <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
             New operative? {" "}
             <Link to="/register" className="text-indigo-600 hover:underline transition-colors ml-1">
               Initialize Account
             </Link>
           </p>
           <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
             Oversight? {" "}
             <Link to="/admin/login" className="text-indigo-600 hover:underline transition-colors ml-1">
               Admin Portal
             </Link>
           </p>
        </motion.div>

        <motion.div variants={itemVariants} className="mt-10 flex items-center justify-center gap-8 text-[9px] font-black text-slate-300 uppercase tracking-[0.3em] border-t border-slate-100 pt-10">
          <span className="flex items-center gap-2"><Lock size={12} /> TLS 1.3</span>
          <span className="flex items-center gap-2"><ShieldCheck size={12} /> Verified</span>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Login;


